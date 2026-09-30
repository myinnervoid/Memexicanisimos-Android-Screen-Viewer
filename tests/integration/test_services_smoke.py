"""Smoke de integración entre los 3 servicios del Paso 3.

No reemplaza los tests de contrato. Verifica que las piezas encajan.
Usa un HOME temporal para no tocar el sistema real.
"""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from scrcpy_dock.services.installer_service import InstallerService
from scrcpy_dock.services.profile_service import ProfileService, Profile
from scrcpy_dock.services.security_service import SecurityService
from scrcpy_dock.domain.models import Codec


class ServicesIntegrationSmoke(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        # machine-id falso
        (self.tmp / "machine-id").write_text("fake-machine-id-12345678")

    def test_full_user_flow(self):
        # 1. Instalador prepara el layout
        installer = InstallerService(home=self.tmp)
        r = installer.ensure_layout()
        self.assertTrue(r.success)
        self.assertTrue((self.tmp / ".MASV" / "config").is_dir())

        # 2. Perfil de cámara para el curso de fotografía
        profiles = ProfileService(config_dir=installer.config_dir)
        p = Profile(
            name="curso-fotografia",
            codec=Codec.H264,
            bit_rate=6_000_000,
            resolution="1080",
            video_source="camera",
            max_fps=30.0,
        )
        self.assertTrue(profiles.save_profile(p).success)
        loaded = profiles.load_profile("curso-fotografia")
        self.assertTrue(loaded.success)
        self.assertEqual(loaded.data.video_source, "camera")
        self.assertEqual(loaded.data.max_fps, 30.0)

        # 3. Vault cifrado con el machine-id local
        sec = SecurityService(
            machine_id_path=self.tmp / "machine-id",
            salt_path=self.tmp / ".MASV" / ".salt",
            pbkdf2_iterations=1_000,
        )
        vault = {
            "version": 1,
            "trusted_devices": [
                {"serial": "MOCK_HWY9_SERIAL_01",
                 "label": "Huawei Y9",
                 "added_at": 1726281000.0},
            ],
        }
        enc = sec.encrypt_vault(vault)
        self.assertTrue(enc.success)

        # 4. Descifrar con otro service (mismo machine-id + salt)
        sec2 = SecurityService(
            machine_id_path=self.tmp / "machine-id",
            salt_path=self.tmp / ".MASV" / ".salt",
            pbkdf2_iterations=1_000,
        )
        dec = sec2.decrypt_vault(enc.data)
        self.assertTrue(dec.success)
        self.assertTrue(
            sec2.is_whitelisted_device("MOCK_HWY9_SERIAL_01", dec.data),
        )
        self.assertFalse(
            sec2.is_whitelisted_device("UNKNOWN", dec.data),
        )

        # 5. Los 3 servicios han escrito en el layout esperado
        self.assertTrue((self.tmp / ".MASV" / "config" / "config.json").exists())
        self.assertTrue((self.tmp / ".MASV" / ".salt").exists())


if __name__ == "__main__":
    unittest.main()
