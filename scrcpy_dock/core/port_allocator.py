"""PortAllocator · Asignación determinista de puertos scrcpy.

Contrato v1 — ver ADR-029 y Paso 1 del roadmap.
"""
from __future__ import annotations
import socket
import threading
from scrcpy_dock.contracts import OperationResult, ErrorCode


class PortAllocator:
    """Pool incremental thread-safe para el flag --port de scrcpy.

    Contrato:
      - Base 27183, incremento +1 por sesión activa.
      - Saltar puertos en estado LISTEN en localhost (EADDRINUSE).
      - Liberar puerto al terminar sesión (release).
      - Si se agota el rango [base, base+max_offset] → PORT_POOL_EXHAUSTED.

    Nota de concurrencia:
      El chequeo de socket mediante bind() es un test efímero (best-effort,
      no atómico) para evitar colisiones con procesos externos en loopback.
    """

    def __init__(self, base: int = 27183, max_offset: int = 20) -> None:
        self._base = base
        self._max_offset = max_offset
        self._reserved: set[int] = set()
        self._lock = threading.Lock()

    def acquire(self) -> OperationResult[int]:
        """Devuelve el primer puerto libre. Marca como reservado."""
        with self._lock:
            for offset in range(self._max_offset + 1):
                candidate = self._base + offset
                if candidate in self._reserved:
                    continue
                if not self._is_system_port_available(candidate):
                    continue

                self._reserved.add(candidate)
                return OperationResult.ok(candidate)

            return OperationResult.fail(
                ErrorCode.PORT_POOL_EXHAUSTED,
                f"No available ports in pool [{self._base}..{self._base + self._max_offset}]",
            )

    def release(self, port: int) -> None:
        """Libera el puerto. Idempotente (no error si no estaba reservado)."""
        with self._lock:
            self._reserved.discard(port)

    def reserved(self) -> frozenset[int]:
        """Snapshot de puertos actualmente reservados."""
        with self._lock:
            return frozenset(self._reserved)

    @staticmethod
    def _is_system_port_available(port: int) -> bool:
        """Verifica disponibilidad real del puerto en loopback sin SO_REUSEADDR."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", port))
                return True
        except OSError:
            return False
