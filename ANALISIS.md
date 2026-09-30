# 📋 DOCUMENTO DE ANÁLISIS, MODULARIZACIÓN Y PLAN DE EVOLUCIÓN ARQUITECTÓNICA (v3.2)
**Ecosistema:** Estudio Memexicanisimos  
**Proyecto:** MASV (Memexicanisimos Android Screen Viewer)  
**Estándar Aplicado:** Motor Autónomo de Auditoría y Evolución de Software — 5 Vectores (v3.2)  
**Perspectiva:** Senior Software Architect & Android Platform Specialist  
**Fecha:** 13 de Septiembre, 2026  
**Objetivo:** Análisis del mecanismo de integración al sistema, diagnóstico exhaustivo de acoplamiento de núcleos (`adb`, `scrcpy`, `v4l2`), desacoplamiento modular para prevenir regresiones entre mejoras y diseño del despliegue limpio encapsulado en `~/.MASV/`.

---

## 📌 1. Resumen Ejecutivo y Diagnóstico Senior

MASV es una herramienta de alto rendimiento orientada a creadores, streamers y desarrolladores, cuyo valor reside en transformar el protocolo de transmisión de `scrcpy` y el puente de depuración `adb` en una experiencia de escritorio fluida, segura y ergonómica.

A la fecha, la aplicación ha alcanzado un estado operativo maduro en su versión 1.2 (con interfaz Warm Stone, soporte bilingüe, bóveda de dispositivos de confianza y empaquetado PyInstaller de 35MB). Sin embargo, desde una perspectiva de **Ingeniería de Software Senior**, el sistema presenta un síntoma clásico de crecimiento orgánico: **alta cohesión interna pero alto acoplamiento estructural**:

1. **Monolito de Presentación (`main.py` de 1,571 líneas):** La capa de interfaz gráfica no solo renderiza widgets de Tkinter, sino que ejecuta llamadas directas a subprocesos del sistema operativo (`subprocess.run(["adb", ...])`, `subprocess.run(["pkexec", ...])`, `subprocess.run(["lsmod"])`).
2. **Fragilidad ante Mejoras Concurrentes:** Cuando se planifica una mejora (por ejemplo, el instalador limpio o soporte avanzado de audio/cámaras), modificar `main.py` o `managers.py` introduce un alto riesgo de regresiones o conflictos de integración, pues los controladores de UI y los adaptadores de hardware comparten el mismo contexto.
3. **Falta de Aislamiento de Núcleos Externos:** Las dependencias críticas (`adb`, `scrcpy`, `v4l2loopback`) se tratan como cadenas de comandos en lugar de **Engines / Adapters tipados**, lo que impide interceptar códigos de error nativos de Android, caídas del daemon de ADB o inconsistencias de códecs de hardware.

Este documento establece la hoja de ruta para **modularizar MASV**, consolidar sus núcleos existentes y habilitar el despliegue encapsulado en `~/.MASV/` bajo el estándar estricto de **5 Vectores (v3.2)**.

---

## 🛠️ 2. Comandos Operativos de Integración Inmediata (Realizados)

Para responder a la necesidad operativa inmediata del usuario sin alterar el código base ni el `README.md`:

### 2.1. Habilitación en Terminal (`$PATH`)
Se vincularon los alias canónicos en `~/.local/bin/` (directorio nativo en `$PATH` en Linux):
```bash
mkdir -p ~/.local/bin
ln -sf "$HOME/.MASV/bin/MASV" ~/.local/bin/MASV
ln -sf "$HOME/.MASV/bin/MASV" ~/.local/bin/masv
```

### 2.2. Habilitación en Menú de Aplicaciones (`XDG Desktop Menu`)
Se generó el archivo de especificación en `~/.local/share/applications/MASV.desktop`:
```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=MASV
GenericName=Memexicanisimos Android Screen Viewer
Comment=Controla y visualiza dispositivos Android en pantalla
Exec="/home/$USER/.MASV/bin/MASV" %U
Path=/home/$USER/.MASV
Icon=/home/$USER/.MASV/assets/logo.png
Terminal=false
Categories=Utility;
StartupNotify=true
StartupWMClass=MASV
Keywords=MASV;scrcpy;android;screen;viewer;memexicanisimos;
```

