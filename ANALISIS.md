# 📋 DOCUMENTO DE ANÁLISIS, MODULARIZACIÓN Y PLAN DE EVOLUCIÓN ARQUITECTÓNICA (v3.3)
**Ecosistema:** Estudio Memexicanisimos
**Proyecto:** MASV (Memexicanisimos Android Screen Viewer)
**Estándar Aplicado:** Motor Autónomo de Auditoría y Evolución de Software — 5 Vectores (v3.2)
**Perspectiva:** Senior Software Architect & Android Platform Specialist
**Versión analizada:** 1.4.1 (commit `795f6e4`, rama `main`)
**Fecha de actualización:** 1 de Octubre, 2026
**Objetivo:** Verificar el resultado de la modularización hexagonal propuesta en la v3.2, medir el estado real del sistema contra las 10 Leyes Globales y los umbrales de la Ley 7, e integrar la revisión de bugs de v1.4.1 como deuda técnica priorizada.

> **Trazabilidad del documento anterior:** la v3.2 del 13-sep-2026 (que diagnosticaba el monolito `main.py` de 1.571 líneas y proponía los Hitos 1–4) queda archivada en el historial de git. Se recupera íntegra con:
> `git show c88c0a2:ANALISIS.md`
> Este documento la **sustituye** y evalúa qué se ejecutó, qué se desvió y qué sigue pendiente. El material operativo de la v3.2 que sigue vigente (decisiones de exclusión, layout de despliegue, runbook de hardware) se preserva condensado en el **Anexo B**.

> **Documentos relacionados generados en la misma ronda:**
> - `INFORME_BUGS_v1.4.1.md` — 22 defectos con evidencia reproducible y parche.
> - `AUDIT_REPORT.md` — verificación de los 11 hallazgos de v1.2 + puntuación por vector.

---

## 📌 1. Resumen Ejecutivo y Diagnóstico Senior

La modularización **se ejecutó**: existe la Arquitectura Hexagonal completa que la v3.2 diseñó sobre el papel.

```
scrcpy_dock/
├── domain/     models.py (Device, DeviceCapabilities, SessionConfig) + protocols.py   ✅
├── core/       adb_engine.py · scrcpy_engine.py · port_allocator.py · tether_engine.py ✅
├── services/   profile_service.py · security_service.py · installer_service.py · tether_service.py ✅
├── contracts.py · errors.py · state.py · context.py                                     ✅
└── UI          main.py · ui_tabs.py · ui_widgets.py · i18n.py          ⚠️ monolito sin modularizar
```

Sin embargo, la medición real (Ley 7) arroja un veredicto matizado: **el andamiaje arquitectónico está construido, pero no está gobernando el sistema**.

| Síntoma | Evidencia medida |
| :--- | :--- |
| La capa de presentación **no fue modularizada** | `main.py` 1.989 líneas · `ui_tabs.py` 1.034 · `ui_widgets.py` 1.201; los `ui/tabs/tab_*.py` del Hito 3 **no existen** |
| La UI **sigue llamando al SO directamente** | 10 sitios con `subprocess.run([self.ctx.adb, …])` en `main.py`, esquivando `AdbEngine` (ADR-006) |
| Los artefactos nuevos **no están cableados** | `get_error_detail()` importado y jamás invocado · `ProfileService` escrito pero la app usa `utils.load_config()` · `SecurityService` (bóveda cifrada) es código muerto · `verify_server_version` nunca llamado |
| La FSM de 5 estados **existe pero no gobierna** | 30 llamadas directas a `_set_status()` frente a 9 a `state_machine.set_*` |
| La UI **no tiene pruebas** | cobertura `main.py` = **0 %**, `ui_tabs.py` = **0 %**, `ui_widgets.py` = **16 %** (umbral Ley 7: ≥60 %) |

**Diagnóstico:** en v1.2 el problema era *"alta cohesión interna pero alto acoplamiento estructural"*. En v1.4.1 el problema mutó a un patrón más sutil y más peligroso: **arquitectura correcta sin cumplimiento forzado**. Se puede romper una funcionalidad anunciada (modo solo-audio), un handler crítico (`stop_session`) o la configuración del usuario, y las **269 pruebas siguen en verde** porque ninguna importa la capa que el usuario toca.

**Consecuencia verificada (Crítico, Ley 10):** la suite de pruebas ejecuta `save_config()` sobre `~/.config/masv/config.json` real y **destruye los perfiles y la bóveda del usuario**. Ocurrió durante esta auditoría.

### Estado de los Hitos de la v3.2

| Hito | Descripción | Estado |
| :---: | :--- | :--- |
| 0 | Comando terminal + acceso `.desktop` | ✅ **Completado** |
| 1 | Extracción de núcleos (`core/adb_engine.py`, `core/scrcpy_engine.py`) | ✅ **Completado** (con la UI todavía sin migrar del todo) |
| 2 | Capa de servicios (`device_service.py`, `stream_service.py`) | ❌ **No ejecutado** — se crearon otros servicios (profile/security/installer/tether), pero la orquestación de dispositivos/stream sigue en `managers.py` |
| 3 | Modularización de UI (`tabs/tab_*.py`) | ❌ **No ejecutado** — `ui_tabs.py` sigue siendo un monolito de 1.034 líneas |
| 4 | Despliegue encapsulado (`--install` / `--uninstall` / `--status` + `.tar.gz`) | 🟡 **Parcial** — `--install`/`--uninstall` y el `.tar.gz` existen; **`--status` no está implementado** |

---

## ⚖️ 2. Cumplimiento de las 10 Leyes Globales (v3.2)

| Ley | Nombre | Estado | Evidencia |
| :---: | :--- | :---: | :--- |
| **1** | Auditoría Primero | ✅ | Este documento + `AUDIT_REPORT.md` |
| **2** | Contratos Existentes y Brechas | 🟢 | `contracts.py` y `errors.py` existen y el catálogo creció a **16/31** códigos con remediación; el `ErrorCode` inexistente se corrigió (P3.4 ✅). Pendiente: firmas `dict`/`bool`/`None` residuales en `utils` y handlers de UI |
| **3** | Profundidad Adaptativa | 🟢 | Hay Modo Seguro y sanitización de shell; la **bóveda cifrada (Fernet+PBKDF2) ya está cableada** con migración verificada y fallback (B5). Deuda: ubicación única de `vault.enc` sin decidir |
| **4** | Bucle de Retroalimentación | ✅ | Este documento actualiza contratos y decisiones a partir de hallazgos nuevos |
| **5** | Estandarización de Transporte/IPC | 🟡 | `OperationResult[T] ≡ { success, data, error_code, message }` cumple el contrato; ahora también en las operaciones mutadoras de `security.py`. **Pendiente**: `utils` y los handlers de UI devuelven `dict`/`None`, y persiste el campo espejo `error` (con `ok().error == NONE`, *truthy*) |
| **6** | Autómata Finito de Interfaz | ✅ | `transition_to()` valida contra un grafo `_ALLOWED` y **rechaza sin mutar** (`IDLE→SUCCESS` imposible); la UI quedó enrutada: 31 transiciones vía FSM frente a 7 `_hint` informativos, y `_set_status` es el único renderizador |
| **7** | Métricas de Aptitud | 🟡 | **2 de 5** umbrales cumplidos (ver §3) |
| **8** | Clarificación Proactiva | ✅ | n/a — acceso completo al repositorio, entorno y suite |
| **9** | Criterio de Finalización de Auditoría | ✅ | Informe de brechas priorizado + matriz de gap (§5) |
| **10** | Clasificación de Hallazgos | ✅ | Aplicada estrictamente: Crítico = seguridad / pérdida de datos / legal; Mayor = rendimiento, escalabilidad, mantenibilidad; Menor = estilo, documentación, opcional (§4 y §6) |

**Cumplimiento: 6 ✅ · 3 🟡 · 0 ❌** *(antes de las Fases A/B: 5 ✅ · 4 🟡 · 1 ❌)*

---

## 📊 3. Métricas del Estado Actual (Ley 7)

Medidas **hoy** sobre el repositorio, no estimadas. Comandos en el §10.

### 3.1 Cobertura de pruebas

Runner: `python -m unittest discover -s tests` (el del CI). Herramienta: `coverage.py`.

| Capa | Umbral Ley 7 | Medido | Veredicto |
| :--- | :---: | :---: | :---: |
| **UI** (`main.py`, `ui_tabs.py`, `ui_widgets.py`) | ≥ 60 % | **0 % / 0 % / 16 %** | ❌ **Brecha grave** |
| **Lógica de negocio / núcleo** | ≥ 80 % | ver desglose | 🟡 Mixto |
| **TOTAL proyecto** | — | **35 %** (4.664 stmts, 3.052 sin cubrir) | — |

Desglose de la capa de negocio (17 módulos):

| Módulo | Cob. | Módulo | Cob. |
| :--- | :---: | :--- | :---: |
| `errors.py` | **100 %** | `services/tether_service.py` | 81 % |
| `domain/models.py` | **100 %** | `core/tether_engine.py` | 77 % |
| `domain/protocols.py` | **100 %** | `core/scrcpy_engine.py` | 75 % |
| `core/port_allocator.py` | **100 %** | `managers.py` | 72 % |
| `contracts.py` | 98 % | `context.py` | 72 % |
| `state.py` | 95 % | `security.py` | 71 % |
| `services/profile_service.py` | 93 % | `utils.py` | 64 % |
| `services/security_service.py` | 93 % | **`core/adb_engine.py`** | **46 %** ⚠️ |
| `services/installer_service.py` | 90 % | | |

**Lectura:** el dominio y los contratos están excelentemente cubiertos (100 %), pero **el adaptador más crítico para la estabilidad operativa —`adb_engine.py`— está al 46 %**: sin cubrir las líneas 379-402 (`revert_tcpip` y sus marcadores de transición de transporte) ni 597-655 (todo el bucle de reconexión de `_TrackerThread._run_once`). La cobertura cae a cero justo donde vive la lógica de reconexión y lock-down.

### 3.2 Complejidad ciclomática (umbral Ley 7: ≤ 10)

`radon cc`: **20 bloques por encima del umbral** de 362 analizados (18 métodos, 1 función, 1 clase): 15 de rank C, 3 D y 2 F.

> **Medición de esta tabla: 01-oct (estado v1.4.1, antes de la Fase A).** Tras las Fases A–C el
> conteo es **17 bloques > 10 (máx. 28)** y las dos entradas F ya no existen: ver §11.1–11.3.

