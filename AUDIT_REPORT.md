# 📋 INFORME DE AUDITORÍA INTEGRAL DE SOFTWARE — MASV

**Motor Autónomo de Auditoría y Evolución de Software — Estándar de 5 Vectores**

Este documento contiene **dos rondas de auditoría**:

| Ronda | Versión auditada | Fecha | Estado |
| :--- | :--- | :--- | :--- |
| **Parte I — Auditoría original** | v1.2 | 2026-09-02 | Referencia histórica (contenido preservado) |
| **Parte II — Verificación de resolución** | v1.4.1 | 2026-10-01 | ✅ Completada |
| **Parte III — Revisión de bugs** | v1.4.1 | 2026-10-01 | ✅ Completada |

> El detalle exhaustivo de los defectos nuevos (con evidencia reproducible y parches sugeridos) vive en
> **`INFORME_BUGS_v1.4.1.md`**. La Parte III de este documento los resume y los mapea por vector.

---
---

# PARTE I — AUDITORÍA ORIGINAL (v1.2)

## 📌 Resumen Ejecutivo

- **Proyecto**: MASV — Memexicanisimos Android Screen Viewer
- **Versión auditada**: 1.2
- **Arquitectura**: Aplicación de escritorio nativa en Python 3 con Tkinter GUI, gestor de procesos asíncronos para `scrcpy` y `adb`, bóveda de dispositivos de confianza (Trusted Vault) y blindaje de puertos TCP/IP.
- **Fecha de auditoría**: 2026-09-02
- **Resultado Global**: **88/100 (Estado Maduro / Operativo con Oportunidades Clave de Estandarización)**

## 🔬 Matriz de Evaluación por Vectores (v1.2)

| Vector | Nombre | Calificación | Estado | Hallazgos Críticos | Hallazgos Mayores | Hallazgos Menores |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **V1** | **Dominio, Invariantes & Marco Legal** | 92% | Sólido | 0 | 1 | 1 |
| **V2** | **Contratos de Datos, Esquema & Catálogo de Fallos** | 78% | Requiere Estandarización | 0 | 2 | 2 |
| **V3** | **Lógica de Dominio, Concurrencia & Hardening** | 90% | Robusto | 0 | 1 | 1 |
| **V4** | **Superficie de Interfaz, Ergonomía & Mapeo de Estados** | 88% | Alta Calidad Visual | 0 | 1 | 2 |
| **V5** | **Infraestructura, Resiliencia & Auditoría Cruzada** | 92% | Automatizado | 0 | 1 | 1 |

## 🔍 Detalle de Hallazgos por Vector (v1.2)

### 🔷 Vector 1: Dominio, Invariantes & Marco Legal
- **Hallazgo 1.1 (Mayor)**: Invariantes de ciclo de vida no formalizados mediante tipos o máquinas de estados explícitas (las entidades `Device`, `Session`, `Profile` se manejan como tuplas y diccionarios sueltos).
  - *Evidencia*: `managers.py` (`DeviceManager.devices = [(serial, model, status)]`, `ScrcpySession`).
  - *Acción Sugerida*: Modelar clases de dominio inmutables o `dataclasses` con estados explícitos (`DeviceState`, `SessionState`).
- **Hallazgo 1.2 (Menor)**: Documentación de términos de licencia y atribución a `scrcpy` (Apache 2.0) y `MASV` (MIT) en el código fuente.
  - *Evidencia*: `README.md` y `LICENSE` presentes, pero falta cabecera formal de invariantes en `context.py`.
  - *Acción Sugerida*: Documentar invariantes y términos legales en cabeceras de arquitectura.

---

### 🔷 Vector 2: Contratos de Datos, Esquema & Catálogo de Fallos
- **Hallazgo 2.1 (Mayor)**: Ausencia de un contrato unificado de transporte/IPC `ApiResponse<T>` / `OperationResult<T>`.
  - *Evidencia*: Métodos en `security.py`, `managers.py` y `main.py` devuelven firmas dispares (`Tuple[bool, str]`, `bool`, `Optional[Tuple[...]]`, `None`).
  - *Acción Sugerida*: Crear módulo `scrcpy_dock/contracts.py` implementando `OperationResult[T]` con `{ success: bool, data: Optional[T], error_code: Optional[ErrorCode], message: str }`.
- **Hallazgo 2.2 (Mayor)**: Ausencia de un catálogo formal de códigos de error (`ErrorCode` Enum).
  - *Evidencia*: Los fallos se representan con cadenas de texto dinámicas en `security.py` y mensajes directos en `main.py`.
  - *Acción Sugerida*: Crear `scrcpy_dock/errors.py` con `ErrorCode` tipado (`DEVICE_NOT_FOUND`, `UNAUTHORIZED_DEVICE`, `PAIRING_TIMEOUT`, `ADB_UNAVAILABLE`, etc.).
