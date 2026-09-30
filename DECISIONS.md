# 🏛️ REGISTRO DE DECISIONES DE ARQUITECTURA (DECISIONS.md)
**MASV — Memexicanisimos Android Screen Viewer**
*Motor de Auditoría y Evolución de Software Existente — v3.1*

---

## 📑 Índice de Decisiones (ADR)

1. [ADR-001: Estandarización de Transporte/IPC con `OperationResult[T]`](#adr-001)
2. [ADR-002: Catálogo Formal de Códigos de Error (`ErrorCode` Enum)](#adr-002)
3. [ADR-003: Autómata Finito de Interfaz (`UIStateMachine`)](#adr-003)
4. [ADR-004: Sanitización Estricta de Argumentos de scrcpy](#adr-004)
5. [ADR-005: Bóveda de Confianza Local con Permisos Restringidos](#adr-005)

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
### ADR-005: Bóveda de Confianza Local con Permisos Restringidos

- **Contexto del Problema**: El uso de ADB por Wi-Fi / TCP/IP en redes compartidas expone el teléfono a conexiones no autorizadas de terceros.
- **Decisión Adoptada**: Mantener la Bóveda de Dispositivos Confiables en `~/.config/masv/config.json` con permisos de sistema de archivos `0o600` (sólo lectura/escritura por el usuario propietario) y `0o700` para el directorio de configuración en sistemas POSIX.
- **Consecuencias**:
  - *Positivas*: Protección de privacidad sin necesidad de almacenar credenciales en la nube ni servicios externos.
  - *Negativas*: Las configuraciones no se sincronizan automáticamente entre múltiples computadoras sin transferir el archivo manualmente.

---

## ⚖️ Matriz de Trade-offs de Decisiones Técnicas

| Decisión Técnica | Beneficio Directo | Costo / Penalización | Alternativa Descartada | Razón del Rechazo |
| :--- | :--- | :--- | :--- | :--- |
| **`OperationResult[T]` con desempaquetado de tupla** | Contratos tipados estándar (`ApiResponse<T>`) manteniendo compatibilidad total con código legacy. | Pequeño boilerplate de definición de clases en `contracts.py`. | Lanzar excepciones personalizadas en cada fallo. | Las excepciones rompen el flujo asíncrono y complican la presentación en Tkinter. |
| **`ErrorCode` Enum con catálogo de remediación** | Clasificación formal de fallos y soporte bilingüe de remediación asistida. | Mantenimiento de la tabla de mapeo de errores. | Mensajes de error en texto plano generados ad-hoc. | Genera inconsistencias y no permite internacionalización fiable. |
| **Autómata de 5 Estados (`UIStateMachine`)** | Consistencia visual absoluta (`IDLE`, `PENDING`, `SUCCESS`, `EMPTY`, `FAULT`). | Despacho de transiciones en hilos secundarios mediante callbacks. | Modificar `_status_lbl` directamente en cada función. | Alta propensión a estados huérfanos o desincronizados. |
| **Sanitización de `extra_args` con lista de rechazo** | Prevención de ataques de inyección de comandos en perfiles compartidos. | Rechazo de scripts compuestos dentro del campo de argumentos. | Ejecutar mediante shell directo con permisos elevados. | Riesgo crítico de seguridad según la Ley Global 3. |
| **Almacenamiento JSON plano con guardado atómico (`fsync` + `os.replace`)** | Cero dependencias de base de datos externa, portabilidad absoluta. | No apto para consultas relacionales masivas concurrentes. | SQLite / PostgreSQL embebido. | Sobrecomplejidad innecesaria para un gestor de configuración local de escritorio. |
