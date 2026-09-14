# 🏛️ ADR MASTER: Migración a Arquitectura Hexagonal y Gobernanza de Hardware (v3.2)
**Proyecto:** MASV (Memexicanisimos Android Screen Viewer)  
**Ecosistema:** Estudio Memexicanisimos  
**Estado:** APROBADO Y CONGELADO  
**Fecha:** 14 de Septiembre, 2026  

---

## 📑 Índice de Decisiones

### A. Dominio y Contratos
* **ADR-001:** Modelo `Device` mínimo (`serial`, `model`, `android_version: int`, `connection_type`, `state`) + `DeviceCapabilities` resuelto bajo demanda (*lazy*).
* **ADR-002:** `SessionConfig` inmutable en dominio (`domain/models.py`). El ciclo de vida (`subprocess.Popen`, PID, `start()`, `stop()`) vive en `services/stream_service.py`. Regla dura: Dominio libre de `subprocess`, `socket` y `os.system`.
* **ADR-003:** `OperationResult[T]` con `__iter__` para compatibilidad con tuplas `ok, msg = res`.
* **ADR-004:** Catálogo `ErrorCode` con política de reintentos:
  - Automático: `CODEC_NOT_SUPPORTED` (fallback a H.264), `PORT_IN_USE` (puerto+1 base 27184), `SOCKET_TIMEOUT`.
  - Acción de usuario: `DEVICE_UNAUTHORIZED`, `DEVICE_OFFLINE`, `V4L2_MODULE_MISSING`.
* **ADR-005:** Perfiles versionados con `schema_version: int` y migración en carga. Nunca romper `config.json`.

### B. AdbEngine
* **ADR-006:** Socket ADB: reutilizar puerto 5037 por defecto. Aislar a 5038 solo si hay 2 fallos consecutivos de bind o por preferencia del usuario.
* **ADR-007:** Detección de chipset por heurística rápida de 2 `getprop` (`ro.product.manufacturer` y `ro.board.platform`). Para Huawei Y9: lista de códecs = `[H.264]` únicamente.
* **ADR-008:** Health Check híbrido reactivo con `adb track-devices` en hilo centinela + reconexión con backoff exponencial.
  - **Adenda ADR-008 (2026-09-14) · Protocolo track-devices:** El socket ADB emite longitud hexadecimal de 4 caracteres sin salto de línea (`<4 hex chars><payload N bytes>\n`). Implementación obligatoria: `read(4)` + `read(N)`. `readline()` queda prohibido en la cabecera para evitar lecturas truncadas o bloqueos.
* **ADR-009:** Cierre de `tcpip 5555` al salir únicamente si MASV activó el flag `wifi_activated_by_masv`.
  - **Adenda ADR-009 (2026-09-14) · Transición de transporte EMUI 10:** En Android 10, revertir a USB vía `adb usb` cierra el socket TCP provocando `error: closed` o `device not found`. Estos patrones de cierre son tratados como reversión exitosa.

### C. ScrcpyEngine
* **ADR-010:** Matriz de códecs en engine (`ScrcpyEngine.get_compatible_codecs(device)`), política de decisión en `StreamService`.
* **ADR-011:** Detección de fallo de códec en handshake por parseo de las primeras 10 líneas de `stderr`. Timeout calibrado: **5.0 s para Android ≤ 10 (Huawei Y9)**, **2.5 s para Android 11+**.
* **ADR-012:** Auto-fallback efímero + Toast informativo con opción de fijar en perfil.
* **ADR-013:** `--video-source=camera` con pestaña propia `ui/tabs/tab_camera.py` y selector rápido para el **Curso de Fotografía**.
* **ADR-014:** Verificación de versión: en scrcpy 4.x el servidor va empaquetado/embebido en el binario (`scrcpy --version`). `_compare_versions` se mantiene como contrato durmiente de compatibilidad si scrcpy desacopla versiones de binario/jar en versiones futuras.
* **ADR-014b:** Prioridad de título de ventana: `build_command` inyecta automáticamente `--window-title "MASV: {device.model}"` a menos que el usuario especifique un `--window-title` personalizado en `extra_args` (en cuyo caso el título del usuario tiene precedencia y suprime el auto).

### D. V4l2Driver
* **ADR-015:** Soporte nativo para Debian / Ubuntu (`v4l2loopback-dkms` y `v4l2-ctl`).
* **ADR-016:** Si el usuario no pertenece al grupo `video`, mostrar instrucción `sudo usermod -aG video $USER` y modo degradado (solo ventana, sin V4L2).
* **ADR-017:** Soporte para 2 webcams virtuales fijas: `/dev/video2` (cámara cenital) y `/dev/video3` (apoyo / plano medio).

### E. Instalador y Despliegue
* **ADR-018:** Raíz en `~/.MASV/` (`bin/`, `assets/`, `config/`, `logs/`) + enlaces XDG en `~/.local/bin/MASV` y `~/.local/share/applications/MASV.desktop`.
* **ADR-019:** Instalación atómica con `os.replace()` de `MASV.new` a `MASV`.
* **ADR-020:** Bóveda `vault.enc` cifrada con `cryptography.Fernet` derivada de `machine-id` + salt local.
* **ADR-021:** Rotación de logs con `RotatingFileHandler(maxBytes=5MB, backupCount=3)`.