- **Hallazgo 2.3 (Menor)**: Validación de esquema de configuración `config.json` basada en `dict.setdefault` sin validación estricta de tipos de datos.
  - *Evidencia*: `utils.py` `load_config()`.
  - *Acción Sugerida*: Implementar validación de esquema con fallback seguro contra archivos de configuración corruptos o con tipos inválidos.

---

### 🔷 Vector 3: Lógica de Dominio, Concurrencia & Hardening
- **Hallazgo 3.1 (Mayor)**: Validación de argumentos adicionales (`extra_args`) en perfiles de usuario.
  - *Evidencia*: `SessionManager.start_scene()` usa `shlex.split(profile_data["extra_args"])`, pero no filtra flags que puedan interferir con la seguridad o rutas no deseadas.
  - *Acción Sugerida*: Implementar lista de flags permitidos o sanitización de argumentos en perfiles.
- **Hallazgo 3.2 (Menor)**: Manejo de cancelación y ciclo de vida de hilos de fondo (`ThreadPoolExecutor` y threads daemon).
  - *Evidencia*: `DeviceManager.scan_devices()` y `SessionManager.start_scene()` lanzan hilos daemon directos.
  - *Acción Sugerida*: Centralizar la ejecución de tareas asíncronas en un despachador de tareas unificado con manejo de excepciones y cancelación.

---

### 🔷 Vector 4: Superficie de Interfaz, Ergonomía & Mapeo de Estados
- **Hallazgo 4.1 (Mayor)**: Ausencia de un Autómata Finito de Interfaz formalizado (`[IDLE]`, `[PENDING]`, `[SUCCESS]`, `[EMPTY]`, `[FAULT]`).
  - *Evidencia*: Los estados de la UI (escaneo, conexión, streaming, fallo) se actualizan modificando etiquetas individuales y botones de manera ad-hoc en `main.py`.
  - *Acción Sugerida*: Implementar un controlador de estado de UI (`UIStateController`) que transicione coherentemente entre los 5 estados canónicos.
- **Hallazgo 4.2 (Menor)**: Notificaciones de error de subprocess en consola sin mapeo semántico a acciones de recuperación.
  - *Evidencia*: Líneas de error de `adb` se imprimen directamente en el log sin ofrecer un botón de acción rápida (ej. "Reconectar USB" o "Aceptar diálogo en teléfono").
  - *Acción Sugerida*: Mapear códigos de fallo a mensajes guiados con acciones contextuales en el log.

---

### 🔷 Vector 5: Infraestructura, Resiliencia & Auditoría Cruzada
- **Hallazgo 5.1 (Mayor)**: Cobertura de pruebas unitarias enfocada únicamente en utilidades y seguridad, sin pruebas automatizadas para managers con mocks de `subprocess` ni para el contrato `ApiResponse`.
  - *Evidencia*: `tests/` contiene 18 pruebas (`test_core.py`, `test_security.py`), cubriendo 0 pruebas de integración de ciclo de vida de sesiones o fallos de ADB.
  - *Acción Sugerida*: Agregar `tests/test_contracts.py` y `tests/test_managers.py` con mocks de subprocess y assertions de contratos.
- **Hallazgo 5.2 (Menor)**: Ejecución de pruebas en el pipeline de GitHub Actions (`.github/workflows/build.yml`) antes del empaquetado.
  - *Evidencia*: El workflow ejecuta `build.py` directamente sin un paso previo obligatorio de `python -m unittest discover`.
  - *Acción Sugerida*: Incorporar el paso de testing automatizado en la matriz de CI/CD.

---

## 📊 Matriz de Brechas y Artefactos Faltantes (v1.2)

| Artefacto Faltante / A Actualizar | Vector | Criticidad | Beneficio |
| :--- | :---: | :---: | :--- |
| `scrcpy_dock/contracts.py` | V2 | **Mayor** | Estandarización de `OperationResult[T]` (Leyes Globales 2 y 5). |
| `scrcpy_dock/errors.py` | V2 | **Mayor** | Catálogo formal de `ErrorCode` con descripciones bilingües. |
| `scrcpy_dock/state.py` | V4 | **Mayor** | Autómata finito de interfaz con estados `[IDLE, PENDING, SUCCESS, EMPTY, FAULT]`. |
| `DECISIONS.md` | V1-V5 | **Mayor** | Registro formal de decisiones arquitectónicas y Matriz de Trade-offs. |
| `tests/test_contracts.py` | V5 | **Mayor** | Verificación automatizada de contratos, errores y serialización. |
| `tests/test_state.py` | V5 | **Mayor** | Pruebas unitarias del autómata de estados de UI. |
| `.github/workflows/build.yml` | V5 | **Menor** | Integración de test runner previo a la compilación. |

