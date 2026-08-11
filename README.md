# 📱 MASV — Memexicanisimos Android Screen Viewer (v1.1)

![Open Source · Python · scrcpy](https://img.shields.io/badge/Open%20Source-Python%20%7C%20scrcpy-BF5AF2?style=for-the-badge&logo=python&logoColor=white)
![Version v1.1](https://img.shields.io/badge/Version-v1.1-64D2FF?style=for-the-badge)
![MIT License](https://img.shields.io/badge/License-MIT-32D74B?style=for-the-badge)
![Platforms](https://img.shields.io/badge/Platforms-Linux%20%7C%20Windows%20%7C%20macOS-0A84FF?style=for-the-badge)

[🇲🇽 Leer en Español](#español) | [🇺🇸 Read in English](#english)

<a name="english"></a>
**MASV** is an advanced, modern, and intuitive graphical user interface (GUI) to manage and stream multiple Android devices simultaneously using [`scrcpy`](https://github.com/Genymobile/scrcpy) and `ADB`.

Designed especially for **streamers, content creators, gamers, and developers** who need to use their mobile phones as secondary cameras for OBS Studio, external audio sources, high-performance screen mirrors, or testing tools.

> 🌐 **Official website**: [myinnervoid.github.io/Memexicanisimos-Android-Screen-Viewer](https://myinnervoid.github.io/Memexicanisimos-Android-Screen-Viewer)

---

## 🚀 What's New in Version 1.1

- 🛡️ **Secure Argument Parsing (`shlex`)**: Profiles with paths or titles containing spaces in quotes no longer break command execution.
- 📐 **Spacing Token System (`SPACE_*`)**: Normalization of margins and visual alignments throughout the Tkinter interface.
- 🧪 **Automated Test Suite (`unittest`)**: Unit test coverage in `tests/test_core.py` for IP/port parsing, serials, and profile management.
- 🪟 **Automated Installation on Windows**: Support for 100% portable packaging with `scrcpy` binaries in `bin/` or unattended installation via `winget`.
- ❓ **Expanded Interactive FAQ**: Complete usage guide with drop-down accordions and one-click copyable chips.
- 🌐 **Bilingual Support**: Added toggle between Spanish and English languages.

---

## 📋 Usage Guide by Operating System

### 🐧 Linux (Debian, Ubuntu, Mint, Arch, Fedora)

#### 1. Prerequisites and dependency installation
```bash
# On Debian / Ubuntu / Pop!_OS / Mint:
sudo apt update
sudo apt install adb scrcpy

# On Arch Linux / Manjaro:
sudo pacman -S android-tools scrcpy

# On Fedora:
sudo dnf install android-tools scrcpy
```

> 📷 **Virtual Webcam (Optional)**:
> ```bash
> sudo apt install v4l2loopback-dkms v4l2loopback-utils
> ```

#### 2. Download the precompiled binary
1. Download version `v1.1` from [Releases](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-Linux.tar.gz).
2. Extract the executable package:
   ```bash
   tar -xzvf MASV-Linux.tar.gz
   chmod +x MASV
   ./MASV
   ```

---

### 🪟 Windows (Windows 10 and Windows 11)

#### 1. Unattended or Portable Installation

**Option A — 100% Portable (Without installing anything)**:
Download the executable `MASV-Windows.exe` which includes the `scrcpy` binaries in the `bin/` folder. Just double-click and it will open immediately!

**Option B — Silent Command (`winget`)**:
Open PowerShell and run:
```powershell
winget install Genymobile.scrcpy --silent
```

#### 2. Run the precompiled binary
1. Download the `.exe` executable from [Releases](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-Windows.exe).
2. Double-click on `MASV-Windows.exe`.

---

### 🍎 macOS (macOS 12 Monterey or higher)

#### 1. Prerequisites
```bash
brew install scrcpy android-platform-tools
```

#### 2. Download the precompiled binary
1. Download from [Releases](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-macOS).
2. Grant execution permissions:
   ```bash
   chmod +x MASV-macOS
   ./MASV-macOS
   ```

---

## ✨ Main Features

| Feature | Description |
|----------------|-------------|
| 🎮 **Multi-device** | Connect and control multiple Android phones at the same time with different profiles |
| ⚙️ **Scene profiles** | Set resolution, FPS, bitrate (quality), codec (H.264/H.265/AV1) and audio sources |
| 🧙 **Wizard Assistant** | 7-stage step-by-step guide to create optimized profiles |
| 📡 **WiFi ADB connection** | Wireless IP connection with automatic *Get IP* button |
| 📷 **Virtual Webcam** | (Linux only) Route rear camera as `/dev/video9` device ready for OBS Studio |
| 🎛️ **Remote Controls** | Built-in buttons for volume, home, back, recents, power, and notifications |
| 📦 **APK Manager** | Install `.apk` files directly from your computer to your phone |
| 🖥️ **Log Console** | Real-time filtered event logging with log exporter |
| 🧪 **Test Suite** | Automatic unit testing module with `python3 -m unittest discover -s tests` |

---

## ⌨️ Keyboard Shortcuts

### 🟢 MASV Shortcuts (Interface)

| Shortcut | Function |
|-------|---------|
| `Ctrl + I` | Start / Stop active stream |
| `Ctrl + R` | Scan and refresh connected devices |
| `Ctrl + H` | Open Help and FAQ tab |
| `Ctrl + Q` | Exit application |
| `Del` | Stop selected session in the table |
| `Right Click` | Context menu on sessions table |

---

<br/>
<br/>

<a name="español"></a>
# 📱 MASV — Memexicanisimos Android Screen Viewer (v1.1)

![Open Source · Python · scrcpy](https://img.shields.io/badge/Open%20Source-Python%20%7C%20scrcpy-BF5AF2?style=for-the-badge&logo=python&logoColor=white)
![Versión v1.1](https://img.shields.io/badge/Versión-v1.1-64D2FF?style=for-the-badge)
![Licencia MIT](https://img.shields.io/badge/Licencia-MIT-32D74B?style=for-the-badge)
![Plataformas](https://img.shields.io/badge/Plataformas-Linux%20%7C%20Windows%20%7C%20macOS-0A84FF?style=for-the-badge)

**MASV** es una interfaz gráfica (GUI) avanzada, moderna e intuitiva para gestionar y transmitir múltiples dispositivos Android simultáneamente mediante [`scrcpy`](https://github.com/Genymobile/scrcpy) y `ADB`.

Diseñada especialmente para **streamers, creadores de contenido, gamers y desarrolladores** de la comunidad latina que necesitan usar sus teléfonos móviles como cámaras secundarias para OBS Studio, fuentes de audio externas, espejos de pantalla de alto rendimiento o herramientas de pruebas.

> 🌐 **Sitio web oficial**: [myinnervoid.github.io/Memexicanisimos-Android-Screen-Viewer](https://myinnervoid.github.io/Memexicanisimos-Android-Screen-Viewer)

---

## 🚀 Novedades de la Versión 1.1

- 🛡️ **Parseo Seguro de Argumentos (`shlex`)**: Los perfiles con rutas o títulos que contengan espacios entre comillas ya no rompen la ejecución del comando.
- 📐 **Sistema de Tokens de Espaciado (`SPACE_*`)**: Normalización de márgenes y alineaciones visuales en toda la interfaz Tkinter.
- 🧪 **Suite de Pruebas Automatizadas (`unittest`)**: Cobertura de pruebas unitarias en `tests/test_core.py` para parseo de IP/puertos, seriales y gestión de perfiles.
- 🪟 **Instalación Automatizada en Windows**: Soporte para empaquetado 100% portable con binarios `scrcpy` en `bin/` o instalación desatendida vía `winget`.
- ❓ **FAQ Interactivo Ampliado**: Guía completa de uso con acordones desplegables y chips copiables de un solo clic.

---

## 📋 Guía de uso por Sistema Operativo

### 🐧 Linux (Debian, Ubuntu, Mint, Arch, Fedora)

#### 1. Requisitos previos e instalación de dependencias
```bash
# En Debian / Ubuntu / Pop!_OS / Mint:
sudo apt update
sudo apt install adb scrcpy

# En Arch Linux / Manjaro:
sudo pacman -S android-tools scrcpy

# En Fedora:
sudo dnf install android-tools scrcpy
```

> 📷 **Webcam Virtual (Opcional)**:
> ```bash
> sudo apt install v4l2loopback-dkms v4l2loopback-utils
> ```

#### 2. Descargar el binario precompilado
1. Descarga la versión `v1.1` desde [Releases](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-Linux.tar.gz).
2. Extrae el paquete ejecutable:
   ```bash
   tar -xzvf MASV-Linux.tar.gz
   chmod +x MASV
   ./MASV
   ```

---

### 🪟 Windows (Windows 10 y Windows 11)

#### 1. Instalación Desatendida o Portable

**Opción A — 100% Portable (Sin instalar nada)**:
Descarga el ejecutable `MASV-Windows.exe` que incluye los binarios de `scrcpy` en la carpeta `bin/`. ¡Solo haz doble clic y abrirá de inmediato!

**Opción B — Comando Silencioso (`winget`)**:
Abre PowerShell y ejecuta:
```powershell
winget install Genymobile.scrcpy --silent
```

#### 2. Ejecutar el binario precompilado
1. Descarga el ejecutable `.exe` desde [Releases](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-Windows.exe).
2. Haz doble clic sobre `MASV-Windows.exe`.

---

### 🍎 macOS (macOS 12 Monterey o superior)

#### 1. Requisitos previos
```bash
brew install scrcpy android-platform-tools
```

#### 2. Descargar el binario precompilado
1. Descarga desde [Releases](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-macOS).
2. Otorga permisos de ejecución:
   ```bash
   chmod +x MASV-macOS
   ./MASV-macOS
   ```

---

## ✨ Características principales

| Característica | Descripción |
|----------------|-------------|
| 🎮 **Multidispositivo** | Conecta y controla múltiples teléfonos Android al mismo tiempo con diferentes perfiles |
| ⚙️ **Perfiles de escena** | Configura resolución, FPS, bitrate (calidad), códec (H.264/H.265/AV1) y fuentes de audio |
| 🧙 **Asistente Wizard** | Guía paso a paso de 7 etapas para crear perfiles optimizados |
| 📡 **Conexión WiFi ADB** | Conexión inalámbrica por IP con botón *Obtener IP* automático |
| 📷 **Webcam Virtual** | (Solo Linux) Enruta la cámara trasera como dispositivo `/dev/video9` listo para OBS Studio |
| 🎛️ **Mando de Controles** | Botones integrados para volumen, inicio, atrás, recientes, encendido y notificaciones |
| 📦 **Gestor de APKs** | Instala archivos `.apk` directamente desde la computadora hacia el móvil |
| 🖥️ **Consola de Logs** | Registro de eventos filtrado en tiempo real con exportador de logs |
| 🧪 **Suite de Pruebas** | Módulo de pruebas unitarias automáticas con `python3 -m unittest discover -s tests` |

---

## ⌨️ Atajos de teclado

### 🟢 Atajos propios de MASV (Interfaz)

| Atajo | Función |
|-------|---------|
| `Ctrl + I` | Iniciar / Detener transmisión activa |
| `Ctrl + R` | Buscar y refrescar dispositivos conectados |
| `Ctrl + H` | Abrir pestaña de Ayuda y Preguntas Frecuentes |
| `Ctrl + Q` | Salir de la aplicación |
| `Supr` | Detener la sesión seleccionada en la tabla |
| `Clic derecho` | Menú contextual en tabla de sesiones |

---

## 🤝 Licencia y Comunidad

Proyecto distribuido bajo la **Licencia MIT**. Desarrollado con pasión para la comunidad latina.
