"""Contratos congelados de ScrcpyEngine. NO modificar sin reabrir ADR-010/011/012/014."""
from __future__ import annotations
import unittest
from pathlib import Path

from scrcpy_dock.core.scrcpy_engine import ScrcpyEngine
from scrcpy_dock.contracts import ErrorCode
from scrcpy_dock.domain.models import Codec, SessionConfig

from tests.contracts.helpers import (
    make_huawei_y9, make_modern_samsung,
    make_caps, make_caps_huawei_y9, make_caps_modern_samsung,
    fake_completed_process,
)


BIN = Path("/usr/bin/scrcpy")
JAR = Path("/usr/share/scrcpy/scrcpy-server.jar")


def _cfg(**kw) -> SessionConfig:
    base = dict(
        port=27183,
        codec=Codec.H265,
        resolution="1080",
        bit_rate=12_000_000,
        video_source="display",
        max_fps=60.0,
    )
    base.update(kw)
    return SessionConfig(**base)


# ─── matriz de códecs · ADR-010 ────────────────────────────────────────────

class CodecMatrixContract(unittest.TestCase):

    def setUp(self):
        self.engine = ScrcpyEngine(BIN, JAR)

    def test_huawei_y9_kirin710_returns_h264_only(self):
        result = self.engine.get_compatible_codecs(
            make_huawei_y9(), make_caps_huawei_y9(),
        )
        self.assertTrue(result.success)
        self.assertEqual(result.data, [Codec.H264])

    def test_android_14_modern_chipset_returns_all_three(self):
        result = self.engine.get_compatible_codecs(
            make_modern_samsung(), make_caps_modern_samsung(),
        )
        self.assertTrue(result.success)
        self.assertEqual(result.data, [Codec.AV1, Codec.H265, Codec.H264])

    def test_android_10_non_huawei_returns_h264_h265(self):
        caps = make_caps(manufacturer="Google", platform="msm8998", sdk_int=29)
        result = self.engine.get_compatible_codecs(make_huawei_y9(), caps)
        self.assertTrue(result.success)
        self.assertEqual(result.data, [Codec.H265, Codec.H264])


# ─── build_command ─────────────────────────────────────────────────────────

class BuildCommandContract(unittest.TestCase):

    def setUp(self):
        self.engine = ScrcpyEngine(BIN, JAR)
        self.device = make_huawei_y9()
        self.caps = make_caps_huawei_y9()

    # ── audio (ajuste #1) ──

    def test_android_10_injects_no_audio_and_omits_audio_source(self):
        result = self.engine.build_command(_cfg(), self.device, self.caps)
        self.assertTrue(result.success)
        argv = result.data
        self.assertIn("--no-audio", argv)
        self.assertNotIn("--audio-source", argv)

    def test_android_11_does_not_inject_no_audio(self):
        result = self.engine.build_command(
            _cfg(), make_modern_samsung(), make_caps_modern_samsung(),
        )
        self.assertTrue(result.success)
        argv = result.data
        self.assertNotIn("--no-audio", argv)
        self.assertIn("--audio-source", argv)

    # ── bitrate clamp (ADR-010 + ajuste #2) ──

    def test_kirin_clamps_high_bitrate_to_8m(self):
        result = self.engine.build_command(
            _cfg(bit_rate=20_000_000), self.device, self.caps,
        )
        argv = result.data
        bitrate = argv[argv.index("--video-bit-rate") + 1]
        self.assertEqual(bitrate, "8M")

    def test_kirin_does_not_inflate_low_bitrate(self):
        result = self.engine.build_command(
            _cfg(bit_rate=4_000_000), self.device, self.caps,
        )
        argv = result.data
        bitrate = argv[argv.index("--video-bit-rate") + 1]
        self.assertEqual(bitrate, "4M")

    def test_bitrate_non_exact_multiple_of_mega_uses_kilo(self):
        result = self.engine.build_command(
            _cfg(bit_rate=4_500_000), self.device, self.caps,
        )
        argv = result.data
        bitrate = argv[argv.index("--video-bit-rate") + 1]
        self.assertEqual(bitrate, "4500k")

    # ── codec forzado en Kirin ──

    def test_kirin_forces_h264_codec(self):
        result = self.engine.build_command(
            _cfg(codec=Codec.H265), self.device, self.caps,
        )
        argv = result.data
        codec = argv[argv.index("--video-codec") + 1]
        self.assertEqual(codec, "h264")

    # ── puerto ──

    def test_assigned_port_is_propagated(self):
        result = self.engine.build_command(
            _cfg(port=27185), self.device, self.caps,
        )
        argv = result.data
        port = argv[argv.index("--port") + 1]
        self.assertEqual(port, "27185")

    # ── max_fps (ajuste #3) ──

    def test_max_fps_formats_int_float_as_integer(self):
        result = self.engine.build_command(
            _cfg(max_fps=60.0), self.device, self.caps,
        )
        argv = result.data
        fps = argv[argv.index("--max-fps") + 1]
        self.assertEqual(fps, "60")

    def test_max_fps_preserves_fractional(self):
        result = self.engine.build_command(
            _cfg(max_fps=59.94), self.device, self.caps,
        )
        argv = result.data
        fps = argv[argv.index("--max-fps") + 1]
        self.assertEqual(fps, "59.94")

    # ── extra_args whitelist (whitelist A) ──

    def test_whitelisted_extra_flag_is_accepted(self):
        result = self.engine.build_command(
            _cfg(extra_args=("--no-control",)), self.device, self.caps,
        )
        self.assertTrue(result.success)
        self.assertIn("--no-control", result.data)

    def test_whitelisted_flag_with_equals_value_is_accepted(self):
        result = self.engine.build_command(
            _cfg(extra_args=("--window-title=MASV Demo",)),
            self.device, self.caps,
        )
        self.assertTrue(result.success)
        self.assertIn("--window-title=MASV Demo", result.data)

    def test_forbidden_flag_returns_invalid_extra_args(self):
        result = self.engine.build_command(
            _cfg(extra_args=("--port", "9999")), self.device, self.caps,
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error, ErrorCode.INVALID_EXTRA_ARGS)

    def test_forbidden_flag_with_equals_returns_invalid_extra_args(self):
        result = self.engine.build_command(
            _cfg(extra_args=("--video-codec=av1",)), self.device, self.caps,
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error, ErrorCode.INVALID_EXTRA_ARGS)

    def test_tcpip_flag_is_rejected(self):
        result = self.engine.build_command(
            _cfg(extra_args=("--tcpip",)), self.device, self.caps,
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error, ErrorCode.INVALID_EXTRA_ARGS)

    # ── camera source ──

    def test_camera_source_propagates_facing_flag(self):
        result = self.engine.build_command(
            _cfg(video_source="camera", camera_facing="back"),
            self.device, self.caps,
        )
        self.assertTrue(result.success)
        argv = result.data
        self.assertEqual(argv[argv.index("--video-source") + 1], "camera")
        self.assertEqual(argv[argv.index("--camera-facing") + 1], "back")

    def test_camera_id_takes_precedence_over_facing(self):
        result = self.engine.build_command(
            _cfg(video_source="camera", camera_id="2", camera_facing="back"),
            self.device, self.caps,
        )
        self.assertTrue(result.success)
        argv = result.data
        self.assertIn("--camera-id", argv)
        self.assertNotIn("--camera-facing", argv)


