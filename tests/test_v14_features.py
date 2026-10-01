import unittest
from unittest.mock import MagicMock
import tkinter as tk

from scrcpy_dock.i18n import _, set_language, get_language
from scrcpy_dock.context import AppContext
from scrcpy_dock.ui_widgets import AccordionItem, ProfileWizard


class TestV14Features(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception:
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        if cls.root:
            try:
                cls.root.destroy()
            except Exception:
                pass

    def test_i18n_v14_keys_available(self):
        set_language("en")
        self.assertEqual(get_language(), "en")
        self.assertEqual(_("Cambiar Idioma"), "Change Language")
        self.assertEqual(_("🛡️ Confiar y Recordar"), "🛡️ Trust and Remember")
        self.assertEqual(_("⌨️  Modo OTG"), "⌨️  OTG Mode")
        self.assertEqual(_("🌐 Compartir Internet (Reverse Tethering)"), "🌐 Share Internet (Reverse Tethering)")
        self.assertEqual(_("ℹ️ Acerca de MASV v1.4"), "ℹ️ About MASV v1.4")
        
        # Test Spanish fallback
        set_language("es")
        self.assertEqual(get_language(), "es")
        self.assertEqual(_("Cambiar Idioma"), "Cambiar Idioma")
        self.assertEqual(_("🛡️ Confiar y Recordar"), "🛡️ Confiar y Recordar")

    def test_app_context_tether_service(self):
        if not self.root:
            self.skipTest("Tkinter display not available")
        # AppContext llama a load_config()/save_config(): aislar del HOME real.
        import os
        import tempfile
        from unittest.mock import patch
        import scrcpy_dock.utils as utils
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(utils, "CONFIG_FILE", os.path.join(tmp, "config.json")), \
                 patch.object(utils, "LOG_FILE", os.path.join(tmp, "masv.log")), \
                 patch.object(utils, "CONFIG_DIR", tmp):
                ctx = AppContext(self.root)
        self.assertIsNotNone(ctx.tether_engine)
        self.assertIsNotNone(ctx.tether_service)

    def test_otg_preset_in_profile_wizard(self):
        self.assertIn("⌨️ Modo OTG (Teclado y Ratón USB)", ProfileWizard.PRESETS)
        otg_data = ProfileWizard.PRESETS["⌨️ Modo OTG (Teclado y Ratón USB)"]
        self.assertEqual(otg_data.get("extra_args"), "--otg")
        self.assertEqual(otg_data.get("audio_source"), "none")

    def test_accordion_toggle_no_event_shadowing(self):
        if not self.root:
            self.skipTest("Tkinter display not available")
        canvas = tk.Canvas(self.root)
        item = AccordionItem(self.root, "Test Title", lambda f: tk.Label(f, text="Inside"), canvas_ref=canvas)
        self.assertFalse(item._expanded)
        
        # Test expand without event
        item.expand()
        self.assertTrue(item._expanded)
        self.assertEqual(item._arrow.cget("text"), "▼")
        
        # Test toggle passing mock Tkinter event (must not crash with TypeError)
        mock_event = MagicMock()
        item._toggle(mock_event)
        self.assertFalse(item._expanded)
        self.assertEqual(item._arrow.cget("text"), "▶")
        
        # Collapse when already collapsed
        item.collapse()
        self.assertFalse(item._expanded)


if __name__ == '__main__':
    unittest.main()
