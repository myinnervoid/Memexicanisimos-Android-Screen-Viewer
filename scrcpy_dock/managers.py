import time
import threading
from pathlib import Path
from dataclasses import dataclass, replace
from typing import List, Dict, Optional, Tuple, Callable, Any

from .contracts import OperationResult, DeviceEntry, SessionInfo
from .errors import ErrorCode
from .domain.models import (
    Codec,
    Device,
    DeviceCapabilities,
    DeviceState,
    SessionConfig,
)
from .domain.protocols import SessionProcess
from .core.adb_engine import AdbEngine
from .core.scrcpy_engine import ScrcpyEngine
from .core.port_allocator import PortAllocator
from .services.stream_service import StreamService
from .utils import find_portable_binaries


def _resolver_servidor_scrcpy() -> "Path":
    """Ruta del `scrcpy-server` si el sistema lo trae suelto; si no, la histórica (§3.18).

    scrcpy 4.x lleva el servidor **embebido** en el binario, así que este dato es
    informativo: el motor no lo usa (`verify_server_version` prueba el binario, ADR-014).
    Se busca en el layout gestionado (`~/.MASV/bin`, que mantiene `InstallerService`) y en
    las rutas de la distribución. Si no aparece, se devuelve la última ruta en lugar de
    `None` porque el parámetro del motor está congelado (ADR-007) y no acepta `None`.
    """
    from .services.installer_service import InstallerService

    candidatas = []
    try:
        candidatas.append(InstallerService().bin_dir / "scrcpy-server")
    except Exception:      # layout no resoluble: quedan las rutas del sistema
        pass
    candidatas += [
        Path("/usr/local/share/scrcpy/scrcpy-server"),
        Path("/usr/share/scrcpy/scrcpy-server"),
    ]
    for ruta in candidatas:
        if ruta.exists():
            return ruta
    return candidatas[-1]



@dataclass(frozen=True)
class _SessionInfo:
    """Información interna de sesión activa generada por SessionManager."""
    port: int
    process: SessionProcess


class ScrcpySession:
    """Envoltorio de sesión activa para compatibilidad con UI y observadores."""

    def __init__(
        self,
        serial: str,
        profile_name: str,
        proc: Any,
        assigned_port: int = 27183,
        config: Any = None,
        device: Any = None,
        caps: Any = None,
    ):
        self.serial = serial
        self.profile_name = profile_name
        self.process = proc
        self.pid = getattr(proc, "pid", 0)
        self.assigned_port = assigned_port
        self.active = True
        self.t0 = time.time()
        # Contexto preservado para poder reconstruir el argv ("Copiar comando scrcpy").
        self.config = config
        self.device = device
        self.caps = caps

    def uptime(self) -> str:
        s = int(time.time() - self.t0)
        return f"{s // 60:02d}:{s % 60:02d}"

    def to_session_info(self) -> SessionInfo:
        return SessionInfo(
            serial=self.serial,
            profile_name=self.profile_name,
            pid=self.pid,
            active=self.active,
            start_time=self.t0,
            uptime_str=self.uptime(),
        )

    def terminate(self, timeout: float = 3.0, block: bool = False):
        self.active = False

        def _reap(proc):
            try:
                proc.terminate()
                steps = max(1, int(timeout / 0.1))
                for _ in range(steps):
                    if proc.poll() is not None:
                        return
                    time.sleep(0.1)
                if proc.poll() is None:
                    proc.kill()
            except Exception:
                pass

        proc = self.process
        if block:
            _reap(proc)
        else:
            t = threading.Thread(target=_reap, args=(proc,), daemon=True)
            t.start()


class ProfileManager:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def get_profiles(self) -> dict:
        return self.cfg.get("profiles", {})

    def save_profile(self, name: str, data: dict, save_cb) -> OperationResult[dict]:
        if not name or not name.strip():
            return OperationResult.fail(ErrorCode.INVALID_INPUT, "El nombre del perfil no puede estar vacío")
        self.cfg.setdefault("profiles", {})[name] = data
        if save_cb:
            save_cb(self.cfg)
        return OperationResult.ok(data=data, message=f"Perfil '{name}' guardado correctamente")

    def delete_profile(self, name: str, save_cb) -> OperationResult[str]:
        if name in self.cfg.get("profiles", {}):
            del self.cfg["profiles"][name]
            if save_cb:
                save_cb(self.cfg)
            return OperationResult.ok(data=name, message=f"Perfil '{name}' eliminado")
        return OperationResult.fail(ErrorCode.PROFILE_NOT_FOUND, f"El perfil '{name}' no existe")


