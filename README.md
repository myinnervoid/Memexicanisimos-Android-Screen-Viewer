# 📱 MASV — Memexicanisimos Android Screen Viewer

![Open Source · Python · scrcpy](https://img.shields.io/badge/Open%20Source-Python%20%7C%20scrcpy-BF5AF2?style=for-the-badge&logo=python&logoColor=white)
![Licencia MIT](https://img.shields.io/badge/Licencia-MIT-32D74B?style=for-the-badge)
![Plataformas](https://img.shields.io/badge/Plataformas-Linux%20%7C%20Windows%20%7C%20macOS-0A84FF?style=for-the-badge)

**MASV** es una interfaz gráfica (GUI) avanzada, moderna e intuitiva para gestionar y transmitir múltiples dispositivos Android simultáneamente mediante [`scrcpy`](https://github.com/Genymobile/scrcpy) y `ADB`.

Diseñada especialmente para **streamers, creadores de contenido, gamers y desarrolladores** de la comunidad latina que necesitan usar sus teléfonos móviles como cámaras secundarias para OBS Studio, fuentes de audio externas, espejos de pantalla de alto rendimiento o herramientas de pruebas.

> 🌐 **Sitio web oficial**: [myinnervoid.github.io/Memexicanisimos-Android-Screen-Viewer](https://myinnervoid.github.io/Memexicanisimos-Android-Screen-Viewer)

---

## 📋 Guía de uso por Sistema Operativo

Selecciona tu sistema operativo a continuación. Cada sección contiene **todos los pasos necesarios** (requisitos, descarga del binario, ejecución desde fuente y compilación) de forma totalmente independiente.

---

### 🐧 Linux (Debian, Ubuntu, Mint, Arch, Fedora)

#### 1. Requisitos previos e instalación de dependencias
Abre una terminal e instala `adb` y `scrcpy` desde el gestor de paquetes de tu distribución:

```bash
# En Debian / Ubuntu / Pop!_OS / Mint:
sudo apt update
sudo apt install adb scrcpy

# En Arch Linux / Manjaro:
sudo pacman -S android-tools scrcpy

# En Fedora:
sudo dnf install android-tools scrcpy
```

> 📷 **Opcional (Webcam Virtual)**: Si deseas usar la cámara de tu teléfono como webcam en OBS Studio, instala también el módulo `v4l2loopback`:
> ```bash
> sudo apt install v4l2loopback-dkms v4l2loopback-utils
> ```

#### 2. Descargar el binario precompilado
1. Descarga la última versión desde [Releases](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-Linux.tar.gz).
2. Extrae el paquete ejecutable y otórgale permisos:
   ```bash
   tar -xzvf MASV-Linux.tar.gz
   chmod +x MASV
   ./MASV
   ```

#### 3. Ejecutar desde el código fuente
Si prefieres correr la aplicación usando Python directamente:
```bash
# Clona el repositorio
git clone https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer.git
cd Memexicanisimos-Android-Screen-Viewer

# Crea un entorno virtual e instala librerías
python3 -m venv .venv
source .venv/bin/activate
pip install pystray Pillow

# Ejecuta MASV
python run.py
```

#### 4. Compilar tu propio ejecutable (PyInstaller)
Para generar el archivo ejecutable `.tar.gz` independiente en tu sistema:
```bash
pip install pyinstaller pystray Pillow
python3 build.py
```
El resultado estará listo en `dist/MASV` y el paquete comprimido `MASV-Linux.tar.gz` se creará automáticamente en la raíz.

---

### 🪟 Windows (Windows 10 y Windows 11)

#### 1. Requisitos previos e instalación de dependencias
Para que MASV pueda comunicarse con tus dispositivos Android, necesitas tener `adb` y `scrcpy`.

**Opción A — Recomendada (Gestor `winget`)**:
Abre una terminal de PowerShell o CMD como administrador y ejecuta:
```cmd
winget install Genymobile.scrcpy
```
Este comando instalará automáticamente `scrcpy` y `adb` configurando sus variables de entorno.

**Opción B — Manual (ZIP Portable)**:
1. Descarga el paquete ZIP portable de scrcpy desde [Releases de Genymobile](https://github.com/Genymobile/scrcpy/releases).
2. Descomprime el archivo en una carpeta de tu preferencia (ej. `C:\scrcpy`).
3. Agrega la ruta `C:\scrcpy` a la variable de entorno `PATH` del sistema, **o bien** copia el contenido del ZIP (`scrcpy.exe`, `adb.exe`, `SDL2.dll`, etc.) dentro de la carpeta `bin/` del proyecto MASV.

#### 2. Descargar el binario precompilado
1. Descarga el ejecutable `.exe` listo para usar desde [Releases](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-Windows.exe).
2. Haz doble clic sobre `MASV-Windows.exe` para abrir la aplicación directamente sin instalación.

#### 3. Ejecutar desde el código fuente
Si prefieres ejecutar el código desde la consola de Windows:
```cmd
:: Clona el repositorio
git clone https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer.git
cd Memexicanisimos-Android-Screen-Viewer

:: Crea el entorno virtual
python -m venv .venv
.venv\Scripts\activate
pip install pystray Pillow

:: Ejecuta MASV
python run.py
```

#### 4. Compilar tu propio ejecutable (PyInstaller)
Para generar un archivo `.exe` portable único:
```cmd
pip install pyinstaller pystray Pillow
python build.py
```
*(Si agregaste los binarios de scrcpy dentro de la carpeta `bin/`, el script los empaquetará dentro del `.exe` resultante en `dist\MASV-Windows.exe`).*

---

### 🍎 macOS (macOS 12 Monterey o superior)

#### 1. Requisitos previos e instalación de dependencias
Instala `scrcpy` y las herramientas de Android usando Homebrew desde la Terminal:

```bash
# Instalar Homebrew si no lo tienes: https://brew.sh
brew install scrcpy android-platform-tools
```

#### 2. Descargar el binario precompilado
1. Descarga el binario para macOS desde [Releases](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-macOS).
2. Otorga permisos de ejecución en la Terminal:
   ```bash
   chmod +x MASV-macOS
   ./MASV-macOS
   ```

#### 3. Ejecutar desde el código fuente
Para correr la app en modo desarrollo con Python:
```bash
# Clona el repositorio
git clone https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer.git
cd Memexicanisimos-Android-Screen-Viewer

# Crea un entorno virtual e instala dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install pystray Pillow

# Inicia la aplicación
python run.py
```

#### 4. Compilar tu propio ejecutable (PyInstaller)
Para compilar un ejecutable independiente en tu Mac:
```bash
pip install pyinstaller pystray Pillow
python3 build.py
```
El archivo ejecutable se generará dentro de la carpeta `dist/MASV-macOS`.

---

## ✨ Características principales

| Característica | Descripción |
|----------------|-------------|
| 🎮 **Multidispositivo** | Conecta y controla múltiples teléfonos Android al mismo tiempo con diferentes perfiles |
| ⚙️ **Perfiles de escena** | Configura resolución, FPS, bitrate (calidad), códec (H.264/H.265/AV1) y fuentes de audio |
| 🧙 **Asistente Wizard** | Guía paso a paso de 6 etapas para crear perfiles optimizados según tu caso de uso |
| 📡 **Conexión WiFi ADB** | Conexión inalámbrica por IP. Botón *Obtener IP* para detectar la dirección del móvil vía ADB |
| 📷 **Webcam Virtual** | (Solo Linux) Enruta la cámara trasera como dispositivo `/dev/video9` listo para OBS Studio |
| 🎛️ **Mando de Controles** | Botones integrados para volumen, inicio, atrás, recientes, encendido y notificaciones |
| 📦 **Gestor de APKs** | Instala archivos `.apk` en el dispositivo seleccionado mediante un explorador de archivos nativo |
| 🛎️ **Bandeja del Sistema** | Minimiza la ventana al System Tray con contador de sesiones activas |
| 💾 **Memoria de Ventana** | Guarda automáticamente la posición y tamaño de la interfaz entre reinicios |
| ❓ **FAQ Interactiva** | 8 secciones con acordeón desplegable y comandos listos para copiar al portapapeles |
| 👋 **Onboarding Guiado** | Tutorial interactivo de bienvenida la primera vez que ejecutas la app |

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
| `Clic derecho` | Menú contextual en tabla de sesiones (copiar serial, copiar comando, forzar cierre) |

### ⚡ Atajos nativos de `scrcpy` (con la ventana de transmisión enfocada)

| Atajo | Función |
|-------|---------|
| `Alt + Up` / `MOD + u` | 🔊 Subir volumen del teléfono |
| `Alt + Down` / `MOD + d` | 🔉 Bajar volumen del teléfono |
| `MOD + p` | ⚡ Botón de encendido / Apagar pantalla |
| `MOD + h` | 🏠 Ir a la pantalla de inicio (Home) |
| `MOD + b` / `Backspace` | ◀ Botón Atrás (Back) |
| `MOD + s` | 📑 Ver aplicaciones recientes |
| `MOD + f` | 🖥️ Activar / Desactivar pantalla completa |
| `MOD + m` | 🔇 Silenciar / Desactivar sonido |
| `MOD + Shift + o` | ☀️ Encender pantalla físicamente |
| `MOD + n` | 🔔 Desplegar panel de notificaciones |
| `MOD + v` | 📋 Pegar portapapeles del PC al teléfono |
| **Arrastrar `.apk`** | 📦 Instalar aplicación arrastrando a la ventana de scrcpy |

---

## 🤝 Cómo contribuir

¡Todas las aportaciones de la comunidad son súper bienvenidas! Queremos que esta herramienta siga creciendo para todos los usuarios de habla hispana.

### Pasos para colaborar:
1. Haz un **Fork** de este repositorio en GitHub.
2. Clona tu fork localmente:
   ```bash
   git clone https://github.com/TU-USUARIO/Memexicanisimos-Android-Screen-Viewer.git
   ```
3. Crea una rama para tu mejora:
   ```bash
   git checkout -b feature/mi-nueva-funcionalidad
   ```
4. Realiza tus cambios y haz un commit claro:
   ```bash
   git commit -m "feat: Añade soporte para X funcionalidad"
   ```
5. Sube tu rama y abre un **Pull Request** en GitHub.

### 💡 Ideas de mejoras en las que puedes aportar:
- 🌐 Traducción de interfaz a otros idiomas (Inglés, Portugués).
- 📊 Panel gráfico de estadísticas en tiempo real (FPS reales, bitrate consumido, latencia).
- 📱 Detección automática de resoluciones nativas del teléfono conectado.
- 🎨 Selector de temas visuales (Modo Claro / Modo Oscuro customizable).
- 🔔 Notificaciones nativas de escritorio del sistema.

---

## 🐛 Reportar un problema

Si encuentras algún fallo o tienes una sugerencia, por favor abre un **[Issue](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/issues)** incluyendo los siguientes datos:

1. **Sistema Operativo**: (ej. Ubuntu 22.04 / Windows 11 / macOS Sonoma).
2. **Versiones de herramientas**: Resultado de `adb version` y `scrcpy --version`.
3. **Pasos para reproducir**: Descripción paso a paso de lo que estabas haciendo cuando ocurrió el error.
4. **Archivo de Log**: Adjunta o copia el contenido de `~/.config/masv/masv.log`.

---

## 📄 Licencia

Este proyecto está distribuido bajo la **Licencia MIT**. Consulta el archivo [LICENSE](LICENSE) para más información.

> *MASV — Desarrollado con pasión para la comunidad latina.*