---

## 🎯 Lista Priorizada de Mejoras (Fase 2)

1. **Prioridad 1 (Contratos & Catálogo de Errores - V2)**:
   - Crear `contracts.py` con `OperationResult[T]`.
   - Crear `errors.py` con `ErrorCode` y mapeo de errores del backend y ADB.
2. **Prioridad 2 (Autómata Finito de Interfaz - V4)**:
   - Crear `state.py` con `UIState` (`IDLE`, `PENDING`, `SUCCESS`, `EMPTY`, `FAULT`) y transiciones seguras.
   - Conectar el estado de la UI en `main.py` y `ui_tabs.py` para reflejar visualmente el estado del sistema.
3. **Prioridad 3 (Hardening & Refactorización de Managers - V3)**:
   - Refactorizar `managers.py` y `security.py` para utilizar `OperationResult[T]` y `ErrorCode`.
   - Validar y sanitizar `extra_args` en perfiles.
4. **Prioridad 4 (Cobertura de Pruebas & Infraestructura - V5)**:
   - Crear suites de prueba para contratos, errores y autómata de estados.
   - Añadir ejecución de pruebas en `.github/workflows/build.yml`.
5. **Prioridad 5 (Documentación & Matriz de Decisiones - V1 & V5)**:
   - Generar `DECISIONS.md` con las justificaciones técnicas y matriz de trade-offs.

---
---

# PARTE II — VERIFICACIÓN DE RESOLUCIÓN (v1.4.1)

**Fecha de verificación:** 2026-10-01 · **Commit:** `795f6e4` (v1.4.1, rama `main`)

**Método:** lectura del código actual + `grep` dirigidos + comprobaciones ejecutables (`hasattr`, conteo de invocaciones, inspección de firmas de retorno). Cada veredicto lleva su evidencia.

## Cuadro de estado

| # | Hallazgo (v1.2) | Sev. | Estado | Evidencia clave |
| :---: | :--- | :---: | :---: | :--- |
| 1.1 | Invariantes de dominio como tuplas/dicts | Mayor | 🟡 **Parcial** | `domain/models.py` creado y usado en el core; `managers.py:105` sigue con tuplas |
| 1.2 | Cabeceras de licencia/invariantes en `context.py` | Menor | ❌ **Pendiente** | `context.py` sigue empezando en `import queue` |
| 2.1 | Contrato unificado `OperationResult[T]` | Mayor | ✅ **Resuelto** | `contracts.py` + uso sistemático en core/services (con matices) |
| 2.2 | Catálogo formal `ErrorCode` | Mayor | ✅ **Resuelto** | `errors.py`: 30 códigos + `ErrorDetail` bilingüe |
| 2.3 | Validación de esquema de `config.json` | Menor | ❌ **Pendiente (agravado)** | `utils.load_config()` sin validación de tipos + alias mutable |
| 3.1 | Validación de `extra_args` | Mayor | ✅ **Resuelto** | Whitelist + rechazo de operadores shell (con **regresión**) |
| 3.2 | Ciclo de vida/cancelación de hilos | Menor | 🟡 **Parcial** | Tracker con backoff; sin watchdog de sesión ni dispatcher |
| 4.1 | FSM de UI de 5 estados | Mayor | 🟡 **Parcial** | `state.py` existe y se suscribe; no valida transiciones y la UI la evade |
| 4.2 | Mapeo error → acción de recuperación | Menor | 🟡 **Parcial** | `ErrorDetail.remediation_*` existe; `get_error_detail` **nunca se usa** |
| 5.1 | Cobertura de pruebas de managers/contratos | Mayor | ✅ **Resuelto** | 269 tests (antes 18), con mocks y contratos |
| 5.2 | Tests en el pipeline de CI | Menor | ✅ **Resuelto** | `.github/workflows/build.yml:58-60` corre `unittest discover` antes del build |

**Resultado:** de 11 hallazgos → **5 resueltos**, **4 parciales**, **2 pendientes**. De los 5 objetivos de la Fase 2: 3 cerrados por completo y 2 a medias.

## Artefactos faltantes (v1.2) — estado

