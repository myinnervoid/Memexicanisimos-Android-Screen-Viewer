# 📱 MASV — Memexicanisimos Android Screen Viewer

**MASV** es una interfaz gráfica (GUI) avanzada, moderna e intuitiva para gestionar múltiples dispositivos Android simultáneamente mediante [`scrcpy`](https://github.com/Genymobile/scrcpy) y `ADB`.

Diseñada para **streamers, creadores de contenido, gamers y desarrolladores** que necesitan usar su teléfono Android como cámara secundaria (OBS), fuente de audio externa o espejo de pantalla de alto rendimiento. **Hecha por y para la comunidad latinoamericana**, ya que este tipo de herramientas casi no existen en español.

> 🌐 **Página del proyecto**: [myinnervoid.github.io/Memexicanisimos-Android-Screen-Viewer](https://myinnervoid.github.io/Memexicanisimos-Android-Screen-Viewer)
> *(Activa GitHub Pages desde Settings → Pages → Branch: main → / (root))*

---

## 🌟 Características principales

| Función | Descripción |
|---------|-------------|
| 🎮 Multidispositivo | Controla varios teléfonos en paralelo, cada uno con su propio perfil |
| ⚙️ Perfiles personalizados | Resolución, FPS, bitrate, códec de vídeo y fuente de audio guardados |
| 🧙 Asistente de perfiles | 6 pasos guiados para crear la configuración óptima según tu uso |
| 📡 Conexión WiFi ADB | Detecta la IP del teléfono automáticamente con un clic |
| 📷 Webcam virtual (Linux) | Enruta la cámara trasera como `/dev/video9` directamente a OBS Studio |
| 🔋 Control de batería | Pantalla del teléfono apagada mientras transmite para ahorrar energía |
| 🛎️ Bandeja del sistema | Minimiza sin interrumpir sesiones activas |
| ❓ FAQ interactiva | 8 secciones con comandos copiables al portapapeles |
| 👋 Tutorial de bienvenida | Guía paso a paso la primera vez que se abre |
| 💾 Memoria de preferencias | Recuerda el tamaño y posición de la ventana |

---

## ⌨️ Atajos de teclado

| Atajo MASV | Acción |
|------------|--------|
| `Ctrl+I` | Iniciar / Detener sesión activa |
| `Ctrl+R` | Buscar dispositivos conectados |
| `Ctrl+H` | Abrir pestaña de Ayuda |
| `Ctrl+Q` | Salir de la aplicación |
| `Supr` | Detener sesión seleccionada (tabla de sesiones) |
| Clic derecho (tabla) | Menú contextual: copiar comando scrcpy, forzar cierre |

### ⌨️ Atajos nativos de scrcpy (control por teclado desde la ventana)

Cuando la ventana de transmisión de `scrcpy` está enfocada, puedes usar estos atajos directo con tu teclado:

| Atajo | Función |
|-------|---------|
| `Alt + Up` / `MOD + u` | 🔊 Subir volumen del teléfono |
| `Alt + Down` / `MOD + d` | 🔉 Bajar volumen del teléfono |
| `MOD + p` | ⚡ Botón de encendido / apagar pantalla |
| `MOD + h` | 🏠 Ir a la pantalla de inicio (Home) |
| `MOD + b` / `Backspace` | ◀ Botón Atrás (Back) |
| `MOD + s` | 📑 Ver aplicaciones recientes |
| `MOD + f` | 🖥️ Pantalla completa (Fullscreen) |
| `MOD + m` | 🔇 Silenciar / Desactivar silencio |
| `MOD + Shift + o` | ☀️ Encender pantalla del teléfono físicamente |
| `MOD + n` | 🔔 Desplegar panel de notificaciones |
| `MOD + v` | 📋 Pegar portapapeles del PC al teléfono |
| Arrastrar `.apk` a la ventana | 📦 Instalar aplicación automáticamente |

---

## 🎮 Controles remotos e instalación de APKs en MASV

Dentro de la pestaña **Acciones**, MASV incluye un mando con botones de control directo sin necesidad de tocar la pantalla del teléfono:

- 🔊 **Vol + / Vol - / Mute**: Control de volumen directo.
- ⚡ **Encender**: Enciende o apaga la pantalla del teléfono (`Power`).
- 🏠 **Inicio / ◀ Atrás / 📑 Recientes**: Navegación Android completa.
- 🔔 **Notificaciones**: Despliega la barra de estado y notificaciones.
- 📦 **Instalar APK...**: Abre un diálogo de archivos para seleccionar e instalar cualquier archivo `.apk` vía ADB automáticamente.

---

## 🚀 Requisitos previos

Antes de usar MASV necesitas tener instalado **ADB** y **scrcpy** en tu sistema:

### 🐧 Linux (Debian, Ubuntu, Mint, etc.)
```bash
sudo apt update
sudo apt install adb scrcpy
```

### 🪟 Windows
```bash
# Opción 1: con winget (recomendado)
winget install Genymobile.scrcpy

# Opción 2: descarga el ZIP portable desde:
# https://github.com/Genymobile/scrcpy/releases
# Descomprime y copia los archivos en la carpeta bin/ del proyecto
```

### 🍎 macOS
```bash
brew install scrcpy android-platform-tools
```

### 📷 Solo si usas la función Webcam Virtual (Linux)
```bash
sudo apt install v4l2loopback-dkms v4l2loopback-utils
```

---

## ⬇️ Descargar binario precompilado

Si no quieres compilar tú mismo, descarga el ejecutable listo para usar desde la sección de **[Releases](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases)**:

| Sistema | Archivo | Notas |
|---------|---------|-------|
| 🐧 Linux | `MASV-Linux.tar.gz` | Descomprime y ejecuta el binario `MASV` |
| 🪟 Windows | `MASV-Windows.exe` | Ejecutable portable directo |
| 🍎 macOS | `MASV-macOS` | Dale permisos con `chmod +x MASV-macOS` |

**En Linux**, para ejecutar después de descomprimir:
```bash
tar -xzvf MASV-Linux.tar.gz
chmod +x MASV
./MASV
```

---

## 💻 Ejecutar desde código fuente (desarrollo)

Si prefieres correrlo directamente con Python:

```bash
# 1. Clona el repositorio
git clone https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer.git
cd Memexicanisimos-Android-Screen-Viewer

# 2. Crea un entorno virtual e instala dependencias
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install pystray Pillow

# 3. Inicia la aplicación
python run.py
```

---

## 📦 Compilar un ejecutable propio (PyInstaller)

Si quieres generar el binario tú mismo, usa el script `build.py` incluido o los comandos manuales.

---

### 🔹 Linux (recomendado — tu sistema actual)

Asegúrate de tener PyInstaller instalado:
```bash
pip install pyinstaller
```

Luego ejecuta el script:
```bash
python3 build.py
```

Esto genera automáticamente:
- `dist/MASV` — ejecutable binario
- `MASV-Linux.tar.gz` — archivo comprimido listo para distribuir

Si por alguna razón no se genera el `.tar.gz`, puedes crearlo a mano:
```bash
cd dist
tar -czvf MASV-Linux.tar.gz MASV
```

---

### 🔹 Windows (desde una máquina con Windows)

1. Instala Python 3.9+ y PyInstaller:
   ```cmd
   pip install pyinstaller pystray Pillow
   ```

2. Si usas los binarios portables de scrcpy/adb, colócalos en la carpeta `bin/` del proyecto.

3. Opción A — usar el script automático:
   ```cmd
   python build.py
   ```
   Genera: `dist\MASV.exe`

4. Opción B — comando manual de PyInstaller:
   ```cmd
   pyinstaller --onefile --windowed --name MASV-Windows --add-data "bin/*;bin" run.py
   ```
   *(Si no tienes la carpeta `bin/` o no necesitas incluirla, omite `--add-data`)*

---

### 🔹 macOS (desde una Mac)

```bash
pip install pyinstaller pystray Pillow
```

Opción A — script automático:
```bash
python3 build.py
```

Opción B — comando manual:
```bash
pyinstaller --onefile --windowed --name MASV-macOS run.py
```

El resultado estará en `dist/MASV-macOS`.

> ⚠️ **Nota importante**: PyInstaller no hace compilación cruzada.
> Debes ejecutar el build **en el sistema operativo destino**.
> Para automatizar la compilación en los 3 sistemas a la vez, usa el workflow de GitHub Actions (ver más abajo).

---

## 🤖 Compilación automática (GitHub Actions)

Este repositorio incluye un workflow en `.github/workflows/build.yml` que compila para **Linux**, **Windows** y **macOS** automáticamente.

Para publicar una nueva versión:

```bash
# Etiqueta tu commit con la versión
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions compilará y publicará los 3 binarios en la sección **Releases** automáticamente. Solo necesitas tener el código subido.

---

## 🐙 Subir el proyecto a GitHub por primera vez

Si aún no has subido el proyecto, sigue estos pasos desde la terminal en la carpeta raíz (`Memexicanisimos-Android-Screen-Viewer/`):

### Paso 1 — Verificar la estructura del proyecto

Asegúrate de que tienes estos archivos antes de subir:
```
Memexicanisimos-Android-Screen-Viewer/
├── index.html          ← página web del proyecto (GitHub Pages)
├── README.md           ← este archivo
├── run.py              ← punto de entrada de la app
├── build.py            ← script de compilación con PyInstaller
├── .gitignore          ← ya configurado (excluye dist/, __pycache__, etc.)
├── LICENSE             ← licencia MIT
├── scrcpy_dock/
│   ├── __init__.py
│   ├── main.py
│   ├── context.py
│   ├── managers.py
│   ├── ui_widgets.py
│   ├── ui_tabs.py
│   └── utils.py
└── .github/
    └── workflows/
        └── build.yml   ← CI para compilación multiplataforma
```

> **No incluyas**: `dist/`, `build/`, archivos `.spec`, `__pycache__/` ni `.venv/`.
> El `.gitignore` ya los excluye automáticamente.

### Paso 2 — Inicializar el repositorio git local

```bash
# Inicializar git (solo si la carpeta aún no tiene .git)
git init

# Vincular con tu repositorio remoto en GitHub
git remote add origin https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer.git

# Agregar todos los archivos (el .gitignore excluirá los binarios)
git add .

# Primer commit
git commit -m "feat: MASV v1.0 — GUI para scrcpy con perfiles, WiFi, webcam virtual y FAQ interactiva"

# Subir a la rama principal
git branch -M main
git push -u origin main
```

### Paso 3 — Generar el binario de Linux para la primera release

Con el código ya en GitHub, genera el ejecutable localmente:
```bash
pip install pyinstaller pystray Pillow
python3 build.py
```

Esto genera:
- `dist/MASV` — ejecutable
- `MASV-Linux.tar.gz` — listo para subir como release

### Paso 4 — Crear la primera release con el binario

```bash
# Etiqueta la versión
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions se encargará de compilar para los 3 sistemas y publicar los archivos en Releases automáticamente.

O si prefieres subir el binario de Linux a mano desde la web de GitHub:
1. Ve a `Releases` → `Create a new release`
2. Elige el tag `v1.0.0`
3. Arrastra y suelta `MASV-Linux.tar.gz`
4. Publica la release

### Paso 5 — Activar GitHub Pages (sitio web del proyecto)

1. Ve a tu repositorio en GitHub
2. `Settings` → `Pages`
3. En **Source**, elige: `Deploy from a branch`
4. Branch: `main` | Folder: `/ (root)`
5. Guarda — en unos minutos estará disponible en:
   `https://myinnervoid.github.io/Memexicanisimos-Android-Screen-Viewer`

---

## 🤝 ¿Cómo contribuir?

¡Toda ayuda es bienvenida! Este proyecto nació para la comunidad latina y con la comunidad crece.

```bash
# 1. Haz un fork del proyecto en GitHub
# 2. Clona tu fork
git clone https://github.com/TU-USUARIO/Memexicanisimos-Android-Screen-Viewer.git

# 3. Crea una rama para tu mejora
git checkout -b feature/mi-mejora

# 4. Haz tus cambios y commitea
git commit -m "Añade soporte para X"

# 5. Sube tu rama
git push origin feature/mi-mejora

# 6. Abre un Pull Request desde GitHub
```

### Ideas para contribuir

- 🌐 Soporte para inglés / portugués
- 🎨 Tema claro / personalizable
- 📊 Panel de estadísticas de sesión (bitrate real, FPS, latencia)
- 📱 Detección automática de resolución del teléfono
- 🔔 Notificaciones de escritorio al iniciar/finalizar sesión

---

## 🐛 Reportar un problema

¿Encontraste un bug? Abre un **[Issue](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/issues)** con:

1. Tu sistema operativo y versión
2. Versión de Python, ADB y scrcpy (`adb version`, `scrcpy --version`)
3. Descripción del error y pasos para reproducirlo
4. El log de la app (en `~/.config/masv/masv.log`)

---

## 📄 Licencia

Este proyecto está bajo la **Licencia MIT**. Consulta el archivo [LICENSE](LICENSE) para más detalles.

Puedes usar, modificar y distribuir libremente este software, siempre que mantengas el aviso de copyright original.
