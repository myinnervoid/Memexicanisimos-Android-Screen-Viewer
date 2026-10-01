"""StreamService · compilación de perfiles legacy y lanzamiento de sesiones scrcpy.

Extracción de `SessionManager.start_scene_legacy` (C1). El manager quedó como
fachada: orquesta sesiones y delega aquí la interpretación del perfil (que es
un problema de dominio distinto: traducir la forma "legacy" de un perfil —
dicts con strings sueltos — a los contratos tipados de `domain.models`).

Reglas que conserva la extracción (verificadas por
`tests/test_fase_c_regressions.py`):
  - Las banderas que el motor modela como atributo nativo (`--video-source`,
    `--camera-id`, `--camera-facing`, `--otg`, `--no-video`) se PROMUEVEN a
    atributos y NO viajan en `extra_args`.
  - Una bandera promovida sin valor se conserva como token (no se descarta en
    silencio): su ausencia es un error del perfil que el motor debe reportar.
  - Los puertos ya ocupados se reservan en el asignador antes de pedir uno.
  - Si el lanzamiento falla, el puerto se libera (no se filtra del pool).
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.domain.models import Codec, Device, DeviceCapabilities, SessionConfig
from scrcpy_dock.errors import ErrorCode
from scrcpy_dock.security import SecurityManager

_DEFAULT_BITRATE = 8_000_000
_DEFAULT_SDK = 11

# Banderas que el motor promueve a atributos nativos de SessionConfig.
_PROMOTED_FLAGS = {
    "--video-source": "video_source",
    "--camera-id": "camera_id",
    "--camera-facing": "camera_facing",
}


class StreamService:
    """Lanza sesiones scrcpy a partir de un perfil legacy.

    Recibe **proveedores** (callables sin argumentos), no valores: el motor, el
    asignador y el canal de logs pueden sustituirse después de construir el
    servicio — lo hacen los tests (`mgr._scrcpy = ...`) y la propia app al
    re-detectar los binarios. Capturarlos por valor rompía esa sustitución en
    silencio.
    """

    def __init__(
        self,
        scrcpy_provider: Callable[[], Any],
        allocator_provider: Callable[[], Any],
        log_q_provider: Optional[Callable[[], Any]] = None,
        sessions: Optional[dict] = None,
        session_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._get_scrcpy = scrcpy_provider
        self._get_allocator = allocator_provider
        self._get_log_q = log_q_provider or (lambda: None)
        self._sessions = sessions if sessions is not None else {}
        self._session_factory = session_factory

    # ─── API pública ───────────────────────────────────────────────────

    def start_legacy(
        self,
        serial: str,
        profile_name: str,
        profile_data: dict,
        device_mgr: Any = None,
        success_cb: Optional[Callable] = None,
    ) -> OperationResult[Any]:
        """Compila `profile_data` y lanza la sesión. Devuelve el OperationResult."""
        if not serial:
            return self._fail(
                ErrorCode.DEVICE_NOT_FOUND, "No se especificó ningún serial de dispositivo",
            )

        dev_props = device_mgr.get_device_props(serial) if device_mgr else {}
        device = self._build_device(serial, dev_props)

        compiled = self._compile_profile(profile_data)
        if not compiled.success:
            return self._fail(
                compiled.error_code or ErrorCode.INVALID_INPUT,
                compiled.message, serial=serial,
            )
        state = compiled.data or {}

        port_res = self._acquire_port()
        if not port_res.success:
            return port_res
        assigned_port = port_res.data
        assert assigned_port is not None, "el asignador garantiza puerto cuando success"

        config = self._build_config(profile_data, state, assigned_port)
        caps = self._build_caps(dev_props, device)

        launch_res = self._get_scrcpy().launch(config, device, caps)
        if not launch_res.success:
            self._get_allocator().release(assigned_port)
            return OperationResult.fail(
                launch_res.error_code or ErrorCode.PROCESS_SPAWN_ERROR, launch_res.message,
            )

        self._register(
            serial, profile_name, launch_res.data, assigned_port,
            config, device, caps, success_cb,
        )
        return OperationResult.ok(
            message=f"Sesión iniciada para {device.model} ({serial}) en puerto {assigned_port}",
        )

    # ─── Compilación del perfil ────────────────────────────────────────

    @staticmethod
    def _default_state(profile_data: dict) -> dict:
        return {
            "video_source": profile_data.get("video_source", "display"),
            "camera_id": profile_data.get("camera_id"),
            "camera_facing": profile_data.get("camera_facing"),
            "otg_mode": bool(profile_data.get("otg_mode", False)),
            # "Solo audio": flag nativo o el campo `no_video` del asistente.
            "video_enabled": not bool(profile_data.get("no_video", False)),
            "extra_args": (),
        }

    def _compile_profile(self, profile_data: dict) -> OperationResult[dict]:
        """Traduce el perfil legacy a un estado limpio (atributos + extra_args)."""
        state = self._default_state(profile_data)
        extra_str = profile_data.get("extra_args", "")
        if not extra_str:
            return OperationResult.ok(state)

        res_args = SecurityManager.validate_extra_arguments(extra_str)
        if not res_args.success:
            return OperationResult.fail(
                res_args.error_code or ErrorCode.INVALID_INPUT, res_args.message,
            )

        raw = list(res_args.data or [])
        filtered: list[str] = []
        idx = 0
        while idx < len(raw):
            idx = self._absorb_token(raw, idx, state, filtered)
        state["extra_args"] = tuple(filtered)
        return OperationResult.ok(state)

    @staticmethod
    def _absorb_token(raw: list[str], idx: int, state: dict, filtered: list) -> int:
        """Clasifica `raw[idx]`: lo promueve a atributo o lo conserva en el argv.

        Devuelve el índice del siguiente token a procesar.
        """
        tok = raw[idx]
        key, sep, value = tok.partition("=")
        promoted = _PROMOTED_FLAGS.get(key)
        if promoted is not None:
            if sep:
                state[promoted] = value
                return idx + 1
            if idx + 1 < len(raw):
                state[promoted] = raw[idx + 1]
                return idx + 2          # consume también el valor
            filtered.append(tok)        # bandera huérfana: que el motor la juzgue
            return idx + 1
        if tok == "--otg":
            state["otg_mode"] = True
            return idx + 1
        if tok == "--no-video":
            state["video_enabled"] = False
            return idx + 1
        filtered.append(tok)
        return idx + 1

    # ─── Construcción de contratos de dominio ──────────────────────────

    @staticmethod
    def _build_device(serial: str, dev_props: dict) -> Device:
        android_v = dev_props.get("android_version", _DEFAULT_SDK)
        if isinstance(android_v, str) and android_v.isdigit():
            android_v = int(android_v)
        return Device(
            serial=serial,
            model=dev_props.get("model", "Android"),
            android_sdk=android_v if isinstance(android_v, int) else _DEFAULT_SDK,
        )

    @staticmethod
    def _parse_codec(profile_data: dict) -> Codec:
        try:
            return Codec(str(profile_data.get("video_codec", "h264")).lower())
        except Exception:
            return Codec.H264

    @staticmethod
    def _parse_bitrate(profile_data: dict) -> int:
        br_val = profile_data.get("bitrate")
        if not br_val:
            return _DEFAULT_BITRATE
        raw = str(br_val)
        try:
            if "M" in raw:
                return int(raw.replace("M", "")) * 1_000_000
            if "k" in raw:
                return int(raw.replace("k", "")) * 1_000
            return int(br_val)
        except Exception:
            return _DEFAULT_BITRATE

    def _build_config(self, profile_data: dict, state: dict, port: int) -> SessionConfig:
        video_source = state.get("video_source", "display")
        camera_id = state.get("camera_id")
        camera_facing = state.get("camera_facing")
        # Cámara sin selección explícita → trasera (id 0).
        if video_source == "camera" and not camera_id and not camera_facing:
            camera_id = "0"

        return SessionConfig(
            port=port,
            codec=self._parse_codec(profile_data),
            resolution=str(profile_data.get("max_size", "1080")),
            bit_rate=self._parse_bitrate(profile_data),
            video_source=video_source,
            max_fps=float(profile_data["max_fps"]) if profile_data.get("max_fps") else None,
            camera_facing=camera_facing,
            camera_id=str(camera_id) if camera_id is not None else None,
            audio_source=profile_data.get("audio_source", "playback"),
            turn_screen_off=bool(profile_data.get("turn_screen_off", True)),
            stay_awake=bool(profile_data.get("stay_awake", True)),
            extra_args=tuple(state.get("extra_args", ())),
            otg_mode=bool(state.get("otg_mode", False)),
            video_enabled=bool(state.get("video_enabled", True)),
        )

    @staticmethod
    def _build_caps(dev_props: dict, device: Device) -> DeviceCapabilities:
        return DeviceCapabilities(
            manufacturer=dev_props.get("manufacturer", ""),
            platform=dev_props.get("platform", ""),
            model=dev_props.get("model", "") or device.model,
            camera2_level="LIMITED",
            supported_codecs=(),
            sensor_orientation=0,
            sdk_int=device.android_sdk,
        )

    # ─── Pool de puertos y registro de la sesión ───────────────────────

    def _acquire_port(self) -> OperationResult[int]:
        """Reserva los puertos ya ocupados y pide uno libre al asignador."""
        allocator = self._get_allocator()
        reserved = getattr(allocator, "_reserved", None)
        if reserved is not None:
            reserved.update(
                s.assigned_port for s in self._sessions.values()
                if hasattr(s, "assigned_port")
            )
        res = allocator.acquire()
        if not res.success:
            return OperationResult.fail(ErrorCode.PORT_POOL_EXHAUSTED, res.message)
        return res

    def _register(
        self, serial: str, profile_name: str, proc: Any, port: int,
        config: SessionConfig, device: Device, caps: DeviceCapabilities,
        success_cb: Optional[Callable] = None,
    ) -> None:
        session = self._session_factory(
            serial, profile_name, proc,
            assigned_port=port, config=config, device=device, caps=caps,
        ) if self._session_factory else proc
        self._sessions[serial] = session

        if success_cb:
            try:
                success_cb()
            except Exception:
                pass

        log_q = self._get_log_q()
        if log_q:
            log_q.put((
                "INFO",
                f"[{serial}] Lanzado PID {proc.pid} en puerto {port} ({device.model})",
            ))

    # ─── Utilidades ────────────────────────────────────────────────────

    def _fail(self, code: ErrorCode, message: str, serial: Optional[str] = None) -> OperationResult[Any]:
        log_q = self._get_log_q()
        if log_q:
            prefix = f"[{serial}] " if serial else ""
            log_q.put(("ERROR", f"{prefix}{message}"))
        return OperationResult.fail(code, message)