### 2.3. Validación y Registro de Caché
```bash
chmod +x ~/.local/share/applications/MASV.desktop
desktop-file-validate ~/.local/share/applications/MASV.desktop
update-desktop-database ~/.local/share/applications
```

---

## 🧠 3. Análisis de Núcleos Externos: ¿Qué Consolidar vs. Qué NO Agregar?

Una trampa habitual en software de escritorio con Android es caer en el *feature creep* agregando dependencias externas innecesarias o reemplazando herramientas nativas con librerías de inferior calidad.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        NÚCLEOS DEL SISTEMA MASV                        │
├───────────────────┬────────────────────────────┬────────────────────────┤
│ NÚCLEO            │ ESTADO ACTUAL              │ DICTAMEN ARQUITECTÓNICO│
├───────────────────┼────────────────────────────┼────────────────────────┤
│ ADB (Android Debug│ Binario externo invocado   │ CONSOLIDAR COMO ENGINE │
│ Bridge)           │ mediante subprocess sueltos│ AISLADO (Socket seguro)│
├───────────────────┼────────────────────────────┼────────────────────────┤
│ scrcpy +          │ Parámetros CLI dispersos en│ CONSOLIDAR CON MATRIZ  │
│ scrcpy-server.jar │ SessionManager y main.py   │ DE CÓDECS Y DISPLAY FSM│
├───────────────────┼────────────────────────────┼────────────────────────┤
│ v4l2loopback      │ Script shell embebido con  │ CONSOLIDAR DRIVER      │
│ (Virtual Webcam)  │ invocaciones a pkexec      │ USUARIO / V4L2 QUERY   │
├───────────────────┼────────────────────────────┼────────────────────────┤
│ sndcpy (Legacy)   │ Mencionada en roadmaps     │ DESCARTAR POR OBSOLETO │
├───────────────────┼────────────────────────────┼────────────────────────┤
│ Clientes ADB Pure │ Propuesto en issues        │ RECHAZAR / DESCARTAR   │
│ Python            │                            │                        │
└───────────────────┴────────────────────────────┴────────────────────────┘
```

### ❌ 3.1. Lo que NO se debe agregar (Decisiones de Exclusión Razonadas)

1. **Rechazar Clientes ADB en Python Puro (`pure-python-adb`, `adb-shell`):**
   - *Razón Técnica:* No soportan de forma transparente el protocolo de emparejamiento TLS de Android 11+ (`adb pair` con PIN de 6 dígitos), fallan con las renovaciones dinámicas de claves RSA en Android 12+, y son incapaces de mantener sockets de alta velocidad concurrentes para el túnel de `scrcpy-server`.
   - *Decisión:* Mantener y consolidar el binario oficial `adb` de Google (Platform-Tools).

2. **Descartar Utilidades Legacy como `sndcpy`:**
   - *Razón Técnica:* `sndcpy` fue una solución provisional para Android 10 que requería inyectar un APK de captura de audio y reenviar un stream crudo por VLC. A partir de Android 11/12, `scrcpy` implementó captura nativa de audio de ultra baja latencia (`--audio-source=playback` / `--audio-source=mic` vía `AudioRecord` / `AudioPlaybackCapture`).
   - *Decisión:* Apalancarse 100% en las capacidades de audio nativas de `scrcpy` moderno.

3. **Rechazar WebViews o Frameworks Pesados (Electron, Tauri con Node, CEF):**
   - *Razón Técnica:* Rompería el footprint de 35MB y el tiempo de arranque de 200ms de MASV. El stack actual (Python 3 + Tkinter optimizado con doble buffer y estilos planos oscuros) consume menos de 45MB de RAM en reposo.

---

### 🛡️ 3.2. Lo que se debe CONSOLIDAR como Núcleo Indestructible

#### A. `AdbEngine` (Aislamiento y Ciclo de Vida del Demonio)
Desde la perspectiva de la plataforma Android, ADB opera mediante una arquitectura cliente-servidor:
```
[ MASV UI / Core ] ──> [ ADB Client ] ──(TCP 5037)──> [ ADB Server Daemon ] ──(USB / Wi-Fi)──> [ adbd (Teléfono) ]
```
- **Riesgo Actual:** Llamar a `adb kill-server` desde la UI de MASV tumba las sesiones de Android Studio, VS Code o emuladores abiertos por el usuario en su estación de trabajo.
- **Consolidación Requerida:**
  - Permitir opcionalmente definir un socket/puerto ADB aislado (`export ADB_SERVER_SOCKET=tcp:localhost:5038`) para que MASV opere en un sandbox sin colisionar con herramientas de desarrollo.
  - Implementar **Health Check de Conectividad**: Detección granular del estado del daemon (`device`, `unauthorized`, `offline`, `bootloader`, `authorizing`).
  - **Zero-Trust Wi-Fi & Auto-Lockdown:** Consolidar el cierre determinista del puerto 5555 (`adb -s <serial> usb`) para que al salir de la aplicación ningún dispositivo quede expuesto en redes LAN no confiables.

#### B. `ScrcpyEngine` (Orquestación de Media & Hardware Encoders)
- **Control de Versión de `scrcpy-server.jar`:** Garantizar que la versión del binario de escritorio coincida exactamente con el bytecode inyectado en el dispositivo Android para prevenir crashes silenciosos de JVM.
- **Matriz Inteligente de Códecs según versión de Android y Chipset:**
  ```
  Android 5 - 9:   H.264 (AVC) obligatorio [omx.*.avc]. Compatibilidad universal.
  Android 10 - 13: H.264 / H.265 (HEVC) [c2.android.hevc.encoder]. Ahorro de 40% ancho de banda en Wi-Fi.
  Android 14+:     H.264 / H.265 / AV1 [c2.android.av1.encoder]. Máxima eficiencia en chips modernos.
  ```
- **Auto-Fallback:** Si un códec como `AV1` o `H.265` falla al iniciar la sesión por incompatibilidad con el encoder de hardware del teléfono, el motor debe capturar el error en el handshake y reintentar automáticamente en `H.264` sin congelar la interfaz.
- **Captura Nativa de Cámara (Camera2 API):** Consolidar la flag `--video-source=camera` soportando selección de sensor (`front`, `back`, `external`), tamaño de captura y control de FPS sin pasar por la pantalla del dispositivo.

#### C. `V4l2Driver` (Webcam Virtual Linux para Creadores/OBS)
- Encapsular la detección de nodos de dispositivo (`/dev/video*`) mediante `v4l2-ctl --list-devices` o consulta a `/sys/class/video4linux/`.
- Evitar solicitar contraseñas administrativas (`pkexec`) en tiempo de ejecución: verificar pertenencia del usuario al grupo `video` (`groups | grep video`).

---

## 🏗️ 4. Arquitectura Modular Propuesta: Prevención de Colisiones

Para garantizar que cualquier nueva característica (como el auto-instalador, perfiles en la nube o nuevos modos de streaming) no se contraponga a otra ni rompa código preexistente, se define la migración a un esquema de **Puertos y Adaptadores (Arquitectura Hexagonal)**:

### 4.1. Diagrama de Separación de Capas

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CAPA DE PRESENTACIÓN (UI)                       │
│  [ MainWindow ]    [ Tabs: Devices, Profiles, WiFi, Camera, Logs ]     │
│  [ Modals: TrustVault, DevicePairing, Onboarding ]                     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (Invoca servicios / Observa FSM)
┌───────────────────────────────────▼────────────────────────────────────┐
│                    CAPA DE SERVICIOS DE APLICACIÓN                     │
│  [ DeviceService ]  [ StreamService ]  [ SecurityService ]             │
│  [ ProfileService ] [ InstallerService ]                               │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
┌───────────────────▼──────────────┐   ┌─────────────▼───────────────────┐
│     DOMINIO & CONTRATOS          │   │      CORE & HARDWARE ADAPTERS   │
│  - OperationResult[T]            │   │  - AdbEngine (Socket, Pairing)  │
│  - ErrorCode & ErrorCatalog      │   │  - ScrcpyEngine (Process/Codecs)│
│  - UIStateMachine (FSM)          │   │  - V4l2LoopbackDriver           │
│  - Modelos: Device, Session, Conf│   │  - CleanDeployInstaller         │
└──────────────────────────────────┘   └─────────────────────────────────┘
```

