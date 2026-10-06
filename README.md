# 📱 MASV — Memexicanisimos Android Screen Viewer (v1.4.2)

![Open Source · Python · scrcpy](https://img.shields.io/badge/Open%20Source-Python%20%7C%20scrcpy-F59E0B?style=for-the-badge&logo=python&logoColor=white)
![Version v1.4.2](https://img.shields.io/badge/Version-v1.4.2-EA580C?style=for-the-badge)
![MIT License](https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge)
![Tests 671 Passed](https://img.shields.io/badge/Tests-671%20Passed-10B981?style=for-the-badge)
![Platforms](https://img.shields.io/badge/Platforms-Linux%20%7C%20Windows%20%7C%20macOS-D97706?style=for-the-badge)

[English Version 🇺🇸](README.en.md) | [Portal Oficial 🌐](https://memexicanisimos.com)

---

**MASV** (Memexicanisimos Android Screen Viewer) es una estación de trabajo gráfica (GUI) nativa, ultraligera y de alto rendimiento para controlar, transmitir y gestionar dispositivos Android en PC utilizando el núcleo de [`scrcpy`](https://github.com/Genymobile/scrcpy) y `ADB`.

Diseñada especialmente para **creadores de contenido, streamers, fotógrafos, gamers y desarrolladores** que requieren una suite completa: control físico OTG/UHID, cámara limpia para OBS Studio con `v4l2loopback`, blindaje de red y gestión multi-dispositivo sin dependencias pesadas de Electron ni navegadores embebidos (< 40 MB RAM, < 1% CPU).

---

### 🚀 Novedades de la Versión 1.4.1

- ⚡ **Terminación Asíncrona sin Bloqueo de UI:**
  - Desconexión y detención de sesiones scrcpy en segundo plano (hilo demonio); elimina por completo los congelamientos de 3 segundos al parar streams o cerrar la app.
- 🩺 **Catálogo Integral de Remediación Asistida (31/31 Códigos bilingües):**
  - Diagnóstico guiado con explicaciones claras y soluciones paso a paso en Español e Inglés para cada situación de error (`ErrorCode`).
- 🎨 **Accesibilidad Visual WCAG 2.1 AA:**
  - Paletas de contraste calibradas en píldoras activas y textos para todos los temas (`Warm Stone`, `Cyber Obsidian` y `Nordic Slate`), garantizando legibilidad óptima (> 4.5:1).
- 📱 **Gobernanza Dinámica de Hardware (Android 10 / EMUI 10 / Kirin 710):**
  - Detección inteligente de terminales con `android_sdk <= 29` (como el Huawei Y9), inyectando automáticamente `--no-audio` y forzando códec H.264 para prevenir caídas de conexión por falta de captura nativa en el SO.
- 📷 **Perfiles de Cámara Frontal y Trasera de Fábrica:**
  - Integración inmediata de perfiles dedicados `"📷 Cámara HD"` (trasera) y `"📷 Cámara Frontal"` para streaming, fotografía y monitoreo en vivo con OBS Studio.
- 🛡️ **Bóveda Cifrada PBKDF2/Fernet con Fallback Seguro:**
  - Almacenamiento seguro de dispositivos autorizados (`vault.enc`) con clave derivada del host y fallback no destructivo a rutas previas.
- 🧪 **Suite Automatizada de 668 Pruebas (100% Verdes):**
  - Arquitectura hexagonal blindada con cobertura integral (> 85% global, 100% en adaptadores de red y procesos), 0 bloques de complejidad ciclomática > 10 y guardián estricto de no invasión de datos locales del usuario.
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
