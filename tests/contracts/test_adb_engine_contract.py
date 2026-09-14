"""Contratos congelados de AdbEngine. NO modificar sin reabrir ADR-006/007/008/009."""
from __future__ import annotations
import unittest
from pathlib import Path
from unittest.mock import patch

from scrcpy_dock.core.adb_engine import AdbEngine
from scrcpy_dock.contracts import ErrorCode
from scrcpy_dock.domain.models import DeviceState

from tests.contracts.helpers import (
    fake_completed_process,
    DEVICES_L_FIXTURE,
    GETPROPS_HUAWEI_Y9_FIXTURE,
)

ADB = Path("/usr/bin/adb")


# ─── start_daemon · ADR-006 ────────────────────────────────────────────────

class StartDaemonContract(unittest.TestCase):

    @patch("subprocess.run")
    def test_uses_preferred_port_when_free(self, run_mock):
        run_mock.return_value = fake_completed_process()
        engine = AdbEngine(ADB)
        result = engine.start_daemon()
        self.assertTrue(result.success)
        self.assertEqual(result.data, 5037)
        self.assertEqual(engine.effective_socket_port, 5037)

    @patch("subprocess.run")
    def test_falls_back_to_5038_after_two_bind_failures(self, run_mock):
        run_mock.side_effect = [
            fake_completed_process(stderr="cannot bind 'tcp:5037'", returncode=1),
            fake_completed_process(stderr="cannot bind 'tcp:5037'", returncode=1),
            fake_completed_process(returncode=0),
        ]
        engine = AdbEngine(ADB)
        result = engine.start_daemon()
        self.assertTrue(result.success)
        self.assertEqual(result.data, 5038)
        self.assertEqual(engine.effective_socket_port, 5038)

    @patch("subprocess.run")
    def test_daemon_dead_when_both_ports_fail(self, run_mock):
        run_mock.return_value = fake_completed_process(
            stderr="cannot bind 'tcp:5037'", returncode=1,
        )
        engine = AdbEngine(ADB)
        result = engine.start_daemon()
        self.assertFalse(result.success)
        self.assertEqual(result.error, ErrorCode.ADB_DAEMON_DEAD)

    @patch("subprocess.run")
    def test_idempotent_second_call_does_not_restart(self, run_mock):
        run_mock.return_value = fake_completed_process()
        engine = AdbEngine(ADB)
        engine.start_daemon()
        calls_after_first = run_mock.call_count
        engine.start_daemon()
        self.assertEqual(run_mock.call_count, calls_after_first)


# ─── list_devices ──────────────────────────────────────────────────────────

class ListDevicesContract(unittest.TestCase):

    @patch("subprocess.run")
    def test_parses_all_three_states(self, run_mock):
        run_mock.return_value = fake_completed_process(stdout=DEVICES_L_FIXTURE)
        engine = AdbEngine(ADB)
        result = engine.list_devices()
        self.assertTrue(result.success)
        by_serial = {d.serial: d for d in result.data}
        self.assertEqual(by_serial["HWY9PRIME001"].state, DeviceState.DEVICE)
        self.assertEqual(by_serial["SM-S921B"].state, DeviceState.UNAUTHORIZED)
        self.assertEqual(by_serial["OLDDEVICE"].state, DeviceState.OFFLINE)

    @patch("subprocess.run")
    def test_empty_output_returns_empty_list_not_error(self, run_mock):
        run_mock.return_value = fake_completed_process(
            stdout="List of devices attached\n",
        )
        engine = AdbEngine(ADB)
        result = engine.list_devices()
        self.assertTrue(result.success)
        self.assertEqual(result.data, [])


# ─── get_properties · ADR-007 ──────────────────────────────────────────────

class GetPropertiesContract(unittest.TestCase):

    @patch("subprocess.run")
    def test_makes_exactly_one_subprocess_call(self, run_mock):
        run_mock.return_value = fake_completed_process(
            stdout=GETPROPS_HUAWEI_Y9_FIXTURE,
        )
        engine = AdbEngine(ADB)
        result = engine.get_properties("HWY9PRIME001")
        self.assertTrue(result.success)
        self.assertEqual(run_mock.call_count, 1)

    @patch("subprocess.run")
    def test_parses_all_required_props(self, run_mock):
        run_mock.return_value = fake_completed_process(
            stdout=GETPROPS_HUAWEI_Y9_FIXTURE,
        )
        engine = AdbEngine(ADB)
        props = engine.get_properties("HWY9PRIME001").data
        self.assertEqual(props["ro.build.version.sdk"], "29")
        self.assertEqual(props["ro.product.manufacturer"], "HUAWEI")
        self.assertEqual(props["ro.board.platform"], "kirin710")


# ─── tcpip · ADR-009 ───────────────────────────────────────────────────────

class TcpipContract(unittest.TestCase):

    @patch("subprocess.run")
    def test_revert_skips_when_not_activated_by_masv(self, run_mock):
        run_mock.return_value = fake_completed_process()
        engine = AdbEngine(ADB)
        result = engine.revert_tcpip("HWY9PRIME001")
        self.assertTrue(result.success)
        # No debe haber ejecutado adb usb
        for call in run_mock.call_args_list:
            args = call.args[0] if call.args else call.kwargs.get("args", [])
            self.assertNotIn("usb", args)

    @patch("subprocess.run")
    def test_revert_runs_when_activated_by_masv(self, run_mock):
        run_mock.return_value = fake_completed_process()
        engine = AdbEngine(ADB)
        engine.start_tcpip("HWY9PRIME001")
        run_mock.reset_mock()
        engine.revert_tcpip("HWY9PRIME001")
        self.assertGreaterEqual(run_mock.call_count, 1)


# ─── tracker · ADR-008 ─────────────────────────────────────────────────────

class TrackerContract(unittest.TestCase):

    def test_stop_tracker_is_idempotent_when_never_started(self):
        engine = AdbEngine(ADB)
        engine.stop_tracker()
        engine.stop_tracker()


if __name__ == "__main__":
    unittest.main()
