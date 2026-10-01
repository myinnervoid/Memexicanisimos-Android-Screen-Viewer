"""Tests exhaustivos para todos los modos de conexión de MASV:
1. Modo Pantalla USB (Screen Mirroring) en Android moderno (SDK 35) vs legacy (SDK 29)
2. Modo Cámara (Camera Mode) con prevención de crash de sensor 48MP y guard Android 12+
3. Modo OTG (HID Keyboard/Mouse)
4. Modo Inalámbrico TCP/IP (Wireless IP:Port)
5. Gobernanza de Perfiles y Normalización de Argumentos Legacy
"""
from __future__ import annotations
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from scrcpy_dock.core.scrcpy_engine import ScrcpyEngine
from scrcpy_dock.contracts import ErrorCode
from scrcpy_dock.domain.models import Codec, Device, DeviceCapabilities, DeviceState, ConnectionType, SessionConfig
from scrcpy_dock.managers import SessionManager
from scrcpy_dock.services.profile_service import ProfileService

BIN = Path("/usr/local/bin/scrcpy")
JAR = Path("/usr/local/share/scrcpy/scrcpy-server")


def make_modern_vivo() -> Device:
    """Dispositivo moderno: vivo V2314, Android 15 (SDK 35)."""
    return Device(
        serial="10ADCR1U6B000QF",
        model="V2314",
        android_sdk=35,
        state=DeviceState.DEVICE,
        connection_type=ConnectionType.USB,
    )


def make_caps_vivo() -> DeviceCapabilities:
    return DeviceCapabilities(
        manufacturer="vivo",
        platform="qcom",
        camera2_level="FULL",
        supported_codecs=(Codec.H264, Codec.H265, Codec.AV1),
        sensor_orientation=90,
        sdk_int=35,
    )


def make_huawei_y9() -> Device:
    """Dispositivo legacy: Huawei Y9 Prime 2019, Android 10 (SDK 29), Kirin 710."""
    return Device(
        serial="FKTVB20A17002956",
        model="STK-LX3",
        android_sdk=29,
        state=DeviceState.DEVICE,
        connection_type=ConnectionType.USB,
    )


def make_caps_huawei() -> DeviceCapabilities:
    return DeviceCapabilities(
        manufacturer="HUAWEI",
        platform="kirin710",
        camera2_level="LIMITED",
        supported_codecs=(Codec.H264,),
        sensor_orientation=270,
        sdk_int=29,
    )


def make_wireless_device() -> Device:
    """Dispositivo inalámbrico conectado por TCP/IP."""
    return Device(
        serial="192.168.100.2:5555",
        model="V2314",
        android_sdk=35,
        state=DeviceState.DEVICE,
        connection_type=ConnectionType.WIFI,
    )


class TestUsbMirrorMode(unittest.TestCase):
    """Pruebas del modo de duplicación de pantalla USB."""

    def setUp(self):
        self.engine = ScrcpyEngine(BIN, JAR)

    def test_modern_device_usb_mirror_allows_h265_and_playback_audio(self):
        config = SessionConfig(
            port=27183,
            codec=Codec.H265,
            resolution="1080",
            bit_rate=16_000_000,
            video_source="display",
            audio_source="playback",
            max_fps=60.0,
        )
        res = self.engine.build_command(config, make_modern_vivo(), make_caps_vivo())
        self.assertTrue(res.success)
        argv = res.data

        self.assertIn("-s", argv)
        self.assertIn("10ADCR1U6B000QF", argv)
        self.assertIn("--video-source", argv)
        self.assertEqual(argv[argv.index("--video-source") + 1], "display")
        self.assertIn("--video-codec", argv)
        self.assertEqual(argv[argv.index("--video-codec") + 1], "h265")
        self.assertIn("--video-bit-rate", argv)
        self.assertEqual(argv[argv.index("--video-bit-rate") + 1], "16M")
        self.assertIn("--max-fps", argv)
        self.assertEqual(argv[argv.index("--max-fps") + 1], "60")
        self.assertIn("--audio-source", argv)
        self.assertEqual(argv[argv.index("--audio-source") + 1], "playback")
        self.assertIn("--no-downsize-on-error", argv)

    def test_legacy_huawei_y9_forces_h264_clamps_bitrate_and_disables_audio(self):
        config = SessionConfig(
            port=27183,
            codec=Codec.H265,  # Pide H265 pero hardware Kirin debe forzar H264
            resolution="1080",
            bit_rate=16_000_000,  # Pide 16M pero Kirin debe clampear a 8M
            video_source="display",
            audio_source="playback",
        )
        res = self.engine.build_command(config, make_huawei_y9(), make_caps_huawei())
        self.assertTrue(res.success)
        argv = res.data

        self.assertIn("--video-codec", argv)
        self.assertEqual(argv[argv.index("--video-codec") + 1], "h264")
        self.assertIn("--video-bit-rate", argv)
        self.assertEqual(argv[argv.index("--video-bit-rate") + 1], "8M")
        self.assertIn("--no-audio", argv)
        self.assertNotIn("--audio-source", argv)


