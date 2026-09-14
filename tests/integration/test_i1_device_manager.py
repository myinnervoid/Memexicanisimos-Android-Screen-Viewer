"""I1 · DeviceManager debe consumir AdbEngine, no subprocess."""
from __future__ import annotations
import unittest
from pathlib import Path
from unittest.mock import patch

from scrcpy_dock.domain.models import Device, DeviceState
from tests.integration.fakes import FakeAdbEngine
from scrcpy_dock.managers import DeviceManager


class DeviceManagerDelegationContract(unittest.TestCase):

    def setUp(self):
        self.fake_adb = FakeAdbEngine()
        self.dm = DeviceManager(adb_engine=self.fake_adb)

    def test_scan_devices_delegates_to_adb_engine(self):
        self.fake_adb.queue_devices([
            Device(serial="X", model="M", android_sdk=29),
            Device(serial="Y", model="N", android_sdk=34),
        ])
        result = self.dm.scan_devices()
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 2)
        self.assertEqual(self.fake_adb.list_devices_calls, 1)

    def test_scan_devices_does_not_touch_subprocess(self):
        with patch("subprocess.run") as sp, \
             patch("subprocess.Popen") as spopen:
            self.fake_adb.queue_devices([])
            self.dm.scan_devices()
            sp.assert_not_called()
            spopen.assert_not_called()


class DeviceManagerEnrichmentContract(unittest.TestCase):

    def setUp(self):
        self.fake_adb = FakeAdbEngine()
        self.dm = DeviceManager(adb_engine=self.fake_adb)

    def test_get_capabilities_queries_properties_once(self):
        self.fake_adb.set_properties("HWY9", {
            "ro.build.version.sdk": "29",
            "ro.product.manufacturer": "HUAWEI",
            "ro.board.platform": "kirin710",
            "ro.product.model": "STK-LX3",
        })
        caps = self.dm.get_capabilities("HWY9")
        self.assertIsNotNone(caps)
        self.assertEqual(caps.manufacturer, "HUAWEI")
        self.assertEqual(caps.platform, "kirin710")
        self.assertEqual(self.fake_adb.get_properties_calls, ["HWY9"])

    def test_get_capabilities_caches_second_call(self):
        self.fake_adb.set_properties("HWY9", {
            "ro.build.version.sdk": "29",
            "ro.product.manufacturer": "HUAWEI",
            "ro.board.platform": "kirin710",
        })
        self.dm.get_capabilities("HWY9")
        self.dm.get_capabilities("HWY9")
        # Debe consultar solo una vez
        self.assertEqual(self.fake_adb.get_properties_calls, ["HWY9"])


class DeviceManagerTrackerContract(unittest.TestCase):

    def setUp(self):
        self.fake_adb = FakeAdbEngine()
        self.dm = DeviceManager(adb_engine=self.fake_adb)

    def test_start_tracking_wires_callback(self):
        self.dm.start_tracking()
        self.assertTrue(self.fake_adb.tracker_started)

    def test_tracker_event_reaches_subscribers(self):
        received = []
        self.dm.subscribe_devices(lambda devs: received.append(devs))
        self.dm.start_tracking()
        self.fake_adb.emit_device_change([
            Device(serial="Z", model="M", android_sdk=29),
        ])
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][0].serial, "Z")

    def test_stop_tracking_is_idempotent(self):
        self.dm.stop_tracking()
        self.dm.stop_tracking()  # no-op


if __name__ == "__main__":
    unittest.main()