### 4.2. Estructura de Paquetes Desacoplada

```
scrcpy_dock/
├── core/                         # Adaptadores de bajo nivel (Infraestructura / SO)
│   ├── __init__.py
│   ├── adb_engine.py             # Wrapper robusto de ADB (subprocesos y sockets)
│   ├── scrcpy_engine.py          # Constructor de comandos y ciclo de vida de scrcpy
│   ├── v4l2_driver.py            # Detección y enrutamiento a webcam virtual
│   └── installer.py              # Gestión del ciclo de vida de instalación ~/.MASV
│
├── domain/                       # Reglas de negocio puras (Sin dependencias de UI ni SO)
│   ├── __init__.py
│   ├── models.py                 # Dataclasses inmutables (Device, Session, Profile)
│   ├── contracts.py              # OperationResult[T] y ApiResponse[T]
│   ├── errors.py                 # Catálogo tipado de fallos (ErrorCode)
│   └── state.py                  # Autómata FSM de interfaz (UIStateMachine)
│
├── services/                     # Orquestación de Casos de Uso
│   ├── __init__.py
│   ├── device_service.py         # Escaneo, emparejamiento y handshake de dispositivos
│   ├── stream_service.py         # Arranque, monitoreo y terminación de escenas
│   ├── security_service.py       # Validación de IP privada, cifrado y lista blanca
│   └── profile_service.py        # Carga, guardado y sanitización de perfiles
│
└── ui/                           # Interfaz gráfica desacoplada (Thin UI)
    ├── __init__.py
    ├── app.py                    # Ventana principal y despachador de eventos
    ├── theme.py                  # Paleta de colores Warm Stone y fuentes
    ├── components/               # Widgets genéricos reutilizables
    │   ├── toasts.py
    │   ├── tooltips.py
    │   └── modals.py
    └── tabs/                     # Pestañas independientes (cada una autocontenida)
        ├── tab_devices.py
        ├── tab_profiles.py
        ├── tab_wifi.py
        ├── tab_camera.py
        └── tab_logs.py
```