| Función | Rank | CC | Ubicación |
| :--- | :---: | :---: | :--- |
| `ScrcpyEngine.build_command` | **F** | **50** | `core/scrcpy_engine.py:194` |
| `SessionManager.start_scene_legacy` | **F** | **43** | `managers.py:428` |
| `ProfileService.sanitize_profile_dict` | **D** | 28 | `services/profile_service.py:132` |
| `ScrcpyDockApp._exit` | **D** | 23 | `main.py:1852` |
| `ScrcpyDockApp._on_dev_select` | **D** | 21 | `main.py:744` |
| `ScrcpyDockApp._toggle_scene` | C | 18 | `main.py:1448` |
| `ScrcpyDockApp._toggle_view` | C | 17 | `main.py:527` |
| `main()` | C | 15 | `main.py:1916` |
| `ProfileChipsView.set_profile` | C | 14 | `ui_widgets.py:469` |
| `ScrcpyDockApp._on_tab_changed` | C | 14 | `main.py:1538` |
| `_TrackerThread._run_once` | C | 13 | `core/adb_engine.py:595` |
| `ScrcpyEngine` (clase) | C | 12 | `core/scrcpy_engine.py:91` |
| `get_compatible_codecs` · `_change_theme` · `_launch_with_fallback` | C | 12 | varios |
| `parse_pair_ip_port_code` · `scan_devices` · `is_private_ip` · `revert_tcpip` · `_select_tab` | C | 11 | varios |

**Lectura:** `build_command` (CC **50** en la medición de esta auditoría; **63** al re-medirla tras A7, que añadió las guardas de solo-audio; **6** tras C5) es el punto de máxima fragilidad y **explica la regresión P3.5**: medio centenar de caminos de decisión sin una sola prueba de aceptación de los perfiles que la propia aplicación distribuye.

### 3.3 Duplicación de código (umbral Ley 7: ≤ 5 %)

**2,9 %** — 24 bloques de ≥ 6 líneas normalizadas repetidos; 252 líneas de 8.769. ✅ **Cumple.**
*(Medición propia por bloques normalizados, no herramienta estándar de duplicación; sirve como orden de magnitud.)*
Concentrada en las invocaciones repetidas de `subprocess.run(...)` en `adb_engine.py` (los mismos `capture_output/text/timeout/env` ×6), candidata natural a un helper único `_run_adb()`.

### 3.4 Mantenibilidad (radon MI)

| Archivo | MI | Nota |
| :--- | :---: | :--- |
| `main.py` | **C** | 1.989 líneas, UI + SO mezclados |
| `ui_widgets.py` | **C** | 1.201 líneas |
| `managers.py` | B | 592 líneas |
| Resto (22 archivos) | **A** | — |

### 3.5 Vulnerabilidades (umbral Ley 7: 0 críticas/altas)

`pip-audit -r requirements.txt` → **No known vulnerabilities found** ✅
*(Nota de rigor: se auditan las 4 dependencias directas —`cryptography`, `pystray`, `Pillow`, `pyinstaller`—. Al no existir lockfile, las transitivas no quedan cubiertas.)*

### 3.6 Resumen de cumplimiento (Ley 7)

| Métrica | Umbral | Medido | ¿Cumple? |
| :--- | :---: | :---: | :---: |
| Cobertura lógica de negocio | ≥ 80 % | 46 %–100 % (mixto; `adb_engine` 46 %) | 🟡 |
| Cobertura UI | ≥ 60 % | 3 %–16 % → **49 %–98 %** tras D1 | 🟡 |
| Complejidad ciclomática | ≤ 10 | **14** bloques > 10 (máx. 18; era 20 con máx. 63) — **0 con rank D o F** | 🟡 |
| Duplicación | ≤ 5 % | 2,9 % | ✅ |
| Vulnerabilidades | 0 altas/críticas | 0 | ✅ |

**2 ✅ · 2 🟡 · 1 ❌** — la complejidad pasó de ❌ a 🟡: ya no hay ni un bloque Rank D o F (el peor es CC 18, frente a 63), pero aún quedan 14 bloques entre 11 y 18 que hay que bajar del umbral. Cobertura total: **35 % → 72 %**.

---

## 🔬 4. Evaluación por los 5 Vectores (v1.4.1)

### 🔷 Vector 1 — Dominio, Invariantes & Marco Legal · 88 % → **90 %** *(tras Fases A/B)*

- ✅ **Logro del Hito 1**: `domain/models.py` con `@dataclass(frozen=True)` (`Device`, `DeviceCapabilities`, `SessionConfig`) y enums `DeviceState`, `Codec`, `ConnectionType`; `domain/protocols.py` con `SessionProcess` y `TrackerHandle`.
- ❌ **Brecha 1.1 (Mayor)** — La frontera no migró: `managers.py:105-107` mantiene **tres representaciones** del mismo dato (`List[Tuple[str,str,str]]`, `List[DeviceEntry]`, `_caps_cache`); `ScrcpySession` sigue con `active: bool` y **no existe `SessionState`**.
- ❌ **Brecha 1.2 (Menor)** — `context.py` sin cabecera de invariantes/licencia.
- 🐞 **Derivado P3.8 (Mayor)** — `DeviceCapabilities` no transporta el modelo → `get_device_props()` devuelve el **fabricante** como modelo → título de ventana `MASV: vivo` en lugar de `MASV: V2314`. Una brecha de dominio cobrada como bug de usuario.

### 🔷 Vector 2 — Contratos de Datos, Esquema & Catálogo de Fallos · 88 % → **92 %** *(tras Fases A/B)*

- ✅ `contracts.py` (`OperationResult[T]`, `DeviceEntry`, `SessionInfo`, `ProfileConfig`, `TrustedDeviceEntry`) y `errors.py` (30 `ErrorCode` + `ErrorDetail` bilingüe con remediación).
- 🟡 **Brecha 2.1 (Mayor)** — Ley 5 no aplicada transversalmente: `security.py` devuelve `dict`/`bool`/`int`/`None` en 5 métodos; `utils` devuelve `dict`; los handlers de UI devuelven `None`. El doble campo `error`/`error_code` con `ok().error == NONE` (*truthy*) es una trampa semántica.
- 🟡 **Brecha 2.2 (Mayor)** — `ERROR_CATALOG` detalla **11 de 30** códigos; 3 definidos sin uso; y **P3.4**: `ErrorCode.INTERNAL_ERROR` se invoca sin existir (`services/security_service.py:207`) → `AttributeError` que enmascara el error original de cifrado.
- ❌ **Brecha 2.3 (Mayor, agravada)** — `utils.load_config()` sigue sin validar tipos (un `"profiles": []` se conserva tal cual) y ahora **comparte subdicts con `DEFAULT_CONFIG`** por copia superficial (P3.11): guardar un perfil contamina los valores de fábrica del proceso.
- 🐞 **P3.14 (Crítico, Ley 10)** — Divergencia `security.py` (dict, texto plano) vs `services/security_service.py` (Fernet+PBKDF2, lista) → dos fuentes de verdad de seguridad y la robusta es **código muerto**.
- ℹ️ **Aviso de la Ley 4**: `DECISIONS.md` declara «guardado atómico con validación de esquema», pero esa implementación vive en `ProfileService` y **no en el camino que usa la aplicación**. La decisión documentada describe código no ejecutado.

### 🔷 Vector 3 — Lógica de Dominio, Concurrencia & Hardening · 84 % → **88 %** *(tras Fases A/B)*

- ✅ Hardening de `extra_args` en tres capas (rechazo de operadores de shell + whitelist + normalización de tokens legacy). **Cierra el Hallazgo 3.1 de v1.2.**
- ❌ **Regresión P3.5 (Mayor)** — La whitelist no incluye `--no-video`: el **perfil por defecto `🎙️ Stream OBS (Huawei)` y el preset del asistente no arrancan nunca** (`INVALID_EXTRA_ARGS`). El hardening se aplicó sin prueba de aceptación de los perfiles distribuidos.
- ❌ **P3.1 y P3.2 (Mayor)** — `SessionManager.stop()` y `_build_cmd()` no existen; dos handlers (`_stop_selected`, `_copy_sess_cmd`) mueren con `AttributeError`. `_stop_selected` está además **duplicado** (`main.py:1527` y `:1660`).
- 🟡 **Brecha 3.2 (Menor)** — Persisten hilos `daemon` sin dispatcher: `start_scene_legacy` lanza scrcpy **sin watchdog** (`on_exit`/`on_stderr_line` ausentes, a diferencia del camino hexagonal), y `_TrackerThread.stop()` no desbloquea el `read(4)`.
- ❌ **P3.15 (Mayor)** — La UI evita `AdbEngine` en 10 puntos y ejecuta `adb kill-server` directo: se pierde el socket aislado (`ADB_SERVER_SOCKET tcp:localhost:5038`) y se tumba el daemon compartido del usuario (Android Studio, VS Code).
- 🟡 **P3.21 (Menor)** — `SingleInstance` sin `SO_REUSEADDR` → falso «ya está en ejecución» tras `_restart_app()`.

### 🔷 Vector 4 — Superficie de Interfaz, Ergonomía & Mapeo de Estados · 80 % → **86 %** *(tras Fases A/B)*

- 🟡 **Brecha 4.1 (Mayor)** — **La FSM no gobierna.** Existe `UIStateMachine` con los 5 estados y está suscrita (`main.py:121`), pero `transition_to()` **siempre retorna `True`** sin validar (P3.19) y la UI la evade: **30 llamadas a `_set_status()` vs 9 a `state_machine.set_*`** (77 % fuera del autómata). **Ley 6 NO cumplida.**
- 🟡 **Brecha 4.2 (Mayor)** — El mapeo error→remediación existe (`ErrorDetail.remediation_es/en`) pero `get_error_detail()` **se importa y nunca se usa** (`pyflakes`).
- ❌ **P3.12 (Mayor)** — **i18n incompleta**: 563 claves EN, pero **133 literales** pasados a `_()` sin traducción (todos los menús Archivo/Editar/Ver, `Modo Seguro: ON/OFF`, `Blindar Red`, la barra lateral completa). En inglés la app sigue en español; el test que lo «verifica» sólo comprueba 5 claves. Hay **6 claves duplicadas** (P3.13).
- ❌ **P3.9 (Mayor)** — Los 4 botones de Quick Cast buscan perfiles con nombres inexistentes (`Juego Rápido` vs `🎮 Juego Rápido`): no hacen nada, en silencio.
- 🟡 **P3.20 (Mayor)** — `ScrcpySession.terminate()` bloquea el hilo de Tk hasta 3 s por sesión.
- 🟡 **P3.10 (Menor)** — `_connect_wifi` nunca detecta IP inválida: `if not parsed` sobre una tupla `(None, None)` que es *truthy*.
- ❌ **P3.6 (Mayor)** — `NameError` en el `lambda` que captura `e` de un `except` finalizado.
- ℹ️ **WCAG 2.2 AA**: la paleta declara contraste AAA (`utils.py:52`) y hay foco visible, pero **no hay verificación automatizada** de contraste ni de áreas táctiles para los 3 temas.

### 🔷 Vector 5 — Infraestructura, Resiliencia & Auditoría Cruzada · 90 % → **91 %** *(tras Fases A/B)*