| Artefacto | Estado | Nota |
| :--- | :---: | :--- |
| `scrcpy_dock/contracts.py` | ✅ Creado | Con `OperationResult`, `DeviceEntry`, `SessionInfo`, `ProfileConfig`, `TrustedDeviceEntry` |
| `scrcpy_dock/errors.py` | ✅ Creado | 30 `ErrorCode`; `ERROR_CATALOG` detalla 13 |
| `scrcpy_dock/state.py` | ✅ Creado | `UIState` + `UIStateMachine` (sin validación de transiciones) |
| `DECISIONS.md` | ✅ Creado | Registro de ADR y matriz de trade-offs |
| `tests/test_contracts.py` | ✅ Creado | + `tests/contracts/` (7 suites de contrato) |
| `tests/test_state.py` | ✅ Creado | Cubre transiciones y observadores |
| CI con test runner | ✅ Integrado | Pendiente paso de linter |

## Detalle por hallazgo

### 1.1 🟡 Parcial — Modelo de dominio creado, frontera sin migrar

**Resuelto:** existe `scrcpy_dock/domain/models.py` con `@dataclass(frozen=True)` para `Device`, `DeviceCapabilities` y `SessionConfig`, más enums explícitos `DeviceState{DEVICE, UNAUTHORIZED, OFFLINE}`, `Codec{H264,H265,AV1}` y `ConnectionType{USB,WIFI}`. `domain/protocols.py` define los `Protocol` `SessionProcess` y `TrackerHandle`. El núcleo (`scrcpy_engine`, `adb_engine`, `SessionManager._start_scene_hexagonal`) ya consume estos tipos, en lugar de tuplas.

**Pendiente:**
- `managers.py:105-107` mantiene **tres representaciones paralelas** del mismo dato: `devices: List[Tuple[str,str,str]]`, `device_entries: List[DeviceEntry]` y `_caps_cache`.
- `ScrcpySession` (`managers.py:31`) sigue siendo una clase plana con `self.active: bool`; **no existe `SessionState`** (verificado: `grep -rn "SessionState" scrcpy_dock/domain/` → sin resultados; la acción sugerida pedía ambos enums).
- `DeviceCapabilities` no transporta el modelo del dispositivo, lo que provoca directamente el bug **P3.8** de la Parte III (título de ventana "MASV: vivo" en vez de "MASV: V2314").

**Conclusión:** la deuda se movió, no se eliminó. El dominio está tipado; la capa de managers/UI sigue con tuplas.

### 1.2 ❌ Pendiente

`scrcpy_dock/context.py` sigue sin cabecera de invariantes/licencia (sus primeras líneas son `import queue` / `import tkinter as tk`). `LICENSE`, `README.md` y `docs/adr/ADR_MASTER_HEXAGONAL.md` existen, así que el marco legal está presente, pero no a nivel de cabecera de arquitectura como pedía la acción sugerida.

### 2.1 ✅ Resuelto (con matices)

`scrcpy_dock/contracts.py` implementa `OperationResult[T]` con `ok()`, `fail()`, `__iter__` (compatibilidad con el patrón `ok, msg = func()`), `__bool__` y `to_dict()`. `core/` y `services/` lo devuelven de forma sistemática.

**Matices:**
- `security.py` conserva firmas heterogéneas: `trust_device() -> dict`, `untrust_device() -> None`, `remove_device_from_vault() -> None`, `lockdown_all_devices() -> int`, `kill_adb_server() -> bool`. La estandarización del Vector 2 no llegó a ese módulo.
- `OperationResult` arrastra **dos campos espejo** (`error` y `error_code`) sincronizados en `__post_init__`, y `ok()` deja `error = ErrorCode.NONE`, que es *truthy* ⇒ un `if res.error:` es siempre verdadero. Trampa latente para el siguiente que lo use.

### 2.2 ✅ Resuelto (con deuda)

`errors.py` define 30 códigos y `ErrorDetail` bilingüe (`title_es/en`, `description_es/en`, `remediation_es/en`) más `get_error_detail()` con fallback seguro para códigos desconocidos.

**Deuda:**
- `ERROR_CATALOG` sólo detalla **13 de los 30** códigos.
- `BLOCKED_IP_ACCESS`, `DEVICE_OFFLINE` y `V4L2_LOOPBACK_ERROR` están definidos y **no se usan en ningún punto**.
- Existe un código **invocado pero inexistente**: `ErrorCode.INTERNAL_ERROR` (`services/security_service.py:207`), que convierte una ruta de error en `AttributeError` (bug **P3.4**).

### 2.3 ❌ Pendiente (agravado)

`utils.load_config()` (`utils.py:265-281`) sigue sin validar tipos: si `config.json` contiene `"profiles": []`, la guarda `elif isinstance(v, dict) and isinstance(data[k], dict)` no se cumple y **el valor inválido se conserva tal cual**. El fallback "fichero corrupto" tampoco valida estructura.

