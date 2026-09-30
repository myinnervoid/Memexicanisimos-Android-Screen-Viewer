import unittest
from unittest.mock import patch, MagicMock
import subprocess
from scrcpy_dock.core.tether_engine import TetherEngine
from scrcpy_dock.services.tether_service import TetherService
from scrcpy_dock.errors import ErrorCode

class TestTetherEngine(unittest.TestCase):
    @patch("scrcpy_dock.core.tether_engine.shutil.which")
    def test_find_gnirehtet_found(self, mock_which):
        mock_which.return_value = "/usr/local/bin/gnirehtet"
        engine = TetherEngine()
        self.assertEqual(engine._binary_path, "/usr/local/bin/gnirehtet")

    @patch("scrcpy_dock.core.tether_engine.shutil.which")
    def test_find_gnirehtet_not_found(self, mock_which):
        mock_which.return_value = None
        engine = TetherEngine()
        self.assertIsNone(engine._binary_path)

    @patch("scrcpy_dock.core.tether_engine.subprocess.Popen")
    def test_start_success(self, mock_popen):
        engine = TetherEngine(binary_path="/mock/gnirehtet")
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        res = engine.start("12345")
        self.assertTrue(res.success)
        self.assertEqual(res.data, mock_proc)
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        self.assertEqual(args, ["/mock/gnirehtet", "run", "12345"])

    def test_start_no_binary(self):
        engine = TetherEngine(binary_path=None)
        res = engine.start("12345")
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.BINARY_NOT_FOUND)

    @patch("scrcpy_dock.core.tether_engine.subprocess.run")
    def test_stop_success(self, mock_run):
        engine = TetherEngine(binary_path="/mock/gnirehtet")
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_run.return_value = mock_res

        res = engine.stop("12345")
        self.assertTrue(res.success)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["/mock/gnirehtet", "stop", "12345"])

    def test_stop_no_binary(self):
        engine = TetherEngine(binary_path=None)
        res = engine.stop("12345")
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.BINARY_NOT_FOUND)

class TestTetherService(unittest.TestCase):
    def setUp(self):
        self.mock_engine = MagicMock()
        self.service = TetherService(engine=self.mock_engine)

    def test_start_tethering_new(self):
        mock_res = MagicMock()
        mock_res.success = True
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_res.data = mock_proc
        self.mock_engine.start.return_value = mock_res

        res = self.service.start_tethering("dev1")
        self.assertTrue(res.success)
        self.mock_engine.start.assert_called_once_with("dev1")
        self.assertIn("dev1", self.service._sessions)
        self.assertTrue(self.service.is_tethering_active("dev1"))

    def test_start_tethering_already_active(self):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.poll.return_value = None
        self.service._sessions["dev1"] = mock_proc

        res = self.service.start_tethering("dev1")
        self.assertTrue(res.success)
        self.mock_engine.start.assert_not_called()
        self.assertEqual(res.message, "Tethering already active for dev1")

    def test_stop_tethering_active(self):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        self.service._sessions["dev1"] = mock_proc

        mock_stop_res = MagicMock()
        mock_stop_res.success = True
        self.mock_engine.stop.return_value = mock_stop_res

        res = self.service.stop_tethering("dev1")
        self.assertTrue(res.success)

        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once()
        self.mock_engine.stop.assert_called_once_with("dev1")
        self.assertNotIn("dev1", self.service._sessions)
        self.assertFalse(self.service.is_tethering_active("dev1"))

if __name__ == "__main__":
    unittest.main()
