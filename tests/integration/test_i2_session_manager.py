"""I2 · SessionManager orquesta ScrcpyEngine + PortAllocator."""
from __future__ import annotations
import unittest
from dataclasses import dataclass

from scrcpy_dock.core.port_allocator import PortAllocator
from scrcpy_dock.domain.models import Codec, Device
from tests.integration.fakes import FakeAdbEngine, FakeScrcpyEngine
from tests.contracts.helpers import make_huawei_y9
from scrcpy_dock.managers import SessionManager


@dataclass
class FakeProfile:
    codec: Codec = Codec.H264
    bit_rate: int = 8_000_000
    resolution: str = "1080"
    video_source: str = "display"
    max_fps: float | None = None


class SessionManagerStartContract(unittest.TestCase):

    def setUp(self):
        self.fake_adb = FakeAdbEngine()
        self.fake_scrcpy = FakeScrcpyEngine()
        self.allocator = PortAllocator(base=28000, max_offset=10)
        self.sm = SessionManager(
            adb_engine=self.fake_adb,
            scrcpy_engine=self.fake_scrcpy,
            allocator=self.allocator,
        )

    def test_start_scene_allocates_port_from_pool(self):
        self.fake_scrcpy.queue_launch(alive_after_handshake=True)
        device = make_huawei_y9()
        result = self.sm.start_scene(device, FakeProfile())
        self.assertTrue(result.success)
        self.assertIn(result.data.port, range(28000, 28011))

    def test_start_scene_passes_allocated_port_to_build_command(self):
        self.fake_scrcpy.queue_launch(alive_after_handshake=True)
        device = make_huawei_y9()
        self.sm.start_scene(device, FakeProfile())
        config = self.fake_scrcpy.build_commands[0]
        self.assertEqual(config.port, 28000)

    def test_start_scene_calls_launch_with_wired_callbacks(self):
        self.fake_scrcpy.queue_launch(alive_after_handshake=True)
        device = make_huawei_y9()
        self.sm.start_scene(device, FakeProfile())
        launch = self.fake_scrcpy.launches[0]
        self.assertIsNotNone(launch["on_stderr_line"])
        self.assertIsNotNone(launch["on_exit"])

    def test_two_devices_get_distinct_ports(self):
        self.fake_scrcpy.queue_launch(alive_after_handshake=True)
        self.fake_scrcpy.queue_launch(alive_after_handshake=True)
        r1 = self.sm.start_scene(make_huawei_y9(), FakeProfile())
        r2 = self.sm.start_scene(
            Device(serial="SM2", model="S", android_sdk=34), FakeProfile(),
        )
        self.assertNotEqual(r1.data.port, r2.data.port)


class SessionManagerStopContract(unittest.TestCase):

    def setUp(self):
        self.fake_adb = FakeAdbEngine()
        self.fake_scrcpy = FakeScrcpyEngine()
        self.allocator = PortAllocator(base=28000, max_offset=10)
        self.sm = SessionManager(
            adb_engine=self.fake_adb,
            scrcpy_engine=self.fake_scrcpy,
            allocator=self.allocator,
        )

    def test_stop_scene_releases_port(self):
        self.fake_scrcpy.queue_launch(alive_after_handshake=True)
        device = make_huawei_y9()
        start = self.sm.start_scene(device, FakeProfile())
        port = start.data.port
        self.assertIn(port, self.allocator.reserved())
        self.sm.stop_scene(device.serial)
        self.assertNotIn(port, self.allocator.reserved())

    def test_stop_scene_terminates_process(self):
        self.fake_scrcpy.queue_launch(alive_after_handshake=True)
        device = make_huawei_y9()
        start = self.sm.start_scene(device, FakeProfile())
        proc = start.data.process
        self.sm.stop_scene(device.serial)
        self.assertIsNotNone(proc.poll())   # ya no está vivo

    def test_stop_scene_unknown_serial_is_noop(self):
        self.sm.stop_scene("NEVER-STARTED")  # no lanza


if __name__ == "__main__":
    unittest.main()