class DeviceManager:
    """Administrador de dispositivos basado en AdbEngine."""

    def __init__(self, adb_engine: Optional[AdbEngine] = None):
        if adb_engine is not None:
            self._adb = adb_engine
        else:
            adb_bin, _ = find_portable_binaries()
            self._adb = AdbEngine(adb_bin)

        self.devices: List[Tuple[str, str, str]] = []
        self.device_entries: List[DeviceEntry] = []
        self.device_props: Dict[str, dict] = {}
        self.refreshing = False

        self._caps_cache: Dict[str, DeviceCapabilities] = {}
        self._subscribers: List[Callable[[List[Device]], None]] = []
        self._tracking = False

    def get_device_props(self, serial: str) -> dict:
        """Retorna las propiedades de hardware cacheadas como dict para compatibilidad legacy."""
        if serial in self.device_props:
            return self.device_props[serial]
        caps = self.get_capabilities(serial)
        if caps:
            # P3.8: `model` debe ser el modelo real (ro.product.model / adb devices -l),
            # nunca el fabricante.
            model = caps.model or self.get_device_model(serial) or serial
            return {
                "model": model,
                "android_version": caps.sdk_int,
                "manufacturer": caps.manufacturer,
                "platform": caps.platform,
                "connection_type": "WIFI" if ":" in serial else "USB",
            }
        return {}

    def get_device_model(self, serial: str) -> str:
        """Devuelve el modelo real del dispositivo (ro.product.model) por serial.

        Prioriza `device_entries` (poblado desde `adb devices -l`), que es la
        única fuente fiable: `get_device_props()` no transporta el modelo
        (devuelve el fabricante). Devuelve "" si no se conoce.
        """
        for entry in self.device_entries:
            if entry.serial == serial and entry.model:
                return entry.model
        for s, model, state in self.devices:
            if s == serial and state == "ok" and model:
                return model
        return ""

    def get_capabilities(self, serial: str) -> Optional[DeviceCapabilities]:
        """Obtiene capacidades de hardware cacheadas resolviendo con get_properties una sola vez."""
        if serial in self._caps_cache:
            return self._caps_cache[serial]

        props_res = self._adb.get_properties(serial)
        if not props_res.success or not props_res.data:
            return None

        data = props_res.data
        sdk_int = 0
        sdk_str = data.get("ro.build.version.sdk", "")
        if sdk_str.isdigit():
            sdk_int = int(sdk_str)

        caps = DeviceCapabilities(
            manufacturer=data.get("ro.product.manufacturer", ""),
            platform=data.get("ro.board.platform", ""),
            model=data.get("ro.product.model", ""),
            camera2_level="LIMITED",
            supported_codecs=(),
            sensor_orientation=0,
            sdk_int=sdk_int,
        )
        self._caps_cache[serial] = caps
        return caps

    def _mapear_dispositivo_para_ui(self, d: Device) -> Tuple[Tuple[str, str, str], DeviceEntry]:
        """Mapea un Device de dominio a la tupla legacy de Tkinter y al DeviceEntry."""
        if d.state == DeviceState.DEVICE:
            tupla = (d.serial, d.model, "ok")
            conn_val = getattr(d.connection_type, "value", str(d.connection_type))
            entry = DeviceEntry(
                serial=d.serial,
                model=d.model,
                state="device",
                android_version=d.android_sdk,
                connection_type=conn_val,
            )
            return tupla, entry

        if d.state == DeviceState.UNAUTHORIZED:
            return (
                (d.serial, "⚠  Acepta el permiso en el teléfono", "unauth"),
                DeviceEntry(serial=d.serial, model="Android", state="unauthorized"),
            )

        if d.state == DeviceState.OFFLINE:
            return (
                (d.serial, "🔌  Dispositivo desconectado (offline)", "offline"),
                DeviceEntry(serial=d.serial, model="Android", state="offline"),
            )

        st_str = d.state.value if hasattr(d.state, "value") else str(d.state)
        return (
            (d.serial, f"[{st_str}]", "other"),
            DeviceEntry(serial=d.serial, model="Android", state=st_str),
        )

    def scan_devices(
        self,
        callback_update_ui: Optional[Callable] = None,
        log_cb: Optional[Callable] = None,
    ) -> OperationResult[List[Device]]:
        """Escanea dispositivos delegando exclusivamente en AdbEngine."""
        res = self._adb.list_devices()
        if not res.success:
            if log_cb:
                log_cb("ERROR", f"Escaneo ADB falló: {res.message}")
            if callback_update_ui:
                callback_update_ui([])
            return res

        devices = res.data or []
        found: List[Tuple[str, str, str]] = []
        entries: List[DeviceEntry] = []

        for d in devices:
            tupla, entry = self._mapear_dispositivo_para_ui(d)
            found.append(tupla)
            entries.append(entry)

        self.devices = found
        self.device_entries = entries

        if callback_update_ui:
            callback_update_ui(found)

        return OperationResult.ok(devices)

    def start_tracking(self) -> None:
        """Inicia el tracking reactivo asíncrono si no estaba corriendo."""
        if self._tracking:
            return

        def _on_change(devs: List[Device]):
            for sub in self._subscribers:
                try:
                    sub(devs)
                except Exception:
                    pass

        self._adb.track_devices_async(
            on_change=_on_change,
            on_daemon_dead=lambda err: None,
        )
        self._tracking = True

    def stop_tracking(self) -> None:
        """Detiene el tracker de forma idempotente."""
        if self._tracking:
            self._adb.stop_tracker()
            self._tracking = False

    def subscribe_devices(self, cb: Callable[[List[Device]], None]) -> None:
        self._subscribers.append(cb)