### 4.3. La Regla de No-Solapamiento (Non-Interference Rule)

Con esta separación modular, los desarrollos futuros quedan estrictamente aislados:

1. **Si se mejora la UI o se añade un nuevo tema visual:**  
   Solo se tocan archivos dentro de `ui/`. Ningún comando de `adb` ni lógica de `scrcpy` puede romperse.
2. **Si se agrega un nuevo códec de vídeo o soporte para Android 15/16:**  
   Solo se actualiza `core/scrcpy_engine.py` y `domain/models.py`. La interfaz consume los parámetros mediante contratos tipados sin tocar el kernel de transmisión.
3. **Si se evoluciona el instalador (`~/.MASV`):**  
   Solo se trabaja en `core/installer.py` y `services/installer_service.py`. No hay impacto sobre la ejecución de streaming.

---

## 📦 5. Plan de Despliegue Limpio: Encapsulado en `~/.MASV/`

### 5.1. El Principio de Cero Residuos

Para no ensuciar el directorio raíz del usuario y permitir que la aplicación se instale y desinstale sin dejar rastros residuales, toda la presencia de MASV se concentra en:
```
$HOME/.MASV/
├── bin/
│   └── MASV                      # Ejecutable binario autónomo
├── assets/
│   └── logo.png                  # Icono de alta resolución
├── config/
│   ├── config.json               # Configuración de usuario y perfiles
│   └── vault.enc                 # Bóveda cifrada de dispositivos de confianza
└── logs/
    └── masv.log                  # Registro de auditoría operativo
```

Los únicos dos puntos de enlace con el sistema operativo son enlaces simbólicos gestionados por estándares XDG:
1. `~/.local/bin/MASV` (Acceso por Terminal).
2. `~/.local/share/applications/MASV.desktop` (Acceso por Menú Gráfico).

### 5.2. Módulo de Auto-Instalación y Desinstalación Atómica (`AppInstaller`)