- ✅ **Cierre del Hallazgo 5.1**: **269 pruebas** (antes 18) con `tests/contracts/` (7), `tests/integration/` (5), mocks de `subprocess`/`AdbEngine`, y cobertura 100 % en dominio/contratos.
- ✅ **Cierre del Hallazgo 5.2**: `build.yml:58-60` ejecuta la suite antes del empaquetado (matriz ubuntu/windows/macos).
- ❌ **Brecha 5.1b (Crítico, Ley 10)** — **0 pruebas importan `scrcpy_dock.main`.** Toda la superficie de UI está sin verificar (0 %), lo que hace invisibles los 4 fallos duros de handlers (P3.1, P3.2, P3.3, P3.6).
- ❌ **P3.7 (Crítico, Ley 10)** — **La suite destruye datos del usuario**: `tests/test_core.py:41-45` llama a `save_config()`/`load_config()` sin aislar `HOME`, sobrescribiendo `~/.config/masv/config.json` (perfiles + bóveda) con `{"test_key": …}`. Reproducido en esta auditoría.
- 🟡 **P3.17 (Menor)** — `index.html` y `style.css` versionados con restos de prueba (`"Prueba de Concurrencia"`, `p { color: red; }`).
- 🟡 **P3.18 (Menor)** — `verify_server_version()`/`_compare_versions()` (ADR-014) implementados y nunca invocados; `managers.py:260` con ruta de `scrcpy-server` hardcodeada e inútil.
- 🟡 **Higiene de CI (Menor)** — sin linter (`pyflakes`/`ruff`) ni `--failfast`; habría detectado P3.6 y los 20+ imports muertos.

---

## 📐 5. Matriz de Brechas (columnas del estándar v3.2)

| Vector | Artefacto esperado | Estado actual | Brecha | Criticidad | Acción propuesta |
| :---: | :--- | :--- | :--- | :---: | :--- |
| V1 | `domain/models.py` con `SessionState` | Solo `DeviceState`; `ScrcpySession.active: bool` | Falta ciclo de vida formal de sesión | Mayor | Añadir enum `SessionState`; eliminar las 3 representaciones de `devices` |
| V1 | `DeviceCapabilities.model` | Ausente | Bug funcional P3.8 | Mayor | Añadir campo y propagar `ro.product.model` |
| V1 | Cabecera legal/invariantes en `context.py` | Ausente | Hallazgo 1.2 de v1.2 sigue abierto | Menor | Añadir cabecera + invariantes |
| V2 | `contracts.py` · `OperationResult[T]` | ✅ Creado y usado en core/services | No transversal (security/utils/UI) | Mayor | Migrar `security.py`; exponer solo `OperationResult` |
| V2 | Catálogo `ErrorCode` completo | 30 códigos; catálogo detalla 11; 1 invocado inexistente | P3.4 rompe el contrato | Mayor | `INTERNAL_ERROR`→`UNKNOWN_ERROR`; cubrir los 19 restantes |
| V2 | Validación de esquema de config | Sin validar tipos + alias mutable | P3.11 + brecha 2.3 | Mayor | Cablear `ProfileService` a la UI (o validar + `deepcopy`) |
| V2/V3 | Una sola fuente de verdad de seguridad | `security.py` (plano) vs `security_service.py` (cifrado, muerto) | P3.14 — privacidad | **Crítico** | Cablear `SecurityService` (Fernet+PBKDF2) y retirar el duplicado |
| V3 | Whitelist de `extra_args` coherente | Bloquea `--no-video` (perfil por defecto) | P3.5 — regresión | Mayor | Añadir `--no-video` / `SessionConfig.video_enabled` |
| V3 | Handlers de sesión operativos | `stop()` y `_build_cmd()` inexistentes; `_stop_selected` duplicado | P3.1, P3.2 | Mayor | Corregir y consolidar definiciones |
| V3 | UI sobre `AdbEngine` (ADR-006) | 10 llamadas `subprocess` directas | P3.15 | Mayor | Migrar a `AdbEngine` con socket aislado |
| V3 | Despachador de tareas unificado | ~15 `Thread(daemon=True)` sueltos | Brecha 3.2 de v1.2 | Menor | Centralizar en un `TaskDispatcher` |
| V4 | FSM gobernante (Ley 6) | `transition_to()` siempre `True`; UI la evade 30 vs 9 | P3.19 + brecha 4.1 | Mayor | Tabla `_ALLOWED` + enrutar UI por la FSM |
| V4 | `get_error_detail()` cableado | Importado y nunca usado | Brecha 4.2 de v1.2 | Mayor | Mapear errores a acciones en consola |
| V4 | i18n EN completa | 133 faltantes, 6 duplicadas | P3.12, P3.13 | Mayor | Completar + test AST de cobertura |
| V4 | Presets y perfiles coherentes | 4 botones con nombres inexistentes | P3.9 | Mayor | Constantes compartidas / match tolerante |
| V4 | Verificación de contraste WCAG 2.2 AA | Declarado, no verificado | Check del vector sin evidencia | Menor | Script de contraste por tema |
| V5 | Suite sin efectos secundarios | Escribe el `config.json` real | P3.7 — **pérdida de datos** | **Crítico** | Aislar `CONFIG_FILE` con `tmp` + `patch` |
| V5 | Smoke test de UI | 0 pruebas importan `main.py` | Cobertura UI 0 % | **Crítico** | Suite Tk oculta sobre handlers |
| V5 | `TRADEOFFS_MATRIX.md` | Vive dentro de `DECISIONS.md` | Artefacto del estándar no separado | Menor | Extraer a archivo propio |
| V5 | `services/device_service.py`, `stream_service.py` (Hito 2) | No existen | Hito 2 desviado | Mayor | Extraer orquestación de `managers.py` |
| V5 | `ui/tabs/tab_*.py` (Hito 3) | No existen (`ui_tabs.py` 1.034 líneas) | Hito 3 no ejecutado | Mayor | Modularizar la presentación |
| V5 | `requirements-dev.txt` | Todo en `requirements.txt` (incl. `pyinstaller`) | Higiene de despliegue | Menor | Separar runtime/dev |
| V5 | Linter en CI | Ausente | ~20 imports muertos; P3.6 indetectable | Menor | `ruff`/`pyflakes` + `--failfast` |
| V5 | Artefactos basura fuera del repo | `index.html`, `style.css`, `backups/` | P3.17 | Menor | `git rm --cached` y limpieza |

---

## 🐞 6. Integración de la Revisión de Bugs (v1.4.1)

Los 22 defectos del `INFORME_BUGS_v1.4.1.md`, reclasificados según la **Ley 10** (Crítico = seguridad / pérdida de datos / legal; Mayor = rendimiento, escalabilidad, mantenibilidad; Menor = estilo, documentación, opcional).

> **Nota de nomenclatura:** el informe de bugs usa una escala *operativa* de 4 niveles (`🔴` = rompe funcionalidad anunciada). La Ley 10 es más estricta con «Crítico». Ambas columnas se ofrecen para que la conciliación sea explícita.

| ID | Defecto | Sev. operativa | **Ley 10** | Vector |
| :---: | :--- | :---: | :---: | :---: |
| P3.7 | La suite sobrescribe el `config.json` real → pérdida de perfiles y bóveda | 🔴 | **Crítico** | V5 |
| P3.14 | Bóveda cifrada sin cablear; credenciales en texto plano; seguridad divergente | 🟡 | **Crítico** | V2/V3 |
| P3.1 | `SessionManager.stop()` inexistente (handler duplicado) | 🔴 | Mayor | V3 |
| P3.2 | `SessionManager._build_cmd()` inexistente | 🔴 | Mayor | V3 |
| P3.3 | `DeviceManager.get_device_model()` inexistente (rompe TrustPrompt) | 🔴 | Mayor | V1/V4 |
| P3.4 | `ErrorCode.INTERNAL_ERROR` inexistente (ruta de cifrado) | 🔴 | Mayor | V2 |
| P3.5 | `--no-video` fuera de la whitelist (perfil por defecto inoperante) | 🔴 | Mayor | V3 |
| P3.6 | `NameError` por `lambda` capturando `e` de un `except` | 🔴 | Mayor | V4 |
| P3.8 | `get_device_props()` devuelve el fabricante como modelo | 🟠 | Mayor | V1 |
| P3.9 | Botones de Quick Cast sin efecto (nombres inexistentes) | 🟠 | Mayor | V4 |
| P3.11 | `load_config()` comparte subdicts con `DEFAULT_CONFIG` | 🟠 | Mayor | V2 |
| P3.12 | i18n EN incompleta (133 claves) | 🟠 | Mayor | V4 |
| P3.15 | La UI evade `AdbEngine` (rompe aislamiento ADR-006) | 🟡 | Mayor | V3 |
| P3.19 | `transition_to()` no valida (FSM decorativa) | 🟡 | Mayor | V4 |
| P3.20 | `terminate()` bloquea el hilo de Tk hasta 3 s | 🟡 | Mayor | V4 |
| P3.10 | `_connect_wifi` no detecta IP inválida | 🟠 | Menor | V4 |
| P3.13 | 6 claves i18n duplicadas | 🟠 | Menor | V4 |
| P3.16 | Docs vs código (puertos 16 vs 21, versión, ejemplos) | 🟡 | Menor | V1 |
| P3.17 | `index.html`/`style.css` basura versionada | 🟡 | Menor | V5 |
| P3.18 | Código muerto/sin cablear | 🟡 | Menor | V2/V5 |
| P3.21 | `SingleInstance` sin `SO_REUSEADDR` | 🟡 | Menor | V3 |
| P3.22 | `_TrackerThread.stop()` no desbloquea el `read` | 🟡 | Menor | V3 |

**Totales según Ley 10: 2 Críticos · 12 Mayores · 8 Menores.**

### Patrón raíz (hallazgo transversal)

Cuatro de los seis fallos «mayores» de handlers (P3.1, P3.2, P3.3, P3.6) y el crítico P3.7 comparten una sola causa raíz: **la capa `main.py` no tiene ninguna prueba y el CI no tiene linter**. Cerrar esas dos brechas (Fase D del plan) tiene la mejor relación impacto/esfuerzo de todo el backlog.

---

## 🗺️ 7. Diagnóstico de Acoplamiento: qué se desacopló y qué no

**Se desacopló correctamente (Hito 1):** los núcleos externos (`adb`, `scrcpy`, `v4l2`) ya no son cadenas de comando sueltas dentro de la UI para el camino principal de streaming; viven en `core/` tras interfaces tipadas (`SessionProcess`) con `OperationResult`. El camino `_start_scene_hexagonal` es limpio y testeado.

**No se desacopló (Hitos 2 y 3 pendientes):**

```
ANTES (v1.2)                          AHORA (v1.4.1)
main.py 1.571 líneas                  main.py 1.989 líneas   ← creció, no se dividió
  ├─ widgets Tkinter                    ├─ widgets Tkinter
  ├─ subprocess adb directo             ├─ subprocess adb directo   (10 sitios)
  ├─ subprocess pkexec/lsmod            ├─ subprocess pkexec/lsmod
  └─ lógica de sesión                   └─ lógica de sesión
                                        ▲
                                        └─ mientras core/ y services/ existen al lado,
                                           pero NO son el único camino de acceso
```

El síntoma clásico que la v3.2 quería eliminar —**«la capa de interfaz ejecuta llamadas directas al SO»**— sigue presente literalmente. Lo que cambió es que ahora hay un motor correcto *al lado* que la UI ignora la mitad de las veces: **deuda silenciosa** (dos formas de hacer lo mismo, una verificada y otra no).