class TestCameraMode(unittest.TestCase):
    """Pruebas del modo cámara con protección de sensores de alta resolución (48MP/12MP)."""

    def setUp(self):
        self.engine = ScrcpyEngine(BIN, JAR)

    def test_camera_mode_on_modern_device_omits_no_downsize_on_error(self):
        config = SessionConfig(
            port=27183,
            codec=Codec.H264,
            resolution="1920",
            bit_rate=12_000_000,
            video_source="camera",
            camera_id="0",
            max_fps=30.0,
        )
        res = self.engine.build_command(config, make_modern_vivo(), make_caps_vivo())
        self.assertTrue(res.success)
        argv = res.data

        # CRÍTICO: --no-downsize-on-error NO debe estar presente para que MediaCodec
        # pueda auto-ajustarse si el sensor físico reporta 4608x3456
        self.assertNotIn("--no-downsize-on-error", argv)
        self.assertIn("--video-source", argv)
        self.assertEqual(argv[argv.index("--video-source") + 1], "camera")
        self.assertIn("--camera-id", argv)
        self.assertEqual(argv[argv.index("--camera-id") + 1], "0")
        self.assertIn("--camera-fps", argv)
        self.assertEqual(argv[argv.index("--camera-fps") + 1], "30")
        self.assertNotIn("--max-fps", argv)

    def test_camera_mode_front_camera_id_1(self):
        config = SessionConfig(
            port=27183,
            codec=Codec.H264,
            resolution="1080",
            bit_rate=8_000_000,
            video_source="camera",
            camera_id="1",
        )
        res = self.engine.build_command(config, make_modern_vivo(), make_caps_vivo())
        self.assertTrue(res.success)
        argv = res.data

        self.assertIn("--camera-id", argv)
        self.assertEqual(argv[argv.index("--camera-id") + 1], "1")

    def test_camera_mode_camera_facing_back_fallback(self):
        config = SessionConfig(
            port=27183,
            codec=Codec.H264,
            resolution="1080",
            bit_rate=8_000_000,
            video_source="camera",
            camera_facing="back",
        )
        res = self.engine.build_command(config, make_modern_vivo(), make_caps_vivo())
        self.assertTrue(res.success)
        argv = res.data

        self.assertIn("--camera-facing", argv)
        self.assertEqual(argv[argv.index("--camera-facing") + 1], "back")

    def test_camera_mode_native_resolution_clamps_to_safe_1920(self):
        """Si la resolución es native en modo cámara, se limita a 1920 para no saturar MediaCodec."""
        config = SessionConfig(
            port=27183,
            codec=Codec.H264,
            resolution="native",
            bit_rate=8_000_000,
            video_source="camera",
            camera_id="0",
        )
        res = self.engine.build_command(config, make_modern_vivo(), make_caps_vivo())
        self.assertTrue(res.success)
        argv = res.data

        self.assertIn("--max-size", argv)
        self.assertEqual(argv[argv.index("--max-size") + 1], "1920")

    def test_camera_mode_rejects_android_below_sdk_31(self):
        """Cámara requiere Android 12+ (SDK 31). Android 10 (SDK 29) debe ser rechazado."""
        config = SessionConfig(
            port=27183,
            codec=Codec.H264,
            resolution="1080",
            bit_rate=8_000_000,
            video_source="camera",
            camera_id="0",
        )
        res = self.engine.build_command(config, make_huawei_y9(), make_caps_huawei())
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.INVALID_INPUT)
        self.assertIn("SDK 31", res.message)


