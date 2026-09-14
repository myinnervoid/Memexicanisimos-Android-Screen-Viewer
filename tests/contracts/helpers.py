"""Helpers compartidos para los tests de contrato.

Todos los tests mockean subprocess para no depender de dispositivos (ADR-026).
"""
from __future__ import annotations
from unittest.mock import MagicMock

from scrcpy_dock.domain.models import (
    Device, DeviceState, ConnectionType, DeviceCapabilities, Codec,
)


# ─── Device ────────────────────────────────────────────────────────────────

def make_device(
    serial: str = "ABC123",
    model: str = "HUAWEI Y9 Prime 2019",
    android_sdk: int = 29,
    state: DeviceState = DeviceState.DEVICE,
    connection: ConnectionType = ConnectionType.USB,
) -> Device:
    return Device(
        serial=serial,
        model=model,
        android_sdk=android_sdk,
        state=state,
        connection_type=connection,
    )


def make_huawei_y9() -> Device:
    """Huawei Y9 Prime 2019 · EMUI 10 · SDK 29 · Kirin 710."""
    return make_device(
        serial="HWY9PRIME001",
        model="HUAWEI Y9 Prime 2019",
        android_sdk=29,
    )


def make_modern_samsung() -> Device:
    """Samsung S24 · Android 14 · SDK 34 · Exynos 2400."""
    return make_device(
        serial="SM-S921B",
        model="SM-S921B",
        android_sdk=34,
    )


# ─── DeviceCapabilities ────────────────────────────────────────────────────

def make_caps(
    manufacturer: str = "HUAWEI",
    platform: str = "kirin710",
    camera2_level: str = "LIMITED",
    supported_codecs: tuple[Codec, ...] = (),
    sensor_orientation: int = 0,
    sdk_int: int = 29,
) -> DeviceCapabilities:
    return DeviceCapabilities(
        manufacturer=manufacturer,
        platform=platform,
        camera2_level=camera2_level,
        supported_codecs=supported_codecs,
        sensor_orientation=sensor_orientation,
        sdk_int=sdk_int,
    )


def make_caps_huawei_y9() -> DeviceCapabilities:
    return make_caps(
        manufacturer="HUAWEI",
        platform="kirin710",
        camera2_level="LIMITED",
        sdk_int=29,
    )


def make_caps_modern_samsung() -> DeviceCapabilities:
    return make_caps(
        manufacturer="samsung",
        platform="exynos2400",
        camera2_level="LEVEL_3",
        sdk_int=34,
    )


# ─── subprocess mock ───────────────────────────────────────────────────────

def fake_completed_process(
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> MagicMock:
    """Objeto compatible con subprocess.CompletedProcess."""
    m = MagicMock()
    m.stdout = stdout
    m.stderr = stderr
    m.returncode = returncode
    return m


DEVICES_L_FIXTURE = """\
List of devices attached
HWY9PRIME001     device usb:1-2 product:HUAWEI_Y9 model:HUAWEI_Y9_Prime device:HWY9 transport_id:1
SM-S921B         unauthorized usb:1-3
OLDDEVICE        offline usb:1-4
"""

GETPROPS_HUAWEI_Y9_FIXTURE = (
    "29\n"                          # ro.build.version.sdk
    "10\n"                          # ro.build.version.release
    "HUAWEI\n"                      # ro.product.manufacturer
    "HUAWEI Y9 Prime 2019\n"        # ro.product.model
    "kirin710\n"                    # ro.board.platform
)
