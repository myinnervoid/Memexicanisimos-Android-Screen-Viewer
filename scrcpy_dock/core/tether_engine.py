import os
import shutil
import sys
import subprocess
import logging

from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.errors import ErrorCode
from scrcpy_dock.utils import CONFIG_DIR

log = logging.getLogger(__name__)

class TetherEngine:
    """Core adapter for managing gnirehtet reverse tethering binary."""

    def __init__(self, binary_path: str | None = None):
        self._binary_path = binary_path or self._find_gnirehtet()

    def _find_gnirehtet(self) -> str | None:
        """Searches for gnirehtet binary in portable bin folders and system PATH."""
        search_paths = []

        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            search_paths.append(os.path.join(exe_dir, "bin"))
            search_paths.append(os.path.join(sys._MEIPASS, "bin"))
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            search_paths.append(os.path.join(base_path, "bin"))

        search_paths.append(os.path.join(CONFIG_DIR, "bin"))

        search_path_str = os.pathsep.join(search_paths)
        return shutil.which("gnirehtet", path=search_path_str) or shutil.which("gnirehtet")

    def start(self, serial: str) -> OperationResult[subprocess.Popen]:
        """Starts reverse tethering tunnel for a given device serial."""
        if not self._binary_path:
            return OperationResult.fail(ErrorCode.BINARY_NOT_FOUND, "gnirehtet binary not found.")

        try:
            # Note: gnirehtet run <serial> keeps process foreground.
            cmd = [self._binary_path, "run", serial]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            return OperationResult.ok(proc, f"gnirehtet started for {serial}")
        except Exception as e:
            log.exception(f"Failed to start gnirehtet for {serial}: {e}")
            return OperationResult.fail(ErrorCode.PROCESS_SPAWN_ERROR, str(e))

    def stop(self, serial: str) -> OperationResult[None]:
        """Stops the reverse tethering tunnel on the device."""
        if not self._binary_path:
            return OperationResult.fail(ErrorCode.BINARY_NOT_FOUND, "gnirehtet binary not found.")

        try:
            cmd = [self._binary_path, "stop", serial]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode != 0:
                log.warning(f"gnirehtet stop returned {res.returncode}: {res.stderr}")
                return OperationResult.fail(ErrorCode.UNKNOWN_ERROR, f"Stop failed: {res.stderr}")
            return OperationResult.ok(None, f"gnirehtet stopped for {serial}")
        except Exception as e:
            log.exception(f"Failed to execute gnirehtet stop for {serial}: {e}")
            return OperationResult.fail(ErrorCode.UNKNOWN_ERROR, str(e))
