# 📱 MASV — Memexicanisimos Android Screen Viewer (v1.4)

![Open Source · Python · scrcpy](https://img.shields.io/badge/Open%20Source-Python%20%7C%20scrcpy-F59E0B?style=for-the-badge&logo=python&logoColor=white)
![Version v1.4](https://img.shields.io/badge/Version-v1.4-EA580C?style=for-the-badge)
![MIT License](https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge)
![Platforms](https://img.shields.io/badge/Platforms-Linux%20%7C%20Windows%20%7C%20macOS-D97706?style=for-the-badge)

[English Version 🇺🇸](README.en.md) | [Portal Oficial 🌐](https://memexicanisimos.com)

---

**MASV** (Memexicanisimos Android Screen Viewer) es una interfaz gráfica (GUI) avanzada, moderna, ligera y de alto rendimiento para controlar, transmitir y gestionar dispositivos Android en PC utilizando el núcleo de [`scrcpy`](https://github.com/Genymobile/scrcpy) y `ADB`.

Diseñada especialmente para **creadores de contenido, streamers, fotógrafos, gamers y desarrolladores** que requieren una estación de trabajo completa: control físico OTG/UHID, cámara limpia para OBS Studio con `v4l2loopback`, blindaje de red y gestión multi-dispositivo sin dependencias pesadas de Electron ni navegadores embebidos (< 40 MB RAM, < 1% CPU).

---

### 🚀 Novedades de la Versión 1.4

- 🛡️ **Bóveda de Dispositivos Confiables sin Fricción:**
  - Nuevo modal interactivo "Confiar y Recordar" que registra dispositivos en la Bóveda en un solo clic, eliminando las advertencias repetitivas al iniciar sesión en Modo Seguro.
- ⌨️ **Modo OTG Integrado (Control Físico USB sin Pantalla):**
  - Controla tu teléfono con el teclado y ratón de la PC mediante emulación USB HID (`--otg`).
  - No abre ventana de video en la computadora, reduciendo el consumo de CPU a prácticamente 0% mientras escribes o navegas en el teléfono. Botón directo en el dashboard principal y menú `Dispositivo`.
- 🌐 **Compartir Internet por USB (Reverse Tethering con `gnirehtet`):**
  - Provee conectividad a internet de alta velocidad de tu PC hacia el teléfono Android por el cable USB cuando no hay Wi-Fi ni señal de datos. Botón integrado en la pestaña Dispositivo.
- 📱 **Soporte Multidispositivo Robusto (Hasta 16 teléfonos):**
  - Gestor dinámico de puertos `PortPoolAllocator` (puertos 27183 a 27199) que permite transmitir múltiples teléfonos en simultáneo con ventanas individuales e identificadas.
- 🌐 **Internacionalización Total (Español 🇲🇽 / English 🇺🇸):**
  - Cambio de idioma dinámico desde el menú `Ver` $\rightarrow$ `Idioma / Language` o botón en barra inferior con opción de reinicio asistido en 1 clic.
- ❓ **Centro de Ayuda y FAQ Interactivo Perfeccionado (19 Secciones):**
  - Desplazamiento fluido con rueda de ratón (mousewheel) completamente sincronizado en todos los elementos.
  - Corrección de apertura/cierre de acordeones y documentación 100% bilingüe.
- 🎨 **Temas Visuales y Contrastes Calibrados:**
  - `Warm Stone` (por defecto), `Cyber Obsidian` y `Nordic Slate` con refresco dinámico que preserva la legibilidad perfecta de tarjetas, textos y botones.
- 📷 **Modo Cámara Inteligente & Protección de Sensores Modernos (48MP / 12MP):**
  - Soporte garantizado para cámaras de Android 12+ (SDK 31+) con sensores físicos de alta resolución (vivo, Samsung, Motorola, Xiaomi).
  - Límite automático preventivo a 1920 px y omisión de `--no-downsize-on-error`, evitando que MediaCodec colapse al recibir dimensiones masivas (ej. 4608x3456 en sensores de 48MP).
  - Detección asistida de `v4l2loopback`: si `/dev/video9` no está cargado en Linux, permite alternar con un clic hacia una ventana de previsualización en pantalla o revisar la guía de instalación para OBS Studio.
  - Normalización automática de perfiles: extrae flags de cámara y OTG desde `extra_args` sin disparar errores de lista blanca.
- 🧪 **Suite Exhaustiva de Pruebas de Conexión (269 Tests):**
  - Verificación automatizada de duplicación USB, modo cámara, modo OTG, conectividad inalámbrica TCP/IP y gobernanza de hardware (Kirin vs Qualcomm).
- 🔀 **Atajos Rápidos de Productividad:**
  - `Ctrl + M`: Alternar Modo Compacto (500x620) y Avanzado.
  - `Ctrl + B`: Colapsar / Expandir barra lateral (Dashboard).
  - `Ctrl + I`: Iniciar / Alternar transmisión.
  - `Ctrl + R`: Refrescar dispositivos.
  - `Ctrl + H`: Abrir Centro de Ayuda.
  - `Ctrl + Q`: Salir con blindaje automático (`adb usb`).

---

### 📥 Descargas Directas Listas para Usar

| Sistema Operativo | Archivo / Formato | Tipo de Instalación |
| :--- | :--- | :--- |
| **🐧 Linux** (Debian, Ubuntu, Arch, Fedora, Mint) | [`MASV-Linux.tar.gz`](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-Linux.tar.gz) | **100% Portable** o mediante `./install.sh` |
| **🪟 Windows** (Windows 10 y 11) | [`MASV-Windows.exe`](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-Windows.exe) | **Standalone Portable** (Incluye núcleo scrcpy/adb) |
| **🍎 macOS** (Intel & Apple Silicon) | [`MASV-macOS`](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-macOS) | Binario para macOS Monterey o superior |

---

### 📋 Guía de Instalación en Linux

Elige el método que mejor se adapte a tu flujo de trabajo:

#### Opción A: Instalación Automática con 1 Solo Comando (Recomendado)
Abre tu terminal y pega:
```bash
curl -sSL https://raw.githubusercontent.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/main/install.sh | bash
```
*Esto descarga la última versión oficial, instala el binario en `~/.MASV/bin/`, configura el icono en tu menú de aplicaciones y habilita el comando `MASV` en terminal.*

---

#### Opción B: Modo 100% Portable (Sin tocar el sistema)
1. Descarga [`MASV-Linux.tar.gz`](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-Linux.tar.gz).
2. Descomprímelo en cualquier carpeta o memoria USB:
   ```bash
   tar -xzf MASV-Linux.tar.gz
   ```
3. Haz doble clic en el ejecutable `MASV` (o ejecútalo con `./MASV`). ¡Listo! Abre inmediatamente sin requerir instalación.
*(Si después decides instalarlo, solo ve al menú `Archivo` $\rightarrow$ `📥 Instalar en Sistema`).*

---

#### Opción C: Desde el Repositorio de Código Fuente (`git clone`)
```bash
git clone https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer.git MASV
cd MASV
./install.sh
```

---

### 🗑️ Desinstalación Limpia

Puedes desinstalar MASV en cualquier momento sin dejar residuos:
* **Desde Terminal:**
  ```bash
  MASV --uninstall
  ```
  *(o `MASV --uninstall --purge` si deseas borrar también configuraciones y perfiles)*.
* **Desde la Interfaz Gráfica:**
  Menú `Archivo` $\rightarrow$ `🗑️ Desinstalar del Sistema`.

---

### 🪟 Instrucciones para Windows

1. Descarga [`MASV-Windows.exe`](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-Windows.exe).
2. Haz doble clic sobre el archivo descargado.
3. El ejecutable viene con `scrcpy` y `adb` integrados por dentro; comenzará a funcionar inmediatamente sin necesidad de instalar controladores externos.

---

### ❓ Preguntas Frecuentes (FAQ)

#### 🔴 ¿Qué hacer si el dispositivo aparece en estado "Offline"?
Indica que el teléfono perdió comunicación con el socket ADB (común por micro-cortes o suspensión de energía del puerto USB).
* **Solución:** Reconecta el cable USB, comprueba que el puerto no suspenda energía y pulsa **"⚡ Reiniciar ADB"** en MASV (o atajo en menú Dispositivo).

#### 📱 Restricciones y Optimización en Huawei Y9 / Android 10 (EMUI 10)
* **Audio:** Android 10 no admite captura nativa interna de audio por `scrcpy` (requiere Android 11+). MASV activa automáticamente `--no-audio`.
* **Rendimiento:** Para el chipset Kirin 710, se recomienda el códec **H.264** a un bitrate máximo de **8 Mbps** y resolución **1080p o 720p**.

#### 🛡️ Bóveda de Dispositivos Confiables y Modo Seguro
Registrar equipos en la Bóveda evita conexiones accidentales o no autorizadas en redes Wi-Fi públicas. El **Modo Seguro** revoca el puerto 5555 ejecutando `adb usb` para blindar el dispositivo al salir con `Ctrl + Q`.

#### 📷 Modo Estudio Fotográfico & Clean Camera Feed
Permite usar la cámara trasera limpia del teléfono en **OBS Studio** sin elementos de interfaz gráfica. En Linux, MASV monta la cámara como webcam virtual de cero latencia mediante el módulo del kernel `v4l2loopback`.

#### 🚪 Cierre Limpio vs. Minimizar a la Bandeja
El botón Salir (o `Ctrl + Q`) cierra deterministamente la interfaz, detiene los subprocesos de scrcpy y apaga el rastreador de dispositivos (`Device Tracker`), liberando limpiamente los puertos de red y locks de archivo.

---

## 📜 Licencia

Desarrollado por **Memexicanisimos Studio** bajo la licencia **MIT**. Basado en el motor de código abierto de Genymobile/scrcpy.
