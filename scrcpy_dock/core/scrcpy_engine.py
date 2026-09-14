"""ScrcpyEngine · Adaptador de bajo nivel para scrcpy.

Contrato v1 congelado — ver ADR-010, ADR-011, ADR-012, ADR-014.
"""
from __future__ import annotations
from pathlib import Path
from typing import Callable

from scrcpy_dock.contracts import OperationResult, ErrorCode
from scrcpy_dock.domain.models import (
    Device, DeviceCapabilities, SessionConfig, Codec,
)
from scrcpy_dock.domain.protocols import SessionProcess


class ScrcpyEngine:
    """Constructor de comandos y ciclo de vida de procesos scrcpy.

    Responsabilidades:
      - Verificar coherencia versión binario ↔ scrcpy-server.jar (ADR-014).
      - Resolver códecs compatibles por device+caps (ADR-010).
      - Construir la línea de comandos con gobernanza de hardware.
      - Lanzar el proceso con timeout adaptativo (ADR-011).
      - Detectar fallo de códec en stderr para fallback (ADR-011/012).

    NO responsabilidades:
      - Asignar puertos TCP (eso es PortAllocator).
      - Decidir política de fallback (eso es StreamService).
      - Tocar la UI.
    """

    def __init__(
        self,
        scrcpy_binary: Path,
        server_jar: Path,
    ) -> None:
        raise NotImplementedError

    def verify_server_version(self) -> OperationResult[str]:
        """Compara `scrcpy --version` con la versión del jar.

        Contrato:
          - Coinciden → OperationResult(success=True, data=version_str).
          - Discrepan → success=False, error=SCRCPY_SERVER_VERSION_MISMATCH.
          - Sin SHA-256 (ADR-014, uso no corporativo).
        """
        raise NotImplementedError

    def _compare_versions(self, client_ver: str, server_ver: str) -> OperationResult[str]:
        """Compara versiones textuales de cliente y servidor scrcpy.

        Contrato:
          - Coinciden → OperationResult.ok(data=version_extraída).
          - Discrepan → OperationResult.fail(ErrorCode.SCRCPY_SERVER_VERSION_MISMATCH).
        """
        raise NotImplementedError

    def get_compatible_codecs(
        self,
        device: Device,
        caps: DeviceCapabilities,
    ) -> OperationResult[list[Codec]]:
        """Lista ordenada de códecs soportados, mejor primero.

        Matriz base (por android_sdk):
          - SDK 21-28  → [H264]
          - SDK 29-33  → [H265, H264]
          - SDK 34+    → [AV1, H265, H264]

        Override por chipset (ADR-010 + calibración Kirin 710):
          - Huawei Kirin 710/710F/710A → filtrar H265 (encoder HW inestable).
            Resultado en Huawei Y9 (SDK 29): [H264] solamente.
        """
        raise NotImplementedError

    def build_command(
        self,
        config: SessionConfig,
        device: Device,
        caps: DeviceCapabilities,
    ) -> OperationResult[list[str]]:
        """Construye argv completo de scrcpy.

        Gobernanza obligatoria:
          1. Si device.android_sdk <= 29 → inyectar --no-audio y omitir --audio-source.
          2. Si manufacturer es HUAWEI y platform empieza con 'kirin7' →
             forzar códec=H264 y bitrate = min(config.bitrate, 8_000_000).
          3. Nunca inflar bitrate elegido por usuario:
             effective = min(user_bitrate, cap_por_chipset).
          4. Puerto de scrcpy-server → usar config.port asignado por PortAllocator.
          5. Whitelist A para extra_args. Si aparece flag fuera de whitelist -> INVALID_EXTRA_ARGS.
        """
        raise NotImplementedError

    def launch(
        self,
        config: SessionConfig,
        device: Device,
        caps: DeviceCapabilities,
        on_stderr_line: Callable[[str], None] | None = None,
        on_exit: Callable[[int], None] | None = None,
    ) -> OperationResult[SessionProcess]:
        """Lanza scrcpy y devuelve handle al proceso.

        Timeout adaptativo para detección temprana de fallo (ADR-011):
          - android_sdk <= 29 → 5.0 s
          - android_sdk >= 30 → 2.5 s

        El timeout NO mata el proceso; solo define la ventana en que
        `is_codec_failure()` puede declarar fallo temprano.
        """
        raise NotImplementedError

    def is_codec_failure(
        self,
        stderr_lines: list[str],
        elapsed_s: float,
        android_sdk: int,
    ) -> bool:
        """Heurística pura — sin side effects.

        Contrato:
          - Ventana: solo se evalúan las primeras 10 líneas de stderr.
          - Timeout de fallo: 5.0 s si sdk<=29, 2.5 s si sdk>=30.
          - Patrones de fallo de códec (case-insensitive):
              'could not open encoder'
              'codec not supported'
              'mediacodec error'
          - Patrones de desconexión (NO cuentan como fallo de códec):
              'device not found', 'no such device', 'adb: device'
          - Devolver True SOLO si hay patrón de códec Y elapsed_s <= timeout.
        """
        raise NotImplementedError