Y hay un defecto **nuevo** en esa misma función: el camino "fichero ausente/corrupto" devuelve `dict(DEFAULT_CONFIG)`, una **copia superficial** cuyos subdicts comparten identidad con la constante global (`profiles`, `security`, `device_associations`). Cualquier mutación (guardar perfil, confiar dispositivo, alternar Modo Seguro) contamina los valores "de fábrica" del proceso — verificado experimentalmente (bug **P3.11**).

**Nota importante:** la solución correcta **ya está escrita** en `services/profile_service.py` (`sanitize_profile_dict`, `migrate_v1_to_v2`, escritura atómica `.tmp` + `os.replace`, `schema_version`, permisos). Pero **no está cableada a la UI**: la aplicación real sigue leyendo por `utils.load_config()`. El artefacto existe y está desconectado.

### 3.1 ✅ Resuelto — con una regresión funcional introducida

Hay **doble capa de defensa**, justo lo que pedía la acción sugerida:

1. `SecurityManager.validate_extra_arguments()` (`security.py:213-234`) rechaza operadores de shell (`;`, `&&`, `||`, `|`, backtick, `$(`, `>`, `<`).
2. `ScrcpyEngine.build_command()` (`scrcpy_engine.py:208-215`) valida cada token contra `ALLOWED_EXTRA_FLAGS = {--no-control, --power-off-on-close, --show-touches, --stay-awake, --window-title}`.
3. `SessionManager.start_scene_legacy()` (`managers.py:489-514`) normaliza tokens legacy (`--video-source=camera`, `--camera-id`, `--camera-facing`, `--otg`) promoviéndolos a campos tipados de `SessionConfig`, de modo que ya no disparan la whitelist.

**Regresión:** la whitelist es tan estricta que rompe una función propia. `--no-video` (modo "solo audio") **no** está permitido, así que el **perfil por defecto `🎙️ Stream OBS (Huawei)`** (`utils.py:241`) y el preset equivalente del asistente (`ui_widgets.py:545`) **no arrancan nunca**:

```
build_command(SessionConfig(extra_args=("--no-video",)))
  → success: False | error_code: INVALID_EXTRA_ARGS
  → "Flag no permitido en extra_args: --no-video"
```

El hardening resolvió el hallazgo pero introdujo una regresión que ningún test detecta (bug **P3.5**).

### 3.2 🟡 Parcial

**Resuelto:** `AdbEngine.track_devices_async()` + `_TrackerThread` (`adb_engine.py:462-661`) con reconexión y backoff exponencial (1, 2, 4, 8, 16 s), `stop_tracker()` idempotente, y la fachada `DeviceManager.start_tracking()/stop_tracking()`.

**Pendiente:**
- `start_scene_legacy()` lanza scrcpy **sin** `on_exit` ni `on_stderr_line` (`managers.py:556`), a diferencia del camino hexagonal (`managers.py:360` que sí los usa): el camino que usa la UI no tiene watchdog de muerte de la sesión.
- `_TrackerThread.stop()` no interrumpe el `proc.stdout.read(4)` bloqueante; el `join(timeout=2.0)` puede retornar con el hilo todavía vivo (bug **P3.22**).
- No existe el "despachador de tareas unificado" pedido: siguen conviviendo `threading.Thread(daemon=True)` sueltos (~15 sitios en `main.py`) y en managers.

### 4.1 🟡 Parcial — FSM creada, pero no gobernante

**Resuelto:** `state.py` implementa `UIState{IDLE, PENDING, SUCCESS, EMPTY, FAULT}` y `UIStateMachine` con `subscribe`/`unsubscribe`, `transition_to`, helpers `set_idle/set_pending/set_success/set_empty/set_fault` y `get_status_info()`. Está suscrita en `main.py:121` (`_on_ui_state_change`) y pinta el color de estado en la barra inferior. Tiene tests (`tests/test_state.py`).

**Pendiente:**
- `transition_to()` **no valida transiciones**: siempre retorna `True` y no consulta tabla alguna, pese a documentar "si es válida". No es un autómata, es un *setter* (bug **P3.19**).
- La UI **evade la FSM**: **30 llamadas directas a `self._set_status(...)`** frente a sólo **9** a `state_machine.set_*`. La mayoría de los mensajes visibles (errores de ADB, WiFi, emparejamiento, APK, lockdown) no pasan por el autómata, así que el estado visible no es coherente ni respeta las transiciones canónicas.

### 4.2 🟡 Parcial — el mapeo existe, pero no llega a la UI

**Resuelto:** `ErrorDetail` incluye `title`, `description` y `remediation` en ES/EN, y `errors.get_error_detail()` resuelve el detalle con fallback.

**Pendiente:** `get_error_detail` se **importa en `main.py:25` y nunca se invoca** (confirmado por `pyflakes`: `'get_error_detail' imported but unused`). Los errores siguen mostrándose como texto crudo del subprocess en la consola, sin acción contextual. El artefacto se construyó y quedó desconectado.

