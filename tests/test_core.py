import unittest
import os
import json
import tempfile
from scrcpy_dock.utils import parse_ip_port, _extract_serial, load_config, save_config
from scrcpy_dock.managers import ProfileManager, SessionManager
from scrcpy_dock.i18n import _translations, get_language, set_language

class TestUtils(unittest.TestCase):
    def test_parse_ip_port_default(self):
        ip, port = parse_ip_port("192.168.1.50")
        self.assertEqual(ip, "192.168.1.50")
        self.assertEqual(port, "5555")

    def test_parse_ip_port_custom(self):
        ip, port = parse_ip_port("192.168.1.50:5556")
        self.assertEqual(ip, "192.168.1.50")
        self.assertEqual(port, "5556")

    def test_parse_ip_port_empty(self):
        ip, port = parse_ip_port("   ")
        self.assertIsNone(ip)
        self.assertIsNone(port)

    def test_extract_serial_formatted(self):
        serial = _extract_serial("Pixel 6 Pro (1A2B3C4D)")
        self.assertEqual(serial, "1A2B3C4D")

    def test_extract_serial_raw(self):
        serial = _extract_serial("192.168.1.50:5555")
        self.assertEqual(serial, "192.168.1.50:5555")

    def test_atomic_save_config(self):
        test_cfg = {"test_key": "test_value_123"}
        save_config(test_cfg)
        loaded = load_config()
        self.assertEqual(loaded.get("test_key"), "test_value_123")

class TestProfileManager(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "profiles": {
                "Test Profile": {"bitrate": "8M", "max_size": "1080"}
            }
        }
        self.pm = ProfileManager(self.cfg)

    def test_get_profiles(self):
        profiles = self.pm.get_profiles()
        self.assertIn("Test Profile", profiles)

    def test_save_profile(self):
        saved = False
        def fake_save(cfg):
            nonlocal saved
            saved = True
        self.pm.save_profile("New Profile", {"bitrate": "16M"}, fake_save)
        self.assertTrue(saved)
        self.assertIn("New Profile", self.cfg["profiles"])

    def test_delete_profile(self):
        saved = False
        def fake_save(cfg):
            nonlocal saved
            saved = True
        self.pm.delete_profile("Test Profile", fake_save)
        self.assertTrue(saved)
        self.assertNotIn("Test Profile", self.cfg["profiles"])

class TestI18n(unittest.TestCase):
    def test_translation_dict_structure(self):
        self.assertIn("en", _translations)
        en_keys = _translations["en"]
        self.assertTrue(len(en_keys) > 0)
        set_language("en")
        self.assertEqual(get_language(), "en")
        set_language("es")
        self.assertEqual(get_language(), "es")

if __name__ == "__main__":
    unittest.main()