class SessionManager:
    """Administrador y orquestador de sesiones scrcpy sobre engines core."""

    def __init__(
        self,
        log_q_or_adb: Any = None,
        scrcpy_engine: Optional[ScrcpyEngine] = None,
        allocator: Optional[PortAllocator] = None,
        clock: Optional[Callable[[], float]] = None,
        device_mgr: Optional[DeviceManager] = None,
        adb_engine: Optional[AdbEngine] = None,
    ):
        if adb_engine is not None:
            self._adb = adb_engine
            # Un `log_q` explícito sigue siendo válido aunque se inyecte motor:
            # antes se descartaba en silencio y el panel de logs dejaba de
            # recibir los mensajes de sesión.
            self.log_q = log_q_or_adb if hasattr(log_q_or_adb, "put") else None
        elif isinstance(log_q_or_adb, AdbEngine):
            self._adb = log_q_or_adb
            self.log_q = None
        else:
            self.log_q = log_q_or_adb
            adb_bin, _ = find_portable_binaries()
            self._adb = AdbEngine(adb_bin)

        if scrcpy_engine is not None:
            self._scrcpy = scrcpy_engine
        else:
            _, scrcpy_bin = find_portable_binaries()
            self._scrcpy = ScrcpyEngine(
                Path(scrcpy_bin or "/usr/local/bin/scrcpy"),
                _resolver_servidor_scrcpy(),
            )

        self._allocator = allocator or PortAllocator(base=27183, max_offset=20)
        self._clock = clock or time.monotonic
        self.device_mgr = device_mgr

        self.sessions: Dict[str, Any] = {}
        self._session_info: Dict[str, _SessionInfo] = {}

        # C1: la compilación del perfil y el lanzamiento viven en un servicio;
        # este manager queda como fachada. Se comparten por referencia el pool
        # de puertos y el registro de sesiones (son la misma fuente de verdad).
        self._stream = StreamService(
            scrcpy_provider=lambda: self._scrcpy,
            allocator_provider=lambda: self._allocator,
            log_q_provider=lambda: self.log_q,
            sessions=self.sessions,
            session_factory=ScrcpySession,
        )

    def get_session(self, serial: str) -> Optional[Any]:
        return self.sessions.get(serial)

    def get_session_info(self, serial: str) -> Optional[SessionInfo]:
        sess = self.sessions.get(serial)
        if hasattr(sess, "to_session_info"):
            return sess.to_session_info()
        return None

    def build_command_for(self, serial: str) -> OperationResult[list[str]]:
        """Reconstruye el argv de scrcpy de una sesión activa.

        Usado por la UI para "Copiar comando scrcpy" sin acceder a los
        internals del motor. Requiere que la sesión conserve su contexto
        (`config`, `device`, `caps`), que se guarda al lanzarla.
        """
        sess = self.sessions.get(serial)
        if sess is None:
            return OperationResult.fail(
                ErrorCode.DEVICE_NOT_FOUND, f"No hay sesión activa para {serial}",
            )
        config = getattr(sess, "config", None)
        device = getattr(sess, "device", None)
        caps = getattr(sess, "caps", None)
        if config is None or device is None or caps is None:
            return OperationResult.fail(
                ErrorCode.INVALID_INPUT,
                "La sesión no conserva su configuración; no se puede reconstruir el comando.",
            )
        return self._scrcpy.build_command(config, device, caps)

    def start_scene(self, *args, **kwargs) -> OperationResult[Any]:
        """Punto de entrada: despacha entre nueva API hexagonal y API legacy."""
        if len(args) >= 2 and isinstance(args[0], Device):
            return self._start_scene_hexagonal(args[0], args[1])
        return self.start_scene_legacy(*args, **kwargs)

    def _start_scene_hexagonal(self, device: Device, profile: Any) -> OperationResult[_SessionInfo]:
        # 1. Adquirir puerto
        port_res = self._allocator.acquire()
        if not port_res.success:
            return OperationResult.fail(port_res.error_code or ErrorCode.PORT_POOL_EXHAUSTED, port_res.message)
        port = port_res.data

        # 2. Construir SessionConfig
        codec_val = getattr(profile, "codec", Codec.H264)
        if isinstance(codec_val, str):
            codec_val = Codec(codec_val.lower())

        config = SessionConfig(
            port=port,
            codec=codec_val,
            resolution=str(getattr(profile, "resolution", "1080")),
            bit_rate=int(getattr(profile, "bit_rate", 8_000_000)),
            video_source=str(getattr(profile, "video_source", "display")),
            max_fps=getattr(profile, "max_fps", None),
            camera_id=str(getattr(profile, "camera_id")) if getattr(profile, "camera_id", None) is not None else None,
            camera_facing=getattr(profile, "camera_facing", None),
            audio_source=getattr(profile, "audio_source", "playback"),
            turn_screen_off=bool(getattr(profile, "turn_screen_off", True)),
            stay_awake=bool(getattr(profile, "stay_awake", True)),
            extra_args=tuple(getattr(profile, "extra_args", ())),
            otg_mode=bool(getattr(profile, "otg_mode", False)),
            video_enabled=bool(getattr(profile, "video_enabled", True)),
        )

        # 3. Resolver DeviceCapabilities
        caps = None
        if self.device_mgr:
            caps = self.device_mgr.get_capabilities(device.serial)
        if caps is None:
            props_res = self._adb.get_properties(device.serial)
            if props_res.success and props_res.data:
                caps = DeviceCapabilities(
                    manufacturer=props_res.data.get("ro.product.manufacturer", ""),
                    platform=props_res.data.get("ro.board.platform", ""),
                    model=props_res.data.get("ro.product.model", "") or device.model,
                    camera2_level="LIMITED",
                    supported_codecs=(),
                    sensor_orientation=0,
                    sdk_int=device.android_sdk,
                )
            else:
                caps = DeviceCapabilities(
                    manufacturer="",
                    platform="",
                    model=device.model,
                    camera2_level="LIMITED",
                    supported_codecs=(),
                    sensor_orientation=0,
                    sdk_int=device.android_sdk,
                )

        # 4. Lanzar con handshake y fallback
        return self._launch_with_fallback(device, caps, config)

    @staticmethod
    def _verificar_handshake(proc: Any, timeout: float) -> bool:
        """Retorna True si el proceso sobrevivió el handshake inicial."""
        try:
            proc.wait(timeout=timeout)
            return False
        except Exception:
            return proc.poll() is None

    def _registrar_sesion_activa(
        self, device: Device, config: SessionConfig, proc: Any
    ) -> _SessionInfo:
        """Registra la sesión en las tablas hexagonal y legacy."""
        info = _SessionInfo(port=config.port, process=proc)
        self._session_info[device.serial] = info
        self.sessions[device.serial] = ScrcpySession(
            serial=device.serial,
            profile_name=getattr(config, "video_source", "display"),
            proc=proc,
            assigned_port=config.port,
        )
        return info

    def _reintentar_con_fallback(
        self,
        device: Device,
        caps: DeviceCapabilities,
        config: SessionConfig,
        collected_stderr: List[str],
        elapsed: float,
    ) -> OperationResult[_SessionInfo]:
        """Evalúa si el fallo fue de códec y reintenta con H.264."""
        self._allocator.release(config.port)
        if config.codec == Codec.H264:
            return OperationResult.fail(ErrorCode.PROCESS_CRASH, "handshake falló")

        if not self._scrcpy.is_codec_failure(collected_stderr, elapsed, device.android_sdk):
            return OperationResult.fail(ErrorCode.PROCESS_CRASH, "handshake falló")

        retry_port_res = self._allocator.acquire()
        if not retry_port_res.success:
            return OperationResult.fail(ErrorCode.PORT_POOL_EXHAUSTED, retry_port_res.message)

        retry_config = replace(config, port=retry_port_res.data, codec=Codec.H264)
        return self._launch_with_fallback(device, caps, retry_config)

    def _launch_with_fallback(
        self,
        device: Device,
        caps: DeviceCapabilities,
        config: SessionConfig,
    ) -> OperationResult[_SessionInfo]:
        cmd_res = self._scrcpy.build_command(config, device, caps)
        if not cmd_res.success:
            self._allocator.release(config.port)
            return OperationResult.fail(cmd_res.error_code or ErrorCode.INVALID_INPUT, cmd_res.message)

        collected_stderr: List[str] = []
        t0 = self._clock()
        launch_res = self._scrcpy.launch(
            config,
            device,
            caps,
            on_stderr_line=collected_stderr.append,
            on_exit=lambda exit_code: None,
        )

        if not launch_res.success:
            self._allocator.release(config.port)
            return OperationResult.fail(launch_res.error_code or ErrorCode.PROCESS_SPAWN_ERROR, launch_res.message)

        proc = launch_res.data
        timeout = 5.0 if device.android_sdk <= 29 else 2.5

        if self._verificar_handshake(proc, timeout):
            return OperationResult.ok(self._registrar_sesion_activa(device, config, proc))

        elapsed = self._clock() - t0
        return self._reintentar_con_fallback(device, caps, config, collected_stderr, elapsed)

    def stop_scene(self, serial: str) -> None:
        """Detiene la sesión hexagonal y libera el puerto."""
        sess_info = self._session_info.pop(serial, None)
        if sess_info is not None:
            try:
                sess_info.process.terminate()
            except Exception:
                pass
            self._allocator.release(sess_info.port)

        legacy_sess = self.sessions.pop(serial, None)
        if legacy_sess is not None and hasattr(legacy_sess, "terminate"):
            try:
                legacy_sess.terminate()
            except Exception:
                pass

    def start_scene_legacy(
        self,
        serial: str,
        profile_name: str,
        profile_data: dict,
        success_cb: Optional[Callable] = None,
    ) -> OperationResult[Any]:
        """Fachada legacy para main.py y tests.

        La compilación del perfil y el lanzamiento viven en `StreamService`
        (C1); este método sólo delega. La firma se conserva por compatibilidad.
        """
        return self._stream.start_legacy(
            serial=serial,
            profile_name=profile_name,
            profile_data=profile_data,
            device_mgr=self.device_mgr,
            success_cb=success_cb,
        )

    def stop_session(self, serial: str) -> OperationResult[str]:
        if serial in self.sessions:
            sess = self.sessions[serial]
            sess.terminate()
            del self.sessions[serial]
            if hasattr(sess, "assigned_port"):
                self._allocator.release(sess.assigned_port)
            return OperationResult.ok(data=serial, message=f"Sesión {serial} detenida")
        return OperationResult.fail(ErrorCode.DEVICE_NOT_FOUND, f"No hay sesión activa para {serial}")

    def stop_all(self) -> int:
        count = 0
        for serial in list(self.sessions.keys()):
            res = self.stop_session(serial)
            if res.success:
                count += 1
        return count
