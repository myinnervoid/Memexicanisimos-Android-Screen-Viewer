"""ScrcpyEngine · Adaptador de bajo nivel para scrcpy 4.1.

Contrato v1 congelado — ver ADR-010, ADR-011, ADR-012, ADR-014.
Calibrado contra scrcpy 4.1 (SDL 3.2.10, libavcodec 61).
"""
from __future__ import annotations

import logging
import re
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional

from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.errors import ErrorCode
from scrcpy_dock.domain.models import (
    ALLOWED_EXTRA_FLAGS,
    Codec,
    Device,
    DeviceCapabilities,
    SessionConfig,
)
from scrcpy_dock.domain.protocols import SessionProcess

log = logging.getLogger(__name__)

# Gobernanza de hardware · ADR-010
_KIRIN_PLATFORM_PREFIXES = ("kirin710", "kirin710f", "kirin710a", "hi6250")
_KIRIN_MAX_BITRATE = 8_000_000

# Codecs disponibles por versión de Android (mejor primero)
_CODECS_BY_SDK = (
    (34, (Codec.AV1, Codec.H265, Codec.H264)),
    (29, (Codec.H265, Codec.H264)),
    (21, (Codec.H264,)),
)

# Whitelist de flags extra (ADR-013 · Opción A estricta).
# Fuente única de verdad: scrcpy_dock.domain.models.ALLOWED_EXTRA_FLAGS.
# (Antes estaba duplicada aquí y en domain/models, con riesgo de divergir.)

# Timeouts adaptativos de detección de fallo (ADR-011)
_CODEC_FAILURE_TIMEOUT_SDK_LOW = 5.0    # android_sdk <= 29
_CODEC_FAILURE_TIMEOUT_SDK_HIGH = 2.5   # android_sdk >= 30

# Patrones de fallo de códec (case-insensitive)
_CODEC_FAILURE_PATTERNS = (
    "could not open encoder",
    "could not create default video encoder",
    "codec not supported",
    "mediacodec error",
    "codecexception",
)

# Patrones de desconexión (NO cuentan como fallo de códec)
_DISCONNECT_PATTERNS = (
    "device not found",
    "no such device",
    "adb: device",
)


class _PopenSessionProcess:
    """Envoltura mínima sobre subprocess.Popen cumpliendo el protocolo SessionProcess."""

    def __init__(self, proc: subprocess.Popen) -> None:
        self._proc = proc

    @property
    def pid(self) -> int:
        return self._proc.pid

    def poll(self) -> int | None:
        return self._proc.poll()

    def terminate(self) -> None:
        self._proc.terminate()

    def kill(self) -> None:
        self._proc.kill()

    def wait(self, timeout: float | None = None) -> int:
        return self._proc.wait(timeout=timeout)


