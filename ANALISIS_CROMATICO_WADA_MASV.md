# 🎨 AUDITORÍA Y ANÁLISIS CROMÁTICO DE MASV (Sanzo Wada × Identidad Mexicana)
> **Aplicación:** `MASV` (Memexicanisimos Android Screen Viewer)  
> **Rol en el Estudio:** Monitor de campo, cámara cenital y consola Android para el **Curso de Fotografía** y transmisiones en vivo.  
> **Referencia Normativa:** [`MANUAL_ARMONIA_CROMATICA_WADA_MEXICO.md`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MANUAL_ARMONIA_CROMATICA_WADA_MEXICO.md)

---

## 1. Resumen Ejecutivo del Diagnóstico

Al inspeccionar el código fuente de `MASV` (específicamente [`scrcpy_dock/utils.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/scrcpy_dock/utils.py#L9-L195), [`scrcpy_dock/main.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/scrcpy_dock/main.py#L400-L441) y las pestañas en `scrcpy_dock/ui/tabs/`), se confirma tu observación: **las tres plantillas de temas actuales utilizan colores neón sintéticos (Cyberpunk) y paletas predeterminadas de Tailwind CSS** que rompen tanto con la armonía de Sanzo Wada como con la identidad cromática mexicana.

Además, al ser `MASV` una herramienta para el **Curso de Fotografía** (donde se evalúa balance de blancos, exposición e iluminación desde la cámara del Huawei Y9), los acentos neón como `#00F0FF` (cian láser) y `#FF0055` (magenta neón) generan **adaptación cromática retiniana (post-imagen)** en el ojo del fotógrafo, distorsionando la percepción real de los colores del video.

---

## 2. Hallazgos Críticos en el Código Actual

### 🔴 Hallazgo 1: El tema `cyber_obsidian` en [`utils.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/scrcpy_dock/utils.py#L117-L155) es Cyberpunk Neón Puro
En las líneas 117–155 de [`scrcpy_dock/utils.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/scrcpy_dock/utils.py#L117-L155), la plantilla usa colores RGB al 100% de saturación digital que no existen en ningún pigmento natural ni en el catálogo de Sanzo Wada:

| Clave en `utils.py` | Valor Actual | Problema Visual / Fotográfico |
| :--- | :---: | :--- |
| `"pill_active"` / `"blue"` / `"focus"` | `#00F0FF` | **Cian láser neón.** Deslumbra en entorno oscuro y altera la percepción del balance de blancos (hace ver cálida la imagen de cámara). |
| `"red"` / `"state_err"` | `#FF0055` | **Magenta/Rosa neón gamer.** Vibra agresivamente sobre el fondo `#0B0D13`. |
| `"indigo"` | `#3B82F6` | `blue-500` genérico de Tailwind CSS. |
| `"purple"` | `#8B5CF6` | `violet-500` sintético de Tailwind CSS. |
| `"green"` / `"state_ok"` | `#10B981` | `emerald-500` estándar de Tailwind CSS. |

---

### 🟠 Hallazgo 2: El tema `nordic_slate` en [`utils.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/scrcpy_dock/utils.py#L156-L194) es una copia literal de Tailwind Slate + Sky
En las líneas 156–194 de [`scrcpy_dock/utils.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/scrcpy_dock/utils.py#L156-L194), toda la paleta es el preset frío de documentación SaaS (`slate-900` a `slate-600` con acentos fluorescentes):

| Clave en `utils.py` | Valor Actual | Problema Visual |
| :--- | :---: | :--- |
| `"bg"` / `"card"` / `"card2"` | `#0F172A` / `#1E293B` / `#334155` | Escala `slate` fría genérica de Tailwind, ajena al estudio. |
| `"pill_active"` / `"blue"` / `"focus"` | `#38BDF8` | `sky-400` fluorescente. |
| `"purple"` | `#A855F7` | `purple-500` eléctrico. |
| `"green"` | `#34D399` | `emerald-400` menta neón. |
| `"cyan"` | `#22D3EE` | `cyan-400` brillante. |

---

### 🟡 Hallazgo 3: El tema por defecto `warm_stone` en [`utils.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/scrcpy_dock/utils.py#L11-L116) mezcla Tailwind Stone con Esmeralda/Rosa Sintéticos
Aunque `warm_stone` intentó ser cálido usando la escala `stone` de Tailwind (`#141210`, `#1E1B18`, `#A8A29E`), sus acentos siguen siendo colores Tailwind puros sin contrapeso armónico de Sanzo Wada:
- `"red": "#E11D48"` (`rose-600`) y `"state_err": "#EF4444"` (`red-500`).
- `"green": "#10B981"` (`emerald-500` frío que choca con el fondo marrón piedra).
- `"blue"`, `"indigo"` y `"purple"` están **repetidos con los mismos tonos ámbar** (`#D97706` y `#F59E0B`), perdiendo la riqueza de una tríada o tétrada donde existe un contrapeso mineral (como el Azul Maya/Cerúleo `#0093a5` o Jade `#00b49b`).

---

### 🟣 Hallazgo 4: Colores Hardcodeados Fuera del Diccionario `C` (18 instancias)
Existen colores fijos incrustados directamente en los widgets que ignoran el sistema de temas y violan la prohibición de `#FFFFFF` puro o usan colores de iOS/macOS:

1. **Icono de Bandeja del Sistema (`_make_tray_icon` y fallback en [`main.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/scrcpy_dock/main.py#L2147-L2250)):**
   - Línea 2147: `"#0A84FF"` (Azul sistema iOS).
   - Línea 2236: `fill="#BF5AF2"` (Púrpura neón iOS para el círculo del icono de bandeja).
   - Línea 2250: `fill="#FFFFFF"` (Texto blanco puro).
2. **Consola ADB ([`ui/tabs/tab_console.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/scrcpy_dock/ui/tabs/tab_console.py#L32-L40)):**
   - Línea 32: `bg="#0E0D0B"` (Fondo hardcodeado que no cambia cuando el usuario cambia de tema).
   - Línea 40: `(_("ADB"), "#A0D8EF")` (Azul cielo hardcodeado en lugar de usar un token del tema como `Pale King's Blue #a7d4e4` o `Calamine Blue #78cdd0`).
3. **Blanco Matemático `#FFFFFF` / `#FFF` en Botones y Menús (14 instancias):**
   - En [`main.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/scrcpy_dock/main.py#L434-L440), [`tab_device.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/scrcpy_dock/ui/tabs/tab_device.py#L30), [`tab_actions.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/scrcpy_dock/ui/tabs/tab_actions.py#L54), [`tab_profile.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/scrcpy_dock/ui/tabs/tab_profile.py#L33), [`tab_quickcast.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/scrcpy_dock/ui/tabs/tab_quickcast.py#L103) y [`ui_widgets.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/scrcpy_dock/ui_widgets.py#L659) se fuerza `fg="#FFFFFF"` o `"#FFF"` en lugar de usar el blanco de cal/papel amate (`C["text"]` = `#f5ecc2` o `#ffefae`) o el texto oscuro de alto contraste (`#111314`) cuando el botón es amarillo/ámbar.

---

## 3. Propuesta de Rediseño: Las 3 Plantillas de MASV bajo Sanzo Wada × México

Para mantener **100% de compatibilidad con la arquitectura actual y sus pruebas automatizadas** ([`tests/test_bloque3_final.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/tests/test_bloque3_final.py#L74-L96) y [`tests/test_fase_c2_regressions.py`](file:///home/myinnervoid/Estudio%20Memexicanisimos/MASV/tests/test_fase_c2_regressions.py#L156-L185)), conservamos las 3 llaves internas (`warm_stone`, `cyber_obsidian`, `nordic_slate`), pero transformamos su paleta e identidad visual a **combinaciones auténticas de Sanzo Wada**:

### 🏺 Plantilla 1: `warm_stone` → **"Barro Negro y Cal (Cuarto Oscuro)"**
* **Inspiración:** Cuarto oscuro fotográfico sobre obsidiana (`Black #111314`), barro bruñido (`Vandyke Brown #4b3317`), siena (`Raw Sienna #bb7125`), ocre dorado de enfoque (`Golden Yellow #f3a257`) y blanco de cal (`Sulpher Yellow #f5ecc2`).
* **Combinaciones Sanzo Wada Base:**
  - **Combo `#069`:** `Warm Gray` (`#a1a39a`) + `Black` (`#111314`) *(Neutralidad absoluta alrededor del video de cámara).*
  - **Combo `#182`:** `Raw Sienna` (`#bb7125`) + `Vandyke Brown` (`#4b3317`) + `Deep Indigo` (`#051230`)
  - **Combo `#229`:** `Golden Yellow` (`#f3a257`) + `Deep Slate Olive` (`#253122`) + `Neutral Gray` (`#b6bfc1`)
* **Ratios WCAG 2.1 Verificados:**
  - `text` (`#f5ecc2`) sobre `bg` (`#111314`): **15.67 : 1 (AAA)**
  - `text2` (`#ffefae`) sobre `card` (`#1d1612`): **15.49 : 1 (AAA)**
  - `pill_text_act` (`#111314`) sobre `pill_active` (`#f3a257`): **8.98 : 1 (AAA)**

---

### 🌿 Plantilla 2: `cyber_obsidian` → **"Obsidiana y Jade Maya"** *(Adiós al Neón `#00F0FF` y `#FF0055`)*
* **Inspiración:** Sustituye el cian y fucsia láser por la elegancia nocturna de Sanzo Wada: fondo de obsidiana azul (`Deep Indigo #051230`), tarjetas en pizarra verde profunda (`Deep Slate Green #112f2c`), pastilla activa en **Jade Maya** (`Sea Green #00b49b`), acento cálido en **Rojo Jaspe/Tezontle** (`Jasper Red #eb5324`) y **Grana Cochinilla** (`Carmine #cc1236`).
* **Combinaciones Sanzo Wada Base:**
  - **Combo `#155`:** `Jasper Red` (`#eb5324`) + `Benzol Green` (`#00978d`) + `Deep Indigo` (`#051230`)
  - **Combo `#271`:** `Pomegranite Purple` (`#b71f57`) + `Cobalt Green` (`#96d1aa`) + `Green Blue` (`#099197`) + `Deep Slate Green` (`#112f2c`)
* **Ratios WCAG 2.1 Verificados:**
  - `text` (`#f5ecc2`) sobre `bg` (`#051230`): **15.55 : 1 (AAA)**
  - `text2` (`#ebd3a2`) sobre `card` (`#112f2c`): **9.80 : 1 (AAA)**
  - `pill_text_act` (`#051230`) sobre `pill_active` (`#00b49b`): **7.05 : 1 (AAA)**

---

### 🏺 Plantilla 3: `nordic_slate` → **"Añil Oaxaca y Cempasúchil"** *(Adiós al Tailwind Slate)*
* **Inspiración:** Basado en la icónica **Combinación `#002`** y **`#279`** de Sanzo Wada: lienzo en **Azul Añil Profundo** (`Dark Tyrian Blue #12354e`), contenedores en piedra pizarra (`Slate Color #34454c`), pastilla activa en **Cempasúchil Dorado** (`Yellow Orange #f99d1b`), primario en **Azul Maya** (`Cerulian Blue #0093a5`) y textos en **Crema Amate** (`Pale Lemon Yellow #ffefae`).
* **Combinaciones Sanzo Wada Base:**
  - **Combo `#002`:** `Yellow Orange` (`#f99d1b`) + `Dark Tyrian Blue` (`#12354e`)
  - **Combo `#279`:** `Raw Sienna` (`#bb7125`) + `Vinaceous Cinnamon` (`#eea78c`) + `Ecru` (`#c2ae93`) + `Dark Tyrian Blue` (`#12354e`)
* **Ratios WCAG 2.1 Verificados:**
  - `text` (`#ffefae`) sobre `bg` (`#12354e`): **11.07 : 1 (AAA)**
  - `text2` (`#ebd3a2`) sobre `card` (`#1c2d38`): **9.70 : 1 (AAA)**
  - `pill_text_act` (`#111314`) sobre `pill_active` (`#f99d1b`): **8.75 : 1 (AAA)**

---

## 4. Tabla Comparativa de Tokens (`utils.py`: Antes vs. Después Wada)

| Token (`C[...]`) | Antes (`cyber_obsidian` Neón) | Después (**Obsidiana & Jade · Wada `#155`/`#271`**) | Nombre Original Sanzo Wada |
| :--- | :---: | :---: | :--- |
| `"bg"` | `#0B0D13` | `#051230` | `Deep Indigo` |
| `"card"` | `#12151F` | `#112f2c` | `Deep Slate Green` |
| `"card2"` | `#1A1F2C` | `#12354e` | `Dark Tyrian Blue` |
| `"card3"` | `#222A3A` | `#34454c` | `Slate Color` |
| `"card_border"` | `#2E364F` | `#547076` | `Dark Medici Blue` |
| `"pill_active"` | `#00F0FF` ❌ | `#00b49b` ✅ | `Sea Green` (Jade Maya) |
| `"blue"` | `#00F0FF` ❌ | `#0093a5` ✅ | `Cerulian Blue` (Azul Maya) |
| `"indigo"` | `#3B82F6` ❌ | `#00978d` ✅ | `Benzol Green` (Malaquita) |
| `"red"` / `"state_err"` | `#FF0055` ❌ | `#cc1236` ✅ | `Carmine` (Grana Cochinilla) |
| `"green"` / `"state_ok"` | `#10B981` ❌ | `#00b49b` ✅ | `Sea Green` (Jade) |
| `"orange"` / `"state_warn"` | `#F59E0B` ❌ | `#f37420` ✅ | `Orange` (Cempasúchil) |
| `"purple"` | `#8B5CF6` ❌ | `#b71f57` ✅ | `Pomegranite Purple` (Bugambilia) |
| `"cyan"` | `#06B6D4` ❌ | `#78cdd0` ✅ | `Calamine Blue` |
| `"text"` | `#F1F5F9` | `#f5ecc2` ✅ | `Sulpher Yellow` (Blanco de Cal) |
| `"text2"` | `#CBD5E1` | `#ebd3a2` ✅ | `Ivory Buff` (Cantera Clara) |
| `"muted"` | `#64748B` | `#a2b0ad` ✅ | `Mineral Gray` |