**Regla de no-solapamiento (sección 4.3 de la v3.2):** sigue sin poder garantizarse. Mejorar el tema visual está aislado, pero tocar «arrancar sesión» afecta a **dos rutas vivas** (`_start_scene_hexagonal`, testeada, y `start_scene_legacy`, CC 43 y 0 % de cobertura de UI).

---

## 📱 8. Compatibilidad de Hardware — Estado Validado en v1.4.1

### 8.1 Matriz de comportamiento (código + tests)

| Caso | Comportamiento v1.4.1 | Verificación |
| :--- | :--- | :--- |
| Android ≤ 10 (SDK ≤ 29) | `--no-audio` forzado automáticamente | `scrcpy_engine.py:281` · `test_hardware_governance::test_android_10_forces_no_audio` |
| Kirin 710 (Huawei) | Códec forzado H.264 + clamp de bitrate a 8 M | `scrcpy_engine.py:226-228` · `test_connection_modes::test_legacy_huawei_y9...` |
| `--stay-awake` / `--turn-screen-off` | Inyectados salvo conflicto con `extra_args` | `scrcpy_engine.py:305-310` |
| Cámara nativa (sensor 48 MP) | `--max-size 1920` si no se pidió tamaño + sin `--no-downsize-on-error` | `scrcpy_engine.py:238-271` · `test_camera_mode_native_resolution_clamps_to_safe_1920` |
| Cámara en Android < 12 | Rechazo preventivo `INVALID_INPUT` (SDK < 31) | `test_camera_mode_rejects_android_below_sdk_31` |
| Webcam virtual v4l2loopback | Comando a `/dev/video9` con pre-chequeo del nodo | `main.py:1167-1226` ⚠️ **fuera del motor** (P3.15) |
| Modo OTG (HID) | `--otg` sin flags de video; limpia `--no-downsize-on-error` | `test_otg_mode_injects_flag_and_omits_video_params` |
| Multi-dispositivo | Pool de **21 puertos** reales (27183–27203, `max_offset=20`) | `port_allocator.py:25` ⚠️ las docs dicen «16» y «27199» → **P3.16** |

**Corrección documental requerida:** el rango real es `[27183, 27203]` = **21 sesiones concurrentes**, no 16. (Afecta a `ui_tabs.py:972`, `i18n.py:567` y el CHANGELOG.)

### 8.2 Runbook EMUI 10 (Huawei Y9) — preservado de v3.2

1. **Audio:** Android 10 no soporta `AudioPlaybackCapture` (Android 11+). MASV ya lo resuelve forzando `--no-audio`; el usuario debe elegir fuente `mic` si necesita sonido.
2. **Encoder Kirin 710:** H.264 a 8 Mbps máximo (ya forzado por el motor).
3. **Ajustes en el teléfono (requeridos, no automatizables):**
   - *Opciones de Desarrollador* → activar **«Permitir depuración ADB en modo solo carga»**.
   - Activar **«Entrada de simulación de pantalla / depuración táctil por USB»**.
   - Excluir las apps del sistema del «Optimizador» agresivo de batería de EMUI.
   - Mantener `--stay-awake` y `--turn-screen-off` (activos por defecto).

### 8.3 Modo Estudio Fotográfico (Clean Camera Feed + V4L2) — preservado de v3.2

- **Cámara cenital / detalle de producto** (feed limpio, sin UI del teléfono):
  `scrcpy -s <serial> --video-source=camera --camera-facing=back --camera-size=1920x1080 --camera-fps=30`
  *(En MASV se obtiene con el perfil `📷 Cámara HD` o `route_cam`; el motor fuerza `--max-size 1920` en sensores 48 MP.)*
- **Webcam virtual para OBS / Discord / Zoom:** `--v4l2-sink=/dev/video9` (requiere `v4l2loopback`; el módulo puede cargarse desde la UI con `pkexec`).
- **Monitor de campo inalámbrico:** segundo teléfono como referencia de encuadre; el pool de 21 puertos permite ambos simultáneos con títulos de ventana `MASV: <modelo>` (pendiente P3.8: hoy mostraría el fabricante).

---

## 🚀 9. Plan de Evolución (Fase 2 del Motor)

### Fase A — Detener el sangrado (1–2 h)
*Objetivo: eliminar el Crítico de pérdida de datos (P3.7) y los 7 fallos funcionales de arranque/handler (P3.1–P3.6). El segundo Crítico (P3.14, bóveda cifrada) se cierra en la Fase B (B5).*

> **Estado: ✅ EJECUTADA (2026-10-01).** Las 7 acciones están implementadas y cubiertas por
> `tests/test_fase_a_regressions.py` (22 pruebas nuevas, 291/291 en verde).
> Cobertura total 35 % → 38 %; `ui_tabs.py` 0 % → 3 %. Detalle en el §11.

| # | Acción | Criterio de aceptación |
| :--- | :--- | :--- |
| A1 | Aislar `CONFIG_FILE`/`HOME` en `tests/test_core.py` (`TemporaryDirectory` + `patch`) | La suite deja de modificar `~/.config/masv/` (verificar hash antes/después) |
| A2 | `main.py:1670` → `stop_session`; borrar la definición duplicada de `:1660` | `_stop_selected()` detiene la sesión sin excepción |
| A3 | `main.py:1710` → reconstruir el argv con `ScrcpyEngine.build_command` | «Copiar comando» produce un comando válido |
| A4 | `main.py:1400/1458` → usar `device_mgr.devices` (o implementar `get_device_model`) | Modo Seguro + dispositivo no confiable muestra el TrustPrompt |
| A5 | `security_service.py:207` → `ErrorCode.UNKNOWN_ERROR` | `encrypt_vault` falla con `OperationResult`, no con `AttributeError` |
| A6 | `main.py:667-668` → materializar el mensaje antes del `lambda` | El toast de error de instalación muestra el texto, no `NameError` |
| A7 | `--no-video` en la whitelist **o** `SessionConfig.video_enabled` | El perfil `🎙️ Stream OBS (Huawei)` arranca |

### Fase B — Cumplir las Leyes 5 y 6 (medio día)

> **Estado: ✅ EJECUTADA (2026-10-01).** Las 5 acciones están implementadas y cubiertas por
> `tests/test_fase_b_regressions.py` (24 pruebas nuevas, **315/315 en verde**).
> Cobertura total 38 % → **39 %**; catálogo de errores 11 → **16** códigos.
> Detalle y métricas en el §11.

| # | Acción | Criterio de aceptación |
| :--- | :--- | :--- |
| B1 | `transition_to()` con tabla `_ALLOWED` que devuelva `False` ante transición inválida | Test: `IDLE→SUCCESS` no cambia estado → **Ley 6 cumplida a nivel de máquina** |
| B2 | Enrutar por la FSM todos los mensajes de estado de la UI | `grep -c "_set_status("` baja de 30 a < 5 |
| B3 | Cablear `get_error_detail()` a la consola con acción contextual | Cada `ErrorCode` en consola muestra su `remediation_*` |
| B4 | `DeviceCapabilities.model` + propagación de `ro.product.model` | Título de ventana = `MASV: V2314` (test de `build_command`) |
| B5 | Migrar `security.py` a `OperationResult` y **unificar** con `SecurityService` (bóveda cifrada) | Una sola fuente de verdad; `vault.enc` en uso; ADR actualizado |

### Fase C — Cerrar los Hitos 2 y 3 (deuda estructural, 1–2 días)

> **Estado: 🟡 EJECUTADA PARCIALMENTE (2026-10-01).** C1, C3, C4 y C5 hechas y verificadas
> (**346/346 en verde**, `tests/test_fase_c_regressions.py`). **C2 (modularización de la
> presentación) NO se ejecutó**: partir `ui_tabs.py` (1.034 líneas) y `main.py` (2.052) sin
> una prueba de humo de UI dejaría un refactor de 3.000 líneas sin red de seguridad — la
> propia D1 de la Fase D es el requisito previo. Detalle en el §11.3.

| # | Acción | Criterio de aceptación |
| :--- | :--- | :--- |
| C1 | Extraer `services/device_service.py` y `stream_service.py`; dejar `managers.py` como fachada | `start_scene_legacy` sale de `managers.py`; CC de `build_command` < 20 |
| C2 | Dividir la presentación en `ui/tabs/tab_devices.py`, `tab_profiles.py`, `tab_wifi.py`, `tab_camera.py`, `tab_logs.py` | Ningún archivo de UI > 400 líneas; `main.py` < 500 | 🚫 **Pendiente — requiere D1** (prueba de humo de UI) como red de seguridad |
| C3 | Migrar **todas** las llamadas ADB de la UI a `AdbEngine` (socket aislado) | `grep -c "subprocess.run(\[self.ctx.adb" main.py` → 0 |
| C4 | Completar las 133 traducciones EN y deduplicar las 6 claves | Test AST de cobertura i18n = 100 % |
| C5 | Refactorizar `build_command` (CC 50) en un ensamblador por bloques | CC ≤ 10 por bloque; tests por bloque |

### Fase D — Ingeniería de guardia (prevención de regresiones)

> **Estado: 🟡 EN EJECUCIÓN (2026-10-01). D1 ✅ HECHA y en verde.**
> `tests/test_ui_smoke.py` (23 pruebas) instancia la aplicación REAL sobre un `Tk`
> oculto y ejercita todos los flujos: construcción, 7 pestañas, clic en cada botón,
> los 3 perfiles de fábrica, detener/copiar/pánico, consola y la ruta "faltan
> dependencias". **369/369 pruebas OK.**
> Efecto medido en la Ley 7: cobertura total **41 % → 70 %**; `ui_tabs.py` **3 % →
> 98 %**; `ui_widgets.py` **16 % → 49 %**; `main.py` al 55 %.
> La primera pasada cazó **2 defectos reales** (§11.4). D2–D5 pendientes.

> **Estado: ✅ CERRADA la deuda ciclomática (01-oct, §11.5).** Con D1 como red se demolieron
> los **tres últimos bloques Rank D** del repositorio: `sanitize_profile_dict` CC **28 → 2**,
> `_exit` CC **23 → 1**, `_on_dev_select` CC **21 → 2**. El repositorio queda con **0 bloques
> Rank D o F** y 14 bloques > 10 (todos Rank C, máximo 18). **399/399 pruebas OK.** La segunda
> pasada cazó **P3.24** (§3.24 del informe de bugs), un defecto de producción real.

| # | Acción | Criterio de aceptación |
| :--- | :--- | :--- |
| D1 | **Smoke test de UI** (Tk oculto): construir `ScrcpyDockApp` y ejercitar detener sesión, copiar comando, TrustPrompt y **arranque de cada perfil de `DEFAULT_CONFIG`** | Habría cazado P3.1, P3.2, P3.3, P3.5, P3.6, P3.9 |
| D2 | Linter en CI (`ruff`/`pyflakes`) + `--failfast` | 0 imports/variables muertos; P3.6 imposible de reintroducir |
| D3 | Subir `adb_engine.py` del 46 % al ≥ 80 % (`revert_tcpip` y `_TrackerThread`) | Umbral de negocio de la Ley 7 alcanzado |
| D4 | Test de exhaustividad de `ERROR_CATALOG` (30/30) y de contraste WCAG por tema | 0 códigos sin `ErrorDetail`; contraste verificado |
| D5 | Separar `requirements-dev.txt`; extraer `TRADEOFFS_MATRIX.md` | Artefactos del estándar completos |