class ScrcpyEngine:
    """Constructor de comandos y ciclo de vida de procesos scrcpy."""

    def __init__(
        self,
        scrcpy_binary: Path,
        server_jar: Path,
    ) -> None:
        self._scrcpy_binary = Path(scrcpy_binary)
        self._server_jar = Path(server_jar)

    # ─── TODO-5 · verify_server_version (ADR-014) ──────────────────
    def verify_server_version(self) -> OperationResult[str]:
        """Verifica que el binario de scrcpy responde y reporta su versión.

        En scrcpy 4.x el servidor va embebido en el paquete / binario.
        Se ejecuta `scrcpy --version` y se extrae el string de versión.
        """
        try:
            proc = subprocess.run(
                [str(self._scrcpy_binary), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except FileNotFoundError as e:
            return OperationResult.fail(ErrorCode.SCRCPY_NOT_FOUND, str(e))
        except subprocess.TimeoutExpired as e:
            return OperationResult.fail(
                ErrorCode.PROCESS_TIMEOUT, f"timeout al verificar versión: {e}",
            )

        if proc.returncode != 0:
            return OperationResult.fail(
                ErrorCode.SCRCPY_NOT_FOUND,
                proc.stderr or "scrcpy --version falló",
            )

        first_line = proc.stdout.splitlines()[0] if proc.stdout.splitlines() else ""
        ver_pattern = re.compile(r"(\d+\.\d+(?:\.\d+)?)")
        m = ver_pattern.search(first_line)
        if not m:
            return OperationResult.fail(
                ErrorCode.SCRCPY_SERVER_VERSION_MISMATCH,
                f"No se pudo extraer versión del binario: '{first_line}'",
            )
        version = m.group(1)
        return OperationResult.ok(version, f"Versión verificada: {version}")

    @staticmethod
    def _compare_versions(
        scrcpy_version_output: str,
        server_version_output: str,
    ) -> OperationResult[str]:
        """Compara las dos cadenas de versión extrayendo sus números de versión."""
        ver_pattern = re.compile(r"(\d+\.\d+(?:\.\d+)?)")
        m_client = ver_pattern.search(scrcpy_version_output)
        m_server = ver_pattern.search(server_version_output)

        if not m_client or not m_server:
            return OperationResult.fail(
                ErrorCode.SCRCPY_SERVER_VERSION_MISMATCH,
                f"No se pudo extraer versión: client='{scrcpy_version_output}', server='{server_version_output}'",
            )

        client_ver = m_client.group(1)
        server_ver = m_server.group(1)

        if client_ver != server_ver:
            return OperationResult.fail(
                ErrorCode.SCRCPY_SERVER_VERSION_MISMATCH,
                f"Discrepancia de versión: client={client_ver} != server={server_ver}",
            )

        return OperationResult.ok(client_ver, f"Versión verificada: {client_ver}")

    @staticmethod
    def _base_codecs_for_sdk(sdk: int) -> list[Codec]:
        """Selecciona los códecs soportados por nivel de SDK Android."""
        for sdk_threshold, codecs in _CODECS_BY_SDK:
            if sdk >= sdk_threshold:
                return list(codecs)
        return [Codec.H264]

    # ─── TODO-6 · get_compatible_codecs (ADR-010) ──────────────────
    def get_compatible_codecs(
        self,
        device: Device,
        caps: DeviceCapabilities,
    ) -> OperationResult[list[Codec]]:
        """Lista ordenada de códecs soportados, mejor primero."""
        base = self._base_codecs_for_sdk(device.android_sdk)
        if self._is_kirin(caps):
            base = [c for c in base if c == Codec.H264]
        return OperationResult.ok(base)

    # ─── TODO-7 · build_command (ADR-010 + Hallazgos 1-3) ──────────
    def build_command(
        self,
        config: SessionConfig,
        device: Device,
        caps: DeviceCapabilities,
    ) -> OperationResult[list[str]]:
        """Construye argv completo de scrcpy con gobernanza de hardware.

        Descompuesto en ensambladores por bloque (C5): cada uno tiene una sola
        responsabilidad y complejidad baja, de modo que tocar la gobernanza de
        audio no obligue a releer la de cámara — ni a arrastrar 60 caminos
        posibles en una única función.
        """
        is_camera = config.video_source == "camera" or "--video-source=camera" in config.extra_args
        is_audio_only = (not config.video_enabled) or ("--no-video" in config.extra_args)

        # Guardas de dominio: el primer bloque que detecta un problema corta.
        for fallo in (
            self._validate_source_guards(config, device),
            self._validate_extra_args(config),
            self._validate_stream_mode(config, device, is_camera, is_audio_only),
        ):
            if fallo is not None:
                return fallo

        effective_codec, effective_bitrate = self._governance_codec(caps, config)
        bitrate_str = self._format_bitrate(effective_bitrate)

        argv = self._base_argv(config, device, is_camera, is_audio_only)
        if config.otg_mode:
            argv.append("--otg")
        else:
            self._append_video_options(
                argv, config, is_camera, is_audio_only, effective_codec, bitrate_str,
            )
            self._append_audio_options(argv, config, device)
            self._append_fps_options(argv, config, is_audio_only)
            self._append_camera_options(argv, config, is_audio_only)

        self._append_hid_options(argv, config)
        self._append_display_options(argv, config)
        self._append_window_title(argv, config, device)
        self._append_extra_args(argv, config)

        return OperationResult.ok(argv, "comando construido exitosamente")

    # ─── Ensambladores de build_command (C5 · un bloque, una responsabilidad) ───

    def _base_argv(
        self, config: SessionConfig, device: Device,
        is_camera: bool, is_audio_only: bool,
    ) -> list[str]:
        argv = [str(self._scrcpy_binary)]
        if device.serial:
            argv.extend(["-s", device.serial])
        if not is_camera and not config.otg_mode and not is_audio_only:
            argv.append("--no-downsize-on-error")
        return argv

    def _append_video_options(
        self, argv: list[str], config: SessionConfig, is_camera: bool,
        is_audio_only: bool, codec: Codec, bitrate_str: str,
    ) -> None:
        if is_audio_only:
            # Solo audio: prohibir el flujo de vídeo y omitir los flags de vídeo.
            argv.extend(["--no-video", "--port", str(config.port)])
            return
        self._append_video_size(argv, config, is_camera)
        argv.extend([
            "--port", str(config.port),
            "--video-codec", codec.value,
            "--video-bit-rate", bitrate_str,
            "--video-source", config.video_source,
        ])

    def _append_video_size(
        self, argv: list[str], config: SessionConfig, is_camera: bool,
    ) -> None:
        """Traduce `resolution` a `--max-size`, con default seguro en cámara."""
        res_str = str(config.resolution or "").strip()
        if res_str and res_str.lower() != "native":
            if "x" in res_str:
                try:
                    argv.extend(["--max-size", str(max(int(x) for x in res_str.split("x")))])
                except ValueError:
                    argv.extend(["--max-size", res_str])
            else:
                argv.extend(["--max-size", res_str])
            return
        if is_camera and not self._has_size_flag(config):
            # En cámara, 'native' puede ser un sensor de 48MP/12MP (ej.
            # 4608x3456) que desborda el encoder de hardware: default a 1920.
            argv.extend(["--max-size", "1920"])

    @staticmethod
    def _has_size_flag(config: SessionConfig) -> bool:
        return any(
            t.startswith("--max-size") or t.startswith("--camera-size") or t == "-m"
            for t in config.extra_args
        )

    @staticmethod
    def _append_audio_options(
        argv: list[str], config: SessionConfig, device: Device,
    ) -> None:
        """Gobernanza de audio (espejo y solo-audio; OTG no tiene flujo)."""
        if device.android_sdk <= 29 or config.audio_source == "none":
            argv.append("--no-audio")
            return
        a_src = "playback" if config.audio_source == "system" else config.audio_source
        argv.extend(["--audio-source", a_src])

    @staticmethod
    def _append_fps_options(
        argv: list[str], config: SessionConfig, is_audio_only: bool,
    ) -> None:
        if is_audio_only or config.max_fps is None:
            return
        fps_flag = "--camera-fps" if config.video_source == "camera" else "--max-fps"
        argv.extend([fps_flag, f"{config.max_fps:g}"])

    @staticmethod
    def _append_camera_options(
        argv: list[str], config: SessionConfig, is_audio_only: bool,
    ) -> None:
        """camera_id precede a camera_facing; sin vídeo no aplican."""
        if is_audio_only or config.video_source != "camera":
            return
        if config.camera_id is not None:
            argv.extend(["--camera-id", str(config.camera_id)])
        elif config.camera_facing is not None:
            argv.extend(["--camera-facing", config.camera_facing])

    @staticmethod
    def _append_hid_options(argv: list[str], config: SessionConfig) -> None:
        if config.keyboard_mode:
            argv.extend(["--keyboard", config.keyboard_mode])
        if config.mouse_mode:
            argv.extend(["--mouse", config.mouse_mode])

    @staticmethod
    def _append_display_options(argv: list[str], config: SessionConfig) -> None:
        """Apagar pantalla del dispositivo y evitar suspensión (no en OTG)."""
        if config.otg_mode:
            return
        if config.turn_screen_off and "--turn-screen-off" not in config.extra_args:
            argv.append("--turn-screen-off")
        if config.stay_awake and "--stay-awake" not in config.extra_args:
            argv.append("--stay-awake")

    def _append_window_title(
        self, argv: list[str], config: SessionConfig, device: Device,
    ) -> None:
        if device.model and not self._has_title_flag(config):
            argv.extend(["--window-title", f"MASV: {device.model}"])

    @staticmethod
    def _has_title_flag(config: SessionConfig) -> bool:
        return any(
            token == "--window-title" or token.startswith("--window-title=")
            for token in config.extra_args
        )

    @staticmethod
    def _append_extra_args(argv: list[str], config: SessionConfig) -> None:
        """Inyecta extra_args ya validados, sin duplicar los del motor."""
        for token in config.extra_args:
            if token not in argv:
                argv.append(token)

    # ─── Guardas de dominio de build_command ──────────────────────────

    @staticmethod
    def _validate_source_guards(
        config: SessionConfig, device: Device,
    ) -> Optional[OperationResult[list[str]]]:
        if config.video_source == "camera" and device.android_sdk < 31:
            return OperationResult.fail(
                ErrorCode.INVALID_INPUT,
                f"Camera source requiere Android 12+ (SDK 31). Dispositivo: SDK {device.android_sdk}",
            )
        return None

    @staticmethod
    def _validate_extra_args(config: SessionConfig) -> Optional[OperationResult[list[str]]]:
        """Validación estricta de extra_args contra ALLOWED_EXTRA_FLAGS."""
        for token in config.extra_args:
            if token.split("=", 1)[0] not in ALLOWED_EXTRA_FLAGS:
                return OperationResult.fail(
                    ErrorCode.INVALID_EXTRA_ARGS,
                    f"Flag no permitido en extra_args: {token}",
                )
        return None

    @staticmethod
    def _validate_stream_mode(
        config: SessionConfig, device: Device,
        is_camera: bool, is_audio_only: bool,
    ) -> Optional[OperationResult[list[str]]]:
        """Coherencia del modo 'solo audio': sin vídeo debe quedar algún flujo."""
        if not is_audio_only:
            return None
        if is_camera:
            return OperationResult.fail(
                ErrorCode.INVALID_INPUT,
                "El modo solo audio (--no-video) es incompatible con video_source='camera'.",
            )
        if device.android_sdk <= 29:
            # La captura de audio de scrcpy requiere Android 11+ (SDK 30).
            # Sin vídeo y sin audio no habría nada que reproducir.
            return OperationResult.fail(
                ErrorCode.INVALID_INPUT,
                "El modo solo audio requiere Android 11+ (SDK 30). "
                f"Dispositivo: SDK {device.android_sdk}",
            )
        if config.audio_source == "none":
            return OperationResult.fail(
                ErrorCode.INVALID_INPUT,
                "Modo solo audio (--no-video) con audio_source='none' no reproduciría ningún flujo.",
            )
        return None

    # ─── Gobernanza de plataforma (Kirin) ─────────────────────────────

    @staticmethod
    def _is_kirin(caps: DeviceCapabilities) -> bool:
        platform_lower = (caps.platform or "").lower()
        manufacturer_lower = (caps.manufacturer or "").lower()
        return any(p in platform_lower for p in _KIRIN_PLATFORM_PREFIXES) or (
            manufacturer_lower == "huawei" and platform_lower.startswith("kirin")
        )

    def _governance_codec(
        self, caps: DeviceCapabilities, config: SessionConfig,
    ) -> tuple[Codec, int]:
        """Kirin: códec H.264 forzado y bitrate acotado a 8M."""
        if self._is_kirin(caps):
            return Codec.H264, min(config.bit_rate, _KIRIN_MAX_BITRATE)
        return config.codec, config.bit_rate

    @staticmethod
    def _format_bitrate(n: int) -> str:
        """Formatea bitrate en Mbps (ej. 8M) o kbps (ej. 4500k)."""
        if n % 1_000_000 == 0:
            return f"{n // 1_000_000}M"
        return f"{n // 1_000}k"

    # ─── TODO-8 · is_codec_failure (ADR-011) ───────────────────────
    def is_codec_failure(
        self,
        stderr_lines: list[str],
        elapsed_s: float,
        android_sdk: int,
    ) -> bool:
        """Heurística pura para detección temprana de fallo de códec."""
        # 1. Ventana de timeout adaptativa
        timeout = (
            _CODEC_FAILURE_TIMEOUT_SDK_LOW
            if android_sdk <= 29
            else _CODEC_FAILURE_TIMEOUT_SDK_HIGH
        )
        if elapsed_s > timeout:
            return False

        # 2. Solo evaluar las primeras 10 líneas
        window = stderr_lines[:10]
        blob = "\n".join(window).lower()

        # 3. Desconexión tiene precedencia y NO es fallo de códec
        if any(p in blob for p in _DISCONNECT_PATTERNS):
            return False

        # 4. Buscar patrones de fallo de códec
        return any(p in blob for p in _CODEC_FAILURE_PATTERNS)

    # ─── TODO-9 · launch (ADR-011 · smoke manual) ──────────────────
    def launch(
        self,
        config: SessionConfig,
        device: Device,
        caps: DeviceCapabilities,
        on_stderr_line: Callable[[str], None] | None = None,
        on_exit: Callable[[int], None] | None = None,
    ) -> OperationResult[SessionProcess]:
        """Lanza scrcpy y devuelve handle al proceso SessionProcess."""
        cmd_result = self.build_command(config, device, caps)
        if not cmd_result.success:
            return OperationResult.fail(
                cmd_result.error_code or ErrorCode.PROCESS_SPAWN_ERROR,
                cmd_result.message,
            )

        argv = cmd_result.data
        try:
            proc = subprocess.Popen(
                argv,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except (FileNotFoundError, OSError) as e:
            return OperationResult.fail(ErrorCode.PROCESS_SPAWN_ERROR, str(e))

        # Hilo centinela para capturar stderr si se solicita callback
        if on_stderr_line is not None and proc.stderr is not None:
            def _stderr_reader():
                for line in proc.stderr:
                    on_stderr_line(line.rstrip("\r\n"))
                if on_exit is not None:
                    proc.wait()
                    on_exit(proc.returncode)

            t = threading.Thread(target=_stderr_reader, daemon=True, name="scrcpy-stderr")
            t.start()
        elif on_exit is not None:
            def _exit_watcher():
                proc.wait()
                on_exit(proc.returncode)

            t = threading.Thread(target=_exit_watcher, daemon=True, name="scrcpy-exit")
            t.start()

        return OperationResult.ok(_PopenSessionProcess(proc), "proceso iniciado")