### F. UI y No-Solapamiento
* **ADR-022:** Tkinter nativo optimizado con tema Warm Stone (`ui/theme.py`). Sin frameworks pesados. Arranque <200ms, RAM <45MB.
* **ADR-023:** `UIStateMachine` explícita con 5 estados: `IDLE`, `SCANNING`, `STREAMING`, `EMPTY`, `FAULT`.
* **ADR-024:** Lazy loading de pestañas por evento `<<NotebookTabChanged>>`. Cero imports de plataforma en top-level.
* **ADR-025:** Modales como `tk.Toplevel` con `grab_set()` y centrado relativo.

### G. Testing y CI
* **ADR-026:** Tests con mocks de subprocesos (`unittest.mock.patch`). Sin dependencia de hardware físico en CI.
* **ADR-027:** CI Linux-first con `@pytest.mark.linux_only`.
* **ADR-028:** Cobertura >85% en `domain/` y `core/`.

### H. Roadmap Strangler Fig
* **Paso 1 (Inmediato):** Parche en `managers.py` (`--no-audio` en Android 10 + puertos dinámicos para 2 teléfonos).
* **Paso 2:** Extraer `core/adb_engine.py` y `core/scrcpy_engine.py`.
* **Paso 3:** Extraer `services/stream_service.py` y `services/device_service.py`.
* **Paso 4:** Modularizar pestañas en `ui/tabs/`.

### I. Transversales
* **ADR-029:** Pool de sesiones en `StreamService` con puertos incrementales desde `27183`.
* **ADR-030:** Cero telemetría externa. Botón "Exportar Diagnóstico" (ZIP local sanitizado).
* **ADR-031:** Atajos en `config.json` e internacionalización de errores en `i18n.py`.

---

## 🔒 Apéndice: API Contract v1 (Firmas Congeladas Paso 2)

Las siguientes firmas y contratos de datos están estrictamente congelados para la implementación de la Capa A y Capa C. Cualquier cambio requiere reabrir el ADR correspondiente.

### 1. Modelos de Dominio (`domain/models.py`)

```python
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
    max_fps: Optional[float] = 60.0
    camera_facing: Optional[str] = None
    camera_id: Optional[str] = "0"
    audio_source: str = "playback"
    turn_screen_off: bool = True
    stay_awake: bool = True
    extra_args: tuple[str, ...] = ()
```

### 2. Protocolos de Dominio (`domain/protocols.py`)

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SessionProcess(Protocol):
    @property
    def pid(self) -> int: ...
    def poll(self) -> int | None: ...
    def terminate(self) -> None: ...
    def kill(self) -> None: ...
    def wait(self, timeout: float | None = None) -> int: ...

@runtime_checkable
class TrackerHandle(Protocol):
    def stop(self, timeout: float = 2.0) -> None: ...
    def is_alive(self) -> bool: ...
```

### 3. PortAllocator (`core/port_allocator.py`)

```python
class PortAllocator:
    def __init__(self, base: int = 27183, max_offset: int = 20) -> None: ...
    def acquire(self) -> OperationResult[int]: ...
    def release(self, port: int) -> None: ...
    def reserved(self) -> frozenset[int]: ...
```

### 4. AdbEngine (`core/adb_engine.py`)

```python
class AdbEngine:
    def __init__(
        self,
        adb_binary: Path,
        preferred_socket_port: int = 5037,
        fallback_socket_port: int = 5038,
    ) -> None: ...
    @property
    def effective_socket_port(self) -> int: ...
    def start_daemon(self) -> OperationResult[int]: ...
    def list_devices(self) -> OperationResult[list[Device]]: ...
    def get_properties(self, serial: str) -> OperationResult[dict[str, str]]: ...
    def start_tcpip(self, serial: str, port: int = 5555) -> OperationResult[None]: ...
    def revert_tcpip(self, serial: str) -> OperationResult[None]: ...
    def connect_wifi(self, host: str, port: int = 5555) -> OperationResult[str]: ...
    def disconnect_wifi(self, serial: str) -> OperationResult[None]: ...
    def track_devices_async(
        self,
        on_change: Callable[[list[Device]], None],
        on_daemon_dead: Callable[[ErrorCode], None],
        max_reconnect_attempts: int = 5,
    ) -> OperationResult[TrackerHandle]: ...
    def stop_tracker(self) -> None: ...
```

### 5. ScrcpyEngine (`core/scrcpy_engine.py`)

```python
class ScrcpyEngine:
    def __init__(self, scrcpy_binary: Path, server_jar: Path) -> None: ...
    def verify_server_version(self) -> OperationResult[str]: ...
    def _compare_versions(self, client_ver: str, server_ver: str) -> OperationResult[str]: ...
    def get_compatible_codecs(self, device: Device, caps: DeviceCapabilities) -> OperationResult[list[Codec]]: ...
    def build_command(self, config: SessionConfig, device: Device, caps: DeviceCapabilities) -> OperationResult[list[str]]: ...
    def launch(
        self,
        config: SessionConfig,
        device: Device,
        caps: DeviceCapabilities,
        on_stderr_line: Callable[[str], None] | None = None,
        on_exit: Callable[[int], None] | None = None,
    ) -> OperationResult[SessionProcess]: ...
    def is_codec_failure(self, stderr_lines: list[str], elapsed_s: float, android_sdk: int) -> bool: ...
```