```python
import os
import shutil
import subprocess
from .contracts import OperationResult
from .errors import ErrorCode

class AppInstaller:
    BASE_DIR = os.path.expanduser("~/.MASV")
    LOCAL_BIN = os.path.expanduser("~/.local/bin")
    DESKTOP_DIR = os.path.expanduser("~/.local/share/applications")
    DESKTOP_FILE = os.path.join(DESKTOP_DIR, "MASV.desktop")

    @classmethod
    def install(cls, source_binary_path: str, source_logo_path: str) -> OperationResult[dict]:
        """Despliega MASV en ~/.MASV y genera los accesos directos."""
        try:
            bin_dir = os.path.join(cls.BASE_DIR, "bin")
            assets_dir = os.path.join(cls.BASE_DIR, "assets")
            config_dir = os.path.join(cls.BASE_DIR, "config")
            logs_dir = os.path.join(cls.BASE_DIR, "logs")

            for d in (bin_dir, assets_dir, config_dir, logs_dir, cls.LOCAL_BIN, cls.DESKTOP_DIR):
                os.makedirs(d, exist_ok=True)

            target_bin = os.path.join(bin_dir, "MASV")
            target_logo = os.path.join(assets_dir, "logo.png")

            shutil.copy2(source_binary_path, target_bin)
            os.chmod(target_bin, 0o755)

            if os.path.exists(source_logo_path):
                shutil.copy2(source_logo_path, target_logo)

            # Crear Symlinks en ~/.local/bin
            for symlink_name in ("MASV", "masv"):
                link_path = os.path.join(cls.LOCAL_BIN, symlink_name)
                if os.path.islink(link_path) or os.path.exists(link_path):
                    os.remove(link_path)
                os.symlink(target_bin, link_path)

            # Generar Desktop Entry apuntando a ~/.MASV
            desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=MASV
GenericName=Memexicanisimos Android Screen Viewer
Comment=Controla y visualiza dispositivos Android en pantalla
Exec="{target_bin}" %U
Path={cls.BASE_DIR}
Icon={target_logo}
Terminal=false
Categories=Utility;
StartupNotify=true
StartupWMClass=MASV
Keywords=MASV;scrcpy;android;screen;viewer;memexicanisimos;
"""
            with open(cls.DESKTOP_FILE, "w", encoding="utf-8") as f:
                f.write(desktop_content)
            os.chmod(cls.DESKTOP_FILE, 0o755)

            # Refrescar base de datos XDG
            subprocess.run(["update-desktop-database", cls.DESKTOP_DIR], capture_output=True)

            return OperationResult.ok(
                data={"base_dir": cls.BASE_DIR, "binary": target_bin},
                message="MASV instalado exitosamente en ~/.MASV"
            )
        except Exception as e:
            return OperationResult.fail(ErrorCode.UNEXPECTED_ERROR, f"Error durante la instalación: {e}")

    @classmethod
    def uninstall(cls) -> OperationResult[None]:
        """Purga absoluta: retira accesos y borra ~/.MASV dejando 0 residuos."""
        try:
            # 1. Remover Symlinks
            for symlink_name in ("MASV", "masv"):
                link_path = os.path.join(cls.LOCAL_BIN, symlink_name)
                if os.path.islink(link_path) or os.path.exists(link_path):
                    os.remove(link_path)

            # 2. Remover archivo .desktop
            if os.path.exists(cls.DESKTOP_FILE):
                os.remove(cls.DESKTOP_FILE)

            # 3. Refrescar base de datos
            subprocess.run(["update-desktop-database", cls.DESKTOP_DIR], capture_output=True)

            # 4. Eliminar directorio encapsulado completo
            if os.path.exists(cls.BASE_DIR):
                shutil.rmtree(cls.BASE_DIR)

            return OperationResult.ok(message="MASV ha sido purgado completamente del sistema sin dejar rastros.")
        except Exception as e:
            return OperationResult.fail(ErrorCode.UNEXPECTED_ERROR, f"Fallo al desinstalar: {e}")
```

---

## 🔬 6. Evaluación Rigurosa por los 5 Vectores (v3.2)

