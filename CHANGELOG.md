# 📜 Registro de Cambios (Changelog) — MASV

Todas las modificaciones notables de **MASV (Memexicanisimos Android Screen Viewer)** se documentan en este archivo.
El formato sigue los lineamientos de [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [1.4.1] — 2026-10-01

### 🛠️ Corregido (Fixed)
- **Desbordamiento de MediaCodec en Modo Cámara (Sensores 48MP/12MP):**
  - Se eliminó la inyección incondicional de `--no-downsize-on-error` en transmisiones de cámara (`video_source == "camera"`). En teléfonos modernos (ej. vivo V2314 con Android 15), los sensores físicos de 48 MP (`4608x3456`) hacían colapsar el codificador de hardware MediaCodec al no permitírsele auto-ajuste.
  - Clampeo seguro de resolución nativa: cuando la resolución de la cámara es nativa o no está especificada, MASV inyecta automáticamente `--max-size 1920`, garantizando inicio instantáneo en Full HD sin caídas.
- **Normalización Automática de Argumentos de Perfiles:**
  - `start_scene_legacy`, `_start_scene_hexagonal` y `ProfileService.sanitize_profile_dict` ahora extraen de forma transparente tokens heredados como `--video-source=camera`, `--camera-id` y `--otg` dentro de cadenas `extra_args`, promoviéndolos a atributos nativos de `SessionConfig` y limpiando la cadena para no disparar alertas en la lista blanca de seguridad.
- **Detección Asistida de `v4l2loopback` en Linux:**
  - El botón "📷 Webcam / Enrutar cámara" ahora verifica proactivamente si el nodo virtual `/dev/video9` existe en el sistema. Si el módulo de kernel no está cargado, ofrece al usuario abrir la cámara de inmediato en una ventana de escritorio en pantalla o consultar la guía de instalación para OBS Studio.
- **Limpieza de flags en Modo OTG:**
  - Se omite `--no-downsize-on-error` en sesiones OTG donde no existe flujo de video.

### 🧪 Añadido (Added)
- **Suite de Pruebas de Modos de Conexión (`tests/test_connection_modes.py`):**
  - 12 pruebas unitarias automatizadas que validan:
    1. Duplicación USB en dispositivos modernos (SDK 35 Qualcomm) vs legacy (SDK 29 Kirin 710 con forzado H.264, 8M y `--no-audio`).
    2. Modo Cámara con auto-downsizing, ID de sensor frontal/trasero y rechazo preventivo en Android < 12 (SDK < 31).
    3. Modo OTG (inyección limpia de `--otg` sin flags de video).
    4. Conectividad inalámbrica TCP/IP y asignación de puertos en pool multi-dispositivo.
    5. Normalización segura de perfiles legacy.
- **Total de pruebas del proyecto:** 269 pruebas automatizadas (100% pasando).

---

## [1.4.0] — 2026-10-01

### 🚀 Añadido (Added)
- **Bóveda sin Fricción ("Confiar y Recordar"):**
  - Modal interactivo `TrustPromptModal` que permite registrar dispositivos en la Bóveda en 1 solo clic al detectarse un dispositivo nuevo en Modo Seguro.
- **Modo OTG Integrado (Control Físico USB sin Pantalla):**
  - Control de teléfono mediante teclado y ratón de la PC con emulación USB HID (`--otg`), reduciendo el consumo de CPU a prácticamente 0%.
- **Reverse Tethering por USB (`gnirehtet`):**
  - Compartir internet de alta velocidad de la PC hacia el móvil por cable USB en zonas sin Wi-Fi ni datos móviles.
- **Soporte Multidispositivo Concurrente:**
  - Asignación dinámica de puertos (27183 a 27199) para gestionar hasta 16 teléfonos en simultáneo sin conflictos de socket.
- **Internacionalización Completa (Español 🇲🇽 / English 🇺🇸):**
  - Selector de idioma en tiempo real con opción de reinicio asistido en 1 clic.
  - Documentación y Centro de Ayuda completamente bilingües.
- **Centro de Ayuda y FAQ Interactivo:**
  - 19 tópicos organizados por acordeón con soporte completo de scroll por rueda de ratón (mousewheel).

### 🛠️ Corregido (Fixed)
- Solución al error `TypeError` en el evento de acordeón del FAQ.
- Calibración de contraste en temas `Warm Stone`, `Cyber Obsidian` y `Nordic Slate`.

---

## [1.3.0] — 2026-09-30

### 🚀 Añadido (Added)
- **Modo Compacto Responsivo (500x620 px):**
  - Vista minimalista para control rápido sin saturar la pantalla del creador.
- **Atajos Globales de Teclado:**
  - `Ctrl + M` (Alternar Modo Compacto), `Ctrl + B` (Colapsar Sidebar), `Ctrl + I` (Alternar sesión), `Ctrl + R` (Refrescar), `Ctrl + Q` (Salir con blindaje).

### 🛠️ Corregido (Fixed)
- Calibración de dimensiones de ventana para evitar recortes de botones en resoluciones 1080p y monitores auxiliares.

---

## [1.0.0 - 1.2.0] — 2026-09-14 a 2026-09-29

- Arquitectura Hexagonal con separación de Dominio, Puertos y Adaptadores (ADR-001 a ADR-014).
- Soporte para chipsets Kirin 710 (Huawei Y9 Prime) con gobernanza estricta de códec H.264 y bitrate clamp a 8M.
- Soporte para webcam virtual vía `v4l2loopback` para OBS Studio.
- Sistema de Modo Seguro y revocación de puertos TCP/IP al cerrar.
