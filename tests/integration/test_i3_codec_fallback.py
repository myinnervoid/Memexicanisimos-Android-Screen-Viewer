"""I3 · Auto-fallback de códec en SessionManager."""
from __future__ import annotations
import unittest

from scrcpy_dock.core.port_allocator import PortAllocator
from scrcpy_dock.domain.models import Codec, Device
from tests.integration.fakes import (
    FakeAdbEngine, FakeScrcpyEngine, FakeClock,
)
from tests.contracts.helpers import make_huawei_y9, make_modern_samsung
from scrcpy_dock.managers import SessionManager
from tests.integration.test_i2_session_manager import FakeProfile


class CodecFallbackContract(unittest.TestCase):

    def setUp(self):
        self.fake_adb = FakeAdbEngine()
        self.fake_scrcpy = FakeScrcpyEngine()
        self.allocator = PortAllocator(base=28000, max_offset=10)
        self.clock = FakeClock()
        self.sm = SessionManager(
            adb_engine=self.fake_adb,
            scrcpy_engine=self.fake_scrcpy,
            allocator=self.allocator,
            clock=self.clock,
        )

    def test_fallback_triggers_on_codec_error_within_window(self):
        """Primer launch muere con patrón de códec → retry con H.264."""
        # 1er intento: muere con 'Could not open encoder'
        self.fake_scrcpy.queue_launch(
            stderr_lines=["ERROR: Could not open encoder for h265"],
            exit_code=1,
            alive_after_handshake=False,
        )
        # 2do intento: sobrevive
        self.fake_scrcpy.queue_launch(alive_after_handshake=True)

        device = make_huawei_y9()   # SDK 29 → ventana 5 s
        profile = FakeProfile(codec=Codec.H265)
        result = self.sm.start_scene(device, profile)

        self.assertTrue(result.success)
        self.assertEqual(len(self.fake_scrcpy.build_commands), 2)
        self.assertEqual(self.fake_scrcpy.build_commands[0].codec, Codec.H265)
        self.assertEqual(self.fake_scrcpy.build_commands[1].codec, Codec.H264)

    def test_no_fallback_on_device_disconnect(self):
        """stderr con 'device not found' NO es fallo de códec."""
        self.fake_scrcpy.queue_launch(
            stderr_lines=["ERROR: adb: device 'X' not found"],
            exit_code=1,
            alive_after_handshake=False,
        )
        device = make_huawei_y9()
        result = self.sm.start_scene(device, FakeProfile(codec=Codec.H265))
        self.assertFalse(result.success)
        # Solo un build_command → no reintentó
        self.assertEqual(len(self.fake_scrcpy.build_commands), 1)

    def test_fallback_only_once_no_infinite_loop(self):
        """Si H.264 también falla → no reintenta más."""
        self.fake_scrcpy.queue_launch(
            stderr_lines=["ERROR: Could not open encoder for h265"],
            exit_code=1, alive_after_handshake=False,
        )
        self.fake_scrcpy.queue_launch(
            stderr_lines=["ERROR: Could not open encoder for h264"],
            exit_code=1, alive_after_handshake=False,
        )
        device = make_huawei_y9()
        result = self.sm.start_scene(device, FakeProfile(codec=Codec.H265))
        self.assertFalse(result.success)
        # Exactamente 2 builds: H.265 y H.264, no más
        self.assertEqual(len(self.fake_scrcpy.build_commands), 2)
        # El puerto del primer intento debe liberarse
        self.assertEqual(len(self.allocator.reserved()), 0)

    def test_fallback_survives_successful_h264(self):
        """Tras fallback exitoso, el puerto queda reservado."""
        self.fake_scrcpy.queue_launch(
            stderr_lines=["ERROR: Could not open encoder"],
            exit_code=1, alive_after_handshake=False,
        )
        self.fake_scrcpy.queue_launch(alive_after_handshake=True)
        device = make_huawei_y9()
        result = self.sm.start_scene(device, FakeProfile(codec=Codec.H265))
        self.assertTrue(result.success)
        self.assertEqual(len(self.allocator.reserved()), 1)


if __name__ == "__main__":
    unittest.main()
