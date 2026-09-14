"""Fakes para tests de integración de managers.

Implementan la misma API que AdbEngine/ScrcpyEngine/PortAllocator
pero sin tocar subprocess ni sockets.
"""
from __future__ import annotations

import subprocess
from typing import Callable, Optional
from unittest.mock import MagicMock

from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.errors import ErrorCode
from scrcpy_dock.domain.models import (
    Codec, Device, DeviceCapabilities, SessionConfig,
)


# ─── FakeClock · simula paso del tiempo ────────────────────────────

class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, dt: float) -> None:
        self._now += dt


# ─── FakeSessionProcess · cumple SessionProcess con semántica Popen ──

class FakeSessionProcess:
    def __init__(
        self,
        pid: int = 1234,
        exit_code: int | None = None,
        clock: FakeClock | None = None,
        advance_on_wait: float = 0.0,
    ) -> None:
        self._pid = pid
        self._exit_code = exit_code
        self._clock = clock
        self._advance_on_wait = advance_on_wait

    @property
    def pid(self) -> int:
        return self._pid

    def poll(self) -> int | None:
        return self._exit_code

    def terminate(self) -> None:
        self._exit_code = 0

    def kill(self) -> None:
        self._exit_code = -9

    def wait(self, timeout: float | None = None) -> int:
        if self._clock is not None and self._advance_on_wait > 0:
            self._clock.advance(self._advance_on_wait)

        if self._exit_code is None:
            if timeout is not None:
                raise subprocess.TimeoutExpired(cmd="fake-scrcpy", timeout=timeout)
            raise RuntimeError("FakeSessionProcess.wait() sin timeout sobre proceso vivo")
        return self._exit_code


# ─── FakeAdbEngine ─────────────────────────────────────────────────

class FakeAdbEngine:
    def __init__(self) -> None:
        self.list_devices_calls = 0
        self.get_properties_calls: list[str] = []
        self.tracker_started = False
        self.tracker_stopped = False
        self._devices_queue: list[list[Device]] = []
        self._properties: dict[str, dict[str, str]] = {}
        self._on_change: Callable | None = None
        self._on_dead: Callable | None = None

    def queue_devices(self, devices: list[Device]) -> None:
        self._devices_queue.append(devices)

    def set_properties(self, serial: str, props: dict[str, str]) -> None:
        self._properties[serial] = props

    def emit_device_change(self, devices: list[Device]) -> None:
        if self._on_change:
            self._on_change(devices)

    def emit_daemon_dead(self) -> None:
        if self._on_dead:
            self._on_dead(ErrorCode.ADB_DAEMON_DEAD)

    # API compatible con AdbEngine
    def list_devices(self) -> OperationResult[list[Device]]:
        self.list_devices_calls += 1
        if self._devices_queue:
            return OperationResult.ok(self._devices_queue.pop(0))
        return OperationResult.ok([])

    def get_properties(self, serial: str) -> OperationResult[dict[str, str]]:
        self.get_properties_calls.append(serial)
        if serial in self._properties:
            return OperationResult.ok(self._properties[serial])
        return OperationResult.fail(
            ErrorCode.DEVICE_NOT_FOUND, f"sin props para {serial}",
        )

    def track_devices_async(self, on_change, on_daemon_dead,
                            max_reconnect_attempts=5):
        self._on_change = on_change
        self._on_dead = on_daemon_dead
        self.tracker_started = True
        return OperationResult.ok(MagicMock())

    def stop_tracker(self) -> None:
        self.tracker_stopped = True
        self._on_change = None
        self._on_dead = None

    def start_daemon(self):
        return OperationResult.ok(5037)

    def start_tcpip(self, serial, port=5555):
        return OperationResult.ok(None)

    def revert_tcpip(self, serial):
        return OperationResult.ok(None)

    def connect_wifi(self, host, port=5555):
        return OperationResult.ok(f"{host}:{port}")

    def disconnect_wifi(self, serial):
        return OperationResult.ok(None)


# ─── FakeScrcpyEngine ──────────────────────────────────────────────

class _LaunchBehavior:
    def __init__(self, stderr_lines, exit_code, alive_after_handshake):
        self.stderr_lines = stderr_lines
        self.exit_code = exit_code
        self.alive_after_handshake = alive_after_handshake


class FakeScrcpyEngine:
    def __init__(self) -> None:
        self.build_commands: list[SessionConfig] = []
        self.launches: list[dict] = []
        self._behaviors: list[_LaunchBehavior] = []
        from scrcpy_dock.core.scrcpy_engine import ScrcpyEngine
        from pathlib import Path
        self._real_engine = ScrcpyEngine(
            Path("/usr/bin/scrcpy"), Path("/tmp/fake-server.jar"),
        )

    def queue_launch(
        self,
        stderr_lines: list[str] | None = None,
        exit_code: int | None = None,
        alive_after_handshake: bool = True,
    ) -> None:
        self._behaviors.append(_LaunchBehavior(
            stderr_lines or [], exit_code, alive_after_handshake,
        ))

    def build_command(self, config, device, caps):
        self.build_commands.append(config)
        return OperationResult.ok([
            "fake-scrcpy", "--port", str(config.port),
            "--video-codec", config.codec.value,
        ])

    def launch(self, config, device, caps,
               on_stderr_line=None, on_exit=None):
        behavior = self._behaviors.pop(0) if self._behaviors else _LaunchBehavior(
            [], None, True,
        )
        if on_stderr_line:
            for line in behavior.stderr_lines:
                on_stderr_line(line)

        poll_value = None if behavior.alive_after_handshake else behavior.exit_code
        proc = FakeSessionProcess(
            pid=1234 + len(self.launches),
            exit_code=poll_value,
        )

        if on_exit and not behavior.alive_after_handshake:
            on_exit(behavior.exit_code or 0)

        self.launches.append({
            "config": config,
            "process": proc,
            "stderr_lines": behavior.stderr_lines,
            "on_stderr_line": on_stderr_line,
            "on_exit": on_exit,
        })
        return OperationResult.ok(proc)

    def is_codec_failure(self, stderr_lines, elapsed_s, android_sdk):
        return self._real_engine.is_codec_failure(
            stderr_lines, elapsed_s, android_sdk,
        )

    def verify_server_version(self):
        return OperationResult.ok("4.1")
