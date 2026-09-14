"""AdbEngine · Adaptador de bajo nivel para ADB.

Contrato v1 congelado — ver ADR-006, ADR-007, ADR-008, ADR-009.
NO cambiar firmas sin reabrir el ADR.
"""
from __future__ import annotations
from pathlib import Path
from typing import Callable

from scrcpy_dock.contracts import OperationResult, ErrorCode
from scrcpy_dock.domain.models import Device
from scrcpy_dock.domain.protocols import TrackerHandle


class AdbEngine:
    """Wrapper robusto sobre el binario oficial `adb` de Platform-Tools.

    Responsabilidades:
      - Ciclo de vida del daemon (reutiliza 5037, fallback a 5038 — ADR-006).
      - Parseo tipado de `adb devices -l` (estados DEVICE/UNAUTHORIZED/OFFLINE).
      - Lectura de propiedades del dispositivo vía UNA sola invocación ADB (ADR-007).
      - Tracker reactivo `adb track-devices` con reconexión backoff (ADR-008).
      - Activación y reversión de `tcpip 5555` (ADR-009).

    NO responsabilidades:
      - Construir comandos de scrcpy.
      - Gestionar puertos TCP de sesión (eso es PortAllocator).
      - Tocar la UI.
    """

    def __init__(
        self,
        adb_binary: Path,
        preferred_socket_port: int = 5037,
        fallback_socket_port: int = 5038,
    ) -> None:
        """Guarda rutas. NO arranca el daemon aquí (lazy)."""
        raise NotImplementedError

    @property
    def effective_socket_port(self) -> int:
        """Puerto real del daemon tras `start_daemon()`. 0 si no ha arrancado."""
        raise NotImplementedError

    def start_daemon(self) -> OperationResult[int]:
        """Arranca/verifica el daemon.

        Contrato:
          - Si 5037 responde → devuelve OperationResult(success=True, data=5037).
          - Si 5037 falla DOS veces con 'cannot bind' → reintenta en 5038.
          - Si 5038 también falla → ErrorCode.ADB_DAEMON_DEAD.
          - Idempotente: llamarlo dos veces no reinicia el daemon.
        """
        raise NotImplementedError

    def list_devices(self) -> OperationResult[list[Device]]:
        """Ejecuta `adb devices -l` y devuelve lista tipada.

        Mapeo de estados:
          - 'device'      → DeviceState.DEVICE
          - 'unauthorized'→ DeviceState.UNAUTHORIZED
          - 'offline'     → DeviceState.OFFLINE
          - resto         → ignorar + log WARNING
        """
        raise NotImplementedError

    def get_properties(self, serial: str) -> OperationResult[dict[str, str]]:
        """Lee en UNA sola invocación ADB las props necesarias.

        Props mínimas requeridas:
          - ro.build.version.sdk
          - ro.build.version.release
          - ro.product.manufacturer
          - ro.product.model
          - ro.board.platform   (fallback: ro.hardware)

        Contrato duro: EXACTAMENTE 1 llamada a subprocess.run por invocación.
        """
        raise NotImplementedError

    def start_tcpip(self, serial: str, port: int = 5555) -> OperationResult[None]:
        """Ejecuta `adb -s <serial> tcpip <port>`.

        Contrato:
          - Marca `activated_by_masv[serial] = True` para permitir reversión.
          - Si el dispositivo ya estaba en tcpip ANTES de llamar → no-op exitoso.
        """
        raise NotImplementedError

    def revert_tcpip(self, serial: str) -> OperationResult[None]:
        """Revierte `tcpip` a USB SOLO si MASV lo activó (ADR-009).

        Si `activated_by_masv[serial]` es False → no-op exitoso.
        """
        raise NotImplementedError

    def connect_wifi(self, host: str, port: int = 5555) -> OperationResult[str]:
        """`adb connect host:port`. Devuelve el serial resultante."""
        raise NotImplementedError

    def disconnect_wifi(self, serial: str) -> OperationResult[None]:
        raise NotImplementedError

    def track_devices_async(
        self,
        on_change: Callable[[list[Device]], None],
        on_daemon_dead: Callable[[ErrorCode], None],
        max_reconnect_attempts: int = 5,
    ) -> OperationResult[TrackerHandle]:
        """Lanza `adb track-devices` en un hilo centinela.

        Contrato:
          - on_change se invoca con la lista tipada cada vez que cambia.
          - Si el daemon muere, reintenta con backoff [1,2,4,8,16]s.
          - Si agota max_reconnect_attempts → on_daemon_dead(ADB_DAEMON_DEAD).
        """
        raise NotImplementedError

    def stop_tracker(self) -> None:
        """Detiene el tracker si está vivo. Idempotente."""
        raise NotImplementedError
