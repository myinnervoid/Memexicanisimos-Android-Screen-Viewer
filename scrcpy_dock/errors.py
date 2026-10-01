"""Catálogo formal de códigos de error y mapeo semántico para MASV.

Estándar de 5 Vectores — Vector 2 (Contratos de Datos & Catálogo de Fallos)
"""

from enum import Enum
from typing import Dict, NamedTuple

class ErrorCode(str, Enum):
    # Sin error
    NONE = "NONE"

    # Errores de Dependencias & Binarios
    ADB_NOT_FOUND = "ERR_ADB_NOT_FOUND"
    SCRCPY_NOT_FOUND = "ERR_SCRCPY_NOT_FOUND"
    BINARY_NOT_FOUND = "ERR_BINARY_NOT_FOUND"
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

    # Errores de Gestión de Aplicaciones
    APK_INSTALL_FAILED = "ERR_APK_INSTALL_FAILED"

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
    ErrorCode.BINARY_NOT_FOUND: ErrorDetail(
        code=ErrorCode.BINARY_NOT_FOUND,
        title_es="Binario no encontrado",
        title_en="Binary Not Found",
        description_es="No se encontró el binario requerido en el layout local ni en el PATH del sistema.",
        description_en="The required binary was not found in local layout or system PATH.",
        remediation_es="Verifica la instalación del binario o colócalo en ~/.MASV/bin/.",
        remediation_en="Verify binary installation or place it in ~/.MASV/bin/."
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
    ErrorCode.APK_INSTALL_FAILED: ErrorDetail(
        code=ErrorCode.APK_INSTALL_FAILED,
        title_es="No se pudo instalar la APK",
        title_en="APK installation failed",
        description_es="ADB rechazó la instalación del paquete en el dispositivo.",
        description_en="ADB rejected the package installation on the device.",
        remediation_es="Comprueba que el APK es compatible con la versión de Android del teléfono "
                       "y que la opción 'Instalar vía USB' está permitida en el dispositivo.",
        remediation_en="Check that the APK is compatible with the phone's Android version and that "
                       "'Install via USB' is allowed on the device."
    ),
    ErrorCode.DEVICE_OFFLINE: ErrorDetail(
        code=ErrorCode.DEVICE_OFFLINE,
        title_es="Dispositivo desconectado",
        title_en="Device offline",
        description_es="El teléfono perdió comunicación con el socket ADB.",
        description_en="The phone lost communication with the ADB socket.",
        remediation_es="Reconecta el cable USB, evita que el puerto suspenda la energía y pulsa "
                       "'Reiniciar ADB'.",
        remediation_en="Reconnect the USB cable, prevent the port from suspending power, and press "
                       "'Restart ADB'."
    ),
    ErrorCode.LOCKDOWN_FAILED: ErrorDetail(
        code=ErrorCode.LOCKDOWN_FAILED,
        title_es="No se pudo cerrar el puerto TCP/IP",
        title_en="Could not close the TCP/IP port",
        description_es="El comando 'adb usb' no consiguió devolver el dispositivo a modo USB.",
        description_en="The 'adb usb' command could not return the device to USB mode.",
        remediation_es="Desconecta y vuelve a conectar el cable y reintenta el blindaje; si persiste, "
                       "reinicia la depuración inalámbrica en el teléfono.",
        remediation_en="Disconnect and reconnect the cable and retry the lockdown; if it persists, "
                       "restart wireless debugging on the phone."
    ),
    ErrorCode.CONFIG_CORRUPT: ErrorDetail(
        code=ErrorCode.CONFIG_CORRUPT,
        title_es="Configuración corrupta",
        title_en="Corrupted configuration",
        description_es="El archivo de configuración o la bóveda no se pudieron leer.",
        description_en="The configuration file or the vault could not be read.",
        remediation_es="Restaura el archivo desde una copia o elimina config.json para regenerar los "
                       "valores por defecto (se perderán los perfiles).",
        remediation_en="Restore the file from a backup or delete config.json to regenerate defaults "
                       "(profiles will be lost)."
    ),
    ErrorCode.INVALID_EXTRA_ARGS: ErrorDetail(
        code=ErrorCode.INVALID_EXTRA_ARGS,
        title_es="Argumento no permitido en el perfil",
        title_en="Disallowed profile argument",
        description_es="El perfil incluye una bandera que no está en la lista blanca de seguridad.",
        description_en="The profile includes a flag that is not in the security whitelist.",
        remediation_es="Edita el perfil y elimina los argumentos adicionales no permitidos.",
        remediation_en="Edit the profile and remove the disallowed extra arguments."
    ),
    ErrorCode.DEPENDENCY_INSTALL_FAILED: ErrorDetail(
        code=ErrorCode.DEPENDENCY_INSTALL_FAILED,
        title_es="Fallo al instalar dependencias",
        title_en="Dependency Installation Failed",
        description_es="El gestor de paquetes no pudo descargar o instalar los paquetes requeridos.",
        description_en="The package manager could not download or install required packages.",
        remediation_es="Comprueba tu conexión a Internet o instala adb y scrcpy manualmente.",
        remediation_en="Check your Internet connection or install adb and scrcpy manually."
    ),
    ErrorCode.DEVICE_BUSY: ErrorDetail(
        code=ErrorCode.DEVICE_BUSY,
        title_es="Dispositivo ocupado",
        title_en="Device Busy",
        description_es="El dispositivo ya tiene una sesión de captura o transmisión activa.",
        description_en="The device already has an active capture or streaming session.",
        remediation_es="Detén la sesión previa o desconecta y vuelve a conectar el dispositivo.",
        remediation_en="Stop the previous session or disconnect and reconnect the device."
    ),
    ErrorCode.ADB_SERVER_FAILED: ErrorDetail(
        code=ErrorCode.ADB_SERVER_FAILED,
        title_es="Error del servidor ADB",
        title_en="ADB Server Error",
        description_es="No se pudo comunicar con el servidor local de ADB o el puerto 5037 está ocupado.",
        description_en="Could not communicate with local ADB server or port 5037 is busy.",
        remediation_es="Pulsa 'Reiniciar ADB' en MASV o reinicia el daemon desde la terminal.",
        remediation_en="Click 'Restart ADB' in MASV or restart daemon from terminal."
    ),
    ErrorCode.ADB_DAEMON_DEAD: ErrorDetail(
        code=ErrorCode.ADB_DAEMON_DEAD,
        title_es="Demonio ADB finalizado inesperadamente",
        title_en="ADB Daemon Terminated",
        description_es="El proceso en segundo plano de ADB murió durante la operación.",
        description_en="The background ADB daemon process died during operation.",
        remediation_es="Reinicia el servicio ADB desde el dock o reconecta el cable USB.",
        remediation_en="Restart ADB service from the dock or reconnect the USB cable."
    ),
    ErrorCode.PORT_POOL_EXHAUSTED: ErrorDetail(
        code=ErrorCode.PORT_POOL_EXHAUSTED,
        title_es="Grupo de puertos agotado",
        title_en="Port Pool Exhausted",
        description_es="No hay puertos TCP disponibles en el rango asignado para nuevas sesiones.",
        description_en="No TCP ports available in the allocated range for new sessions.",
        remediation_es="Cierra sesiones scrcpy inactivas o libera puertos huérfanos.",
        remediation_en="Close inactive scrcpy sessions or release orphaned ports."
    ),
    ErrorCode.SCRCPY_SERVER_VERSION_MISMATCH: ErrorDetail(
        code=ErrorCode.SCRCPY_SERVER_VERSION_MISMATCH,
        title_es="Discrepancia en versión de scrcpy-server",
        title_en="scrcpy-server Version Mismatch",
        description_es="La versión de scrcpy-server.jar no coincide con la versión del binario cliente.",
        description_en="The scrcpy-server.jar version does not match the client binary version.",
        remediation_es="Actualiza scrcpy o descarga el scrcpy-server correspondiente a tu versión.",
        remediation_en="Update scrcpy or download the matching scrcpy-server for your version."
    ),
    ErrorCode.PAIRING_TIMEOUT: ErrorDetail(
        code=ErrorCode.PAIRING_TIMEOUT,
        title_es="Tiempo de espera agotado al emparejar",
        title_en="Pairing Timeout",
        description_es="El dispositivo Android no respondió al emparejamiento Wi-Fi a tiempo.",
        description_en="The Android device did not respond to Wi-Fi pairing in time.",
        remediation_es="Mantén encendida la pantalla en 'Depuración inalámbrica' y reintenta.",
        remediation_en="Keep screen on in 'Wireless debugging' and retry."
    ),
    ErrorCode.CONNECTION_REFUSED: ErrorDetail(
        code=ErrorCode.CONNECTION_REFUSED,
        title_es="Conexión rechazada",
        title_en="Connection Refused",
        description_es="El dispositivo rechazó la conexión TCP en la IP y puerto especificados.",
        description_en="The device refused TCP connection on specified IP and port.",
        remediation_es="Verifica que la depuración inalámbrica esté activa y los datos sean correctos.",
        remediation_en="Verify wireless debugging is active and settings match the phone."
    ),
    ErrorCode.BLOCKED_IP_ACCESS: ErrorDetail(
        code=ErrorCode.BLOCKED_IP_ACCESS,
        title_es="Acceso bloqueado a dirección IP",
        title_en="IP Address Access Blocked",
        description_es="La dirección IP ingresada está bloqueada por la política de seguridad.",
        description_en="The entered IP address is blocked by the security policy.",
        remediation_es="Revisa la lista de IPs bloqueadas y los ajustes de Modo Seguro.",
        remediation_en="Check blocked IP list and Safe Mode settings."
    ),
    ErrorCode.PROCESS_SPAWN_ERROR: ErrorDetail(
        code=ErrorCode.PROCESS_SPAWN_ERROR,
        title_es="Error al iniciar proceso",
        title_en="Process Spawn Error",
        description_es="El sistema operativo no pudo iniciar el subproceso requerido.",
        description_en="The operating system failed to spawn the required subprocess.",
        remediation_es="Verifica los permisos de ejecución del binario y la memoria disponible.",
        remediation_en="Verify binary execution permissions and available system memory."
    ),
    ErrorCode.PROCESS_TIMEOUT: ErrorDetail(
        code=ErrorCode.PROCESS_TIMEOUT,
        title_es="Tiempo de espera del proceso agotado",
        title_en="Process Timeout",
        description_es="El proceso tardó más del tiempo máximo permitido en responder.",
        description_en="The process exceeded the maximum allowed response time.",
        remediation_es="Comprueba la estabilidad del enlace USB/Wi-Fi y reduce la resolución.",
        remediation_en="Check USB/Wi-Fi link stability and reduce resolution or bitrate."
    ),
    ErrorCode.V4L2_LOOPBACK_ERROR: ErrorDetail(
        code=ErrorCode.V4L2_LOOPBACK_ERROR,
        title_es="Error de cámara virtual V4L2",
        title_en="V4L2 Loopback Error",
        description_es="No se pudo acceder o emitir hacia el dispositivo virtual /dev/videoX.",
        description_en="Could not access or stream to virtual device /dev/videoX.",
        remediation_es="Asegúrate de haber cargado el módulo v4l2loopback en el sistema.",
        remediation_en="Ensure v4l2loopback kernel module is loaded on the system."
    ),
    ErrorCode.PROFILE_NOT_FOUND: ErrorDetail(
        code=ErrorCode.PROFILE_NOT_FOUND,
        title_es="Perfil no encontrado",
        title_en="Profile Not Found",
        description_es="El perfil de transmisión especificado no existe en la configuración.",
        description_en="The specified streaming profile does not exist in configuration.",
        remediation_es="Elige un perfil existente en la lista o crea uno nuevo en Perfiles.",
        remediation_en="Select an existing profile or create a new one in Profiles."
    ),
    ErrorCode.INVALID_INPUT: ErrorDetail(
        code=ErrorCode.INVALID_INPUT,
        title_es="Parámetro o entrada inválida",
        title_en="Invalid Input Parameter",
        description_es="Uno o más datos proporcionados no cumplen con el formato requerido.",
        description_en="One or more provided values do not meet the required format.",
        remediation_es="Revisa los valores ingresados y corrige los campos señalados.",
        remediation_en="Check entered values and correct the highlighted fields."
    ),
    ErrorCode.UNKNOWN_ERROR: ErrorDetail(
        code=ErrorCode.UNKNOWN_ERROR,
        title_es="Error no clasificado",
        title_en="Unclassified Error",
        description_es="Ha ocurrido un error inesperado no catalogado.",
        description_en="An unexpected uncataloged error has occurred.",
        remediation_es="Consulta masv.log o la consola de depuración para más información.",
        remediation_en="Check masv.log or debug console for further information."
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
