"""Catálogo formal de códigos de error y mapeo semántico para MASV.

Estándar de 5 Vectores — Vector 2 (Contratos de Datos & Catálogo de Fallos)
"""

from enum import Enum
from typing import Dict, NamedTuple, Optional

class ErrorCode(str, Enum):
    # Sin error
    NONE = "NONE"

    # Errores de Dependencias & Binarios
    ADB_NOT_FOUND = "ERR_ADB_NOT_FOUND"
    SCRCPY_NOT_FOUND = "ERR_SCRCPY_NOT_FOUND"
    DEPENDENCY_INSTALL_FAILED = "ERR_DEPENDENCY_INSTALL_FAILED"

    # Errores de Dispositivos & ADB
    DEVICE_NOT_FOUND = "ERR_DEVICE_NOT_FOUND"
    DEVICE_UNAUTHORIZED = "ERR_DEVICE_UNAUTHORIZED"
    DEVICE_OFFLINE = "ERR_DEVICE_OFFLINE"
    DEVICE_BUSY = "ERR_DEVICE_BUSY"
    ADB_SERVER_FAILED = "ERR_ADB_SERVER_FAILED"
    ADB_DAEMON_DEAD = "ERR_ADB_DAEMON_DEAD"

    # Recursos & Puertos
    PORT_POOL_EXHAUSTED = "ERR_PORT_POOL_EXHAUSTED"

    # Dependencias de scrcpy
    SCRCPY_SERVER_VERSION_MISMATCH = "ERR_SCRCPY_SERVER_VERSION_MISMATCH"

    # Errores de Red & Emparejamiento Wi-Fi
    INVALID_IP_RANGE = "ERR_INVALID_IP_RANGE"
    PAIRING_FAILED = "ERR_PAIRING_FAILED"
    PAIRING_TIMEOUT = "ERR_PAIRING_TIMEOUT"
    CONNECTION_REFUSED = "ERR_CONNECTION_REFUSED"
    LOCKDOWN_FAILED = "ERR_LOCKDOWN_FAILED"

    # Errores de Seguridad & Bóveda de Confianza
    UNTRUSTED_DEVICE = "ERR_UNTRUSTED_DEVICE"
    BLOCKED_IP_ACCESS = "ERR_BLOCKED_IP_ACCESS"
    UNSAFE_ARGUMENT_DETECTED = "ERR_UNSAFE_ARGUMENT_DETECTED"
    INVALID_EXTRA_ARGS = "ERR_INVALID_EXTRA_ARGS"

    # Errores de Sesión & Ejecución de scrcpy
    PROCESS_SPAWN_ERROR = "ERR_PROCESS_SPAWN_ERROR"
    PROCESS_CRASH = "ERR_PROCESS_CRASH"
    PROCESS_TIMEOUT = "ERR_PROCESS_TIMEOUT"
    V4L2_LOOPBACK_ERROR = "ERR_V4L2_LOOPBACK_ERROR"

    # Errores de Configuración & Estado
    CONFIG_CORRUPT = "ERR_CONFIG_CORRUPT"
    PROFILE_NOT_FOUND = "ERR_PROFILE_NOT_FOUND"
    INVALID_INPUT = "ERR_INVALID_INPUT"
    UNKNOWN_ERROR = "ERR_UNKNOWN_ERROR"


class ErrorDetail(NamedTuple):
    code: ErrorCode
    title_es: str
    title_en: str
    description_es: str
    description_en: str
    remediation_es: str
    remediation_en: str