### Criterios de éxito globales (re-medición)

| Métrica | Hoy | Objetivo |
| :--- | :---: | :---: |
| Cobertura UI | 0–16 % | ≥ 60 % |
| Cobertura `adb_engine` | 46 % | ≥ 80 % |
| Bloques CC > 10 | 17 (máx. 28) | 0 (máx. ≤ 10) |
| Cuerpo de `main.py` | 1.989 líneas | < 500 |
| Ley 6 (FSM gobernante) | ❌ | ✅ |
| Defectos Críticos | 2 | 0 |

---

### 9.1 Runbook Quirúrgico de Ejecución por Fases (Guía de Implementación Paso a Paso)

#### 🛡️ Fase 0 — Hotfixes Críticos & Blindaje de Datos del Host (Estimación: 1 a 2 horas)
*Meta: Detener la pérdida silenciosa de datos en `~/.config/masv/config.json` y reparar los métodos rotos de la UI que colapsan ante interacción del usuario.*

1. **Paso A.1: Aislamiento del Test de Configuración (Prevención de Pérdida de Datos)**
   - **Archivo:** `tests/test_core.py` (método `test_atomic_save_config`).
   - **Acción:** Emplear `unittest.mock.patch("scrcpy_dock.utils.CONFIG_FILE")` apuntando a un archivo temporal dentro de `tempfile.TemporaryDirectory()`.
   - **Verificación:** Ejecutar `python3 -m unittest discover -s tests` y comprobar con `stat` o `sha256sum` que `~/.config/masv/config.json` no sufre ninguna modificación.

2. **Paso A.2: Reparación del Manejador de Detención de Sesión (`AttributeError`)**
   - **Archivo:** `scrcpy_dock/main.py`.
   - **Acción:** Localizar la redefinición duplicada de `_stop_selected` en la línea 1660 que invoca `self.ctx.session_mgr.stop(serial)`. Eliminar la duplicidad o corregir a `self.ctx.session_mgr.stop_session(serial)`.
   - **Verificación:** Probar que el menú contextual y la tecla `Supr` invocan `stop_session` sin excepciones.

3. **Paso A.3: Reconstrucción del Comando scrcpy en Portapapeles**
   - **Archivo:** `scrcpy_dock/main.py` (`_copy_sess_cmd`).
   - **Acción:** Reemplazar la llamada inexistente `_build_cmd` por la llamada al motor hexagonal `self.ctx.session_mgr._scrcpy.build_command(...)`.
   - **Verificación:** Hacer clic en "📋 Copiar comando scrcpy" y verificar que el portapapeles contiene la cadena completa de ejecución.

4. **Paso A.4: Desbloqueo del Flujo "Confiar y Recordar" (TrustPromptModal)**
   - **Archivos:** `scrcpy_dock/managers.py` y `scrcpy_dock/main.py`.
   - **Acción:** Implementar `get_device_model(self, serial: str) -> str` en `DeviceManager`, extrayendo el modelo de `self.devices` o retornando `"Android"` como fallback defensivo. Usarlo en `_start_otg_mode` y `_toggle_scene`.
   - **Verificación:** Conectar un dispositivo no registrado con Modo Seguro activo; verificar que el diálogo `TrustPromptModal` se despliega sin arrojar `AttributeError`.

5. **Paso A.5: Corrección de Símbolo Inexistente en Catálogo de Errores**
   - **Archivo:** `scrcpy_dock/services/security_service.py:207`.
   - **Acción:** Sustituir `ErrorCode.INTERNAL_ERROR` por `ErrorCode.UNKNOWN_ERROR`.
   - **Verificación:** Comprobar con introspección `hasattr(ErrorCode, "INTERNAL_ERROR")` que no quedan referencias rotas en el código.

6. **Paso A.6: Materialización de Mensaje en Excepciones Asíncronas (`NameError`)**
   - **Archivo:** `scrcpy_dock/main.py:667-668`.
   - **Acción:** Asignar `err_msg = str(e)` dentro del bloque `except Exception as e:` antes de despachar el `lambda` diferido a `root.after`.
   - **Verificación:** Simular un fallo de instalación y confirmar que el `Toast` muestra el texto descriptivo del error en vez de `NameError: free variable 'e'`.

7. **Paso A.7: Habilitación de `--no-video` en la Lista Blanca de Seguridad**
   - **Archivos:** `scrcpy_dock/domain/models.py` y `scrcpy_dock/core/scrcpy_engine.py`.
   - **Acción:** Incorporar `"--no-video"` al conjunto inmutable `ALLOWED_EXTRA_FLAGS`.
   - **Verificación:** Probar que el perfil predeterminado `"🎙️ Stream OBS (Huawei)"` genera su `argv` sin ser rechazado con `INVALID_EXTRA_ARGS`.

---

#### 🎨 Fase 1 — Estabilización de UI, Ergonomía & Coherencia de Perfiles (Estimación: medio día)
*Meta: Resolver la desconexión visual entre los botones del Dashboard y el backend, blindar la memoria contra aliasing y completar el soporte bilingüe.*

1. **Paso B.1: Búsqueda Tolerante a Emojis en Quick Cast**
   - **Archivo:** `scrcpy_dock/ui_tabs.py:75-87`.
   - **Acción:** Modificar `_select_preset(name)` para realizar coincidencia normalizada (slug o substring en minúsculas), permitiendo que `"Juego Rápido"` enlace automáticamente con `"🎮 Juego Rápido"`, y que `"Modo OTG"` active el comando OTG de inmediato.
   - **Verificación:** Clic en los 4 botones del panel principal y confirmar activación visual.

2. **Paso B.2: Copia Profunda en `load_config` contra Aliasing Mutable**
   - **Archivo:** `scrcpy_dock/utils.py`.
   - **Acción:** Aplicar `copy.deepcopy(DEFAULT_CONFIG)` en lugar de la copia superficial `dict(DEFAULT_CONFIG)`.
   - **Verificación:** Modificar un perfil en una sesión en memoria y comprobar que `DEFAULT_CONFIG` permanece inmutable.

3. **Paso B.3: Validación Estricta de Tupla de Conexión Inalámbrica**
   - **Archivo:** `scrcpy_dock/main.py:812-816`.
   - **Acción:** Ajustar la condición a `if not parsed or not parsed[0]:` para interceptar correctamente tuplas `(None, None)`.
   - **Verificación:** Ingresar `999.999.1.1:5555` y verificar que muestra "IP inválida" en vez de "IP no permitida".

4. **Paso B.4: Propagación de Modelo Real en Títulos de Ventana**
   - **Archivos:** `scrcpy_dock/domain/models.py` y `scrcpy_dock/managers.py`.
   - **Acción:** Añadir `model: str = ""` a `DeviceCapabilities` y poblarlo con `ro.product.model` para que los títulos generados sean `MASV: V2314` en vez de `MASV: vivo`.
   - **Verificación:** Comprobar `--window-title` generado en `build_command`.

5. **Paso B.5: Cobertura Bilingüe Completa (133 claves i18n)**
   - **Archivo:** `scrcpy_dock/i18n.py`.
   - **Acción:** Traducir los 133 literales pasados a `_()` que carecen de traducción en inglés (menús, cabeceras, botones de navegación) y deduplicar las 6 claves redundantes.
   - **Verificación:** Ejecutar la app con `language="en"` y constatar que ningún elemento visible queda en español.

---

#### 🏛️ Fase 2 — Robustecimiento Arquitectónico, FSM y Bóveda Cifrada (Estimación: 1 a 2 días)
*Meta: Hacer efectiva la gobernanza de las Leyes 5 y 6, activar la bóveda cifrada en producción y canalizar todo ADB por el motor aislado.*

1. **Paso C.1: Autómata de Estados con Validación Estricta de Transiciones (Ley 6)**
   - **Archivo:** `scrcpy_dock/state.py`.
   - **Acción:** Declarar la matriz `_ALLOWED_TRANSITIONS: dict[UIState, set[UIState]]`. Si una transición no es válida (ej. `FAULT → SUCCESS` sin pasar por `PENDING`), retornar `False` y no notificar a los suscriptores.
   - **Verificación:** Test unitario en `tests/test_state.py` comprobando rechazo de transiciones ilegales.

2. **Paso C.2: Gobernanza Centralizada de Estado en UI**
   - **Archivo:** `scrcpy_dock/main.py`.
   - **Acción:** Reemplazar las 30 llamadas directas `_set_status()` por invocaciones a `self.ctx.state_machine.set_*`.
   - **Verificación:** `grep -c "_set_status(" scrcpy_dock/main.py` reducido a 0.

3. **Paso C.3: Mapeo Contextual de Errores con Remediación**
   - **Archivo:** `scrcpy_dock/main.py`.
   - **Acción:** Cablear `get_error_detail(error_code)` para que cuando ocurra un fallo en consola, se desplieguen los pasos de mitigación recomendados (`remediation_es` / `remediation_en`).
   - **Verificación:** Provocar desconexión de USB y verificar despliegue de ayuda guiada en log.

4. **Paso C.4: Unificación de Bóveda hacia `SecurityService` (Cifrado Fernet)**
   - **Archivos:** `scrcpy_dock/security.py` y `scrcpy_dock/services/security_service.py`.
   - **Acción:** Migrar la persistencia de dispositivos de confianza de texto plano en `config.json` hacia `~/.MASV/config/vault.enc` protegido con derivación PBKDF2 y sal local.
   - **Verificación:** Verificar que la clave y la lista de seriales autorizados no son legibles en texto plano en disco.

5. **Paso C.5: Canalización Total de ADB hacia `AdbEngine` (Socket 5038)**
   - **Archivo:** `scrcpy_dock/main.py`.
   - **Acción:** Erradicar los 10 `subprocess.run([self.ctx.adb, ...])` directos y reemplazarlos por los métodos del adaptador `AdbEngine`.
   - **Verificación:** `grep -c "subprocess.run(\[self.ctx.adb" scrcpy_dock/main.py` igual a 0.

---

#### 🧪 Fase 3 — Prevención de Regresiones, Modularización & CI/CD Guards (Estimación: 2 días)
*Meta: Garantizar que ningún cambio futuro pueda introducir métodos rotos o fallos de contrato sin romper el build en GitHub Actions.*

1. **Paso D.1: Suite de Pruebas de Humo de UI (`tests/test_ui_smoke.py`)**
   - **Acción:** Crear prueba automatizada que instancie `ScrcpyDockApp` con `root.withdraw()` (modo headless) y simule:
     - Apertura y cierre de cada pestaña.
     - Clic en los botones de Quick Cast.
     - Ejecución de `_stop_selected`, `_copy_sess_cmd`, `_start_otg_mode`.
     - Carga de cada uno de los perfiles de `DEFAULT_CONFIG`.
   - **Verificación:** Si algún handler llama a un método inexistente, el test falla de inmediato.

2. **Paso D.2: Integración de Linter Estricto en GitHub Actions (`build.yml`)**
   - **Archivo:** `.github/workflows/build.yml`.
   - **Acción:** Añadir paso previo al empaquetado:
     `python -m pyflakes scrcpy_dock/ tests/` (o `ruff check .`) con bandera que aborte el flujo ante variables no usadas o imports rotos.
   - **Verificación:** Ejecución limpia en pull request.