class TestOtgMode(unittest.TestCase):
    """Pruebas del modo OTG (HID Keyboard/Mouse sin stream de video)."""

    def setUp(self):
        self.engine = ScrcpyEngine(BIN, JAR)

    def test_otg_mode_injects_flag_and_omits_video_params(self):
        config = SessionConfig(
            port=27183,
            codec=Codec.H264,
            resolution="1080",
            bit_rate=8_000_000,
            video_source="display",
            otg_mode=True,
        )
        res = self.engine.build_command(config, make_modern_vivo(), make_caps_vivo())
        self.assertTrue(res.success)
        argv = res.data

        self.assertIn("--otg", argv)
        self.assertNotIn("--video-source", argv)
        self.assertNotIn("--video-codec", argv)
        self.assertNotIn("--video-bit-rate", argv)
        self.assertNotIn("--port", argv)
        self.assertNotIn("--no-downsize-on-error", argv)


class TestWirelessTcpIpMode(unittest.TestCase):
    """Pruebas de conexión inalámbrica mediante TCP/IP (IP:puerto)."""

    def setUp(self):
        self.engine = ScrcpyEngine(BIN, JAR)

    def test_wireless_device_serial_passed_directly(self):
        config = SessionConfig(
            port=27183,
            codec=Codec.H264,
            resolution="1080",
            bit_rate=8_000_000,
            video_source="display",
        )
        dev = make_wireless_device()
        res = self.engine.build_command(config, dev, make_caps_vivo())
        self.assertTrue(res.success)
        argv = res.data

        self.assertIn("-s", argv)
        self.assertEqual(argv[argv.index("-s") + 1], "192.168.100.2:5555")

    def test_multi_device_port_pool_allocation(self):
        """Verifica que dos sesiones simultáneas no colisionen en puerto."""
        mgr = SessionManager()
        p1 = mgr._allocator.acquire()
        p2 = mgr._allocator.acquire()
        self.assertTrue(p1.success)
        self.assertTrue(p2.success)
        self.assertNotEqual(p1.data, p2.data)
        mgr._allocator.release(p1.data)
        mgr._allocator.release(p2.data)


class TestProfileNormalizationAndSafety(unittest.TestCase):
    """Pruebas de normalización de perfiles y sanitización de argumentos."""

    def test_legacy_profile_with_camera_in_extra_args_is_normalized(self):
        """Un perfil v1 con '--video-source=camera' en extra_args debe normalizarse."""
        raw_profile = {
            "bitrate": "12M",
            "max_size": "1920",
            "max_fps": "30",
            "audio_source": "mic",
            "camera_id": "0",
            "video_codec": "h264",
            "extra_args": "--video-source=camera",
        }
        normalized = ProfileService.sanitize_profile_dict(raw_profile)
        self.assertEqual(normalized["video_source"], "camera")

    def test_start_scene_legacy_normalizes_extra_args_tokens(self):
        """start_scene_legacy extrae '--video-source=camera' y '--otg' sin fallar en whitelist."""
        mgr = SessionManager()
        # Mock de scrcpy engine
        mock_scrcpy = MagicMock()
        mock_scrcpy.launch.return_value = MagicMock(success=True, data=MagicMock())
        mgr._scrcpy = mock_scrcpy

        # Mock de adb
        mock_adb = MagicMock()
        mock_adb.get_properties.return_value = MagicMock(success=True, data={
            "ro.product.manufacturer": "vivo",
            "ro.board.platform": "qcom",
        })
        mgr._adb = mock_adb

        legacy_profile_data = {
            "bitrate": "12M",
            "max_size": "1920",
            "max_fps": "30",
            "audio_source": "mic",
            "camera_id": "0",
            "video_codec": "h264",
            "turn_screen_off": False,
            "stay_awake": True,
            "extra_args": "--video-source=camera",
        }

        # Ejecutamos start_scene_legacy para un dispositivo Android 15
        dev = make_modern_vivo()
        if mgr.device_mgr:
            mgr.device_mgr.get_device = MagicMock(return_value=dev)

        res = mgr.start_scene_legacy(dev.serial, "📷 Cámara HD", legacy_profile_data)
        self.assertTrue(res.success)

        # Verificamos que el config pasado a self._scrcpy.launch tenga video_source='camera'
        # y que extra_args ya NO contenga '--video-source=camera' (evitando violación de whitelist)
        call_args = mock_scrcpy.launch.call_args
        config_passed = call_args[0][0]
        self.assertEqual(config_passed.video_source, "camera")
        self.assertEqual(config_passed.camera_id, "0")
        self.assertNotIn("--video-source=camera", config_passed.extra_args)


if __name__ == "__main__":
    unittest.main()