### 5.1 ✅ Resuelto

De 18 a **269 pruebas**, verificado con dos runners:

```bash
python -m pytest -q                              # 269 passed
python -m unittest discover -s tests -v          # 269 tests OK (el del CI)
```

| Suite | Contenido |
| :--- | :--- |
| `tests/contracts/` (7 archivos) | Contratos de `adb_engine`, `scrcpy_engine`, `port_allocator`, `profile_service`, `security_service`, `installer_service`, `domain_models` |
| `tests/integration/` (5 archivos) | Device manager, session manager, codec fallback, smoke de servicios, estructural — con `fakes.py` |
| `tests/test_managers.py`, `test_hardware_governance.py` | Mocks de `subprocess.Popen` y de `AdbEngine` |
| `tests/test_contracts.py`, `test_state.py`, `test_security.py`, `test_core.py` | Contratos, FSM, seguridad, utilidades |
| `tests/test_connection_modes.py`, `test_tether_engine.py`, `test_v14_features.py` | Modos USB/cámara/OTG/WiFi, tethering, features v1.4 |

**Brecha nueva (no medible en v1.2 porque apenas había tests):** **0 pruebas importan `scrcpy_dock.main`**. Por eso la suite pasa 269/269 mientras los handlers de UI contienen 4 fallos duros (`AttributeError`/`NameError`, Parte III P3.1-P3.3 y P3.6). La cobertura es profunda en dominio y **nula en la superficie que el usuario toca**.

### 5.2 ✅ Resuelto

`.github/workflows/build.yml:58-60` ejecuta `python -m unittest discover -s tests -v` antes de `python build.py` (línea 65), en la matriz ubuntu/windows/macos.

**Pendiente:** no hay paso de análisis estático (`pyflakes`/`ruff`) ni `--failfast`. Un linter habría detectado P3.6 y los 20+ imports muertos.

---
---

# PARTE III — REVISIÓN DE BUGS (v1.4.1)

> Detalle completo, evidencia reproducible y parches sugeridos uno por uno: **`INFORME_BUGS_v1.4.1.md`**.
> Aquí se resume y se mapea cada defecto al vector correspondiente.

**Resultado de la suite:** 269/269 OK. Los defectos siguientes **no** están cubiertos por ningún test.

## Tabla resumen

| ID | Sev. | Defecto | Vector | Ubicación |
| :--- | :---: | :--- | :---: | :--- |
| P3.1 | 🔴 | `SessionManager.stop()` inexistente → Detener sesión (Supr / clic derecho / botón) lanza `AttributeError`; el método además está **duplicado** | V3 | `main.py:1660,1670` (+ `1527`) |
| P3.2 | 🔴 | `SessionManager._build_cmd()` inexistente → "Copiar comando scrcpy" lanza `AttributeError` | V3 | `main.py:1710` |
| P3.3 | 🔴 | `DeviceManager.get_device_model()` inexistente → Modo Seguro + dispositivo no confiable rompe **antes** del *TrustPrompt* | V1/V4 | `main.py:1400,1458` |
| P3.4 | 🔴 | `ErrorCode.INTERNAL_ERROR` no existe en el catálogo → `AttributeError` enmascara errores de cifrado | V2 | `services/security_service.py:207` |
| P3.5 | 🔴 | `--no-video` fuera de la whitelist → el modo "solo audio" y el perfil por defecto nunca arrancan | V3 | `utils.py:241`, `ui_widgets.py:545`, `scrcpy_engine.py:39` |
| P3.6 | 🔴 | `NameError`: un `lambda` captura la variable `e` de un `except` ya finalizado | V4 | `main.py:667-668` |
| P3.7 | 🔴 | La suite escribe en el `config.json` real del usuario → **pérdida de datos** (perfiles + bóveda) | V5 | `tests/test_core.py:41-45` |
| P3.8 | 🟠 | `get_device_props()` devuelve el **fabricante** como modelo → título "MASV: vivo" en vez de "MASV: V2314" | V1 | `managers.py:121` |
| P3.9 | 🟠 | Los 4 botones de Quick Cast buscan perfiles con nombres inexistentes → no hacen nada, en silencio | V4 | `ui_tabs.py:83-87` |
| P3.10 | 🟠 | `_connect_wifi` nunca detecta IP inválida: `if not parsed` sobre una tupla `(None, None)` (*truthy*) | V4 | `main.py:812-816` |
| P3.11 | 🟠 | `load_config()` comparte subdicts con `DEFAULT_CONFIG` (copia superficial) → contamina los defaults | V2 | `utils.py:265-281` |
| P3.12 | 🟠 | i18n EN incompleta: **133 literales** pasados a `_()` sin traducción (menús, cabecera, barra lateral) | V4 | `i18n.py` vs `main.py`/`ui_tabs.py` |
| P3.13 | 🟠 | 6 claves duplicadas en el diccionario EN (valores sobrescritos en silencio) | V4 | `i18n.py:166/487, 284/489, 285/490, 10/176` |
| P3.14 | 🟡 | `security.py` y `services/security_service.py` divergen; la bóveda cifrada (Fernet+PBKDF2) es código muerto | V2/V3 | ambos módulos |
| P3.15 | 🟡 | La UI evita `AdbEngine` y usa `subprocess` directo → rompe el aislamiento de socket (ADR-006) | V3 | `main.py` (10 sitios) |
| P3.16 | 🟡 | Docs vs código: puertos (21 reales vs "16 / 27199"), perfiles citados inexistentes, versión "v1.4" vs 1.4.1, ejemplos de `extra_args` no permitidos | V1 | varios |
| P3.17 | 🟡 | `index.html` y `style.css` versionados con restos de prueba ("Prueba de Concurrencia") | V5 | raíz del repo |
| P3.18 | 🟡 | Código muerto/sin cablear: `verify_server_version`, `get_error_detail`, catálogo incompleto, ruta `server_jar`, doble campo `error`/`error_code` | V2/V5 | varios |
| P3.19 | 🟡 | `UIStateMachine.transition_to()` no valida transiciones (retorna siempre `True`) | V4 | `state.py:54-67` |
| P3.20 | 🟡 | `ScrcpySession.terminate()` bloquea el hilo de Tk hasta 3 s por sesión | V4 | `managers.py:57-68` + `main.py:1501` |
| P3.21 | 🟡 | `SingleInstance` sin `SO_REUSEADDR` → falso "ya está en ejecución" tras reinicio | V3 | `utils.py:350-363` |
| P3.22 | 🟡 | `_TrackerThread.stop()` no desbloquea el `read(4)`; el hilo puede sobrevivir al `join` | V3 | `adb_engine.py:612,657` |

