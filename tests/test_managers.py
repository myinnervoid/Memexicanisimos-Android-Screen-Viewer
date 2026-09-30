import unittest
import queue
from scrcpy_dock.managers import ProfileManager, SessionManager, DeviceManager
from scrcpy_dock.security import SecurityManager
from scrcpy_dock.errors import ErrorCode

class TestManagersEvolution(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "profiles": {
                "Juego": {"bitrate": "16M", "max_fps": "60"}
            }
        }
        self.log_q = queue.Queue()
        self.pm = ProfileManager(self.cfg)
        self.sm = SessionManager(self.log_q)

    def test_profile_manager_empty_name_fails(self):
        res = self.pm.save_profile("", {"bitrate": "8M"}, None)
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.INVALID_INPUT)

    def test_profile_manager_delete_nonexistent_fails(self):
        res = self.pm.delete_profile("PerfilInexistente", None)
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.PROFILE_NOT_FOUND)

    def test_profile_manager_save_and_delete_success(self):
        res_save = self.pm.save_profile("NuevoPerfil", {"bitrate": "10M"}, None)
        self.assertTrue(res_save.success)
        self.assertIn("NuevoPerfil", self.pm.get_profiles())

        res_del = self.pm.delete_profile("NuevoPerfil", None)
        self.assertTrue(res_del.success)
        self.assertNotIn("NuevoPerfil", self.pm.get_profiles())

    def test_security_validate_extra_arguments_safe(self):
        res = SecurityManager.validate_extra_arguments("--always-on-top --fullscreen --max-size 1080")
        self.assertTrue(res.success)
        self.assertEqual(res.data, ["--always-on-top", "--fullscreen", "--max-size", "1080"])

    def test_security_validate_extra_arguments_empty(self):
        res = SecurityManager.validate_extra_arguments("   ")
        self.assertTrue(res.success)
        self.assertEqual(res.data, [])

    def test_security_validate_extra_arguments_dangerous_rejected(self):
        # Shell chaining and pipe injection attempts
        dangerous_inputs = [
            "--always-on-top; rm -rf /",
            "--fullscreen && echo hacked",
            "| cat /etc/passwd",
            "`whoami`",
            "$(cat /dev/urandom)",
            "> output.txt",
            "< input.txt"
        ]
        for dangerous in dangerous_inputs:
            res = SecurityManager.validate_extra_arguments(dangerous)
            self.assertFalse(res.success, f"Debería haber rechazado: {dangerous}")
            self.assertEqual(res.error_code, ErrorCode.UNSAFE_ARGUMENT_DETECTED)

    def test_session_manager_missing_serial_fails(self):
        res = self.sm.start_scene("", "Juego", {})
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.DEVICE_NOT_FOUND)

    def test_session_manager_stop_nonexistent_fails(self):
        res = self.sm.stop_session("DEV_NON_EXISTENT")
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.DEVICE_NOT_FOUND)

if __name__ == "__main__":
    unittest.main()