3. **Paso D.3: Modularización de Pestañas (`ui/tabs/tab_*.py`)**
   - **Acción:** Dividir el monolito `ui_tabs.py` (1.034 líneas) en subcomponentes por responsabilidad: `tab_devices.py`, `tab_streaming.py`, `tab_profiles.py`, `tab_wifi.py`, `tab_help.py`.
   - **Verificación:** Ningún archivo de interfaz debe superar 400 líneas de código.

---

## 🔎 10. Verificación — Comandos de esta Auditoría

```bash
cd "/home/myinnervoid/Estudio Memexicanisimos/MASV"
V=.venv/bin   # o el intérprete con las dependencias

# Ley 7 · Cobertura
python -m coverage run --source=scrcpy_dock -m unittest discover -s tests
python -m coverage report -m

# Ley 7 · Complejidad ciclomática (umbral ≤ 10)
python -m radon cc -s -n C scrcpy_dock/

# Ley 7 · Mantenibilidad
python -m radon mi scrcpy_dock/

# Ley 7 · Vulnerabilidades
python -m pip_audit -r requirements.txt

# Ley 7 · Duplicación (bloques ≥ 6 líneas normalizadas)
# Ley 6 · Gobierno de la FSM
grep -c "_set_status(" scrcpy_dock/main.py          # 30
grep -c "state_machine\.set_" scrcpy_dock/main.py   #  9

# Ley 5 · Contratos y código muerto
python -m pyflakes scrcpy_dock build.py run.py tests

# Ley 6 · La FSM no valida transiciones
grep -n "return True" scrcpy_dock/state.py           # state.py:67

# Ley 9 · Suite
python -m unittest discover -s tests -v              # 269 tests OK
```

---

## 11. Registro de Ejecución — Fases A y B

### 11.1 Fase A (2026-10-01) — Detener el sangrado

Ejecutada íntegramente. **291/291 pruebas en verde** (269 previas + 22 nuevas en `tests/test_fase_a_regressions.py`).

| # | Acción | Archivos modificados | Prueba de aceptación | Estado |
| :--- | :--- | :--- | :--- | :---: |
| A1 | Aislar la config real en tests | `tests/test_core.py`, `tests/test_v14_features.py` | `TestA1AislamientoDeConfig::test_la_suite_no_escribe_la_config_real` (compara bytes antes/después) | ✅ |
| A2 | Consolidar `_stop_selected` (era duplicado y llamaba a `SessionManager.stop()`, inexistente) | `main.py` | `TestA2DetenerSesion` (3 pruebas: usa `stop_session`, tolera evento de Tk, sin selección no rompe) | ✅ |
| A3 | Reconstruir el comando vía motor | `main.py`, `managers.py` | `TestA3CopiarComando` (4 pruebas, incl. `build_command_for` y guarda anti-`_build_cmd`) | ✅ |
| A4 | Implementar `DeviceManager.get_device_model()` | `managers.py` | `TestA4ModeloDeDispositivo` (4 pruebas) | ✅ |
| A5 | `ErrorCode.INTERNAL_ERROR` → `UNKNOWN_ERROR` | `services/security_service.py` | `TestA5CatalogoDeErrores` (3 pruebas, incl. auditoría AST de todo `ErrorCode.*` referenciado) | ✅ |
| A6 | Materializar la variable del `except` antes del `lambda` | `main.py` | `TestA6DiferidoSeguro` (guarda por `inspect.getsource`) | ✅ |
| A7 | Modo solo audio correcto + whitelist única | `domain/models.py`, `core/scrcpy_engine.py`, `managers.py` | `TestA7PerfilesYAudioSolo` (6 pruebas, incl. "todo perfil de `DEFAULT_CONFIG` construye un comando válido") | ✅ |

**Mejoras aplicadas más allá del plan original** (detectadas al revisarlo):
- `ALLOWED_EXTRA_FLAGS` estaba **duplicada** en `domain/models.py` y `core/scrcpy_engine.py`: ahora es fuente única.
- El modo solo audio **no inyecta** flags de vídeo (`--video-codec`, `--max-size`, `--video-source`) y `--no-video` no se duplica en el argv.
- Guardas de dominio nuevas: solo audio + `camera` → `INVALID_INPUT`; solo audio en Android ≤ 10 → `INVALID_INPUT` con mensaje explícito (en Android 10 no hay captura de audio: `--no-video --no-audio` no reproduciría nada).
- `SessionManager.build_command_for(serial)`: API pública que evita que la UI acceda a `_scrcpy` (interno).

**Métricas tras la Fase A:**

| Métrica | Antes | Después |
| :--- | :---: | :---: |
| Pruebas | 269 | **291** |
| Cobertura total | 35 % | **38 %** |
| Cobertura `ui_tabs.py` | 0 % | 3 % |
| `pyflakes` "undefined name 'e'" | 1 | **0** |
| Códigos `ErrorCode` referenciados que no existen | 1 | **0** |
| Perfiles de fábrica que arrancan | 2 de 3 | **3 de 3** |

**Riesgo residual declarado:** el perfil `🎙️ Stream OBS (Huawei)` con `--no-video` ahora falla **con un mensaje claro** en Android 10 (SDK ≤ 29), porque Android 10 no puede capturar audio en absoluto. En v1.4.1 fallaba igual (por la whitelist) pero con un error engañoso. Decidir si ese perfil debe renombrarse o rediseñarse (p. ej. `mic` + vídeo) es una **decisión de producto**, no técnica: queda para la Fase B.

---

### 11.2 Fase B (2026-10-01) — Cumplir las Leyes 5 y 6

Ejecutada íntegramente. **315/315 pruebas en verde** (24 nuevas en `tests/test_fase_b_regressions.py`).

| # | Acción | Archivos modificados | Prueba de aceptación | Estado |
| :--- | :--- | :--- | :--- | :---: |
| B1 | Grafo `_ALLOWED` en la FSM: rechaza transiciones inválidas sin mutar estado ni notificar | `state.py` | `TestB1FSMValidaTransiciones` (5 pruebas, incl. `IDLE→SUCCESS` rechazado) | ✅ |
| B2 | UI enrutada por la FSM; `_set_status` queda como único renderizador + `_hint` para informativos | `main.py` (27 sitios) | `TestB2UIEnrutadaPorFSM` (4 pruebas) · `grep -c "_set_status("` = **3** (era 30) | ✅ |
| B3 | `get_error_detail()` cableado: cada FAULT registra código, título y remediación bilingüe | `main.py`, `errors.py` | `TestB3RemediacionEnConsola` (4 pruebas, ES + EN) | ✅ |
| B4 | `DeviceCapabilities.model` + propagación de `ro.product.model`; `get_device_props` deja de devolver el fabricante | `domain/models.py`, `managers.py` | `TestB4ModeloDelDispositivo` (4 pruebas, incl. título `MASV: V2314`) | ✅ |
| B5 | `SecurityService` = única implementación criptográfica; `SecurityManager` = fachada con bóveda cifrada | `security.py`, `services/security_service.py`, `context.py` | `TestB5SeguridadUnificada` (7 pruebas, incl. migración verificada) | ✅ |

**Mejoras aplicadas más allá del plan original** (detectadas al ejecutarlo):
- **B2 necesitaba un canal explícito**: no todos los mensajes son estados operativos. Se añadió `_hint()` documentado como el único canal alternativo, con `_set_status()` reducido a renderizador único (2 puntos de llamada). Así el criterio "bajo de 30 a <5" se cumple **sin trampa**: no se renombró el problema, se le dio un sitio propio.
- **B5 necesitaba una propiedad de seguridad que el plan no exigía**: la migración a `vault.enc` ahora hace **verificación de ida y vuelta** (cifrar → descifrar → comparar) y **solo entonces retira el texto plano**, dejando además `config.json.pre-vault.bak`. Si el vault no se puede descifrar, se conserva la copia en claro y se avisa por log: **el usuario nunca pierde la bóveda**.
- **B3 exigía cerrar huecos del catálogo**: 5 códigos nuevos con `ErrorDetail` bilingüe (`APK_INSTALL_FAILED`, `DEVICE_OFFLINE`, `LOCKDOWN_FAILED`, `CONFIG_CORRUPT`, `INVALID_EXTRA_ARGS`) → 11 → **16**.
- **Divergencia de esquema eliminada**: `is_whitelisted_device()` acepta ahora `trusted_devices` como **dict o lista**, que era la causa raíz de que ambos módulos de seguridad no pudieran convivir.
- `security.py` migra sus operaciones mutadoras a `OperationResult` (`trust_device`, `untrust_device`, `remove_device_from_vault`) — avance parcial de la Ley 5 (quedan `utils` y los handlers de UI).

**Métricas tras la Fase B:**

| Métrica | Antes de B | Después de B |
| :--- | :---: | :---: |
| Pruebas | 291 | **315** |
| Cobertura total | 38 % | **39 %** |
| Ley 6 (FSM valida + gobierna) | ❌ / 🟡 | **✅** |
| `_set_status(` en `main.py` | 30 | **3** |
| Catálogo de errores | 11 / 31 códigos | **16 / 31** |
| Implementaciones criptográficas | 2 divergentes (1 muerta) | **1** (`SecurityService`) |
| Bóveda en claro | Siempre en `config.json` | **Cifrada en `vault.enc`** (con fallback y backup) |
| Título de ventana | `MASV: vivo` (fabricante) | **`MASV: V2314`** (modelo) |

**Deuda declarada que NO cierra la Fase B:**
- `vault.enc` vive en `~/.config/masv/` (junto a `config.json`), no en el `~/.MASV/config/` que reserva el layout del instalador. Decidir la ubicación única sigue pendiente (§Anexo B.2).
- La FSM sigue siendo consultada por la UI *después* del cambio, pero `_hint()` no participa del autómata por diseño; si en el futuro se quiere gobernar también esos textos, hay que ampliar el modelo, no usar `_set_status` directamente.
- `get_device_props()` mantiene el nombre legacy y la caché `device_props` nunca se puebla (§4 Vector 1 / P3.18).

### 11.3 Fase C (2026-10-01) — Cerrar los Hitos 2 y 3 (parcial: C1, C3, C4, C5)

**346/346 pruebas en verde** (31 nuevas en `tests/test_fase_c_regressions.py`).
*Nota de entorno:* al ejecutar estas pruebas, el usuario tenía la aplicación abierta con 2 sesiones
scrcpy vivas (puertos 27183/27184), así que 4 pruebas de contrato de puertos fallan por ocupación
real del pool — no por regresión (verificado: con el pool simulado libre pasan). Ver hallazgo nº6.