# ─── is_codec_failure · ADR-011 ────────────────────────────────────────────

class CodecFailureHeuristicContract(unittest.TestCase):

    def setUp(self):
        self.engine = ScrcpyEngine(BIN, JAR)

    def test_android_10_timeout_window_is_5s(self):
        stderr = ["ERROR: Could not open encoder for h265"]
        self.assertTrue(self.engine.is_codec_failure(stderr, 4.9, android_sdk=29))
        self.assertFalse(self.engine.is_codec_failure(stderr, 5.1, android_sdk=29))

    def test_android_11_timeout_window_is_2_5s(self):
        stderr = ["ERROR: Could not open encoder"]
        self.assertTrue(self.engine.is_codec_failure(stderr, 2.4, android_sdk=30))
        self.assertFalse(self.engine.is_codec_failure(stderr, 2.6, android_sdk=30))

    def test_device_disconnect_is_not_codec_failure(self):
        stderr = ["ERROR: adb: device 'ABC' not found"]
        self.assertFalse(self.engine.is_codec_failure(stderr, 1.0, android_sdk=29))

    def test_only_first_10_lines_are_considered(self):
        stderr = [""] * 15 + ["ERROR: Could not open encoder"]
        self.assertFalse(self.engine.is_codec_failure(stderr, 1.0, android_sdk=29))

    def test_patterns_are_case_insensitive(self):
        stderr = ["ERROR: CODEC NOT SUPPORTED"]
        self.assertTrue(self.engine.is_codec_failure(stderr, 1.0, android_sdk=29))

    def test_mediacodec_error_triggers_failure(self):
        stderr = ["MediaCodec error: 0x80000000"]
        self.assertTrue(self.engine.is_codec_failure(stderr, 1.5, android_sdk=29))


# ─── verify_server_version · ADR-014 ──────────────────────────────────────

class VerifyServerVersionContract(unittest.TestCase):

    def test_version_match_returns_success(self):
        engine = ScrcpyEngine(BIN, JAR)
        result = engine._compare_versions("scrcpy 2.5", "scrcpy-server 2.5")
        self.assertTrue(result.success)
        self.assertEqual(result.data, "2.5")

    def test_version_mismatch_returns_error(self):
        engine = ScrcpyEngine(BIN, JAR)
        result = engine._compare_versions("scrcpy 2.5", "scrcpy-server 2.4")
        self.assertFalse(result.success)
        self.assertEqual(result.error, ErrorCode.SCRCPY_SERVER_VERSION_MISMATCH)


if __name__ == "__main__":
    unittest.main()