ERROR_CATALOG: Dict[ErrorCode, ErrorDetail] = {
    ErrorCode.NONE: ErrorDetail(
        code=ErrorCode.NONE,
        title_es="Operación Exitosa",
        title_en="Operation Successful",
        description_es="La operación se completó sin errores.",
        description_en="The operation completed without errors.",
        remediation_es="",
        remediation_en=""
    ),
    ErrorCode.ADB_NOT_FOUND: ErrorDetail(
        code=ErrorCode.ADB_NOT_FOUND,
        title_es="Binario ADB no encontrado",
        title_en="ADB Binary Not Found",
        description_es="No se encontró el ejecutable 'adb' en la ruta portable ni en el PATH del sistema.",
        description_en="The 'adb' executable was not found in portable path or system PATH.",
        remediation_es="Usa el botón de instalación automática o instala Android Platform Tools.",
        remediation_en="Use the auto-install button or install Android Platform Tools."
    ),
    ErrorCode.SCRCPY_NOT_FOUND: ErrorDetail(
        code=ErrorCode.SCRCPY_NOT_FOUND,
        title_es="Binario scrcpy no encontrado",
        title_en="scrcpy Binary Not Found",
        description_es="No se encontró el ejecutable 'scrcpy' en el sistema.",
        description_en="The 'scrcpy' executable was not found on the system.",
        remediation_es="Haz clic en 'Instalar Dependencias' en la pestaña de Ayuda.",
        remediation_en="Click 'Install Dependencies' in the Help tab."
    ),
    ErrorCode.DEVICE_NOT_FOUND: ErrorDetail(
        code=ErrorCode.DEVICE_NOT_FOUND,
        title_es="Dispositivo no detectado",
        title_en="Device Not Found",
        description_es="No hay ningún dispositivo Android conectado o seleccionado.",
        description_en="No Android device connected or selected.",
        remediation_es="Conecta tu dispositivo vía USB o verifica la IP Wi-Fi.",
        remediation_en="Connect your device via USB or verify the Wi-Fi IP."
    ),
    ErrorCode.DEVICE_UNAUTHORIZED: ErrorDetail(
        code=ErrorCode.DEVICE_UNAUTHORIZED,
        title_es="Dispositivo no autorizado",
        title_en="Device Unauthorized",
        description_es="El teléfono requiere autorizar la depuración USB en su pantalla.",
        description_en="The phone requires authorizing USB debugging on its screen.",
        remediation_es="Desbloquea el teléfono y pulsa 'Permitir siempre desde esta computadora'.",
        remediation_en="Unlock the phone and tap 'Always allow from this computer'."
    ),
    ErrorCode.INVALID_IP_RANGE: ErrorDetail(
        code=ErrorCode.INVALID_IP_RANGE,
        title_es="Rango de IP no permitido",
        title_en="Disallowed IP Range",
        description_es="El Modo Seguro bloquea conexiones a direcciones IP públicas o externas (RFC 1918).",
        description_en="Safe Mode blocks connections to public or external IP addresses (RFC 1918).",
        remediation_es="Asegúrate de ingresar una IP local (ej. 192.168.x.x o 10.x.x.x).",
        remediation_en="Ensure you enter a local private IP (e.g. 192.168.x.x or 10.x.x.x)."
    ),
    ErrorCode.PAIRING_FAILED: ErrorDetail(
        code=ErrorCode.PAIRING_FAILED,
        title_es="Fallo en emparejamiento seguro",
        title_en="Secure Pairing Failed",
        description_es="El código de 6 dígitos o el puerto de emparejamiento fueron rechazados por Android.",
        description_en="The 6-digit code or pairing port was rejected by Android.",
        remediation_es="Revisa el código mostrado en Opciones de Desarrollador > Depuración inalámbrica.",
        remediation_en="Check the code shown under Developer Options > Wireless Debugging."
    ),
    ErrorCode.UNTRUSTED_DEVICE: ErrorDetail(
        code=ErrorCode.UNTRUSTED_DEVICE,
        title_es="Dispositivo no confiable",
        title_en="Untrusted Device",
        description_es="El dispositivo no está verificado en la Bóveda de Confianza.",
        description_en="The device is not verified in the Trusted Devices Vault.",
        remediation_es="Agrega el dispositivo a la Bóveda de Dispositivos Confiables antes de transmitir.",
        remediation_en="Add the device to the Trusted Devices Vault before streaming."
    ),
    ErrorCode.UNSAFE_ARGUMENT_DETECTED: ErrorDetail(
        code=ErrorCode.UNSAFE_ARGUMENT_DETECTED,
        title_es="Argumento no seguro detectado",
        title_en="Unsafe Argument Detected",
        description_es="Se detectó un argumento potencialmente peligroso en los comandos extra.",
        description_en="A potentially dangerous argument was detected in extra commands.",
        remediation_es="Elimina comandos no permitidos de la configuración del perfil.",
        remediation_en="Remove disallowed commands from the profile configuration."
    ),
    ErrorCode.PROCESS_CRASH: ErrorDetail(
        code=ErrorCode.PROCESS_CRASH,
        title_es="Finalización inesperada de scrcpy",
        title_en="Unexpected scrcpy Termination",
        description_es="El proceso de transmisión terminó con un código de error.",
        description_en="The streaming process terminated with an error code.",
        remediation_es="Revisa los registros de la consola para ver los detalles del error.",
        remediation_en="Check the console logs for detailed error output."
    ),
}

def get_error_detail(code: ErrorCode) -> ErrorDetail:
    """Devuelve la información detallada para un código de error determinado."""
    return ERROR_CATALOG.get(
        code,
        ErrorDetail(
            code=code,
            title_es="Error Desconocido",
            title_en="Unknown Error",
            description_es=f"Ha ocurrido un error no clasificado ({code.value}).",
            description_en=f"An unclassified error has occurred ({code.value}).",
            remediation_es="Consulta la consola de depuración para más detalles.",
            remediation_en="Check the debug console for more details."
        )
    )
