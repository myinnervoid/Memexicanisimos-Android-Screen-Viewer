# 📱 MASV — Memexicanisimos Android Screen Viewer (v1.2)

![Open Source · Python · scrcpy](https://img.shields.io/badge/Open%20Source-Python%20%7C%20scrcpy-F59E0B?style=for-the-badge&logo=python&logoColor=white)
![Version v1.2](https://img.shields.io/badge/Version-v1.2-EA580C?style=for-the-badge)
![MIT License](https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge)
![Platforms](https://img.shields.io/badge/Platforms-Linux%20%7C%20Windows%20%7C%20macOS-D97706?style=for-the-badge)

[🇲🇽 Leer en Español](#español) | [🇺🇸 Read in English](#english)

---

<a name="english"></a>
## 🇺🇸 English Documentation

**MASV** (Memexicanisimos Android Screen Viewer) is an advanced, modern, and intuitive graphical user interface (GUI) to manage and stream Android devices on PC using [`scrcpy`](https://github.com/Genymobile/scrcpy) and `ADB`.

Designed especially for **gamers, streamers, content creators, and developers** who need high-performance screen mirroring, camera streaming for OBS Studio, wireless Wi-Fi TCP/IP connections, or automated profile management.

> 🌐 **Official website**: [memexicanisimos.com/masv](https://memexicanisimos.com)

---

### 🚀 What's New in Version 1.2

- 🎨 **Warm Cozy Dark UI**: Completely redesigned interface using Warm Stone (`#1C1917`), Amber Gold (`#F59E0B`), and Terracotta (`#EA580C`).
- 🗄️ **Native Window Menu Bar**: Top menu bar (`File`, `Edit`, `View`, `Device`, `Help`) with keyboard shortcuts (`Ctrl+Q`, `Ctrl+R`, `Alt+1..6`).
- 📦 **1-Click Linux `.run` Installer**: Self-extracting installer for Linux that installs to `~/.local/share/masv/`, creates desktop shortcuts, and enables the `MASV` terminal command.
- 🛡️ **Strict IP Validation**: Built-in `ipaddress` validation and strict `0600`/`0700` POSIX atomic permissions.
- 🎬 **Expanded Codec & Camera Support**: Support for `VP8`, `VP9`, `AV1`, `H.264`, `H.265`, Android 12+ native camera capture, audio codecs, and v4l2 virtual webcams.
- 🌐 **Full Bilingual Support**: Toggle dynamically between Spanish and English on both the app and web landing page.

---

### 📋 Installation & Usage

#### 🐧 Linux (Debian, Ubuntu, Mint, Arch, Fedora)

1. **Download the 1-Click Installer**:
   Download `MASV-Linux-Installer.run` from [Releases](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest).

2. **Run the Installer**:
   ```bash
   chmod +x MASV-Linux-Installer.run
   ./MASV-Linux-Installer.run
   ```
   *This automatically creates the desktop icon and enables the `MASV` command in your terminal.*

---

#### 🪟 Windows (Windows 10 & 11)

1. Download `MASV-Windows.exe` from [Releases](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest).
2. Double-click `MASV-Windows.exe` to run immediately (no installation required).

---

<a name="español"></a>
## 🇲🇽 Documentación en Español

**MASV** es una interfaz gráfica (GUI) avanzada, moderna e intuitiva para controlar y transmitir dispositivos Android en PC utilizando el núcleo de [`scrcpy`](https://github.com/Genymobile/scrcpy) y `ADB`.

Diseñada especialmente para **gamers, streamers, creadores de contenido y desarrolladores** que requieren transmisión de pantalla a 120 FPS, webcam virtual HD para OBS Studio, conexión inalámbrica por Wi-Fi y gestión de perfiles de alta eficiencia.

---

### 🚀 Novedades de la Versión 1.2

- 🎨 **Interfaz Cálida Personal**: Rediseño visual en tonos *Warm Stone*, Ámbar Dorado y Terracota para mayor confort visual.
- 🗄️ **Barra de Menús Nativa Superior**: Menú superior (`Archivo`, `Editar`, `Ver`, `Dispositivo`, `Ayuda`) con atajos (`Ctrl+Q`, `Ctrl+R`, `Alt+1..6`).
- 📦 **Instalador Ejecutable `.run` para Linux**: Instalador ejecutable de 1-clic que configura el acceso directo en Escritorio y habilita el comando `MASV` en terminal.
- 🛡️ **Validación Estricta de IP**: Integración del módulo `ipaddress` y permisos POSIX `0600`/`0700` atómicos.
- 🎬 **Códecs y Cámaras Avanzadas**: Soporte para `VP8`, `VP9`, `AV1`, `H.264`, `H.265`, cámara nativa Android 12+, códecs de audio y `v4l2loopback`.
- 🌐 **Soporte Bilingüe Completo**: Conmutación dinámica entre Español e Inglés tanto en la aplicación como en la página web.

---

### 📋 Guía de Uso por Sistema Operativo

#### 🐧 Linux (Debian, Ubuntu, Mint, Arch, Fedora)

1. **Descargar el Instalador de 1-Clic**:
   Descarga `MASV-Linux-Installer.run` desde la sección de [Releases](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest).

2. **Ejecutar el Instalador**:
   ```bash
   chmod +x MASV-Linux-Installer.run
   ./MASV-Linux-Installer.run
   ```
   *Esto instalará la app, creará el icono en tu Escritorio y habilitará el comando `MASV` en cualquier terminal.*

---

#### 🪟 Windows (Windows 10 y 11)

1. Descarga `MASV-Windows.exe` desde [Releases](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest).
2. Haz doble clic sobre `MASV-Windows.exe` para abrir inmediatamente sin necesidad de instalar nada.

---

## 📜 Licencia

Desarrollado por **Memexicanisimos Studio** bajo la licencia **MIT**. Basado en el motor de código abierto de Genymobile/scrcpy.
