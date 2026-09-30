import unittest
import os
import json
import tempfile
from scrcpy_dock.security import SecurityManager
from scrcpy_dock.utils import DEFAULT_CONFIG, load_config, save_config

class TestSecurityManager(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "security": {
                "safe_mode_enabled": True,
                "auto_lockdown_on_exit": True,
                "trusted_devices": {
                    "DEV12345": {
                        "alias": "Mi Galaxy Personal",
                        "model": "Galaxy S23",
                        "serial": "DEV12345",
                        "is_trusted": True
                    }
                },
                "blocked_ips": []
            }
        }
        self.sec = SecurityManager(self.cfg)

    def test_is_private_ip_valid(self):
        # Class A, B, C RFC 1918 + Loopback + Link-local
        self.assertTrue(SecurityManager.is_private_ip("192.168.1.100"))
        self.assertTrue(SecurityManager.is_private_ip("10.0.0.15"))
        self.assertTrue(SecurityManager.is_private_ip("172.16.0.5"))
        self.assertTrue(SecurityManager.is_private_ip("127.0.0.1"))
        self.assertTrue(SecurityManager.is_private_ip("169.254.1.1"))

    def test_is_private_ip_public_rejected(self):
        # Public internet IPs should return False
        self.assertFalse(SecurityManager.is_private_ip("8.8.8.8"))
        self.assertFalse(SecurityManager.is_private_ip("1.1.1.1"))
        self.assertFalse(SecurityManager.is_private_ip("142.250.190.46"))
        self.assertFalse(SecurityManager.is_private_ip("not_an_ip"))
        self.assertFalse(SecurityManager.is_private_ip(""))

    def test_parse_pair_ip_port_code_valid(self):
        result = SecurityManager.parse_pair_ip_port_code("192.168.1.50:38291", "123456")
        self.assertIsNotNone(result)
        ip, port, code = result
        self.assertEqual(ip, "192.168.1.50")
        self.assertEqual(port, "38291")
        self.assertEqual(code, "123456")

    def test_parse_pair_ip_port_code_invalid(self):
        # Invalid code (not 6 digits)
        self.assertIsNone(SecurityManager.parse_pair_ip_port_code("192.168.1.50:38291", "12345"))
        self.assertIsNone(SecurityManager.parse_pair_ip_port_code("192.168.1.50:38291", "abcdef"))
        # Invalid port
        self.assertIsNone(SecurityManager.parse_pair_ip_port_code("192.168.1.50:99999", "123456"))
        # Missing port
        self.assertIsNone(SecurityManager.parse_pair_ip_port_code("192.168.1.50", "123456"))
        # Empty inputs
        self.assertIsNone(SecurityManager.parse_pair_ip_port_code("", ""))

    def test_sanitize_text_input(self):
        # Remove control characters, newlines, tabs
        raw = "Hello\nWorld\r\t\x00\x08Test'Quote"
        cleaned = SecurityManager.sanitize_text_input(raw)
        self.assertNotIn("\n", cleaned)
        self.assertNotIn("\r", cleaned)
        self.assertNotIn("\t", cleaned)
        self.assertNotIn("\x00", cleaned)
        self.assertEqual(cleaned, "Hello World  Test'Quote")

    def test_trusted_device_lifecycle(self):
        # Initial check
        self.assertTrue(self.sec.is_trusted_device("DEV12345"))
        self.assertFalse(self.sec.is_trusted_device("UNKNOWN999"))

        # Trust a new device
        saved = False
        def fake_save(cfg):
            nonlocal saved
            saved = True

        self.sec.trust_device("NEWDEV001", "Pixel 7", "Mi Pixel", fake_save)
        self.assertTrue(saved)
        self.assertTrue(self.sec.is_trusted_device("NEWDEV001"))
        self.assertEqual(self.sec.get_device_alias("NEWDEV001"), "Mi Pixel")

        # Untrust device
        self.sec.untrust_device("NEWDEV001", fake_save)
        self.assertFalse(self.sec.is_trusted_device("NEWDEV001"))

        # Remove from vault completely
        self.sec.remove_device_from_vault("NEWDEV001", fake_save)
        self.assertNotIn("NEWDEV001", self.sec.get_trusted_devices())

    def test_safe_mode_toggle(self):
        saved = False
        def fake_save(cfg):
            nonlocal saved
            saved = True

        self.assertTrue(self.sec.is_safe_mode_enabled)
        self.sec.set_safe_mode(False, fake_save)
        self.assertFalse(self.sec.is_safe_mode_enabled)
        self.assertTrue(saved)

if __name__ == "__main__":
    unittest.main()
