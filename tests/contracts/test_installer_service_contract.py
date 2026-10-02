"""Contratos congelados de InstallerService. NO modificar sin reabrir ADR-018/019."""
from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scrcpy_dock.services.installer_service import InstallerService
from scrcpy_dock.contracts import ErrorCode


def _make_service(tmp: Path, which_map: dict | None = None) -> InstallerService:
    """Service con HOME y XDG_DATA_HOME en tmp, which() controlado."""
    fake_which = lambda name: (which_map or {}).get(name)
    return InstallerService(
        home=tmp,
        xdg_data_home=tmp / ".local" / "share",
        which_fn=fake_which,
    )


# ─── resolve_binary · TODO-I1 ───────────────────────────────────────

class ResolveBinaryContract(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_prefers_masv_bin_over_path(self):
        self.tmp.joinpath(".MASV", "bin").mkdir(parents=True)
        local = self.tmp / ".MASV" / "bin" / "adb"
        local.write_text("#!/bin/sh\n")
        local.chmod(0o755)

        svc = _make_service(self.tmp, which_map={"adb": "/usr/bin/adb"})
        r = svc.resolve_binary("adb")
        self.assertTrue(r.success)
        self.assertEqual(r.data, local)

    def test_falls_back_to_path_when_not_in_masv_bin(self):
        svc = _make_service(self.tmp, which_map={"scrcpy": "/usr/local/bin/scrcpy"})
        r = svc.resolve_binary("scrcpy")
        self.assertTrue(r.success)
        self.assertEqual(r.data, Path("/usr/local/bin/scrcpy").absolute())

    @unittest.skipIf(sys.platform == "win32", "POSIX file permissions do not apply on Windows")
    def test_non_executable_local_is_skipped(self):
        self.tmp.joinpath(".MASV", "bin").mkdir(parents=True)
        local = self.tmp / ".MASV" / "bin" / "adb"
        local.write_text("#!/bin/sh\n")
        local.chmod(0o644)     # no ejecutable

        svc = _make_service(self.tmp, which_map={"adb": "/usr/bin/adb"})
        r = svc.resolve_binary("adb")
        self.assertTrue(r.success)
        self.assertEqual(r.data, Path("/usr/bin/adb").absolute())

    def test_not_found_returns_binary_not_found(self):
        svc = _make_service(self.tmp, which_map={})
        r = svc.resolve_binary("nonexistent")
        self.assertFalse(r.success)
        self.assertEqual(r.error, ErrorCode.BINARY_NOT_FOUND)

    def test_empty_name_rejected(self):
        svc = _make_service(self.tmp)
        self.assertEqual(
            svc.resolve_binary("").error, ErrorCode.INVALID_INPUT,
        )

    def test_name_with_slash_rejected(self):
        svc = _make_service(self.tmp)
        self.assertEqual(
            svc.resolve_binary("../etc/passwd").error, ErrorCode.INVALID_INPUT,
        )
        self.assertEqual(
            svc.resolve_binary("sub/dir").error, ErrorCode.INVALID_INPUT,
        )

    def test_returns_absolute_path(self):
        svc = _make_service(self.tmp, which_map={"adb": "/usr/bin/adb"})
        r = svc.resolve_binary("adb")
        self.assertTrue(r.data.is_absolute())


# ─── ensure_layout · TODO-I2 ────────────────────────────────────────

class EnsureLayoutContract(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.svc = _make_service(self.tmp)

    def test_creates_all_subdirs(self):
        r = self.svc.ensure_layout()
        self.assertTrue(r.success)
        for sub in ("bin", "assets", "config", "logs"):
            self.assertTrue(
                (self.tmp / ".MASV" / sub).is_dir(),
                f"falta {sub}/",
            )

    def test_idempotent(self):
        self.svc.ensure_layout()
        r = self.svc.ensure_layout()
        self.assertTrue(r.success)

    def test_failure_returns_dependency_install_failed(self):
        with patch(
            "scrcpy_dock.services.installer_service.Path.mkdir",
            side_effect=OSError("permission denied"),
        ):
            r = self.svc.ensure_layout()
            self.assertFalse(r.success)
            self.assertEqual(r.error, ErrorCode.DEPENDENCY_INSTALL_FAILED)


# ─── write_desktop_entry · TODO-I3 ──────────────────────────────────

@unittest.skipIf(sys.platform == "win32", "XDG desktop entries and symlinks do not apply on Windows")
class WriteDesktopEntryContract(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.svc = _make_service(self.tmp)
        self.svc.ensure_layout()
        self.exec_path = self.tmp / ".MASV" / "bin" / "MASV"
        self.exec_path.write_text("#!/bin/sh\n")
        self.exec_path.chmod(0o755)
        self.icon_path = self.tmp / ".MASV" / "assets" / "logo.png"

    def test_creates_desktop_file(self):
        r = self.svc.write_desktop_entry(self.exec_path, self.icon_path)
        self.assertTrue(r.success)
        self.assertTrue(self.svc.desktop_entry_path.is_file())

    def test_desktop_content_has_required_keys(self):
        self.svc.write_desktop_entry(self.exec_path, self.icon_path)
        content = self.svc.desktop_entry_path.read_text()
        self.assertIn("[Desktop Entry]", content)
        self.assertIn("Name=MASV", content)
        self.assertIn(f"Exec={self.exec_path.resolve()}", content)
        self.assertIn(f"Icon={self.icon_path.resolve()}", content)

    def test_creates_bin_symlink(self):
        r = self.svc.write_desktop_entry(self.exec_path, self.icon_path)
        self.assertTrue(r.success)
        link = self.svc.bin_symlink_path
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), self.exec_path.resolve())

    def test_idempotent(self):
        self.svc.write_desktop_entry(self.exec_path, self.icon_path)
        r = self.svc.write_desktop_entry(self.exec_path, self.icon_path)
        self.assertTrue(r.success)
        # El symlink debe seguir apuntando al exec_path
        self.assertEqual(
            self.svc.bin_symlink_path.resolve(), self.exec_path.resolve(),
        )


# ─── uninstall · TODO-I4 ────────────────────────────────────────────

@unittest.skipIf(sys.platform == "win32", "XDG desktop entries and symlinks do not apply on Windows")
class UninstallContract(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.svc = _make_service(self.tmp)
        self.svc.ensure_layout()
        self.exec_path = self.tmp / ".MASV" / "bin" / "MASV"
        self.exec_path.write_text("#!/bin/sh\n")
        self.exec_path.chmod(0o755)
        self.icon_path = self.tmp / ".MASV" / "assets" / "logo.png"
        self.svc.write_desktop_entry(self.exec_path, self.icon_path)

    def test_removes_desktop_and_symlink(self):
        r = self.svc.uninstall()
        self.assertTrue(r.success)
        self.assertFalse(self.svc.desktop_entry_path.exists())
        self.assertFalse(self.svc.bin_symlink_path.exists())

    def test_preserves_masv_dir_by_default(self):
        self.svc.uninstall()
        self.assertTrue((self.tmp / ".MASV").is_dir())

    def test_purge_removes_masv_dir(self):
        r = self.svc.uninstall(purge=True)
        self.assertTrue(r.success)
        self.assertFalse((self.tmp / ".MASV").exists())

    def test_idempotent(self):
        self.svc.uninstall()
        r = self.svc.uninstall()
        self.assertTrue(r.success)


if __name__ == "__main__":
    unittest.main()