| # | Acción | Archivos | Prueba de aceptación | Estado |
| :--- | :--- | :--- | :--- | :---: |
| C1 | `StreamService`: la compilación del perfil y el lanzamiento salen de `start_scene_legacy`; el manager queda como fachada | `services/stream_service.py` (nuevo), `managers.py` | `TestC1StreamService` (7 pruebas); `start_scene_legacy` CC **45 → 1** | ✅ |
| C3 | Primitivas `shell`/`install`/`connect`/`kill_server` en el motor + **una sola instancia** compartida | `core/adb_engine.py`, `context.py`, `managers.py`, `main.py` | `TestC3*` (11 pruebas); `subprocess.run([self.ctx.adb` en `main.py`: **17 → 0**; 13 llamadas vía motor | ✅ |
| C4 | 136 cadenas sin traducción EN + fusión verificada | `i18n.py` (bloque `_EN_EXTRA`) | `TestC4CoberturaI18n` (3 pruebas); cobertura de claves usadas **404/404 = 100 %** | ✅ |
| C5 | `build_command` descompuesto en 14 ensambladores/guardas | `core/scrcpy_engine.py` | `TestC5BuildCommandDescompuesto` (8 pruebas); CC **63 → 6**, todos los bloques ≤ 9 | ✅ |
| C2 | Dividir la presentación (`ui/tabs/*`) | — | 🚫 **No ejecutada** (ver decisión abajo) | 🚫 |

**Hallazgos nuevos descubiertos al ejecutar la Fase C** (no estaban en el informe de v1.4.1):

1. **Motor ADB duplicado (Mayor, corregido).** `DeviceManager()` y `SessionManager()` construían **cada uno su propio `AdbEngine`**, con estado independiente: `_effective_port` (socket negociado) y `_activated_by_masv` (registro de quién activó `tcpip`). Consecuencia real: `revert_tcpip()` ejecutado desde la instancia que no activó el modo TCP/IP haría **no-op silencioso** (early-return), dejando el puerto 5555 abierto. Ahora `AppContext` crea **un único** motor y lo inyecta.
2. **El canal de logs se descartaba (Mayor, corregido).** `SessionManager.__init__` hacía `self.log_q = None` en cuanto se le inyectaba un motor ADB: al conectar el motor único, el panel de logs habría dejado de recibir los mensajes de sesión por esa vía. Corregido conservando el `Queue` explícito.
3. **Rama inalcanzable por la whitelist (Menor, documentado).** `_append_video_size`/`_has_size_flag` respetan un tamaño ya elegido (`--max-size`, `--camera-size`, `-m`), pero **ninguno de esos flags está en `ALLOWED_EXTRA_FLAGS`**: esa rama es inalcanzable desde la UI y sólo se puede ejercitar por código. Decisión pendiente: habilitar los flags de tamaño o eliminar la rama muerta.
4. **Trampa de alias en la extracción (Mayor, corregido).** Al extraer el servicio, capturar el motor y el asignador **por valor** rompió 3 pruebas y a cualquier consumidor que sustituya `mgr._scrcpy` después (lo hacen los tests y la propia app al re-detectar binarios). `StreamService` recibe ahora **proveedores** (callables), no valores.
5. **Deuda real de i18n mayor que la declarada (Menor).** No eran "6 claves redundantes": hay **295 entradas EN que no referencia ninguna llamada literal a `_()`** (algunas pueden construirse en runtime). Se tradujo todo lo que faltaba; **no se borró nada** porque la deduplicación exige su propio ADR y pruebas.
6. **La suite no puede correr con la app abierta (Mayor, sin corregir).** `PortAllocator` comprueba disponibilidad real de puerto, y las pruebas de contrato asumen el pool `27183+` libre. Con MASV ejecutándose (uso normal), 4 pruebas fallan. Es una **fragilidad del diseño de pruebas**, no del producto: los tests de contrato de puertos deberían usar una base efímera propia.

**Métricas tras la Fase C:**

| Métrica | Antes de C | Después de C |
| :--- | :---: | :---: |
| Pruebas | 315 | **346** |
| Cobertura total | 39 % | **41 %** |
| Bloques con CC > 10 | 18 (máx. 63) | **17 (máx. 28)** |
| Peor complejidad del repo | `build_command` CC 63 (F) | `sanitize_profile_dict` CC 28 (D) |
| `start_scene_legacy` | CC 45 (F) | **CC 1** (delega) |
| Invocaciones ADB directas desde la UI | 17 | **0** |
| Traducciones EN faltantes | 136 | **0** |
| Motores ADB vivos | 2 (estado divergente) | **1** |

**Decisión de no ejecutar C2 (razonada).** Partir `ui_tabs.py` (1.034 líneas) y `main.py` (2.052) en 5 módulos es un refactor de ~3.000 líneas con **cero cobertura de UI** (3 %–16 %) y sin prueba de humo. La red de seguridad que lo hace verificable es **D1** (smoke test con Tk oculto), que ya está en la Fase D. Ejecutar C2 antes que D1 sería cambiar estructura sin poder demostrar equivalencia de comportamiento — justo el patrón que produjo los bugs de v1.4.1. Se pospone C2 hasta después de D1.

### 11.4 Fase D — D1 · Arnés de humo de UI (2026-10-01)

**369/369 pruebas en verde** (23 nuevas en `tests/test_ui_smoke.py`). El arnés instancia la
aplicación **real** sobre un `Tk` oculto (`DISPLAY=:1`, Xorg disponible) y recorre los flujos
que ninguna prueba unitaria tocaba.

| Bloque | Qué ejercita |
| :--- | :--- |
| D1.1 Construcción | La ventana completa: menú, 7 pestañas, footer, los 37 callbacks del dashboard y las 25 claves de `ui.refs` |
| D1.1b Rastreo estático | Todo `self.X` referenciado en `main.py` existe como método o atributo — caza la clase de P3.2/P3.3 sin ejecutar |
| D1.2 Navegación | Las 7 pestañas por nombre y por índice, `_on_tab_changed`, alternar vista compacta/avanzada |
| D1.3 Botones | **Clic en cada callback registrado** sin dispositivo ni sesión (salvo los de la lista de denegación) |
| D1.4 Sesiones | Arranque de **los 3 perfiles de fábrica** por la UI, detener, copiar comando, matar forzado, pánico, refresco de tabla |
| D1.5 Dependencias | Ruta "faltan adb/scrcpy": se muestra el instalador y la UI aguanta sin motor en vez de reventar |
| D1.6 Validación de IP | El camino real de "Conectar por Wi-Fi" con IP vacía, octetos inválidos y IP privada válida |

**Decisiones de diseño del arnés** (las que costaron iteraciones y no son obvias):

1. **`wait_window` y `grab_set` hay que neutralizarlos.** `TrustPromptModal` llama a
   `parent.wait_window(self.win)` **en su constructor**: sin ese parche, la prueba se congela.
   Y un `grab_set` sin `mainloop` deja el grab global tomado entre pruebas.
2. **Parchear `subprocess.Popen` rompe `subprocess.run`.** `run()` usa `Popen` internamente, así
   que un `MagicMock` como reemplazo hace explotar cualquier `run()` real con
   `ValueError: not enough values to unpack`. La solución es un `Popen` falso **bien
   comportado** (`__enter__`/`__exit__`, `communicate`, `poll`) que devuelve salida vacía y
   código 0: nada se ejecuta, pero `run()` sigue respondiendo.
3. **El doble del motor debe implementar el contrato público completo.** `_copy_sess_cmd` usa
   `build_command`, no sólo `launch`. El doble de scrcpy **valida el argv con el motor real**
   (`ScrcpyEngine.build_command`) y sólo finge el arranque: así el arnés conserva el poder de
   caza de P3.5 (un perfil de fábrica que el motor rechaza) sin abrir procesos.
4. **Lista de denegación explícita.** `_auto_install_deps` (winget/pkexec), `_install_to_system`,
   `_uninstall_from_system`, `_setup_v4l2`/`_route_cam` (modprobe/ffmpeg) y `_open_terminal_install`
   mutan el sistema del usuario: se cubren por otras vías, nunca por clic.
5. **El doble de `SecurityManager` es obligatorio.** `pair_device`/`lockdown_*` lanzan `adb` real
   fuera del motor: sin doblarlos, el arnés tocaría el daemon del usuario.

**Defectos que el arnés cazó en su primera pasada** (no estaban en el informe de v1.4.1):

- **P3.23 — `AttributeError` al conectar por Wi-Fi con una IP vacía o inválida (Mayor).**
  `utils.parse_ip_port()` **nunca devuelve un valor falso**: ante una entrada inválida retorna la
  tupla `(None, None)`, que es *verdadera*. La guarda de `_connect_wifi` era `if not parsed:`, así
  que pasaba de largo con `ip = None` y reventaba en `SecurityManager.is_private_ip(None)` con
  `AttributeError: 'NoneType' object has no attribute 'strip'`. **Reproducido**: escribir cualquier
  cosa inválida (o dejar el campo vacío) y pulsar "Conectar por Wi-Fi".
  *Corregido en dos capas*: la guarda ahora es `if not parsed or not parsed[0]:` (el paso B.3 del
  runbook de la v3.2, que había quedado sin ejecutar) y `is_private_ip()` es **None-safe**
  (devuelve `False`, dirección segura: "desconocida" no es "privada").
  *Causa raíz documentada*: dos parsers hermanos del mismo módulo con convenciones de fallo
  distintas — `parse_ip_port()` devuelve `(None, None)` y `parse_pair_ip_port_code()` devuelve
  `None`. La inconsistencia es la que hizo fácil escribir la guarda equivocada.
- **Flujo de Modo Seguro verificado (no es defecto).** La primera pasada del arnés mostró que los
  perfiles no arrancaban con el dispositivo sin confiar; al leer el código se confirmó que es el
  diseño correcto (`_toggle_scene` abre `TrustPromptModal` y aborta si el usuario no aprueba). El
  arnés se ajustó para recorrer el flujo real (confiar → arrancar) y se añadió la prueba de que
  **sin aprobación no arranca**.

**Métricas tras D1:**

| Métrica | Antes de D1 | Después de D1 |
| :--- | :---: | :---: |
| Pruebas | 346 | **369** |
| Cobertura total | 41 % | **70 %** |
| `ui_tabs.py` | 3 % | **98 %** |
| `ui_widgets.py` | 16 % | **49 %** |
| `main.py` | ~25 % | **55 %** |
| Umbral de la Ley 7 para UI (≥ 60 %) | ❌ | 🟡 (1 de 3 archivos ✅, 2 en camino) |

**Límites declarados del arnés** (lo que D1 *no* cubre, para no confundir cobertura con garantía):
- No abre procesos reales **a propósito**: la ejecución de `scrcpy`/`adb` y el consumo de sus
  salidas siguen dependiendo de las pruebas de integración (`tests/integration/`) y del uso real.
- La bandeja del sistema (`pystray`) y los handlers de instalación/desinstalación quedan fuera por
  su efecto sobre el sistema del usuario.
- Los *internals* de los modales (`ui_widgets.py`, 49 %) sólo se ejercitan en su construcción; sus
  flujos de confirmación siguen sin cubrir (candidato natural para D4).

### 11.5 Fase D (segunda parte) — Demolición de la deuda ciclomática (2026-10-01)

Con D1 como red de seguridad se atacaron los **tres últimos bloques Rank D** del repositorio.
**399/399 pruebas en verde** (30 nuevas en `tests/test_fase_d_regressions.py`).

