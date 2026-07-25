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