**Totales:** 7 🔴 críticos · 6 🟠 altos · 9 🟡 medios/estilo.

## Relación con los hallazgos de la Parte I

- **P3.5 es una regresión del Hallazgo 3.1**: el hardening de `extra_args` (correcto en principio) se aplicó sin verificar que los perfiles por defecto siguieran siendo válidos.
- **P3.8, P3.18 y P3.4 derivan de los pendientes 1.1, 4.2 y 2.2**: modelos de dominio incompletos, mapeo de errores sin cablear y catálogo con huecos.
- **P3.1, P3.2, P3.3 y P3.6 quedaron invisibles por la brecha del Hallazgo 5.1** (cero tests de la capa de UI), no por falta de tests en general.
- **P3.7 es deuda introducida por la propia suite** escrita para cerrar el Hallazgo 5.1.

---
---

# PARTE IV — PUNTUACIÓN ACTUALIZADA (v1.4.1)

> Juicio de ingeniería basado en los hallazgos anteriores; escala comparable a la Parte I.

| Vector | v1.2 | v1.4.1 | Δ | Estado | Justificación |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **V1** Dominio, Invariantes & Legal | 92% | 88% | ▼ 4 | 🟡 | Modelo de dominio creado (mejora), pero managers/UI siguen con tuplas y falta el marco legal en cabeceras; `DeviceCapabilities` incompleto genera un bug funcional (P3.8) |
| **V2** Contratos & Catálogo | 78% | 88% | ▲ 10 | 🟢 | `contracts.py` y `errors.py` existen y se usan en core/services; persisten huecos del catálogo, un código invocado inexistente (P3.4) y la validación de esquema sin conectar (2.3) |
| **V3** Lógica, Concurrencia & Hardening | 90% | 84% | ▼ 6 | 🟡 | Hardening de `extra_args` logrado, pero con regresión funcional (P3.5); seguridad duplicada y divergente; UI fuera de `AdbEngine`; bugs P3.1 y P3.2 |
| **V4** Interfaz, Ergonomía & Estados | 88% | 80% | ▼ 8 | 🟡 | FSM creada pero no validante ni gobernante; i18n incompleta (133 claves); varios handlers de UI rotos (P3.3, P3.6, P3.9, P3.10) |
| **V5** Infraestructura & Resiliencia | 92% | 90% | ▼ 2 | 🟢 | Salto de 18 → 269 tests y CI con test runner (excelente), pero cero cobertura de `main.py` y **la suite destruye la config del usuario** (P3.7) |
| **GLOBAL** | **88** | **86** | ▼ 2 | 🟡 | Mejor arquitectura y cobertura, contrarrestadas por 7 defectos críticos nuevos, dos de ellos con pérdida de datos o funcionalidad anunciada inoperante |

