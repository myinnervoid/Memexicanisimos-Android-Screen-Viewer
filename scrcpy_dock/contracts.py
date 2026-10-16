"""Contratos de datos, tipos formales y envoltorio estándar de transporte/IPC para MASV.

Estándar de 5 Vectores — Vector 2 (Contratos de Datos & Esquema) y Ley Global 5.
"""

from dataclasses import dataclass
from typing import Generic, TypeVar, Optional, Dict, Any
from .errors import ErrorCode

T = TypeVar("T")

@dataclass
class OperationResult(Generic[T]):
    """Contrato estándar de Transporte / IPC / Resultados de Operación.

    Satisface la Ley Global 5: ApiResponse<T> = { success, data, error_code, message }

    Attributes:
        success (bool): Indica si la operación fue exitosa.
        data (Optional[T]): Datos devueltos por la operación si fue exitosa.
        error_code (Optional[ErrorCode]): Código de error si la operación falló.
        message (str): Mensaje descriptivo del resultado.
        error (Optional[ErrorCode]): Alias de `error_code` para compatibilidad.
    """
    success: bool
    data: Optional[T] = None
    error_code: Optional[ErrorCode] = None
    message: str = ""
    error: Optional[ErrorCode] = None

    def __post_init__(self) -> None:
        """Inicializa los campos post creación para asegurar compatibilidad de `error` y `error_code`."""
        if self.error is not None and self.error_code is None:
            self.error_code = self.error
        elif self.error_code is not None and self.error is None:
            self.error = self.error_code

    @classmethod
    def ok(cls, data: Optional[T] = None, message: str = "OK") -> "OperationResult[T]":
        """Crea un OperationResult exitoso.

        Args:
            data (Optional[T], optional): Datos de la operación. Por defecto None.
            message (str, optional): Mensaje de éxito. Por defecto "OK".

        Returns:
            OperationResult[T]: Resultado exitoso.
        """
        return cls(success=True, data=data, error_code=ErrorCode.NONE, error=ErrorCode.NONE, message=message)

    @classmethod
    def fail(cls, error_code: ErrorCode, message: str, data: Optional[T] = None) -> "OperationResult[T]":
        """Crea un OperationResult fallido.

        Args:
            error_code (ErrorCode): Código de error.
            message (str): Mensaje de error detallado.
            data (Optional[T], optional): Datos parciales devueltos. Por defecto None.

        Returns:
            OperationResult[T]: Resultado fallido.
        """
        return cls(success=False, data=data, error_code=error_code, error=error_code, message=message)

    def __iter__(self):
        """Permite desempaquetar como tupla (success, message) para compatibilidad hacia atrás."""
        return iter((self.success, self.message))

    def __bool__(self) -> bool:
        """Evaluación booleana del resultado, depende del éxito."""
        return self.success

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el OperationResult en un diccionario primitivo.

        Returns:
            Dict[str, Any]: Diccionario con el contenido del resultado.
        """
        return {
            "success": self.success,
            "data": self.data,
            "error_code": self.error_code.value if self.error_code else None,
            "message": self.message,
        }


@dataclass(frozen=True)
class DeviceEntry:
    """Modelo inmutable de un dispositivo Android detectado por ADB.

    Attributes:
        serial (str): Identificador único del dispositivo.
        model (str): Nombre del modelo del dispositivo. Por defecto "Android".
        state (str): Estado de la conexión ("device", "unauthorized", "offline", "other"). Por defecto "device".
        alias (str): Alias personalizado para mostrar en la interfaz. Por defecto "".
        is_trusted (bool): Indica si el dispositivo ha sido aprobado como confiable. Por defecto False.
        android_version (int): Versión mayor de Android del dispositivo. Por defecto 11.
        manufacturer (str): Nombre del fabricante del dispositivo. Por defecto "".
        platform (str): Plataforma subyacente. Por defecto "".
        connection_type (str): Tipo de conexión utilizada (e.g., "USB", "TCP/IP"). Por defecto "USB".
    """
    serial: str
    model: str = "Android"
    state: str = "device"
    alias: str = ""
    is_trusted: bool = False
    android_version: int = 11
    manufacturer: str = ""
    platform: str = ""
    connection_type: str = "USB"

    @property
    def display_name(self) -> str:
        """Genera un nombre descriptivo para mostrar en UI.

        Returns:
            str: El alias si está definido, de lo contrario el modelo, seguido por el serial.
        """
        name = self.alias if self.alias else self.model
        return f"{name} ({self.serial})"

    @property
    def is_authorized(self) -> bool:
        """Evalúa si el dispositivo está autorizado por ADB.

        Returns:
            bool: True si el estado es 'device'.
        """
        return self.state == "device"


@dataclass
class SessionInfo:
    """Información de estado y métricas de una sesión scrcpy activa.

    Attributes:
        serial (str): El serial del dispositivo con el que se abrió la sesión.
        profile_name (str): Nombre del perfil utilizado para iniciar la sesión.
        pid (int): Identificador del proceso del motor de transmisión.
        active (bool): Indica si la sesión está en ejecución o activa. Por defecto True.
        start_time (float): Marca de tiempo UNIX indicando cuándo se inició. Por defecto 0.0.
        uptime_str (str): Representación en cadena del tiempo de actividad de la sesión. Por defecto "00:00".
    """
    serial: str
    profile_name: str
    pid: int
    active: bool = True
    start_time: float = 0.0
    uptime_str: str = "00:00"


@dataclass
class ProfileConfig:
    """Definición tipada de un perfil de transmisión scrcpy.

    Attributes:
        name (str): Nombre único del perfil.
        bitrate (str): Tasa de bits del video. Por defecto "8M".
        max_size (str): Tamaño máximo de resolución en un borde. Por defecto "1920".
        max_fps (str): Cuadros por segundo máximos. Por defecto "60".
        video_codec (str): Códec de video utilizado. Por defecto "h264".
        video_source (str): Origen del video ("display" o "camera"). Por defecto "display".
        camera_facing (Optional[str]): Orientación de la cámara (e.g. "front", "back") si aplica. Por defecto None.
        camera_id (Optional[str]): ID numérico de la cámara si aplica. Por defecto "0".
        audio_source (str): Origen de la captura de audio. Por defecto "playback".
        audio_codec (Optional[str]): Códec de audio. Por defecto None.
        turn_screen_off (bool): Apagar la pantalla del dispositivo. Por defecto True.
        force_screen_off_keyevent (bool): Forzar un evento de tecla especial para apagar la pantalla. Por defecto False.
        stay_awake (bool): Mantener el dispositivo despierto mientras se transmite. Por defecto True.
        v4l2_buffer (Optional[int]): Buffer V4L2 en dispositivos Linux. Por defecto None.
        shortcut_mod (Optional[str]): Tecla modificadora para atajos (e.g., "lalt"). Por defecto None.
        start_app (Optional[str]): Componente de aplicación para lanzar (paquete/actividad). Por defecto None.
        extra_args (str): Argumentos de línea de comandos adicionales que pasar a scrcpy. Por defecto "".
    """
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
    """Entrada en la Bóveda de Dispositivos Confiables.

    Attributes:
        serial (str): Identificador único del dispositivo aprobado.
        model (str): Nombre del modelo del dispositivo.
        alias (str): Alias guardado por el usuario.
        is_trusted (bool): Confirmación de confiabilidad. Por defecto True.
        trusted_since (str): Fecha/Hora en que se dio confianza al dispositivo. Por defecto "".
        last_seen (str): Fecha/Hora de la última conexión registrada. Por defecto "".
    """
    serial: str
    model: str
    alias: str
    is_trusted: bool = True
    trusted_since: str = ""
    last_seen: str = ""
