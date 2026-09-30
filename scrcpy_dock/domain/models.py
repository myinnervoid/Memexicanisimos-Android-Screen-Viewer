"""Modelos de dominio puros para MASV.

Invariantes de datos congelados según ADR-001, ADR-002 y API Contract v1.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Sequence


class Codec(str, Enum):
    H264 = "h264"
    H265 = "h265"
    AV1 = "av1"


class ConnectionType(str, Enum):
    USB = "usb"
    WIFI = "wifi"


class DeviceState(str, Enum):
    DEVICE = "device"
    UNAUTHORIZED = "unauthorized"
    OFFLINE = "offline"


_SDK_TO_RELEASE = {
    21: "5.0", 22: "5.1", 23: "6", 24: "7", 25: "7.1",
    26: "8", 27: "8.1", 28: "9", 29: "10", 30: "11",
    31: "12", 32: "12L", 33: "13", 34: "14", 35: "15",
}


@dataclass(frozen=True)
class Device:
    serial: str
    model: str
    android_sdk: int
    state: DeviceState = DeviceState.DEVICE
    connection_type: ConnectionType = ConnectionType.USB

    @property
    def android_version(self) -> str:
        return _SDK_TO_RELEASE.get(self.android_sdk, f"SDK {self.android_sdk}")


@dataclass(frozen=True)
class DeviceCapabilities:
    manufacturer: str
    platform: str
    camera2_level: str = "LIMITED"
    supported_codecs: tuple[Codec, ...] = field(default_factory=tuple)
    sensor_orientation: int = 0
    sdk_int: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.supported_codecs, tuple):
            object.__setattr__(self, "supported_codecs", tuple(self.supported_codecs))


ALLOWED_EXTRA_FLAGS = {
    "--no-control",
    "--power-off-on-close",
    "--show-touches",
    "--stay-awake",
    "--window-title",
}


@dataclass(frozen=True)
class SessionConfig:
    port: int
    codec: Codec
    resolution: str
    bit_rate: int
    video_source: str = "display"
    max_fps: Optional[float] = None
    camera_facing: Optional[str] = None
    camera_id: Optional[str] = None
    audio_source: str = "playback"
    turn_screen_off: bool = True
    stay_awake: bool = True
    extra_args: tuple[str, ...] = ()
    otg_mode: bool = False
    keyboard_mode: Optional[str] = None
    mouse_mode: Optional[str] = None
