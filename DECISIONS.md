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
34. [ADR-034: Datos desde el Modelo, Nunca desde la Etiqueta del Widget](#adr-034)
35. [ADR-035: Una Pestaña, un Módulo — y el Contenedor se Limpia en un Solo Sitio](#adr-035)
36. [ADR-036: Ensayos de Componentes de UI y Prohibición de Enmascaramiento de `_` en Callbacks](#adr-036)
37. [ADR-037: Las Dependencias Opcionales de UI Degradan, Nunca Rompen la Importación](#adr-037)
38. [ADR-038: El Pipeline se Verifica en las Condiciones del Pipeline](#adr-038)
39. [ADR-039: Ninguna Prueba Puede Escribir en los Datos del Usuario — y Hay un Guardián que lo Comprueba](#adr-039)

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

<a name="adr-034"></a>
### ADR-034: Datos desde el Modelo, Nunca desde la Etiqueta del Widget

- **Contexto del Problema**: la UI mostraba la lista de dispositivos escribiendo **texto formateado** en un `Listbox` y, al seleccionar, **reconstruía el serial parseando ese texto** (`_extract_serial`). El formato de la fila variaba según el estado (`"… ({serial})"` para `ok`, pero `"… (Sin autorizar en pantalla)"` para `unauth` y `"… (Desconectado / Offline)"` para `offline`), así que el parser devolvía el mensaje en lugar del serial. Consecuencia: los avisos de "dispositivo no autorizado"/"offline" eran **código inalcanzable** y `active_device_serial` quedaba con basura (P3.24).
- **Decisión Adoptada**: los handlers de UI **no vuelven a interpretar el texto de un widget para recuperar datos de dominio**. `_update_devs_ui` guarda el registro `self._devices_shown` y `_resolve_selected_device` resuelve la selección **por índice** contra ese registro. El parseo del texto queda como respaldo explícito (`_parse_device_row`) y sólo para filas que no provengan de ese registro.
- **Consecuencias**:
  - *Positivas*: los estados `unauth`/`offline` vuelven a avisar al usuario y a alarmar la FSM; el serial es siempre el correcto; el formato de la etiqueta pasa a ser un detalle puramente estético (se puede cambiar sin romper la lógica).
  - *Negativas*: hay que mantener sincronizados el listbox y su registro (una fila insertada por fuera cae al respaldo por texto).
  - *Verificación*: `tests/test_fase_d_regressions.py::TestOnDevSelectDescompuesto` reconstruye el formato exacto de las cinco filas posibles.
  - *Regla derivada*: cuando un widget presenta datos, su contenido es **sólo presentación**; la fuente de verdad viaja en paralelo (índice, id, dataclass).

---

<a name="adr-035"></a>
### ADR-035: Una Pestaña, un Módulo — y el Contenedor se Limpia en un Solo Sitio

- **Contexto del Problema**: `ui_tabs.py` acumulaba 1.034 líneas con siete constructores de 38 a 344 líneas dentro de una sola clase. Consecuencias medidas: el prólogo del lienzo desplazable estaba copiado en 5 pestañas, la limpieza del contenedor existía en 4 de 7 (lo que producía **P3.25**: apilar un árbol de widgets completo en cada cambio de tema), había una importación perezosa escondida en `build_tab_profile` y no había forma de revisar ni probar una pestaña sin cargar todo el archivo.
- **Decisión Adoptada**: cada pestaña vive en su propio módulo de `scrcpy_dock/ui/tabs/` y expone `build(parent, tab)`, donde `tab` es un `TabContext(ctx, cb, refs, faq_items)`. Las piezas compartidas (`clear`, `scrollable`, el propio `TabContext`) viven en `common.py`. `UIBuilder` **permanece en `ui_tabs.py` como fachada** de 62 líneas que delega, conservando la firma `(app_context, callbacks)` y los atributos `refs`/`_faq_items` que `main.py` y el arnés D1 consultan.
- **Consecuencias**:
  - *Positivas*: una pestaña se lee, se revisa y se prueba sola; la cobertura de la capa subió al **99 %** (5 de 7 módulos al 100 %); la duplicación se **redujo a la mitad** (2,9 % → 1,4 %); la limpieza del contenedor tiene un único sitio, así que P3.25 no puede reaparecer por descuido; la importación perezosa desapareció.
  - *Negativas*: un nivel más de importaciones y un objeto de contexto que hay que pasar; quien añada una pestaña debe recordar llamar a `clear(parent)` (hay una guardia que lo comprueba sobre el código).
  - *Invariante de compatibilidad*: `refs` y `faq_items` se comparten **por identidad**, nunca por copia. La FAQ usa `.clear()` en vez de reasignar para no romperla.
  - *Verificación*: `tests/test_fase_c2_regressions.py` (12 pruebas, incluidas las de P3.25) sobre el arnés compartido `tests/ui_harness.py`.
<a name="adr-036"></a>
### ADR-036: Ensayos de Componentes de UI y Prohibición de Enmascaramiento de `_` en Callbacks

- **Contexto del Problema**: `ui_widgets.py` acumulaba 1.201 líneas con una cobertura del 49 % (por debajo del umbral del 60 % de la Ley 7). Al someterlo a pruebas unitarias rigurosas, se descubrieron dos defectos latentes que causaban caídas de ejecución en producción:
  1. `PillNavBar` asignaba lambdas `self.select(tid, i)` a sus botones pero **no implementaba el método `select()`** (`AttributeError: 'PillNavBar' object has no attribute 'select'`).
  2. `_cmd_chip` definía `def copy(_=None):`, usando el identificador `_` para el argumento `event` de Tkinter. Al hacer clic en `📋 Copiar`, `_` pasaba a ser la instancia de `Event`, enmascarando la función global de internacionalización `_()` de `i18n.py` y provocando `TypeError: 'Event' object is not callable`.
- **Decisión Adoptada**:
  - Implementar arnés unitario exhaustivo para todos los componentes de `ui_widgets.py` (`tests/test_ui_widgets_coverage.py`).
  - Prohibir formalmente el uso de `_` como nombre de parámetro en handlers y callbacks de interfaz donde se invoque traducción de texto; usar siempre nombres explícitos como `event=None`.
  - Integrar linter estricto `pyflakes` en el pipeline de GitHub Actions (`.github/workflows/build.yml`) y declarar dependencias en `requirements-dev.txt`.
- **Consecuencias**:
  - *Positivas*: la cobertura de `ui_widgets.py` saltó del 49 % al **94 %** (medido con display; ver §11.9), dejando la Ley 7 de interfaz en **✅ VERDE**; los 558 tests pasan en verde; el copiado en chips y la selección de pastillas funcionan sin excepciones.
  - *Negativas*: los tests de UI requieren simulación y control de mapeo de ventanas en modo headless (Tkinter `update` y neutralización de modales bloqueantes).
  - *Verificación*: `tests/test_ui_widgets_coverage.py` (14 pruebas unitarias) ejecutadas en CI y en local.

---

<a name="adr-037"></a>
### ADR-037: Las Dependencias Opcionales de UI Degradan, Nunca Rompen la Importación

- **Contexto del Problema**: `main.py` envolvía `import pystray` en `except ImportError`. Sin pantalla (CI headless, servidor, sesión sin X) esa importación no falla con `ImportError` sino con `Xlib.error.DisplayNameError`, que se escapaba: **`import scrcpy_dock.main` no funcionaba sin display**. Efecto medido en un runner headless: 3 módulos de pruebas ni se importaban (`_FailedTest`) y 15 pruebas más morían dentro de su propio código — pruebas que no usan Tk y que deberían haber pasado.
- **Decisión Adoptada**: toda dependencia de UI que sea **opcional** (bandeja del sistema, y por extensión cualquier cosa que necesite servidor gráfico) se importa dentro de una guarda que atrapa **cualquier** fallo y degrada a una bandera documentada (`TRAY_AVAILABLE = False`). El resto del módulo debe importarse y funcionar sin ella.
- **Consecuencias**:
  - *Positivas*: la app y toda la suite son importables sin pantalla; en headless las pruebas de UI **se saltan** con elegancia en vez de reventar; el daemon y el núcleo no dependen del entorno gráfico.
  - *Negativas*: `except Exception` también silencia una instalación rota de `pystray`/PIL. Se acepta porque la bandeja es cosmética y su ausencia se degrada sola (la opción simplemente no se ofrece), y porque exigir display para *importar* es un coste mucho mayor.
  - *Regla derivada*: nada que se necesite para importar el paquete puede depender del servidor gráfico.
  - *Verificación*: `ANALISIS.md` §11.9 · headless pasa de `errors=18, skipped=18` a **0 errores**.

---

<a name="adr-038"></a>
### ADR-038: El Pipeline se Verifica en las Condiciones del Pipeline

- **Contexto del Problema**: la Fase D añadió un paso de linter al CI y declaró la suite verde. Ninguna de las dos cosas se sostuvo al comprobarlas en las condiciones del runner: (1) el paso de linter devolvía **exit 1 con 55 hallazgos** — un `run:` falla el job con código distinto de cero, así que el pipeline se ponía rojo en el primer push, en los tres sistemas; (2) los runners son headless y el flujo no preparaba pantalla: además de P3.30, **43 pruebas de UI se habrían saltado en silencio**, dejando un CI verde que nunca ejercitaba la interfaz; (3) la cobertura declarada (82 %) no se reproduce con la suite completa y display (85 %), ni sin él (49 %) — la cifra medía otra cosa.
- **Decisión Adoptada**: (a) un paso de linter sólo está "integrado" cuando **el comando exacto del workflow devuelve 0 sobre el árbol real** — si hay hallazgos, se limpian o no se añade el paso (no se tolera con `|| true`); (b) la suite debe quedar **verde en un runner headless**: las pruebas de UI se saltan con elegancia cuando no hay display, y en Linux el CI corre bajo `xvfb-run -a` para que **se ejecuten de verdad** (el salto es red de seguridad, no objetivo); (c) toda cifra de cobertura se declara **con sus condiciones** (con o sin display), porque la misma suite mide 85 % o 49 % según haya pantalla.
- **Consecuencias**:
  - *Positivas*: el CI ejecuta las 43 pruebas de UI en lugar de saltarlas; el linter es estricto y a la vez verde; las métricas de la Ley 7 son reproducibles por cualquiera.
  - *Negativas*: una dependencia más en el CI (`xvfb`) y dos pasos de pruebas condicionados por sistema operativo; hay que mantener el árbol limpio de hallazgos para no volver a romper el job.
  - *Verificación*: `pyflakes scrcpy_dock/ tests/` → exit 0; headless `558 ejecutadas, OK (43 skips), 0 errores`; con display `558 OK`; YAML validado con `yaml.safe_load`.

---

<a name="adr-039"></a>
### ADR-039: Ninguna Prueba Puede Escribir en los Datos del Usuario — y Hay un Guardián que lo Comprueba

- **Contexto del Problema**: `tests/test_ui_widgets_coverage.py` construía `TrustPromptModal` con un `cfg` de prueba parcial y sin redirigir las rutas; el modal persistía ese `cfg` por su cuenta (`from .utils import save_config` dentro del handler). Resultado: **cada ejecución de la suite reescribía `~/.config/masv/config.json`** con `{"trusted_devices": {}}` y se perdieron los perfiles personalizados del usuario (Ley 10: pérdida de datos). Dos detalles agravaron la invisibilidad: la docstring del archivo de pruebas **afirmaba** que redirigía las configuraciones a temporales, y el mismo error ya había aparecido en la auditoría original (`test_core.py`, hallazgo A1) donde se corrigió sólo ese archivo, sin una regla general.
- **Decisión Adoptada**: (a) toda prueba que pueda provocar un guardado **redirige** `CONFIG_FILE`, `CONFIG_DIR` y `LOG_FILE` a un temporal (`tests/ui_harness.aislar_config`), y las que además ejercitan el guardado anulan `save_config` con un registrador en memoria; (b) **ningún widget escribe en disco por su cuenta**: recibe un `save_cb` y lo invoca, igual que `DeviceTrustModal`/`TrustVaultDialog` — `TrustPromptModal` se alineó con ellos; (c) la invariante no se documenta, **se comprueba**: `tests/test_suite_sin_efectos.py` falla si un módulo de pruebas puede guardar y no aísla (regla estática) y si ejecutar las pruebas de widgets en un subproceso cambia un solo byte del archivo real (sha256 antes/después).
- **Consecuencias**:
  - *Positivas*: la suite es segura de correr en cualquier máquina, incluida la del usuario y el CI; el aislamiento vive en un único sitio; el guardián convierte "confío en haberlo revisado" en una comprobación automática que además es de extremo a extremo.
  - *Negativas*: el guardián ejecuta un subproceso con las pruebas de widgets (~1,5 s) y añade una regla estática que hay que respetar al crear módulos nuevos.
  - *Regla derivada*: una afirmación de aislamiento en una docstring no es aislamiento. Si una propiedad importa tanto como para escribirla en un comentario, hay que escribir la prueba que la verifique.
  - *Verificación*: sha256 de `~/.config/masv/config.json` idéntico antes y después de la suite completa (561 pruebas); el guardián falla si se le quita el aislamiento a un módulo.

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
| **Registro paralelo al widget (`_devices_shown`) en vez de parsear la etiqueta** | El serial es siempre correcto y el formato de la fila se vuelve estético; recupera avisos que eran inalcanzables. | Hay que mantener el listbox y su registro sincronizados. | `_extract_serial()` sobre el texto de la fila. | P3.24: el paréntesis no siempre lleva el serial, así que el parser leía el mensaje de estado. |
| **Descomponer en validadores puros (uno por campo) en lugar de un `if` gigante** | Un campo, una regla: añadir un campo no obliga a releer toda la sanitización y cada regla se prueba aislada. | Más métodos (8 en vez de ~40 líneas de `if`). El parseo del dict ya no se lee de un tirón. | Mantener la función monolítica y bajar su CC con `# noqa`/helpers anidados. | Es el patrón que dejó `sanitize_profile_dict` en CC 28 sin una sola prueba por campo. |
| **Un módulo por pestaña + fachada estable, en vez del archivo único** | Cada pestaña se prueba y se revisa sola; la cobertura de la capa sube al 99 % y P3.25 se vuelve imposible por construcción. | Un nivel más de importaciones; un objeto de contexto que atravesar. | Dejar `ui_tabs.py` con 1.034 líneas y siete constructores. | Con el archivo único, 3 de 7 pestañas se construían sin limpiar el contenedor y nadie podía verlo sin abrir el archivo entero. |
| **Extracción mecánica verificada línea a línea, en vez de retranscribir el código** | Cero riesgo de perder o inventar una línea en una partición de 1.000 líneas; la verificación queda como prueba objetiva. | Un script de extracción y otro de verificación que hay que mantener mientras dura la tarea. | Mover el código a mano, releyendo. | Una transposición manual de 1.000 líneas no tiene forma de demostrar que está completa. |
| **Degradar las dependencias opcionales de UI en vez de exigir display para importar** | La app y la suite son importables sin pantalla; en headless las pruebas de UI se saltan en vez de reventar. | `except Exception` silencia también una instalación rota de `pystray`/PIL. | Mantener `except ImportError` y exigir servidor gráfico. | Sin display el módulo principal no se importaba: 18 errores en un runner headless, incluso en pruebas que no usan Tk. |
| **`xvfb-run` en el CI en vez de aceptar los saltos de las pruebas de UI** | Las 43 pruebas de interfaz se ejecutan de verdad en Linux; el CI no puede estar verde por omisión. | Una dependencia más (`xvfb`) y dos pasos de pruebas condicionados por SO. | Dejar que las pruebas de UI se salten en CI. | El pipeline habría estado verde sin haber ejercitado nunca la interfaz — cobertura aparente, no real. |
| **Aislar y verificar (con guardián) que la suite no toca datos del usuario, en vez de confiar en la revisión** | La suite es segura en cualquier máquina; la pérdida de configuración se detecta automáticamente. | Un subproceso extra en la suite (~1,5 s) y una regla estática que respetar. | Documentar el aislamiento en la docstring del archivo de pruebas. | Es exactamente lo que falló: la docstring afirmaba el aislamiento y el archivo no lo hacía; se perdieron los perfiles del usuario. |
| **Los widgets reciben `save_cb` en vez de guardar por su cuenta** | Un componente de interfaz no puede destruir la configuración del usuario, ni siquiera si le pasan un objeto incompleto. | Un parámetro más que propagar desde `main.py`. | Que el widget importe `save_config` y persista el `cfg` que le den. | Con un `cfg` parcial escribía una configuración incompleta sobre la real (P3.32). |
| **Sanitización de `extra_args` con lista de rechazo** | Prevención de ataques de inyección de comandos en perfiles compartidos. | Rechazo de scripts compuestos dentro del campo de argumentos. | Ejecutar mediante shell directo con permisos elevados. | Riesgo crítico de seguridad según la Ley Global 3. |
| **Almacenamiento JSON plano con guardado atómico (`fsync` + `os.replace`)** | Cero dependencias de base de datos externa, portabilidad absoluta. | No apto para consultas relacionales masivas concurrentes. | SQLite / PostgreSQL embebido. | Sobrecomplejidad innecesaria para un gestor de configuración local de escritorio. |
