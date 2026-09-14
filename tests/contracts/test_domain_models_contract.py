"""Contratos congelados del dominio. NO modificar sin reabrir ADR-001/002/005."""
from __future__ import annotations
import unittest
from dataclasses import FrozenInstanceError

from scrcpy_dock.domain.models import (
    Device, DeviceCapabilities, Codec, DeviceState, ConnectionType,
)


class DeviceModelContract(unittest.TestCase):

    def test_device_is_frozen(self):
        d = Device(serial="X", model="M", android_sdk=29)
        with self.assertRaises(FrozenInstanceError):
            d.serial = "Y"  # type: ignore[misc]

    def test_android_version_mapping_is_correct(self):
        cases = {
            21: "5.0", 22: "5.1", 23: "6", 24: "7", 25: "7.1",
            26: "8", 27: "8.1", 28: "9", 29: "10", 30: "11",
            31: "12", 32: "12L", 33: "13", 34: "14", 35: "15",
        }
        for sdk, expected in cases.items():
            d = Device(serial="X", model="M", android_sdk=sdk)
            self.assertEqual(d.android_version, expected, f"sdk={sdk}")

    def test_unknown_sdk_falls_back_to_literal(self):
        d = Device(serial="X", model="M", android_sdk=99)
        self.assertEqual(d.android_version, "SDK 99")


class DeviceCapabilitiesContract(unittest.TestCase):

    def test_is_frozen(self):
        caps = DeviceCapabilities(manufacturer="HUAWEI", platform="kirin710")
        with self.assertRaises(FrozenInstanceError):
            caps.manufacturer = "samsung"  # type: ignore[misc]

    def test_post_init_converts_list_to_tuple(self):
        caps = DeviceCapabilities(
            manufacturer="HUAWEI",
            platform="kirin710",
            supported_codecs=[Codec.H264, Codec.H265],  # type: ignore[arg-type]
        )
        self.assertIsInstance(caps.supported_codecs, tuple)
        self.assertEqual(caps.supported_codecs, (Codec.H264, Codec.H265))


class EnumsContract(unittest.TestCase):

    def test_codec_values_are_lowercase(self):
        self.assertEqual(Codec.H264.value, "h264")
        self.assertEqual(Codec.H265.value, "h265")
        self.assertEqual(Codec.AV1.value, "av1")

    def test_connection_type_values(self):
        self.assertEqual(ConnectionType.USB.value, "usb")
        self.assertEqual(ConnectionType.WIFI.value, "wifi")

    def test_device_state_values(self):
        self.assertEqual(DeviceState.DEVICE.value, "device")
        self.assertEqual(DeviceState.UNAUTHORIZED.value, "unauthorized")
        self.assertEqual(DeviceState.OFFLINE.value, "offline")


if __name__ == "__main__":
    unittest.main()
