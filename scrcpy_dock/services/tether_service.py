import threading
import logging
from typing import Dict, Optional, Any

from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.errors import ErrorCode
from scrcpy_dock.domain.protocols import SessionProcess

log = logging.getLogger(__name__)

class TetherService:
    """Service to manage reverse tethering sessions lifecycle per device."""

    def __init__(self, engine: Any = None):
        self._engine = engine
        self._lock = threading.Lock()
        self._sessions: Dict[str, SessionProcess] = {}

    def start_tethering(self, serial: str) -> OperationResult[None]:
        """Starts tethering for the specified device."""
        with self._lock:
            if serial in self._sessions:
                proc = self._sessions[serial]
                if proc.poll() is None:
                    # Process is still running
                    return OperationResult.ok(None, f"Tethering already active for {serial}")
                else:
                    # Stale process, remove it
                    del self._sessions[serial]

            res = self._engine.start(serial)
            if not res.success or not res.data:
                return OperationResult.fail(res.error_code or ErrorCode.UNKNOWN_ERROR, res.message)

            self._sessions[serial] = res.data
            return OperationResult.ok(None, f"Tethering session started for {serial}")

    def stop_tethering(self, serial: str) -> OperationResult[None]:
        """Stops the tethering session for the specified device."""
        with self._lock:
            proc = self._sessions.pop(serial, None)
            if proc:
                try:
                    proc.terminate()
                    proc.wait(timeout=2.0)
                except Exception as e:
                    # Ignore wait timeout or errors inside the service boundary
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    log.warning(f"Error terminating gnirehtet process for {serial}: {e}")

            # Send the stop command to the device to clean up the Android side tunnel
            res = self._engine.stop(serial)
            if not res.success:
                log.warning(f"Engine stop command failed for {serial}: {res.message}")
                # We still return OK because the local process is dead and we did our best
            return OperationResult.ok(None, f"Tethering stopped for {serial}")

    def is_tethering_active(self, serial: str) -> bool:
        """Checks if a tethering session is actively running for the device."""
        with self._lock:
            proc = self._sessions.get(serial)
            if proc and proc.poll() is None:
                return True
            return False
