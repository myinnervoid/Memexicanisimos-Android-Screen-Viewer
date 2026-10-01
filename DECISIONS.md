# 🏛️ REGISTRO DE DECISIONES DE ARQUITECTURA (DECISIONS.md)
**MASV — Memexicanisimos Android Screen Viewer**
*Motor de Auditoría y Evolución de Software Existente — v3.1*

---

## 📑 Índice de Decisiones (ADR)

1. [ADR-001: Estandarización de Transporte/IPC con `OperationResult[T]`](#adr-001)
2. [ADR-002: Catálogo Formal de Códigos de Error (`ErrorCode` Enum)](#adr-002)
3. [ADR-003: Autómata Finito de Interfaz (`UIStateMachine`)](#adr-003)
4. [ADR-004: Sanitización Estricta de Argumentos de scrcpy](#adr-004)
5. [ADR-005: Bóveda de Confianza Local Cifrada con Permisos Restringidos](#adr-005)
32. [ADR-032: Motor ADB Único y Canal Exclusivo para la UI](#adr-032)
33. [ADR-033: Extracción de `StreamService` con Proveedores (no valores)](#adr-033)

> ⚠️ **Hueco de trazabilidad detectado (2026-10-01):** el código cita **ADR-001 a ADR-031**
> (`ADR-006/007/008/009` en `adb_engine`, `ADR-029` en `port_allocator`, `ADR-031` en
> `domain/models`, `ADR-010…014`, `ADR-018…020`…), pero este documento sólo recoge los ADR
> 001–005 y `docs/adr/` contiene únicamente el maestro hexagonal: **hay ~26 decisiones
> citadas en el código y no registradas en ninguna parte**. Además los números 003/004 se
> usan aquí (FSM, sanitización) sin ser citados en el código. Una auditoría futura debe
> reconstruir esos ADR desde los commit o renumerar las series (§11.3, hallazgo pendiente).

---

<a name="adr-001"></a>
### ADR-001: Estandarización de Transporte/IPC con `OperationResult[T]`

- **Contexto del Problema**: En versiones previas, los métodos de control de red, procesos y perfiles devolvían firmas heterogéneas (`Tuple[bool, str]`, `bool`, `None`, o lanzaban excepciones silenciosas), dificultando la propagación estructurada de errores hacia la interfaz gráfica y los registros de auditoría.
- **Decisión Adoptada**: Implementar el contrato canónico `OperationResult[Generic[T]]` con campos `{ success: bool, data: Optional[T], error_code: Optional[ErrorCode], message: str }`. Se incorporó compatibilidad de desempaquetado de tupla (`__iter__`) para permitir compatibilidad total hacia atrás con llamadas existentes (`ok, msg = ...`).
- **Consecuencias**:
  - *Positivas*: Tipado formal, contratos predecibles entre capas, trazabilidad de fallos sin depender de cadenas mágicas.
  - *Negativas*: Ligero sobrecosto de instanciación de objetos de resultado (despreciable en entornos de escritorio).

---

<a name="adr-002"></a>
### ADR-002: Catálogo Formal de Códigos de Error (`ErrorCode` Enum)

- **Contexto del Problema**: Los fallos de ejecución en `adb`, `scrcpy`, permisos y red se describían mediante cadenas de texto en lenguaje natural dispersas en el código, impidiendo el mapeo semántico localizado y la sugerencia de acciones de remediación guiada para el usuario.
- **Decisión Adoptada**: Crear el módulo `errors.py` con `ErrorCode` Enum estructurado por categorías (Dependencias, Dispositivos, Red, Seguridad, Sesión, Configuración) y un diccionario de detalles bilingües (`ErrorDetail`) con título, descripción y pasos de remediación.
- **Consecuencias**:
  - *Positivas*: Mapeo 1:1 entre errores del sistema y mensajes de UI, internacionalización limpia y capacidad de auto-recuperación guiada.
  - *Negativas*: Requiere mantener actualizado el catálogo ante nuevos códigos de salida de herramientas externas.

---

<a name="adr-003"></a>
### ADR-003: Autómata Finito de Interfaz (`UIStateMachine`)

- **Contexto del Problema**: El estado visual de la aplicación (etiquetas de estado, botones de acción, diálogos de carga) se modificaba de manera fragmentada en múltiples controladores sin una máquina de estados centralizada, lo que podía causar inconsistencias de estado si un proceso se cerraba abruptamente.
- **Decisión Adoptada**: Implementar `UIStateMachine` en `state.py` gestionando los 5 estados canónicos:
  - `[IDLE]`: Sin transmisión activa, interfaz lista para operar.
  - `[PENDING]`: Operación en curso (escaneo ADB, emparejamiento Wi-Fi, arranque scrcpy).
  - `[SUCCESS]`: Transmisión en vivo activa y estable.
  - `[EMPTY]`: Lista de dispositivos vacía.
  - `[FAULT]`: Error crítico o dependencias ausentes.
- **Consecuencias**:
  - *Positivas*: Transiciones de estado deterministas, interfaz reactiva mediante el patrón Observer, feedback visual inmediato al usuario.
  - *Negativas*: Requiere despachar transiciones explícitas en todos los flujos asíncronos.

- **Revisión (01-oct-2026, Fase B — B1/B2)**: el autómata pasa a **validar** las transiciones contra el grafo `_ALLOWED`: una transición no declarada se rechaza devolviendo `False` **sin mutar el estado ni notificar** a los suscriptores (auto-transiciones y la recuperación desde `FAULT` siempre permitidas). Además la UI queda efectivamente **enrutada**: `_set_status()` es el único renderizador de la barra de estado (3 llamadas, antes 30) y se añade `_hint()` como canal explícito para mensajes informativos que **no** son estado operativo (vista, selección, perfil). Gobernar la UI sin negar la existencia de textos no operativos es la corrección que cierra la Ley 6.

---

<a name="adr-004"></a>
### ADR-004: Sanitización Estricta de Argumentos de scrcpy

- **Contexto del Problema**: El campo `extra_args` de los perfiles permitía inyectar texto libre directamente a `shlex.split()`, lo que representaba un riesgo si un perfil importado o modificado contenía operadores de concatenación de comandos de shell (`&&`, `;`, `|`, `$(...)`, etc.).
- **Decisión Adoptada**: Incorporar el validador `SecurityManager.validate_extra_arguments()` que analiza y rechaza cualquier patrón de concatenación o redirección antes de pasar los argumentos al proceso secundario.
- **Consecuencias**:
  - *Positivas*: Blindaje contra inyecciones de comandos accidentales o maliciosas.
  - *Negativas*: Restringe el uso de tuberías complejas dentro de `extra_args` (las cuales de cualquier modo no corresponden a banderas de scrcpy).

---

<a name="adr-005"></a>
### ADR-005: Bóveda de Confianza Local Cifrada con Permisos Restringidos

- **Contexto del Problema**: El uso de ADB por Wi-Fi / TCP/IP en redes compartidas expone el teléfono a conexiones no autorizadas de terceros.
- **Decisión Adoptada**: Mantener la Bóveda de Dispositivos Confiables en almacenamiento local con permisos de sistema de archivos `0o600` (sólo lectura/escritura por el usuario propietario) y `0o700` para el directorio de configuración en sistemas POSIX.
- **Consecuencias**:
  - *Positivas*: Protección de privacidad sin necesidad de almacenar credenciales en la nube ni servicios externos.
  - *Negativas*: Las configuraciones no se sincronizan automáticamente entre múltiples computadoras sin transferir el archivo manualmente.

- **Revisión (01-oct-2026, Fase B — B5)**: la bóveda deja de residir en **texto plano** dentro de `config.json` (lo que contradecía el nombre de "bóveda" y dejaba los seriales autorizados legibles) y pasa a `vault.enc`, cifrado con **Fernet + derivación PBKDF2-HMAC-SHA256 (480 000 iteraciones) y sal local `0o600`** de 32 bytes.
  - **Una sola implementación criptográfica**: `services/security_service.py` es la única fuente de verdad; `security.py` deja de duplicar el esquema y actúa como **fachada** para la UI. La causa raíz de la divergencia era que `is_whitelisted_device()` sólo aceptaba `trusted_devices` como *lista* mientras la fachada persistía un *dict*: ahora acepta ambas formas.
  - **Migración sin pérdida**: al abrir la app, si existe texto plano se escribe `vault.enc`, se **relee y descifra para verificar** que coincide, y **sólo entonces** se retira la copia en claro (dejando `config.json.pre-vault.bak`). Si el vault no se puede descifrar (sal rotada, fichero corrupto), **se conserva la copia en claro** y se registra un aviso: la bóveda nunca se pierde silenciosamente.
  - *Negativas*: la clave depende del `machine-id` del host; copiar `vault.enc` a otra máquina no funciona sin la sal. La ubicación definitiva (`~/.config/masv/` frente a `~/.MASV/config/`) queda pendiente de decisión.


---

<a name="adr-032"></a>
### ADR-032: Motor ADB Único y Canal Exclusivo para la UI

- **Contexto del Problema**: `DeviceManager()` y `SessionManager()` construían **cada uno su propio `AdbEngine`** (con `_effective_port` y `_activated_by_masv` independientes), y la UI, además, lanzaba `adb` directamente por `subprocess` en 17 puntos —incluido `adb kill-server`, que sin `ADB_SERVER_SOCKET` tumba el daemon **compartido** del usuario (Android Studio, VS Code)—.
- **Decisión Adoptada**:
  1. `AppContext` crea **una sola** instancia de `AdbEngine` y la inyecta en `DeviceManager` y `SessionManager`; se expone como `ctx.adb_engine` y la UI la consume a través de `ScrcpyDockApp._adb()`.
  2. Se añaden al motor las primitivas genéricas que la UI necesitaba (`shell`, `install`, `connect`, `kill_server`, `rebind`), todas con el socket aislado y `OperationResult`.
  3. `kill_server()` invalida `_daemon_started`/`_effective_port` para que el siguiente `start_daemon()` renegocie el puerto.
- **Consecuencias**:
  - *Positivas*: un único estado de daemon y de tcpip (`revert_tcpip` deja de ser no-op silencioso); el texto de `input text` viaja como token de argv sin quoting manual; matar el daemon ya no afecta a otras herramientas del usuario.
  - *Negativas*: `SecurityManager.pair_device`/`lockdown_*` **siguen** recibiendo la ruta del binario y lanzando `adb` por su cuenta (deuda declarada, pendiente de migrar al motor).
  - *Verificación*: `tests/test_fase_c_regressions.py::TestC3*`.

---

<a name="adr-033"></a>
### ADR-033: Extracción de `StreamService` con Proveedores (no valores)

- **Contexto del Problema**: `SessionManager.start_scene_legacy` (CC **45**) mezclaba tres responsabilidades: interpretar la forma *legacy* de un perfil (dicts con strings sueltos), construir los contratos de dominio (`Device`, `SessionConfig`, `DeviceCapabilities`) y orquestar el lanzamiento con el pool de puertos.
- **Decisión Adoptada**: extraer `services/stream_service.py` con la compilación del perfil (`_compile_profile` + `_absorb_token`) y el lanzamiento (`start_legacy`), dejando `SessionManager.start_scene_legacy` como fachada de una línea. El servicio recibe **proveedores** (`scrcpy_provider`, `allocator_provider`, `log_q_provider`), no objetos, y comparte por referencia el dict de sesiones y el pool de puertos.
- **Consecuencias**:
  - *Positivas*: CC 45 → **1** en el método y ningún bloque nuevo > 10; la promoción de banderas a atributos nativos (`--video-source`, `--camera-id`, `--camera-facing`, `--otg`, `--no-video`) queda en un solo sitio y es testeable por unidad.
  - *Negativas*: una indirección más al leer el arranque de una sesión.
  - *Riesgo evitado*: capturar el motor por **valor** rompía en silencio a todo consumidor que sustituya `mgr._scrcpy` tras construir el manager (lo hacen los tests y la app al re-detectar binarios). Es el motivo explícito de usar proveedores; queda cubierto por `TestC1StreamService::test_usa_el_motor_sustituido_despues_de_construir`.
  - *Deuda*: la bandera promovida **huérfana** (sin valor) se conserva como token y la juzga el motor; no se validó con un caso real de perfil malformado.

---

## ⚖️ Matriz de Trade-offs de Decisiones Técnicas

| Decisión Técnica | Beneficio Directo | Costo / Penalización | Alternativa Descartada | Razón del Rechazo |
| :--- | :--- | :--- | :--- | :--- |
| **`OperationResult[T]` con desempaquetado de tupla** | Contratos tipados estándar (`ApiResponse<T>`) manteniendo compatibilidad total con código legacy. | Pequeño boilerplate de definición de clases en `contracts.py`. | Lanzar excepciones personalizadas en cada fallo. | Las excepciones rompen el flujo asíncrono y complican la presentación en Tkinter. |
| **`ErrorCode` Enum con catálogo de remediación** | Clasificación formal de fallos y soporte bilingüe de remediación asistida. | Mantenimiento de la tabla de mapeo de errores. | Mensajes de error en texto plano generados ad-hoc. | Genera inconsistencias y no permite internacionalización fiable. |
| **Autómata de 5 Estados (`UIStateMachine`)** | Consistencia visual absoluta (`IDLE`, `PENDING`, `SUCCESS`, `EMPTY`, `FAULT`). | Despacho de transiciones en hilos secundarios mediante callbacks. | Modificar `_status_lbl` directamente en cada función. | Alta propensión a estados huérfanos o desincronizados. |
| **Validación de transiciones por grafo `_ALLOWED` (rechazo silencioso)** | Hace imposible "llegar a SUCCESS sin pasar por PENDING" o quedar con estados huérfanos; el rechazo no muta estado ni notifica, así que no corrompe la UI. | Coste de declarar el grafo y de mantenerlo cuando se añada un estado. | Aceptar cualquier transición (`return True`) y confiar en el llamador. | Es exactamente el defecto P3.19 que dejaba la Ley 6 sin cumplir. |
| **Canal `_hint()` separado del estado operativo** | Permite gobernar la UI por la FSM sin perder los mensajes informativos (selección, vista, perfil); evita el falso dilema "todo o nada". | Dos canales de texto que hay que distinguir al escribir código nuevo. | Meter todo en la FSM (contamina el autómata con eventos que no son estados) o dejar `_set_status` suelto (rompe la Ley 6). | La FSM modela estado, no notificaciones; forzarla degradaba el modelo. |
| **Bóveda cifrada con migración verificada (ida y vuelta antes de borrar el claro)** | Cierra el hallazgo crítico P3.14 sin riesgo de pérdida de datos: si el vault no se relee, no se retira nada. | Una escritura y una lectura extra en la primera migración; dependencia del `machine-id` para descifrar en otro host. | Cifrar y sobrescribir directamente (más simple). | Un error de derivación destruiría la bóveda del usuario sin remedio — inaceptable bajo la Ley 10 (pérdida de datos = Crítico). |
| **Motor ADB único inyectado (en lugar de uno por manager)** | Un solo socket negociado y un solo registro de tcpip: `revert_tcpip` deja de ser no-op y se cierra el puerto 5555 de verdad. | `AppContext` debe construir el motor antes que los managers y propagarlo. | Dejar que cada manager cree su propio `AdbEngine` (estado inicial). | Es el defecto que causaba fuga del modo TCP/IP y duplicaba la negociación de socket. |
| **Proveedores (callables) en vez de valores al extraer un servicio** | La extracción no rompe la sustitución tardía (`mgr._scrcpy = fake`), que usan tests y la re-detección de binarios. | Un nivel de indirección al leer `self._get_scrcpy()`. | Pasar el objeto y confiar en que nadie lo sustituya. | Ya rompió 3 pruebas al ejecutar C1: la sustitución es legítima y frecuente. |
| **Sanitización de `extra_args` con lista de rechazo** | Prevención de ataques de inyección de comandos en perfiles compartidos. | Rechazo de scripts compuestos dentro del campo de argumentos. | Ejecutar mediante shell directo con permisos elevados. | Riesgo crítico de seguridad según la Ley Global 3. |
| **Almacenamiento JSON plano con guardado atómico (`fsync` + `os.replace`)** | Cero dependencias de base de datos externa, portabilidad absoluta. | No apto para consultas relacionales masivas concurrentes. | SQLite / PostgreSQL embebido. | Sobrecomplejidad innecesaria para un gestor de configuración local de escritorio. |