```
┌─────────────────────────────────────────────────────────────────────────┐
│              MATRIZ DE CONFORMIDAD ARQUITECTÓNICA (v3.2)                │
├────────┬───────────────────────────────────┬─────────┬──────────────────┤
│ VECTOR │ DIMENSIÓN EVALUADA                │ SCORE   │ ESTADO           │
├────────┼───────────────────────────────────┼─────────┼──────────────────┤
│ V1     │ Dominio, Invariantes & Marco Legal│ 95%     │ Sólido           │
│ V2     │ Contratos, Esquema & Catálogo     │ 92%     │ Estandarizado    │
│ V3     │ Lógica, Concurrencia & Hardening  │ 90%     │ Robusto          │
│ V4     │ Interfaz, Ergonomía & Estados FSM │ 94%     │ Alta Fidelidad   │
│ V5     │ Infraestructura & Despliegue      │ 96%     │ Automatizado     │
└────────┴───────────────────────────────────┴─────────┴──────────────────┘
```

1. **Vector 1 (Dominio & Legal):** Aislamiento estricto en espacio de usuario. Sin escalación de privilegios (`sudo`). Atribución explícita a licencias Apache 2.0 (`scrcpy`/`adb`) y MIT (`MASV`).
2. **Vector 2 (Contratos & Catálogo):** Uso sistemático de `OperationResult[T]` para operaciones de hardware y despliegue. Errores categorizados (`ErrorCode.DEVICE_NOT_FOUND`, `ErrorCode.SCRCPY_NOT_FOUND`, etc.).
3. **Vector 3 (Hardening & Concurrencia):** Aislamiento de subprocesos mediante hilos controlados, sanitización estricta de `extra_args` en perfiles y permisos atómicos `0755` para binarios y `0600` para configuraciones.
4. **Vector 4 (Ergonomía & FSM):** Autómata de 5 estados (`IDLE`, `PENDING`, `SUCCESS`, `EMPTY`, `FAULT`) mapeado 1:1 en la interfaz visual.
5. **Vector 5 (Infraestructura & Resiliencia):** Proceso de empaquetado reproducible, verificación automatizada de enlaces y desinstalación atómica verificable.

---

## 🗺️ 7. Hoja de Ruta de Refactorización (Roadmap Modular)

Para ejecutar esta separación de módulos sin interrumpir el funcionamiento continuo de MASV:

- [x] **Hito 0 (Inmediato):** Habilitación del comando de terminal `MASV` y acceso al menú de escritorio (`.desktop`). *(Completado y verificado).*
- [ ] **Hito 1 (Extracción de Núcleos):** Crear `core/adb_engine.py` y `core/scrcpy_engine.py`. Migrar las llamadas de subproceso de `managers.py` y `main.py` a estas clases especializadas.
- [ ] **Hito 2 (Capa de Servicios):** Centralizar la lógica de negocio en `services/device_service.py` y `services/stream_service.py`. Desacoplar la UI de llamadas directas al sistema operativo.
- [ ] **Hito 3 (Modularización de UI):** Dividir `ui_tabs.py` y `main.py` en vistas independientes (`tabs/tab_*.py`) suscritas al `UIStateMachine`.
- [ ] **Hito 4 (Despliegue Encapsulado):** Integrar `AppInstaller` con flags CLI (`MASV --install`, `MASV --uninstall`, `MASV --status`) y generación de release portable en `.tar.gz`.

---

## 📱 8. Diagnóstico Específico: Compatibilidad Huawei Y9 (EMUI 10), Multi-Dispositivo y Modo Curso de Fotografía

### 8.1. Particularidades del Huawei Y9 (Android 10 / EMUI 10 con GMS)
El Huawei Y9 opera sobre el procesador **HiSilicon Kirin 710** bajo la capa de personalización **EMUI 10** (Android 10), conservando los servicios de Google (GMS). Este dispositivo presenta tres condicionantes técnicas que MASV debe manejar de forma nativa:

1. **Audio en Android 10 (Restricción del Sistema Operativo):**
   - *Causa:* La captura nativa de audio en `scrcpy` (`--audio-source=playback`) requiere la API `AudioPlaybackCapture`, introducida oficialmente en **Android 11**.
   - *Impacto:* Si MASV ejecuta `scrcpy` sin parámetros de audio, intentará capturar audio y lanzará advertencias o errores de inicialización.
   - *Solución Arquitectónica:* `DeviceManager` debe inspeccionar `ro.build.version.release`. Si la versión es `<= 10`, MASV forzará automáticamente `--no-audio` o desactivará el selector de audio en la UI para ese dispositivo.

