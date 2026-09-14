"""Protocolos estructurales usados por los engines.

Estos Protocol viven en domain porque los servicios los consumen, pero
su implementación concreta vive en core/. El dominio nunca importa core/.
"""
from __future__ import annotations
from typing import Protocol, runtime_checkable


@runtime_checkable
class SessionProcess(Protocol):
    """Envoltura mínima sobre subprocess.Popen. Mockeable en tests."""

    @property
    def pid(self) -> int: ...

    def poll(self) -> int | None:
        """None si sigue vivo; exit code si terminó."""

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...


@runtime_checkable
class TrackerHandle(Protocol):
    """Handle opaco sobre el hilo centinela de `adb track-devices`."""

    def stop(self, timeout: float = 2.0) -> None: ...

    def is_alive(self) -> bool: ...