| Objetivo | Antes | Después | Descomposición |
| :--- | :---: | :---: | :--- |
| `ProfileService.sanitize_profile_dict` | **D · 28** | **A · 2** | Orquestador declarativo + 8 validadores atómicos (`_sanitize_codec/bitrate/resolution/video_source/fps/audio_source/flag/schema_version`), el peor en CC 7 |
| `ScrcpyDockApp._exit` | **D · 23** | **A · 1** | `_shutdown_step` (aislamiento por paso) + 7 fases: trackers, lockdown, sesiones, geometría, tray, single-instance, root |
| `ScrcpyDockApp._on_dev_select` | **D · 21** | **A · 2** | `_resolve_selected_device`, `_update_device_badges`, `_device_state`, `_set_device_info`, `_apply_device_state`, `_announce_online_device`, `_apply_device_profile_association` |

**Resultado global:** el repositorio queda con **0 bloques Rank D o F** (antes 3 D y 2 F en la
v1.4.1) y **14 bloques > 10**, todos Rank C y con máximo **18** (antes 20 bloques, máximo 63).
Un guardián permanente en `test_fase_d_regressions.py::TestComplejidadSinBloquesD` impide que
vuelva a aparecer un bloque Rank D y falla si el recuento supera 14.

**Mejoras de diseño que trajo la descomposición** (no eran el objetivo, pero salieron):

1. **El cierre ya no se aborta por un paso frágil.** Antes, un fallo en `device_mgr.stop_tracking()`
   saltaba al `except` exterior y **dejaba las sesiones scrcpy vivas y la geometría sin guardar**.
   Ahora cada fase se aísla con `_shutdown_step`: hay una prueba que hace fallar el tray y verifica
   que las sesiones se cierran igual (`test_un_paso_que_falla_no_aborta_el_cierre`).
2. **Los 3 indicadores de confianza se pintan desde un solo sitio.** Antes eran tres bloques
   `if/else` idénticos copiados (deuda de duplicación) que podían divergir; ahora es un bucle sobre
   las tres claves.
3. **`True` ya no se cuela como resolución.** El validador antiguo aceptaba `bool` (que en Python
   es `int`) y guardaba la resolución literal `"True"`. Corregido contra el propio contrato del
   docstring, con prueba que lo fija.
4. **`_set_device_info` usa `.get()`**, así un `refs` a medio construir ya no lanza `KeyError`.

**Defecto cazado en esta pasada — P3.24 (Mayor, corregido)**

Al escribir las pruebas de `_on_dev_select` con el **formato de fila real** (mi primer intento usó
filas inventadas, y por eso no vio nada) apareció esto:

- `_update_devs_ui` escribe filas con formatos distintos según el estado:
  `"  🟢 🛡️  {alias}  ({serial})"` para `ok`, pero
  `"  🟠 ⚠️  {serial}  (Sin autorizar en pantalla)"` para `unauth` y
  `"  🔴 ⚠️  {serial}  (Desconectado / Offline)"` para `offline`.
- `_extract_serial()` devuelve **el contenido del primer paréntesis**. Medido:
  `_extract_serial("  🟠 ⚠️  HWY9  (Sin autorizar en pantalla)")` → `"Sin autorizar en pantalla"`.
- Consecuencia doble: (a) las ramas `unauth`/`offline` de `_on_dev_select` buscaban el estado de un
  serial inexistente, obtenían `"other"` y **nunca mostraban el aviso ni ponían la FSM en FAULT** —
  el usuario jamás veía "Acepta el diálogo en el teléfono"; (b) `active_device_serial` quedaba con
  basura, así que cualquier acción posterior apuntaba a un serial inválido.
- **Corrección de raíz** (no en el call site): `_update_devs_ui` guarda `self._devices_shown` y la
  selección se resuelve **por índice contra ese registro**, sin volver a interpretar el texto. El
  parseo queda sólo como respaldo (`_parse_device_row`) para filas ajenas al registro.
- **Regresión**: `TestOnDevSelectDescompuesto` (11 pruebas) reconstruye el formato exacto de las
  cinco filas posibles y comprueba que el serial se resuelve y que los avisos llegan al panel.

**Métricas de la Fase D (completa):**

| Métrica | v1.4.1 | Tras Fase D |
| :--- | :---: | :---: |
| Pruebas | 269 | **399** |
| Cobertura total | 35 % | **72 %** |
| `main.py` | ~25 % | **61 %** |
| `profile_service.py` | 90 % | **98 %** |
| Bloques Rank D o F | 5 (3 D + 2 F) | **0** |
| Peor complejidad | CC 63 (`build_command`, F) | **CC 18** (`_toggle_scene`, C) |
| Bloques > 10 | 20 | **14** |

**Lo que queda de la Fase D** (para no confundir un hito con el final): D2 (linter en CI), D3
(cobertura de `adb_engine.py` 46 % → ≥ 80 %), D4 (exhaustividad de `ERROR_CATALOG` y contraste WCAG)
y D5 (separar `requirements-dev.txt`, extraer la matriz de trade-offs). Y la deuda declarada en
§11.3–11.4: C2 (modularización de la UI), unificar las convenciones de fallo de los dos parsers de
IP, deduplicar las 295 claves i18n huérfanas y reconstruir los ~26 ADR citados y no escritos.

---

## 📎 Anexo A — Archivos y trazabilidad

| Documento | Rol |
| :--- | :--- |
| `ANALISIS.md` (este) | Análisis arquitectónico y plan de evolución v3.3 |
| `AUDIT_REPORT.md` | Auditoría por 5 vectores + verificación de los 11 hallazgos de v1.2 |
| `INFORME_BUGS_v1.4.1.md` | 22 defectos con evidencia reproducible y parche |
| `DECISIONS.md` | ADR-001…005 + matriz de trade-offs |
| `docs/adr/ADR_MASTER_HEXAGONAL.md` | Especificación de la arquitectura hexagonal |
| `git show c88c0a2:ANALISIS.md` | Documento original v3.2 (13-sep-2026), archivado |

**Principio de cierre (Ley 4):** toda corrección de la Fase A/B debe acompañarse de (a) su prueba de aceptación, (b) la actualización del ADR afectado en `DECISIONS.md`, y (c) la re-medición de las métricas de la Ley 7. Una mejora sin métrica que la respalde no se considera cerrada.

---

## 📎 Anexo B — Material operativo de la v3.2 que sigue vigente

### B.1 Decisiones de exclusión (razonadas, sin cambios)

| Núcleo | Dictamen | Razón |
| :--- | :--- | :--- |
| **ADB** (Android Debug Bridge) | ✅ **Consolidar como Engine aislado** | Ya implementado en `core/adb_engine.py` (socket 5038, health-check de estados). Pendiente: que la UI lo use (P3.15) |
| **scrcpy + server** | ✅ **Consolidar con matriz de códecs** | `core/scrcpy_engine.py` (matriz por SDK + override Kirin + fallback de códec) |
| **v4l2loopback** | 🟡 **Consolidar driver de usuario** | Hoy vive en `main.py:_route_cam/_setup_v4l2`, **fuera del motor** (P3.15) |
| **Clientes ADB en Python** (`pure-python-adb`, `adb-shell`) | ❌ **Rechazar** | No soportan el emparejamiento TLS de Android 11+, ni la rotación de claves RSA de Android 12+, ni sockets concurrentes para `scrcpy-server` |
| **`sndcpy` (legacy)** | ❌ **Descartar** | Obsoleto: scrcpy moderno captura audio nativo (`AudioPlaybackCapture`, Android 11+) |
| **Electron / Tauri+Node / CEF** | ❌ **Rechazar** | Rompería el footprint (~35 MB, <45 MB RAM, arranque ~200 ms) del stack Python 3 + Tkinter |

**Estado del núcleo `ScrcpyEngine` respecto a la v3.2:** la matriz de códecs y el auto-fallback H.264 están implementados y testeados (`_CODECS_BY_SDK`, `is_codec_failure`, `_launch_with_fallback`). El **control de versión de `scrcpy-server.jar` (ADR-014) sigue sin cablear**: `verify_server_version()` existe y nunca se invoca (P3.18).

### B.2 Layout de despliegue encapsulado (`~/.MASV/`) — implementado

```
$HOME/.MASV/
├── bin/MASV              # Ejecutable (copia persistente del binario)
├── assets/logo.png
├── config/               # (reservado)
└── logs/                 # (reservado)
```
Puntos de enlace XDG gestionados por `InstallerService`:
1. `~/.local/bin/MASV` (symlink para terminal) — `installer_service.py:89`.
2. `~/.local/share/applications/MASV.desktop` — `installer_service.py:85`.

> ⚠️ **Configuración real del usuario:** hoy vive en `~/.config/masv/config.json` (no en `~/.MASV/config/`), con permisos `0600` y directorio `0700` (`utils.py:220-227`) según ADR-005. El `config/` de `~/.MASV/` está creado pero vacío. Conviene decidir una sola ubicación.
> ⚠️ **Bóveda cifrada:** el layout prevé `config/vault.enc`, pero el cifrado (`SecurityService`) no se usa (P3.14).
> ⚠️ **Desktop entry:** `installer_service._render_desktop_entry` escribe `Exec={exec_path}` **sin entrecomillar**; una ruta con espacios (como la carpeta de este mismo proyecto, `Estudio Memexicanisimos/MASV`) produce una entrada inválida. Requiere comillas.

### B.3 Scorecard v3.2 vs v3.3 (referencia de evolución)

| Vector | v3.2 (13-sep) | v3.3 (01-oct) | Δ |
| :--- | :---: | :---: | :---: |
| V1 Dominio, Invariantes & Legal | 95 % | 88 % | ▼ 7 |
| V2 Contratos, Esquema & Catálogo | 92 % | 88 % | ▼ 4 |
| V3 Lógica, Concurrencia & Hardening | 90 % | 84 % | ▼ 6 |
| V4 Interfaz, Ergonomía & Estados FSM | 94 % | 80 % | ▼ 14 |
| V5 Infraestructura & Despliegue | 96 % | 90 % | ▼ 6 |
| **Global** | **93 %** (declarado) | **86 %** (medido) | ▼ 7 |

> **Actualización tras las Fases A, B y C (2026-10-01):** V1 90 %, V2 92 %, V3 88 %, V4 86 %, V5 91 % → **global 89 %**. El alza corresponde a 7 correcciones críticas, la FSM gobernante, la bóveda cifrada, la extracción de `StreamService`, el canal ADB único, el 100 % de cobertura i18n y 77 pruebas nuevas (269 → 346); la cobertura de UI (3 %) y la complejidad (17 bloques > 10) siguen lastrando el V4 y no se resuelven hasta la Fase C2/D.

> **Advertencia metodológica:** los porcentajes de la v3.2 eran *declarativos* (proyectaban la arquitectura diseñada). Los de la v3.3 son *medidos* contra umbrales verificables (cobertura, complejidad, FSM). La caída no indica necesariamente una regresión del producto —indica que **ahora se mide lo que antes se asumía**. Los tests pasaron de 18 a 269 y los núcleos existen; el descenso refleja que la UI, la FSM y el catálogo **no alcanzan el estándar que el documento anterior daba por cumplido**.