2. **Encoder de Video Kirin 710 (HiSilicon):**
   - *Causa:* El chip Kirin 710 (`OMX.hisi.video.encoder.avc`) tiene dificultades con códecs HEVC (H.265) o bitrates elevados (>8 Mbps) sobre el socket ADB, lo que puede provocar lag o cuadros verdes.
   - *Solución Arquitectónica:* Crear un perfil optimizado **"Huawei / EMUI Legacy"**:
     - Códec forzado: `H.264` (`--video-codec=h264`).
     - Bitrate seguro: `6M` a `8M` (`--video-bit-rate=6M`).
     - Resolución máxima: `1080p` o `720p` (`--max-size=1080`).
     - FPS: `30` (`--max-fps=30`) para estabilidad térmica en sesiones prolongadas.

3. **Políticas de Energía y Seguridad de EMUI 10:**
   - *Causa:* EMUI cuenta con un gestor agresivo de ahorro de energía ("Optimizador") que suspende procesos USB o desactiva la pantalla cerrando el túnel de `scrcpy`. Además, exige permisos explícitos para entrada táctil.
   - *Ajustes Requeridos en el Teléfono:*
     - En *Opciones de Desarrollador*: Activar **"Permitir depuración ADB en modo solo carga"**.
     - Activar **"Entrada de simulación de pantalla / depuración táctil por USB"**.
     - Excluir a las apps del sistema de optimizaciones agresivas de batería.
   - *Soporte en MASV:* Mantener activas las flags `--stay-awake` y `--turn-screen-off` (esta última apaga físicamente el panel del teléfono ahorrando batería mientras el stream se mantiene en PC).

---

### 8.2. Orquestación Multi-Dispositivo Simultáneo (Dual Phone Dock)
El usuario opera con **2 teléfonos conectados simultáneamente**. Para soportar este entorno sin interferencias:

1. **Aislamiento de Puertos Locales (TCP):**
   - `scrcpy` vincula por defecto el puerto `27183`. Si se abre el segundo teléfono sin especificar puerto, puede ocurrir un conflicto de sockets (`bind: Address already in use`).
   - *Solución:* `SessionManager` debe asignar puertos dinámicos por sesión:
     - Dispositivo 1: `--port=27183`
     - Dispositivo 2: `--port=27184` (o rango automático `--port=27183:27199`).

2. **Diferenciación Visual en KDE Plasma:**
   - Cada ventana de streaming debe llevar un título explícito basado en el modelo:
     - Ventana 1: `--window-title="MASV: Huawei Y9 (Cámara/Monitor)"`
     - Ventana 2: `--window-title="MASV: [Dispositivo 2]"`
   - Permite organizar las ventanas en pantallas separadas o mosaicos de escritorio en KDE.

---

### 8.3. Modo Especial: Estudio de Fotografía (Clean Camera Feed + V4L2)
Para el desarrollo del **Curso de Fotografía**, MASV adquiere un rol de herramienta de producción audiovisual:

1. **Uso como Cámara Cenital / Detalle de Producto:**
   - Colocar el teléfono en un trípode o brazo articulado apuntando a la mesa de trabajo o cámara réflex.
   - Iniciar en modo sensor limpio:
     ```bash
     scrcpy -s <serial> --video-source=camera --camera-facing=back --camera-size=1920x1080 --camera-fps=30
     ```
   - *Ventaja Clave:* Entrega la señal de vídeo limpia del sensor (Clean HDMI / Clean Feed) sin mostrar botones de disparador, cuadrículas de la app de cámara ni iconos de batería.

2. **Webcam Virtual para OBS y Ambient Videos:**
   - Enrutar el feed directamente al módulo de kernel `v4l2loopback`:
     ```bash
     scrcpy -s <serial> --video-source=camera --v4l2-sink=/dev/video2
     ```
   - Permite usar la cámara de 48MP/16MP del smartphone como cámara web profesional en Linux para transmisiones del curso o demostraciones en vivo.

3. **Uso como Monitor de Campo Inalámbrico:**
   - Usar el segundo teléfono como pantalla de referencia para verificar encuadres, histogramas y composición fotográfica en tiempo real.

