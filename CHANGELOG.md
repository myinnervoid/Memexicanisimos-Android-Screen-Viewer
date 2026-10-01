# 📜 Registro de Cambios (Changelog) — MASV

Todas las modificaciones notables de **MASV (Memexicanisimos Android Screen Viewer)** se documentan en este archivo.
El formato sigue los lineamientos de [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [1.4.1] — 2026-10-01

### 🚀 Novedades y Mejoras (Features & Improvements)
- **Terminación Asíncrona de Sesiones (`block=False`):**
  - La detención de sesiones scrcpy ahora se ejecuta de forma asíncrona en un hilo demonio desacoplado, eliminando completamente el congelamiento de 3 segundos de la interfaz gráfica.
- **Catálogo de Errores Integral (31/31 Códigos bilingües ES/EN):**
  - Cobertura del 100% de `ErrorCode` con `ErrorDetail` asistido: mensajes contextuales, explicaciones técnicas y pasos de remediación paso a paso para el usuario en Español e Inglés.
- **Accesibilidad y Contraste WCAG 2.1 AA:**
  - Calibración de colorimetría en píldoras de estado y componentes activos para los temas `Warm Stone`, `Cyber Obsidian` y `Nordic Slate`, garantizando ratios de contraste de luminancia superiores a 4.5:1.
- **Gobernanza Dinámica de Hardware (Android 10 / EMUI 10 / Kirin 710):**
  - Detección automática de terminales con `android_sdk <= 29` (como el Huawei Y9), inyectando de forma transparente `--no-audio` y forzando códec H.264 para evitar fallos de conexión por incompatibilidad de captura nativa.
- **Bóveda de Dispositivos Confiables Cifrada con PBKDF2/Fernet:**
  - Almacenamiento seguro de dispositivos autorizados (`vault.enc`) con clave derivada de hardware local y fallback de lectura transparente y no destructivo hacia rutas legacy (`~/.MASV/config/vault.enc`).
- **Perfil Canónico de Cámara Frontal:**
  - Registro oficial del perfil `"📷 Cámara Frontal"` en la plantilla `DEFAULT_CONFIG["profiles"]`, permitiendo alternancia inmediata entre sensores de cámara frontal y principal.
- **Reactividad de Interfaz y Prevención de Bucles Cíclicos:**
  - Conexión reactiva en tiempo real de las etiquetas `action_device_lbl` y `ctrl_device_lbl` con el dispositivo activo en `AppContext`.
  - Supresión de eventos redundantes en `DashboardSidebar.select(notify=False)` para erradicar re-entrancias y refrescos parásitos.
- **Instancia Única Resiliente (`SingleInstance`):**
  - Configuración con `SO_REUSEADDR` + `bind` + `listen(1)` discriminando exclusivamente `EADDRINUSE`, permitiendo reaperturas inmediatas tras reinicios sin falsos positivos de bloqueo.

### 🛠️ Corregido (Fixed)
- **Desbordamiento de MediaCodec en Modo Cámara (Sensores 48MP/12MP):**
  - Eliminación de `--no-downsize-on-error` en sesiones de cámara con auto-clampeo a 1920 px cuando no se especifica resolución.
- **Normalización de Argumentos y Whitelist Segura:**
  - Admisión formal de flags de tamaño (`--max-size`, `--camera-size`, `-m`) en el validador estricto de `ScrcpyEngine`.
- **Detección Asistida de `v4l2loopback` en Linux:**
  - Comprobación proactiva de `/dev/video9` con fallback a previsualización en ventana o asistente de instalación para OBS Studio.
- **Unificación de Diálogos "Sin dispositivo":**
  - Estandarización de las 8 advertencias de ausencia de dispositivo sobre `messagebox.showwarning` con navegación directa a la pestaña de Dispositivos.
- **Prevención de Mutabilidad en Configuración:**
  - Aislamiento profundo (`deepcopy`) en carga y fusión de diccionarios de configuración en `utils.py`.

### 🧪 Calidad e Infraestructura (Quality & Tests)
- **Suite de Pruebas Automatizadas Expandida a 668 Pruebas (100% Pasando):**
  - 668 pruebas unitarias y de integración verdes con 0 fallos, 0 errores y cobertura > 85% a nivel global (100% en adaptadores críticos como `AdbEngine` y lógica de negocio).
- **Cero Deuda Ciclomática (Ley 7):**
  - Todos los métodos del proyecto reducidos a Complejidad Ciclomática ≤ 10 (0 bloques con Rank D/F).
- **Guardián de Aislamiento de Suite:**
  - Protección estricta que impide que las pruebas toquen la configuración real del usuario en `~/.config/masv/config.json`.


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
