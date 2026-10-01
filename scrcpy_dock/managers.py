import threading
import time
from dataclasses import dataclass, replace
from typing import List, Dict, Optional, Tuple, Callable, Any

from .contracts import OperationResult, DeviceEntry, SessionInfo
from .errors import ErrorCode
from .security import SecurityManager
from .domain.models import (
    Codec,
    Device,
    DeviceCapabilities,
    DeviceState,
    ConnectionType,
    SessionConfig,
)
from .domain.protocols import SessionProcess
from .core.adb_engine import AdbEngine
from .core.scrcpy_engine import ScrcpyEngine
from .core.port_allocator import PortAllocator
from .utils import find_portable_binaries


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

    def terminate(self):
        try:
            self.process.terminate()
            for _ in range(30):
                if self.process.poll() is not None:
                    break
                time.sleep(0.1)
            if self.process.poll() is None:
                self.process.kill()
        except Exception:
            pass
        self.active = False


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
            return {
                "model": caps.manufacturer,
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
            camera2_level="LIMITED",
            supported_codecs=(),
            sensor_orientation=0,
            sdk_int=sdk_int,
        )
        self._caps_cache[serial] = caps
        return caps

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

        # Actualizar modelos legacy para la UI de Tkinter
        found: List[Tuple[str, str, str]] = []
        entries: List[DeviceEntry] = []

        for d in devices:
            if d.state == DeviceState.DEVICE:
                found.append((d.serial, d.model, "ok"))
                entries.append(DeviceEntry(
                    serial=d.serial,
                    model=d.model,
                    state="device",
                    android_version=d.android_sdk,
                    connection_type=d.connection_type.value,
                ))
            elif d.state == DeviceState.UNAUTHORIZED:
                found.append((d.serial, "⚠  Acepta el permiso en el teléfono", "unauth"))
                entries.append(DeviceEntry(serial=d.serial, model="Android", state="unauthorized"))
            elif d.state == DeviceState.OFFLINE:
                found.append((d.serial, "🔌  Dispositivo desconectado (offline)", "offline"))
                entries.append(DeviceEntry(serial=d.serial, model="Android", state="offline"))
            else:
                st_str = d.state.value if hasattr(d.state, "value") else str(d.state)
                found.append((d.serial, f"[{st_str}]", "other"))
                entries.append(DeviceEntry(serial=d.serial, model="Android", state=st_str))

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
            self.log_q = None
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
            from pathlib import Path
            self._scrcpy = ScrcpyEngine(Path(scrcpy_bin or "/usr/local/bin/scrcpy"), Path("/usr/local/share/scrcpy/scrcpy-server"))

        self._allocator = allocator or PortAllocator(base=27183, max_offset=20)
        self._clock = clock or time.monotonic
        self.device_mgr = device_mgr

        self.sessions: Dict[str, Any] = {}
        self._session_info: Dict[str, _SessionInfo] = {}

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
                    camera2_level="LIMITED",
                    supported_codecs=(),
                    sensor_orientation=0,
                    sdk_int=device.android_sdk,
                )
            else:
                caps = DeviceCapabilities(
                    manufacturer="",
                    platform="",
                    camera2_level="LIMITED",
                    supported_codecs=(),
                    sensor_orientation=0,
                    sdk_int=device.android_sdk,
                )

        # 4. Lanzar con handshake y fallback
        return self._launch_with_fallback(device, caps, config)

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

        def _on_line(line: str):
            collected_stderr.append(line)

        def _on_exit(exit_code: int):
            pass

        t0 = self._clock()
        launch_res = self._scrcpy.launch(
            config,
            device,
            caps,
            on_stderr_line=_on_line,
            on_exit=_on_exit,
        )

        if not launch_res.success:
            self._allocator.release(config.port)
            return OperationResult.fail(launch_res.error_code or ErrorCode.PROCESS_SPAWN_ERROR, launch_res.message)

        proc = launch_res.data
        timeout = 5.0 if device.android_sdk <= 29 else 2.5

        # Handshake síncrono
        try:
            exit_code = proc.wait(timeout=timeout)
            is_dead = True
        except Exception:
            is_dead = False
            exit_code = None

        if not is_dead and proc.poll() is None:
            # Proceso sobrevivió el handshake
            info = _SessionInfo(port=config.port, process=proc)
            self._session_info[device.serial] = info
            self.sessions[device.serial] = ScrcpySession(
                serial=device.serial,
                profile_name=getattr(config, "video_source", "display"),
                proc=proc,
                assigned_port=config.port,
            )
            return OperationResult.ok(info)

        # Murió durante el handshake: evaluar fallback de códec
        elapsed = self._clock() - t0
        if (
            config.codec != Codec.H264
            and self._scrcpy.is_codec_failure(collected_stderr, elapsed, device.android_sdk)
        ):
            self._allocator.release(config.port)
            retry_port_res = self._allocator.acquire()
            if not retry_port_res.success:
                return OperationResult.fail(ErrorCode.PORT_POOL_EXHAUSTED, retry_port_res.message)
            retry_config = replace(config, port=retry_port_res.data, codec=Codec.H264)
            return self._launch_with_fallback(device, caps, retry_config)

        self._allocator.release(config.port)
        return OperationResult.fail(ErrorCode.PROCESS_CRASH, "handshake falló")

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
        """Adaptador legacy de compatibilidad hacia atrás para main.py y tests preexistentes."""
        if not serial:
            msg = "No se especificó ningún serial de dispositivo"
            if self.log_q:
                self.log_q.put(("ERROR", msg))
            return OperationResult.fail(ErrorCode.DEVICE_NOT_FOUND, msg)

        # Obtener o inferir Device
        dev_props = self.device_mgr.get_device_props(serial) if self.device_mgr else {}
        model = dev_props.get("model", "Android")
        android_v = dev_props.get("android_version", 11)
        if isinstance(android_v, str) and android_v.isdigit():
            android_v = int(android_v)

        device = Device(
            serial=serial,
            model=model,
            android_sdk=android_v if isinstance(android_v, int) else 11,
        )

        # Parsear perfil legacy
        v_codec_str = profile_data.get("video_codec", "h264")
        codec_enum = Codec.H264
        try:
            codec_enum = Codec(str(v_codec_str).lower())
        except Exception:
            pass

        bitrate_int = 8_000_000
        br_val = profile_data.get("bitrate")
        if br_val:
            try:
                if "M" in str(br_val):
                    bitrate_int = int(str(br_val).replace("M", "")) * 1_000_000
                elif "k" in str(br_val):
                    bitrate_int = int(str(br_val).replace("k", "")) * 1_000
                else:
                    bitrate_int = int(br_val)
            except Exception:
                pass

        v_source = profile_data.get("video_source", "display")
        camera_id = profile_data.get("camera_id")
        camera_facing = profile_data.get("camera_facing")
        otg_mode = bool(profile_data.get("otg_mode", False))
        # "Solo audio": aceptado como flag nativo o vía el campo `no_video` del asistente.
        video_enabled = not bool(profile_data.get("no_video", False))

        extra_args_tuple: tuple[str, ...] = ()
        extra_str = profile_data.get("extra_args", "")
        if extra_str:
            res_args = SecurityManager.validate_extra_arguments(extra_str)
            if not res_args.success:
                if self.log_q:
                    self.log_q.put(("ERROR", f"[{serial}] {res_args.message}"))
                return OperationResult.fail(res_args.error_code or ErrorCode.INVALID_INPUT, res_args.message)
            raw_tokens = list(res_args.data or [])
            filtered_tokens = []
            idx = 0
            while idx < len(raw_tokens):
                tok = raw_tokens[idx]
                if tok.startswith("--video-source="):
                    v_source = tok.split("=", 1)[1]
                elif tok == "--video-source" and idx + 1 < len(raw_tokens):
                    v_source = raw_tokens[idx + 1]
                    idx += 1
                elif tok == "--otg":
                    otg_mode = True
                elif tok == "--no-video":
                    # Promovido a atributo nativo: en la whitelist solo bloquea el vídeo.
                    video_enabled = False
                elif tok.startswith("--camera-id="):
                    camera_id = tok.split("=", 1)[1]
                elif tok == "--camera-id" and idx + 1 < len(raw_tokens):
                    camera_id = raw_tokens[idx + 1]
                    idx += 1
                elif tok.startswith("--camera-facing="):
                    camera_facing = tok.split("=", 1)[1]
                elif tok == "--camera-facing" and idx + 1 < len(raw_tokens):
                    camera_facing = raw_tokens[idx + 1]
                    idx += 1
                else:
                    filtered_tokens.append(tok)
                idx += 1
            extra_args_tuple = tuple(filtered_tokens)

        # Si v_source es "camera" y no hay camera_id ni camera_facing, default a "0" (trasera)
        if v_source == "camera" and not camera_id and not camera_facing:
            camera_id = "0"

        # Sincronizar puertos pre-ocupados en self.sessions (ej. inyectados en tests/UI)
        used_ports = {s.assigned_port for s in self.sessions.values() if hasattr(s, "assigned_port")}
        for p in used_ports:
            if hasattr(self._allocator, "_reserved"):
                self._allocator._reserved.add(p)

        port_res = self._allocator.acquire()
        if not port_res.success:
            return OperationResult.fail(ErrorCode.PORT_POOL_EXHAUSTED, port_res.message)
        assigned_port = port_res.data

        config = SessionConfig(
            port=assigned_port,
            codec=codec_enum,
            resolution=str(profile_data.get("max_size", "1080")),
            bit_rate=bitrate_int,
            video_source=v_source,
            max_fps=float(profile_data["max_fps"]) if profile_data.get("max_fps") else None,
            camera_facing=camera_facing,
            camera_id=str(camera_id) if camera_id is not None else None,
            audio_source=profile_data.get("audio_source", "playback"),
            turn_screen_off=bool(profile_data.get("turn_screen_off", True)),
            stay_awake=bool(profile_data.get("stay_awake", True)),
            extra_args=extra_args_tuple,
            otg_mode=otg_mode,
            video_enabled=video_enabled,
        )

        caps = DeviceCapabilities(
            manufacturer=dev_props.get("manufacturer", ""),
            platform=dev_props.get("platform", ""),
            camera2_level="LIMITED",
            supported_codecs=(),
            sensor_orientation=0,
            sdk_int=device.android_sdk,
        )

        launch_res = self._scrcpy.launch(config, device, caps)
        if not launch_res.success:
            self._allocator.release(assigned_port)
            return OperationResult.fail(launch_res.error_code or ErrorCode.PROCESS_SPAWN_ERROR, launch_res.message)

        proc = launch_res.data
        sess = ScrcpySession(
            serial, profile_name, proc, assigned_port=assigned_port,
            config=config, device=device, caps=caps,
        )
        self.sessions[serial] = sess

        if success_cb:
            try:
                success_cb()
            except Exception:
                pass

        if self.log_q:
            self.log_q.put(("INFO", f"[{serial}] Lanzado PID {proc.pid} en puerto {assigned_port} ({model})"))

        return OperationResult.ok(message=f"Sesión iniciada para {model} ({serial}) en puerto {assigned_port}")

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
