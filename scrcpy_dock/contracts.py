"""Contratos de datos, tipos formales y envoltorio estándar de transporte/IPC para MASV.

Estándar de 5 Vectores — Vector 2 (Contratos de Datos & Esquema) y Ley Global 5.
"""

from dataclasses import dataclass, field
from typing import Generic, TypeVar, Optional, Dict, Any, List
from .errors import ErrorCode

T = TypeVar("T")

@dataclass
class OperationResult(Generic[T]):
    """Contrato estándar de Transporte / IPC / Resultados de Operación.

    Satisface la Ley Global 5: ApiResponse<T> = { success, data, error_code, message }
    """
    success: bool
    data: Optional[T] = None
    error_code: Optional[ErrorCode] = None
    message: str = ""
    error: Optional[ErrorCode] = None

    def __post_init__(self) -> None:
        if self.error is not None and self.error_code is None:
            self.error_code = self.error
        elif self.error_code is not None and self.error is None:
            self.error = self.error_code

    @classmethod
    def ok(cls, data: Optional[T] = None, message: str = "OK") -> "OperationResult[T]":
        return cls(success=True, data=data, error_code=ErrorCode.NONE, error=ErrorCode.NONE, message=message)

    @classmethod
    def fail(cls, error_code: ErrorCode, message: str, data: Optional[T] = None) -> "OperationResult[T]":
        return cls(success=False, data=data, error_code=error_code, error=error_code, message=message)

    def __iter__(self):
        """Permite desempaquetar como tupla (success, message) para compatibilidad hacia atrás."""
        return iter((self.success, self.message))

    def __bool__(self) -> bool:
        return self.success

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error_code": self.error_code.value if self.error_code else None,
            "message": self.message,
        }


@dataclass(frozen=True)
class DeviceEntry:
    """Modelo inmutable de un dispositivo Android detectado por ADB."""
    serial: str
    model: str = "Android"
    state: str = "device"  # "device", "unauthorized", "offline", "other"
    alias: str = ""
    is_trusted: bool = False
    android_version: int = 11
    manufacturer: str = ""
    platform: str = ""
    connection_type: str = "USB"

    @property
    def display_name(self) -> str:
        name = self.alias if self.alias else self.model
        return f"{name} ({self.serial})"

    @property
    def is_authorized(self) -> bool:
        return self.state == "device"


@dataclass
class SessionInfo:
    """Información de estado y métricas de una sesión scrcpy activa."""
    serial: str
    profile_name: str
    pid: int
    active: bool = True
    start_time: float = 0.0
    uptime_str: str = "00:00"


@dataclass
class ProfileConfig:
    """Definición tipada de un perfil de transmisión scrcpy."""
    name: str
    bitrate: str = "8M"
    max_size: str = "1920"
    max_fps: str = "60"
    video_codec: str = "h264"
    video_source: str = "display"
    camera_facing: Optional[str] = None
    camera_id: Optional[str] = "0"
    audio_source: str = "playback"
    audio_codec: Optional[str] = None
    turn_screen_off: bool = True
    force_screen_off_keyevent: bool = False
    stay_awake: bool = True
    v4l2_buffer: Optional[int] = None
    shortcut_mod: Optional[str] = None
    start_app: Optional[str] = None
    extra_args: str = ""


@dataclass
class TrustedDeviceEntry:
    """Entrada en la Bóveda de Dispositivos Confiables."""
    serial: str
    model: str
    alias: str
    is_trusted: bool = True
    trusted_since: str = ""
    last_seen: str = ""