**Lectura:** v1.4.1 mejoró sustancialmente el **andamiaje** (contratos, catálogo, FSM, suite de tests, CI), pero descendió en **verificación de la superficie real**: nada prueba `main.py`, y ahí están los fallos. El patrón dominante del release es *"artefacto construido y no cableado"*: `get_error_detail`, `ProfileService`, `SecurityService`, `verify_server_version`.

---

# PARTE V — PLAN DE ACCIÓN CONSOLIDADO

### Fase 0 — Críticos (1–2 h) — *cierra P3.1-P3.7*
1. `main.py:1670` → usar `stop_session` (y eliminar la definición duplicada de `main.py:1660`).
2. `main.py:1710` → reconstruir el comando vía `ScrcpyEngine.build_command`.
3. `main.py:1400/1458` → sustituir `get_device_model` (o implementarlo en `DeviceManager`).
4. `security_service.py:207` → `ErrorCode.UNKNOWN_ERROR`.
5. `main.py:667-668` → materializar el mensaje antes del `lambda`.
6. **`tests/test_core.py`: aislar `HOME`/`CONFIG_FILE`** (hacerlo antes de volver a correr la suite).
7. `--no-video`: añadirlo a la whitelist **o** modelarlo como `SessionConfig.video_enabled`.

### Fase 1 — Altos (medio día) — *cierra P3.8-P3.13*
8. `DeviceCapabilities.model` + propagar `ro.product.model`.
9. Quick Cast: resolución tolerante de nombres o constantes compartidas.
10. `main.py:813` → `if not parsed or not parsed[0]:`.
11. `utils.load_config()` → `deepcopy(DEFAULT_CONFIG)` **y validación de tipos** (o cablear `ProfileService`).
12. Completar las 133 traducciones y deduplicar las 6 claves.

### Fase 2 — Cableado y deuda (1–2 días) — *cierra P3.14-P3.22 y los pendientes 1.1 / 2.3 / 3.2 / 4.1 / 4.2*
13. Cablear `get_error_detail` a la consola con acciones contextuales (cierra **Hallazgo 4.2**).
14. Hacer que `transition_to` valide transiciones y **enrutar la UI por la FSM** (cierra **Hallazgo 4.1**).
15. Migrar `DeviceManager.devices` a `Device`/`SessionState` tipados (cierra **Hallazgo 1.1**).
16. Unificar `security.py` + `security_service.py` en una sola fuente de verdad con bóveda cifrada real (cierra **P3.14**).
17. Llevar toda llamada ADB de la UI a `AdbEngine` (cierra **P3.15** y restaura ADR-006).
18. Menores: cabecera legal en `context.py` (1.2), `SO_REUSEADDR`, `_TrackerThread.stop()`, watchdog de sesión, terminación fuera del hilo de UI.

### Fase 3 — Prevención de regresiones
19. CI: añadir `pyflakes`/`ruff` (habría detectado P3.6) y `--failfast`.
20. **Smoke test de UI** con Tk oculto que construya `ScrcpyDockApp` y ejercite: detener sesión, copiar comando, TrustPrompt y el arranque de **cada** perfil de `DEFAULT_CONFIG` (habría detectado P3.1-P3.3, P3.5 y P3.9).
21. Test de cobertura i18n por AST y test de exhaustividad de `ERROR_CATALOG`.
22. Separar `requirements.txt` (runtime) de `requirements-dev.txt` (`pyinstaller`, `pytest`, `pyflakes`).

---

## Anexo — Comandos de verificación de esta ronda

```bash
cd "/home/myinnervoid/Estudio Memexicanisimos/MASV"

python -m unittest discover -s tests -v     # 269 tests OK (runner del CI)
python -m pyflakes scrcpy_dock build.py run.py tests

grep -rn "SessionState" scrcpy_dock/domain/          # sin resultados  → 1.1 parcial
grep -c  "_set_status(" scrcpy_dock/main.py          # 30  (la UI evade la FSM)
grep -c  "state_machine\.set_" scrcpy_dock/main.py   # 9
grep -rn "get_error_detail" scrcpy_dock/             # sólo import + definición → 4.2 parcial
grep -nE "def (trust_device|untrust_device|kill_adb_server)" scrcpy_dock/security.py
head -3 scrcpy_dock/context.py                       # sin cabecera legal → 1.2 pendiente
```

*Verificación generada por análisis estático + ejecución real sobre el repositorio. Los veredictos «Resuelto / Parcial / Pendiente» se basan en evidencia del código actual, no en lo que declara el changelog.*
