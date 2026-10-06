# 📱 MASV — App Context & Ficha Técnica

## 🎯 Rol en el Ecosistema
**Memexicanisimos Android Screen Viewer (MASV):** Sistema de acoplamiento, monitoreo y transmisión de dispositivos Android en tiempo real, utilizado principalmente como cámara cenital y monitor de estudio para el **Curso de Fotografía**.

## ⚙️ Stack y Entorno
- **Tecnología:** Python 3.10+, PyQt / Tkinter / WebSockets, OpenCV, scrcpy CLI.
- **Hardware Principal:** Huawei Y9 (STK-LX3, Kirin 710, Android 10 / EMUI 10).
- **Puertos de Red:**
  - scrcpy por defecto: `27183`
  - Segundo dispositivo (multi-device): `27184`

## ⚠️ Reglas Críticas del Dispositivo
1. **Huawei Y9 Audio:** Android 10 no soporta `AudioPlaybackCapture`. Forzar siempre `--no-audio`.
2. **Códec y Bitrate:** Usar `--video-codec=h264`, bitrate `<= 8M`, resolución 1080p o 720p.
3. **Modo Cámara para el Curso:** `scrcpy --video-source=camera --camera-facing=back` para montaje cenital.

## 🚀 Comandos Clave
- Ejecutar: `python3 run.py` o `./run.py`
- Tests: `pytest`
- Compilación: `python3 build.py`

## 📁 Archivos Clave
- `scrcpy_dock/`: Núcleo de control de procesos scrcpy y ventanas.
- `run.py`: Punto de entrada principal.
- `MASV.spec`: Definición de empaquetado PyInstaller.
