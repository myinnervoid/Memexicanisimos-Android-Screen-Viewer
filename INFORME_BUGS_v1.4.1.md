# 🐞 Informe de Análisis de Bugs, Errores y Mejoras — MASV v1.4.1

**Proyecto:** MASV — Memexicanisimos Android Screen Viewer
**Ruta auditada:** `/home/myinnervoid/Estudio Memexicanisimos/MASV/`
**Rama / commit de partida:** `main` @ `795f6e4` (v1.4.1, ahead 5 de origin/main, árbol limpio)
**Fecha del análisis:** 2026-10-01
**Alcance:** revisión estática de `scrcpy_dock/` (12.364 LOC Python), suite de pruebas (`tests/`), empaquetado (`build.py`, `.github/workflows/build.yml`, `install.sh`/`uninstall.sh`) y documentación v1.4/1.4.1.

---

## 1. Resumen ejecutivo

La suite de pruebas declarada pasa íntegra (**269/269 OK**, también con el runner que usa el CI, `python -m unittest discover -s tests`). Sin embargo, la cobertura está sesgada hacia el **dominio/core y los contratos** y **no toca la capa de UI/handlers de `main.py`**, que es justamente donde se concentran los defectos graves.

Resultado de este análisis:

| Severidad | N.º | Descripción corta |
| :--- | :---: | :--- |
| 🔴 Crítico | 7 | `AttributeError`/`NameError` en handlers de UI invocables + pérdida de datos reales por la suite de tests |
| 🟠 Alto | 6 | Lógica de negocio incorrecta (modelo de dispositivo, perfiles por defecto inarrancables, i18n incompleta, aliasing de config) |
| 🟡 Medio | 12 | Deuda arquitectónica, código muerto, artefactos basura versionados, divergencia de versiones |
| 🔵 Menor / estilo | 8 | Imports sin usar, `print()` de depuración, redundancias, mensajes de log mal etiquetados |

**Los 4 hallazgos más urgentes** (rompen funcionalidad anunciada en v1.4 y sólo se detectan con pruebas manuales de UI):

1. **Detener sesión (tecla Supr / clic derecho / botón) lanza `AttributeError`** — `SessionManager.stop()` no existe.
2. **"Copiar comando scrcpy" lanza `AttributeError`** — `SessionManager._build_cmd()` no existe.
3. **Modo Seguro + dispositivo no confiable lanza `AttributeError`** — `DeviceManager.get_device_model()` no existe (bloquea el *TrustPrompt*, el flujo estrella de v1.4).
4. **El modo "Solo Audio / `--no-video`" nunca arranca** — la bandera es rechazada por la whitelist de seguridad del propio motor (`INVALID_EXTRA_ARGS`), y está presente en el perfil por defecto `🎙️ Stream OBS (Huawei)` y en un preset del asistente.

Adicionalmente: **al ejecutar la suite se sobrescribe la configuración real del usuario** (`~/.config/masv/config.json`). Ver §3.7 — este análisis lo reprodujo y el `config.json` de esta máquina quedó reducido a `{"test_key": "test_value_123"}`. Si contenían perfiles o bóveda de confianza, se perdieron.

---

## 2. Metodología y evidencia

Herramientas usadas (todas ejecutadas realmente sobre el repo):

```bash
python -m pytest -q                 # 269 passed
python -m unittest discover -s tests -v   # 269 tests OK (runner del CI)
python -m pyflakes scrcpy_dock build.py run.py tests
```

Además se ejecutaron *probes* propios para verificar cada hallazgo (no se deduce nada “a ojo”):

* Comparación automática de todos los `ErrorCode.<X>` usados vs. definidos → 1 símbolo inexistente.
* Comparación de todos los `self.ctx.<manager>.<método>()` de `main.py` contra las clases reales → 3 métodos inexistentes.
* Construcción real de un `SessionConfig` con `extra_args=("--no-video",)` → `INVALID_EXTRA_ARGS` confirmado.
* Simulación del patrón `except … as e: lambda: …{e}` → `NameError` confirmado.
* Mutación de una copia de `DEFAULT_CONFIG` → contaminación del dict global confirmado.
* Extracción de los 133 literales pasados a `_()` sin traducción EN.
* `git ls-files` para distinguir artefactos versionados de generados.

---

## 3. Hallazgos detallados

### 3.1 🔴 `SessionManager.stop()` no existe — Detener sesión falla con `AttributeError`

* **Ubicación:** `scrcpy_dock/main.py:1660` (método efectivo) → `scrcpy_dock/main.py:1670`
* **Causa:** `_stop_selected` está **definido dos veces**. La primera definición (`main.py:1527`) usa `session_mgr.stop_session(serial)` y es correcta, pero queda **sombre la última definición** (`main.py:1660`), que llama a un método inexistente:

```python
self.ctx.session_mgr.stop(serial)   # SessionManager NO tiene stop()
```

`SessionManager` sólo expone `stop_session`, `stop_scene`, `stop_all` (verificado con `hasattr` → `False`).
* **Impacto:** el menú contextual de la tabla de sesiones (`main.py:1689`), el botón “✕ Detener sesión seleccionada” (`ui_tabs.py:294`) y el atajo **Supr** (`ui_tabs.py:289`) lanzan `AttributeError` y no detienen nada. La función aparece como “implementada” y testeada visualmente, pero está muerta.
* **Fix sugerido:** eliminar la definición duplicada de `main.py:1660` (o reemplazar `stop` por `stop_session`), y añadir la firma opcional `(self, _=None)` sólo en una versión.
* **Prueba recomendada:** test de humo que instancie `ScrcpyDockApp` con Tk oculto y llame a `_stop_selected` sobre una sesión simulada.

---

### 3.2 🔴 `SessionManager._build_cmd()` no existe — “Copiar comando scrcpy” lanza `AttributeError`

* **Ubicación:** `scrcpy_dock/main.py:1710`
* **Causa:** `_copy_sess_cmd` invoca `self.ctx.session_mgr._build_cmd(self.ctx.scrcpy, serial, p)`, pero `SessionManager` no tiene `_build_cmd` (el constructor de argv vive en `ScrcpyEngine.build_command(config, device, caps)`; verificado `hasattr` → `False`).
* **Impacto:** la opción “📋 Copiar comando scrcpy” del menú contextual siempre falla.
* **Fix sugerido:** reescribir usando el motor real:

```python
res = self.ctx.session_mgr._scrcpy.build_command(config, device, caps)
cmd = res.data
```

(el objeto `ScrcpySession` no guarda `config`, por lo que conviene persistirla en la sesión para poder reconstruir el comando).

---

### 3.3 🔴 `DeviceManager.get_device_model()` no existe — bloquea el flujo “Confiar y Recordar” de v1.4

* **Ubicación:** `scrcpy_dock/main.py:1400` (`_start_otg_mode`) y `scrcpy_dock/main.py:1458` (`_toggle_scene`)
* **Causa:** ambos handlers llaman a `self.ctx.device_mgr.get_device_model(serial) or "Android"`. `DeviceManager` sólo tiene `get_device_props` y `get_capabilities` (verificado `hasattr` → `False`).
* **Impacto:** con **Modo Seguro activo** (por defecto) y un dispositivo **no confiable**, iniciar transmisión o Modo OTG lanza `AttributeError` **antes** de mostrar el `TrustPromptModal`. Es exactamente la ruta de “Bóveda sin fricción” promocionada en v1.4.
* **Fix sugerido:** derivarlo del estado ya disponible, p. ej.

```python
model = next((m for s, m, _ in self.ctx.device_mgr.devices if s == serial), "Android")
```

o añadir `DeviceManager.get_device_model(serial)`.

---

### 3.4 🔴 `ErrorCode.INTERNAL_ERROR` no existe — enmascara errores de cifrado

* **Ubicación:** `scrcpy_dock/services/security_service.py:207`
* **Causa:** `encrypt_vault()` hace `return OperationResult.fail(ErrorCode.INTERNAL_ERROR, …)`, pero el catálogo (`scrcpy_dock/errors.py`) **no define** `INTERNAL_ERROR` (tiene `UNKNOWN_ERROR`). Comparación automática de los 30 miembros definidos vs. los usados → `INTERNAL_ERROR` es el único símbolo inexistente.
* **Impacto:** ante un fallo real de cifrado, en lugar de devolver un `OperationResult` fallido se lanza `AttributeError`, rompiendo el contrato del servicio y perdiendo el mensaje de error original.
* **Fix sugerido:**

```python
return OperationResult.fail(ErrorCode.UNKNOWN_ERROR, f"Error al cifrar vault: {e}")
```

* **Prueba recomendada:** test que fuerza `_derive_fernet_key()` a lanzar y asegure `res.success is False` y `res.error_code == ErrorCode.UNKNOWN_ERROR`.

---

### 3.5 🔴 El modo “Solo Audio (`--no-video`)” nunca arranca — perfil por defecto inutilizable

* **Ubicación:** `scrcpy_dock/utils.py:241` (`DEFAULT_CONFIG["profiles"]["🎙️ Stream OBS (Huawei)"]`), `scrcpy_dock/ui_widgets.py:545` (preset `📡 Stream con OBS (solo audio mic)`), rechazo en `scrcpy_dock/core/scrcpy_engine.py:209-215`.
* **Causa:** `build_command()` valida cada token de `extra_args` contra `ALLOWED_EXTRA_FLAGS` (`scrcpy_engine.py:39-45`), que **no incluye `--no-video`**. Cualquier perfil que lo use muere con `INVALID_EXTRA_ARGS`.
* **Evidencia (probe real):**

```
SessionConfig(extra_args=("--no-video",)) →
  success: False | error_code: ErrorCode.INVALID_EXTRA_ARGS
  "Flag no permitido en extra_args: --no-video"
```

* **Impacto:** la función de transmisión “sólo audio” (usada en cursos/streaming) es inarrancable de fábrica; el perfil por defecto `🎙️ Stream OBS (Huawei)` falla al primer clic. Además `main.py:1481` decide el `keyevent 26` buscando `"--no-video"`, lógica que nunca llega a ejecutarse.
* **Fix sugerido (elegir una):**
  * Añadir `--no-video` (y `--no-audio`, `--no-playback`) a `ALLOWED_EXTRA_FLAGS`, o
  * modelarlo como un campo tipado `SessionConfig.video_enabled: bool` (preferible, coherente con la arquitectura hexagonal), o
  * sustituir por `--video-source=camera`… no aplica: para solo-audio lo correcto es exponerlo en `SessionConfig`.
* **Prueba recomendada:** test que cargue **cada perfil de `DEFAULT_CONFIG`** y verifique `build_command(...).success is True`. Hoy ningún test lo hace.

---

### 3.6 🔴 `NameError` en el Toast de error de instalación automática

* **Ubicación:** `scrcpy_dock/main.py:667-668`

```python
except Exception as e:
    self.root.after(0, lambda: Toast(self.root, f"Error en instalación: {e}", "error"))
```

* **Causa:** en Python 3 la variable del `except … as e` se **elimina al salir del bloque**. El `lambda` se ejecuta después (vía `root.after`), y `e` ya no existe. `pyflakes` lo reporta como `local variable 'e' is assigned to but never used` + `undefined name 'e'`.
* **Evidencia (simulación real):**

```
AL EJECUTAR EL LAMBDA -> NameError cannot access free variable 'e' where
it is not associated with a value in enclosing scope
```

* **Impacto:** cualquier fallo de `pkexec`/winget/descarga muestra un `NameError` en consola en vez del mensaje de error.
* **Fix sugerido:**

```python
except Exception as e:
    err = str(e)
    self.root.after(0, lambda: Toast(self.root, f"Error en instalación: {err}", "error"))
```

*(mismo patrón a revisar en cualquier otro `lambda` que capture variables de un `except`.)*

---

### 3.7 🔴 La suite de tests sobrescribe la configuración real del usuario (pérdida de datos)

* **Ubicación:** `tests/test_core.py:41-45`

```python
def test_atomic_save_config(self):
    test_cfg = {"test_key": "test_value_123"}
    save_config(test_cfg)          # ← escribe ~/.config/masv/config.json REAL
    loaded = load_config()
    self.assertEqual(loaded.get("test_key"), "test_value_123")
```

* **Causa:** `utils.save_config()` escribe en `CONFIG_FILE = ~/.config/masv/config.json` sin parametrización ni aislamiento. El test usa el fichero real (importa `tempfile`/`os`/`json` pero **no los usa**, señal de que el aislamiento quedó a medias).
* **Evidencia:** tras ejecutar la suite, el fichero real quedó así:

```
~/.config/masv/config.json  →  {"test_key": "test_value_123"}
```

* **Impacto:** **pérdida de datos del usuario** (perfiles, bóveda de dispositivos confiables, idioma, tema, geometría) cada vez que se corre la suite —incluido el CI si un runner reutilizara HOME—. Es el bug más "silencioso" y destructivo del repo. No existe backup de `config.json` en `~/.MASV/` ni en `backups/` (esta carpeta sólo contiene `index_backup_*.html`).
* **Fix sugerido:** inyectar la ruta de config (`utils` debería exponer `set_config_path()`/variable de entorno `MASV_CONFIG_DIR`) y en el test usar `tempfile.TemporaryDirectory()` + `unittest.mock.patch("scrcpy_dock.utils.CONFIG_FILE", …)`. Nunca tocar el HOME real.
* **Nota de transparencia:** este informe se generó ejecutando la suite, por lo que el `config.json` de esta máquina ya fue sobrescrito. Si tenía datos, hay que regenerarlos (o recuperarlos desde la bóveda del teléfono / reasociando perfiles).

---

### 3.8 🟠 `get_device_props()` devuelve el **fabricante** como modelo

* **Ubicación:** `scrcpy_dock/managers.py:121`

```python
return {
    "model": caps.manufacturer,      # ← bug: debería ser ro.product.model
    ...
}
```

* **Causa:** `DeviceCapabilities` sólo transporta `manufacturer` y `platform`; no incluye `model`, y el adaptador lo sustituye por el fabricante.
* **Evidencia (probe real con props de un vivo V2314):**

```
get_device_props -> {'model': 'vivo', 'android_version': 35,
                     'manufacturer': 'vivo', 'platform': 'qcom', ...}
```

* **Impacto:** `SessionManager.start_scene_legacy` (`managers.py:444`) toma `model = dev_props["model"]` → el título de ventana scrcpy se genera como **“MASV: vivo”** en lugar de **“MASV: V2314”**, y los logs/alias muestran el fabricante. Contradice el ejemplo del FAQ (`ui_tabs.py:974`: *“MASV: vivo V2314”*).
* **Fix sugerido:** añadir `model: str = ""` a `DeviceCapabilities` y poblar `"model"` con `ro.product.model` en `get_capabilities` / `get_device_props`; propágalo en `SessionManager._start_scene_hexagonal` y `start_scene_legacy`.

---

### 3.9 🟠 Los 4 botones rápidos de Quick Cast no hacen nada (nombres de perfil inexistentes)

* **Ubicación:** `scrcpy_dock/ui_tabs.py:83-87`
* **Causa:** los botones buscan perfiles llamados `"Juego Rápido"`, `"Stream OBS"`, `"Webcam HD"`, `"Modo OTG (Teclado y Ratón USB)"`, pero los perfiles reales de `DEFAULT_CONFIG` son `"🎮 Juego Rápido"`, `"🎙️ Stream OBS (Huawei)"` y `"📷 Cámara HD"` — y “Modo OTG (…)” sólo existe como *preset* del asistente, no como perfil guardado.
* **Evidencia (probe real):**

```
profiles DEFAULT: ['🎮 Juego Rápido', '🎙️ Stream OBS (Huawei)', '📷 Cámara HD']
botón 'Juego Rápido' → existe: False
botón 'Stream OBS'   → existe: False
botón 'Webcam HD'    → existe: False
botón 'Modo OTG (Teclado y Ratón USB)' → existe: False
```

`_select_preset()` (`ui_tabs.py:75-81`) hace `if name in profiles:` y, si no coincide, **no hace nada en silencio**.
* **Impacto:** el atajo principal del dashboard “Quick Cast” (el primer panel que ve el usuario) es decorativo.
* **Fix sugerido:** resolver por *substring* normalizado (`"juego" in name.lower()`), o almacenar los nombres canónicos en una constante compartida y sembrar `DEFAULT_CONFIG` desde ella.

---

### 3.10 🟠 `_connect_wifi` nunca detecta IP inválida (comprobación de tupla mal hecha)

* **Ubicación:** `scrcpy_dock/main.py:812-816`
* **Causa:** `parse_ip_port()` devuelve **siempre una tupla** `(ip|None, port|None)`. `(None, None)` es *truthy*, así que `if not parsed:` nunca se cumple.

```
parse_ip_port('999.999.1.1:5555') -> (None, None) -> bool: True
```

* **Impacto:** con una IP malformada no se muestra el error “IP inválida”; se llega a la rama de Modo Seguro con `ip = None` y se muestra un mensaje engañoso (“IP no permitida”), confundiendo al usuario.
* **Fix sugerido:** `if not parsed or not parsed[0]:`.

---

### 3.11 🟠 `load_config()` comparte diccionarios con `DEFAULT_CONFIG` (alias mutable)

* **Ubicación:** `scrcpy_dock/utils.py:265-281`
* **Causa:** cuando el fichero no existe (o falla la lectura) se devuelve `dict(DEFAULT_CONFIG)`: una **copia superficial**. Las claves anidadas `profiles`, `security`, `device_associations` mantienen la **misma identidad** que el dict global.

```
cfg2 = dict(DEFAULT_CONFIG); cfg2["profiles"]["NUEVO_X"] = {}
→ DEFAULT_CONFIG contaminado: True
→ identidad dict anidado compartida: True
```

* **Impacto:** guardar un perfil, confiar en un dispositivo o cambiar `safe_mode` muta los *defaults* del proceso. Si en la misma ejecución se vuelve a llamar `load_config()` (fallback, reinicio interno, tests), los valores del usuario se filtran como si fueran “de fábrica”. Es un bug de clase, fácil de reproducir en tests.
* **Fix sugerido:** `copy.deepcopy(DEFAULT_CONFIG)` (o construir un `DEFAULT_CONFIG()` factory).

---

### 3.12 🟠 Internacionalización (EN) incompleta — la UI principal sigue en español

* **Ubicación:** `scrcpy_dock/i18n.py` (563 claves EN) vs. literales usados en `main.py`/`ui_tabs.py`/`ui_widgets.py`
* **Causa / Evidencia (extractor automático de `_("…")`):** **133 literales pasados a `_()` no tienen traducción EN** y caen al español. Ejemplos:

  * Menús completos: `Archivo`, `Editar`, `Ver`, `Tema Visual`, `🚀 Nueva Transmisión`, `🔄 Refrescar Dispositivos`, `⏹ Detener Todas las Sesiones`, `📥 Instalar en Sistema (Menú y Terminal)`, `🗑️ Desinstalar del Sistema`, `🚪 Salir`, `📖 Guía de Depuración USB`, `📦 Instalar APK en Teléfono`…
  * Barra lateral: `Quick Cast`, `Transmisión`, `Dispositivos`, `Mando Remoto`, `Ayuda / FAQ`.
  * Cabecera/estado: `Modo Seguro: ON`, `Modo Seguro: OFF`, `Blindar Red`, `Modo Compacto`, `Vista Completa`, `✔  ADB + scrcpy OK`, `Atención`… (133 en total).
* **Impacto:** contradice directamente el changelog v1.4 (“Internacionalización Completa Español/English”). Un usuario anglófono ve una app a medio traducir.
* **Nota adicional:** el test `tests/test_v14_features.py::test_i18n_v14_keys_available` sólo comprueba **5 claves**, dando falsa confianza de “i18n completa”.
* **Fix sugerido:** test de cobertura i18n que recorra por AST todas las llamadas `_(literal)` y falle si falta la clave (el extractor de este informe sirve de base). Añadir las 133 claves faltantes.

---

### 3.13 🟠 6 claves duplicadas en el diccionario EN (valores sobrescritos)

* **Ubicación:** `scrcpy_dock/i18n.py` — `pyflakes` reporta:
  * `i18n.py:166` vs `:487` → `"   d. Aparecerá el mensaje: ¡Ahora eres desarrollador!"` (dos traducciones distintas; gana la 2.ª).
  * `i18n.py:284` vs `:489` → `"   a. Regresa a Ajustes → Sistema → Opciones para desarrolladores."`
  * `i18n.py:285` vs `:490` → `"   b. Activa el interruptor 'Depuración USB'."`
  * `i18n.py:10` vs `:176` → `"v1.1  |  Ctrl+H → Ayuda  |  Ctrl+Q → Salir"` (valor idéntico, duplicado muerto).
* **Impacto:** deuda y riesgo de que la traducción “buena” quede enmascarada. Además hay claves huérfanas de versiones anteriores (`"🚀  Acciones"`, `"📋  Dispositivos detectados"`, `"v1.1  |  …"`), que ya no se usan en la UI actual.

---

### 3.14 🟡 Divergencia entre `security.py` y `security_service.py`

* **Ubicación:** `scrcpy_dock/security.py` (usado por la UI) vs `scrcpy_dock/services/security_service.py` (sólo usado por tests).
* **Causa:** dos implementaciones con supuestos incompatibles:
  * `SecurityManager.get_trusted_devices()` → **dict** `{serial: entry}`.
  * `SecurityService.is_whitelisted_device()` → exige `vault["trusted_devices"]` como **lista** de dicts.
* **Impacto:** el `SecurityService` hexagonal (Vault cifrado con Fernet + PBKDF2, `encrypt_vault`/`decrypt_vault`) **no está cableado a la UI**; la app real usa el `SecurityManager` en texto plano dentro de `config.json`. Hay dos fuentes de verdad de seguridad y la más robusta es código muerto.
* **Fix sugerido:** decidir un único dueño (probablemente `SecurityService`) y cablear la UI a él, o eliminar el esqueleto no usado. La bóveda real (`~/.MASV/.salt`, `vault.enc`) no se usa hoy.

---

### 3.15 🟡 La UI evita el `AdbEngine` y llama a `subprocess` directo (rompe ADR-006)

* **Ubicación:** `main.py` — `_check_deps:610`, `_connect_wifi:832`, `_enable_tcpip:966`, `_get_device_ip:991/1001`, `_restart_adb:1520/1522`, `_send_keyevent:1053…1074`, `_install_apk:1108`, `_route_cam:1206`, `_setup_v4l2:1153`.
* **Causa:** aunque existe `AdbEngine` con *socket aislado* (`ADB_SERVER_SOCKET tcp:localhost:5038`) y manejo tipado de errores (ADR-006/007/009), la capa de presentación sigue ejecutando `subprocess.run([self.ctx.adb, …])` sin env aislado ni `on-daemon-dead`.
* **Impacto:** `adb kill-server` desde “Reiniciar ADB” tumba el daemon compartido del usuario (Android Studio/VS Code), contradiciendo la mitigación documentada; y los errores nativos no se mapean a `ErrorCode`.

---

### 3.16 🟡 Documentación vs. código (inconsistencias)

| Afirmación | Realidad en código | Ubicación |
| :--- | :--- | :--- |
| “hasta 16 teléfonos”, rango “27183 a 27199” | `PortAllocator(base=27183, max_offset=20)` → **21 puertos** (27183–27203) | `core/port_allocator.py:25`, `managers.py:262`, `ui_tabs.py:972`, `i18n.py:567` |
| Perfil “Webcam HD” / “Cámara Trasera” en FAQ | no existen; son “📷 Cámara HD” | `ui_tabs.py:825`, `i18n.py:515` |
| Versión “v1.4” | CHANGELOG dice **1.4.1** y hay commit de 1.4.1 | `main.py:186`, `main.py:494` |
| `--max-fps 30`, `--v4l2-buffer 50` como ejemplos válidos de `extra_args` | no están en `ALLOWED_EXTRA_FLAGS` → serán rechazados | `ui_widgets.py:818`, `i18n.py:88` |
| “Comando `MASV --status`” (roadmap ANALISIS.md) | no implementado | `main.py:1917-1973` |

* **Fix sugerido:** centralizar `APP_VERSION = "1.4.1"` y usarla en UI/i18n/desktop entry; alinear textos y whitelist.

---

### 3.17 🟡 Artefactos basura versionados en git

* **`index.html`** (86 B) y **`style.css`** (17 B) están *trackeados* y contienen restos de una prueba:

```html
<div><h2>Prueba de Concurrencia</h2><p>Contenido concurrente</p></div> <!-- Paso 3 -->
```

```css
p { color: red; }
```

* **`backups/`** (15 ficheros `index_backup_*.html` de 86 B) está correctamente ignorado por `.gitignore`, pero ocupa el árbol de trabajo.
* **Impacto:** ruido en el repo; `index.html`/`style.css` no tienen relación con la app de escritorio. Hoy nadie los usa (no hay referencias desde Python).
* **Fix sugerido:** `git rm --cached index.html style.css` y borrarlos (o moverlos a una carpeta de experimentos no versionada).

---

### 3.18 🟡 Código muerto / sin cablear

* `managers.py:260` — `ScrcpyEngine(..., Path("/usr/local/share/scrcpy/scrcpy-server"))`: ruta **hardcodeada** y el `server_jar` **nunca se usa** (scrcpy 4.x embebe el servidor).
* `ScrcpyEngine.verify_server_version()` y `_compare_versions()` (`scrcpy_engine.py:103-165`) — implementados y **nunca invocados**; ADR-014 (control de versión cliente/servidor) queda sin efecto.
* `errors.py` — `ERROR_CATALOG` cubre **11 de 30** códigos; `BLOCKED_IP_ACCESS`, `DEVICE_OFFLINE`, `V4L2_LOOPBACK_ERROR` **nunca se usan**.
* `contracts.py:22` — `OperationResult` mantiene **dos campos espejo** `error` y `error_code` (sincronizados en `__post_init__`); la duplicidad invita a bugs (`if res.error:` es siempre *truthy* porque `ok()` lo deja en `ErrorCode.NONE`).
* `managers.py:105,107` — `self.devices`, `self.device_props`: `device_props` nunca se puebla (siempre cae al `get_capabilities`).
* `pyflakes`: 20+ imports sin usar en `ui_tabs.py`, `ui_widgets.py`, `main.py`, `i18n.py` (`import json`, `import os`, `webbrowser`, `_recolor`, `SafeActionConfirmModal`, `get_error_detail`, `_card_button`…).
* `main.py:60` y `main.py:128` — `WM_DELETE_WINDOW` se rebinde dos veces: el primer binding (`_on_app_close`) queda muerto.
* `main.py:386` y `main.py:396` — `Tooltip(...)` con texto **sin `_()`** (siempre en español); `main.py:404` sí usa `_()` pero la clave no está en el diccionario EN (cae a español). Mezcla inconsistente de estilos de traducción.

---

### 3.19 🟡 `state.py` — la FSM no valida transiciones

* **Ubicación:** `scrcpy_dock/state.py:54-67`
* **Causa:** `transition_to()` documenta “Aplica una transición de estado **si es válida**”, pero **siempre retorna `True`** y no consulta ninguna tabla de transiciones.
* **Impacto:** el “Autómata Finito determinista” del Vector 4 es en realidad un *setter* de estado; no impide transiciones inválidas (p. ej. `FAULT → SUCCESS` sin pasar por `PENDING`).
* **Fix sugerido:** declarar `_ALLOWED: dict[UIState, set[UIState]]` y devolver `False` (sin notificar) ante transiciones no permitidas; testear en `test_state.py`.

---

### 3.20 🟡 UI: `stop_session` bloquea el hilo de Tk hasta 3 s

* **Ubicación:** `managers.py:57-68` (`ScrcpySession.terminate`: `terminate()` + bucle `30 × time.sleep(0.1)` + `kill()`), invocado desde `main.py:1501` (`_stop_current`) y `main.py:914` (`_panic_lockdown`) en el **hilo de la UI**.
* **Impacto:** la interfaz se congela hasta ~3 s por sesión si scrcpy no muere rápido (con `--suspend`/ventanas SDL suele tardar). En `_panic_lockdown` con varios dispositivos el congelamiento se acumula.
* **Fix sugerido:** mover la terminación a un hilo worker y refrescar la tabla por `root.after`, o usar `poll()` con *polling no bloqueante*.

---

### 3.21 🟡 `SingleInstance` sin `SO_REUSEADDR`

* **Ubicación:** `utils.py:350-363`
* **Causa:** el socket de instancia única hace `bind(("127.0.0.1", 47291))` sin `SO_REUSEADDR` y sin `listen()`.
* **Impacto:** tras `_restart_app()` (`os.execl`) o un cierre abrupto, el nuevo proceso puede recibir `EADDRINUSE` y mostrar el falso “ya está en ejecución”. Además el socket no acepta conexiones (sólo reserva el puerto), lo que es suficiente pero frágil.
* **Fix sugerido:** `setsockopt(SO_REUSEADDR, 1)` antes del `bind` y capturar `EADDRINUSE` de forma explícita.

---

### 3.22 🟡 `AdbEngine` / `_TrackerThread`: `stop()` no interrumpe la lectura bloqueante

* **Ubicación:** `core/adb_engine.py:657-661` y `612-614`
* **Causa:** `_run_once()` bloquea en `proc.stdout.read(4)`; `stop()` sólo hace `set()` + `join(timeout=2.0)`. El `read()` no se desbloquea al poner el `Event`.
* **Impacto:** el hilo queda vivo bloqueado (es `daemon=True`, así que no impide cerrar, pero “Idempotente: detener el hilo” no es cierto). En `DeviceManager.stop_tracking()` (`managers.py:222`) no se garantiza la finalización.
* **Fix sugerido:** cerrar/terminar explícitamente el `Popen` en `stop()` antes del `join`, o usar `select`/`os.read` con timeout.

---

### 3.23 🔴 `AttributeError` al conectar por Wi-Fi con IP vacía o inválida *(encontrado por el arnés D1, 01-oct)*

**Archivo**: `scrcpy_dock/main.py:875-882` (guarda) · `scrcpy_dock/utils.py:326` (causa) · `scrcpy_dock/security.py:180`

`utils.parse_ip_port()` **nunca devuelve un valor falso**: ante cualquier entrada inválida retorna la tupla `(None, None)`, que es *verdadera*. La guarda del handler era `if not parsed:`, así que pasaba de largo con `ip = None` y reventaba en `SecurityManager.is_private_ip(None)`:

```
AttributeError: 'NoneType' object has no attribute 'strip'
  security.py:182  clean = ip_str.strip()
```

**Reproducción**: con Modo Seguro activo, dejar el campo IP vacío (o escribir `999.999.1.1`) y pulsar "Conectar por Wi-Fi" → excepción no controlada en lugar del aviso "IP inválida".

**Corrección aplicada**:
1. `if not parsed or not parsed[0]:` en `_connect_wifi` — es el paso B.3 del runbook de la v3.2, que había quedado sin ejecutar.
2. `is_private_ip()` pasa a ser **None-safe**: `(ip_str or "").strip()` → `False`. Dirección segura: una IP desconocida no es privada, así que el Modo Seguro la bloquea en vez de reventar.

**Causa raíz** (por qué la guarda equivocada era fácil de escribir): dos parsers hermanos del mismo módulo tienen convenciones de fallo distintas — `parse_ip_port()` → `(None, None)`; `parse_pair_ip_port_code()` → `None`. Unificarlas es deuda pendiente.

**Regresión**: `tests/test_ui_smoke.py::UISmokeTest.test_ip_vacia_avisa_en_vez_de_reventar` y `::DefectosCazadosPorD1`.

---

### 3.24 🟠 El serial se reconstruía parseando la etiqueta del listbox *(encontrado al refactorizar `_on_dev_select`, 01-oct)*

**Archivo**: `scrcpy_dock/main.py:_update_devs_ui` (escritor) · `scrcpy_dock/main.py:_extract_serial` (lector) · `scrcpy_dock/utils.py:365`

`_update_devs_ui` escribe la fila del listbox **con formato distinto según el estado**:

```
ok       →  "  🟢 🛡️  {alias}  ({serial})"
unauth   →  "  🟠 ⚠️  {serial}  (Sin autorizar en pantalla)"
offline  →  "  🔴 ⚠️  {serial}  (Desconectado / Offline)"
otro     →  "  ⚫  {serial}  [{state}]"
```

y `_extract_serial()` devuelve **el contenido del primer paréntesis**. Medido:

```
_extract_serial("  🟢 🛡️  Mi Vivo  (HWY9)")                 → "HWY9"          ✅
_extract_serial("  🟠 ⚠️  HWY9  (Sin autorizar en pantalla)") → "Sin autorizar en pantalla"  ❌
_extract_serial("  🔴 ⚠️  HWY9  (Desconectado / Offline)")    → "Desconectado / Offline"     ❌
_extract_serial("  ⚫  HWY9  [other]")                        → "⚫  HWY9  [other]"           ❌
```

**Impacto** (dos consecuencias, ambas visibles para el usuario):

1. Las ramas `unauth` y `offline` de `_on_dev_select` buscaban el estado ADB de un serial
   inexistente → recibían `"other"` → **nunca mostraban el aviso en el panel ni ponían la FSM en
   FAULT**. El mensaje "⚠ Acepta el diálogo en el teléfono" era **código inalcanzable**: el usuario
   conectaba un teléfono sin autorizar y la interfaz no le decía qué hacer.
2. `ctx.active_device_serial` quedaba con un texto basura (`"Sin autorizar en pantalla"`), de modo
   que cualquier acción posterior (transmitir, TCP/IP, keyevents) apuntaba a un serial inválido.

**Corrección de raíz** (no parcheando el call site): `_update_devs_ui` guarda el registro
`self._devices_shown` y la selección se resuelve **por índice contra ese registro**, sin volver a
interpretar el texto de la fila. El parseo se conserva sólo como respaldo (`_parse_device_row`) para
filas que no vengan de ese registro.

**Causa raíz de fondo**: reconstruir datos de dominio leyendo la etiqueta *presentacional* de un
widget. Es la misma clase de defecto que §3.23 (dos componentes con convenciones distintas) y queda
como regla en ADR-034.

**Regresión**: `tests/test_fase_d_regressions.py::TestOnDevSelectDescompuesto` (11 pruebas, con el
formato exacto de las cinco filas) — la primera versión de esas pruebas usaba filas inventadas y no
veía el problema; hubo que reproducir el formato real para destaparlo.

---

### 3.25 🟠 Reconstruir una pestaña apilaba su árbol de widgets completo *(encontrado al partir `ui_tabs.py`, 01-oct)*

**Archivo**: `scrcpy_dock/main.py:_change_theme` (invocador) · `scrcpy_dock/ui_tabs.py:build_*` (constructores)

`_change_theme` ofrece reiniciar la app o refrescar la interfaz en caliente. Si el usuario responde
que no, recorre **las siete pestañas sobre los mismos frames**:

```python
for tid, frame in self._tab_frames.items():
    if tid == "quickcast": self.ui.build_simple_view(frame)
    elif tid == "actions": self.ui.build_tab_actions(frame)
    ...
```

Pero sólo **cuatro** de los siete constructores vaciaban el contenedor antes de reconstruirlo
(`for w in p.winfo_children(): w.destroy()`); `build_tab_actions`, `build_tab_controls` y
`build_tab_profile` empezaban a crear widgets directamente.

**Medición** (sonda con la app real, contando hijos directos del frame):

```
pestaña       antes  después (1er cambio)  después (2º)
quickcast         2        2               2
actions           2        4               6      ← DUPLICA
controls          2        4               6      ← DUPLICA
profiles          2        4               6      ← DUPLICA
device            2        2               2
console           4        4               4
help              3        3               3
```

**Impacto**: cada cambio de tema en caliente apila una copia entera de la pestaña (canvas,
scrollbar y todo el árbol) encima de la anterior. El usuario ve widgets superpuestos y `refs[...]`
queda re-apuntado a los widgets nuevos mientras los viejos siguen empaquetados y visibles. La
memoria crece sin límite con cada cambio de tema y los handlers pueden quedar enlazados dos veces.

**Corrección**: la limpieza se unificó en un único ayudante (`ui/tabs/common.py:clear`) que **las
siete** pestañas llaman como primera operación. La reconstrucción es idempotente: el número de hijos
no cambia al repetirla.

**Causa raíz**: siete constructores construidos por separado, cada uno con su propio prólogo copiado
(a veces presente, a veces no). Es una consecuencia directa de la duplicación estructural que C2
eliminó: al haber un solo sitio donde se decide empezar de cero, ya no puede haber discrepancia.

**Regresión**: `tests/test_fase_c2_regressions.py` — `test_cambiar_de_tema_no_duplica_el_contenido_de_las_pestanas`,
`test_cada_pestana_se_puede_reconstruir_sin_acumular`, `test_tras_reconstruir_los_refs_apuntan_al_arbol_vivo`
y `TestCazadoPorC2` (guardia sobre el código). Verificado que **muerden**: al quitar `clear(parent)`
de una sola pestaña fallan 3 de las 12 pruebas de C2.

---

### 3.26 🟡 Doce claves duplicadas en la tabla de traducciones *(encontrado por pyflakes, 01-oct · ✅ CERRADO en Fase D)*

**Archivo**: `scrcpy_dock/i18n.py` (`_translations["en"]`)

En un literal de diccionario **la última clave gana**: doce entradas estaban duplicadas (`v1.1 | Ctrl+H...`, `Estado`, pasos de activación de depuración USB, etc.).

**Corrección aplicada**: se eliminaron las 12 líneas redundantes conservando la mejor redacción, se añadió la clave faltante `'Dirección ingresada:'` a `_EN_EXTRA` y se verificó mediante AST que el 100 % de las 406 invocaciones activas a `_()` en el código poseen traducción en inglés sin claves faltantes ni duplicadas.

---

### 3.27 🔴 PillNavBar carecía del método `select()` provocando `AttributeError` al pulsar botones *(01-oct · ✅ CERRADO en Fase D)*

**Archivo**: `scrcpy_dock/ui_widgets.py:96` (`PillNavBar`)

```python
command=lambda tid=tab_id, i=idx: self.select(tid, i)
```

`PillNavBar` asignaba a cada botón una lambda que invoca `self.select(tid, i)`, pero la clase no implementaba ningún método `select()`. Al hacer clic en cualquier pastilla de navegación, la aplicación fallaba inmediatamente con `AttributeError: 'PillNavBar' object has no attribute 'select'`.

**Corrección**: se implementó `select(self, tab_id, idx=None)` actualizando `self.active_id`, los colores visuales de estado activo/inactivo de las pastillas y despachando el callback `on_select_cb`. Cubierto en `tests/test_ui_widgets_coverage.py`.

---

### 3.28 🔴 Enmascaramiento de función de traducción `_` en `_cmd_chip` provocaba `TypeError: 'Event' object is not callable` *(01-oct · ✅ CERRADO en Fase D)*

**Archivo**: `scrcpy_dock/ui_widgets.py:324` (`_cmd_chip`)

```python
def copy(_=None):
    target = root or chip
    target.clipboard_clear()
    target.clipboard_append(cmd)
    copy_btn.config(text=_("✔ Copiado"), fg=C["green"])
```

El parámetro del callback de clic de Tkinter se llamaba `_` (`def copy(_=None):`), enmascarando la función global de traducción `_` de `i18n.py`. Al hacer clic en `📋 Copiar`, Tkinter pasaba el objeto `Event` como primer argumento, provocando que la llamada `_("✔ Copiado")` intentara invocar la instancia de `Event`, arrojando `TypeError: 'Event' object is not callable` y rompiendo el copiado visual.

**Corrección**: se renombró el parámetro a `event=None`, restaurando el acceso a `_()` para las cadenas `"✔ Copiado"` y `"📋 Copiar"`. Cubierto en `tests/test_ui_widgets_coverage.py`.

**Verificación posterior (01-oct)**: la deduplicación de `i18n.py` quedó confirmada con auditoría
AST propia: **0 duplicadas** y **0 claves sin traducción inglesa**. Y la tabla quedó **podada**:
**700 → 425 entradas** (−275), alineada 1:1 con lo que el código usa de verdad.

---

### 3.29 🔴 El paso de linter recién añadido al CI fallaba siempre *(encontrado al verificar la fase, 01-oct · ✅ CORREGIDO)*

**Archivo**: `.github/workflows/build.yml` (paso *Static Code Analysis & Linting*)

```yaml
      - name: Static Code Analysis & Linting (Pyflakes)
        run: |
          python -m pyflakes scrcpy_dock/ tests/
```

Un `run:` de GitHub Actions **falla el job si el comando devuelve un código distinto de cero**. Ese
comando devolvía **1 con 55 hallazgos** en el árbol tal como quedó la fase (52 imports sin usar, 2
variables asignadas y nunca leídas, 1 f-string sin marcadores): el pipeline se ponía en rojo en el
primer push, y en los **tres** sistemas de la matriz.

```
$ python -m pyflakes scrcpy_dock/ tests/   → exit 1   (55 hallazgos)
```

**Corrección aplicada**:
- **52 imports muertos** retirados con `autoflake --remove-all-unused-imports` en 24 archivos. Antes
  se comprobó que ninguno fuera un re-export: los importadores de `managers`, `main` y
  `tests/integration/fakes` no usan ninguno de los nombres retirados.
- `main.py`: `label=f"■  Detener sesión (Supr)"` → sin `f` (no tenía marcadores).
- `managers.py`: `exit_code = proc.wait(...)` / `exit_code = None` no se leían nunca; se conserva la
  llamada (`proc.wait(timeout=timeout)`, que es la que espera el handshake) y se van las asignaciones.
- `main.py:main()`: `app = ScrcpyDockApp(...)` no se usaba, pero la instancia debe sobrevivir
  mientras corre `mainloop()`. Se cuelga del root (`root.masv_app = …`) en vez de dejarla a merced
  del recolector, con el porqué comentado.

**Verificación**: `python -m pyflakes scrcpy_dock/ tests/` → **exit 0**, y la suite sigue
**558/558 OK**.

---

### 3.30 🔴 Sin display, el módulo principal no se importaba *(encontrado al verificar la fase, 01-oct · ✅ CORREGIDO)*

**Archivo**: `scrcpy_dock/main.py:7-13`

```python
try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    TRAY_AVAILABLE = True
except ImportError:          # ← demasiado estrecho
    TRAY_AVAILABLE = False
```

Sin pantalla, `import pystray` **no** levanta `ImportError`: levanta
`Xlib.error.DisplayNameError: Bad display name ""`. Al no estar contemplado, la excepción escapaba y
`import scrcpy_dock.main` fallaba al completo.

**Impacto medido en un entorno headless** (el caso exacto de `ubuntu-latest` en CI):

```
Ran 496 tests — FAILED (errors=18, skipped=18)
```

Los 18 errores tenían **una sola causa raíz**: tres módulos de pruebas (`test_ui_smoke`,
`test_fase_c2_regressions`, `test_fase_d_regressions`) no llegaban ni a importarse (`_FailedTest`), y
quince pruebas más morían en el `import scrcpy_dock.main` que hacen por dentro — pruebas que, por lo
demás, **no usan Tk en absoluto** (usan dobles de la app). Efecto perverso: el arnés de UI no
llegaba a saltarse con elegancia, *explotaba* al importar.

**Corrección**: `except Exception` con el motivo documentado — la bandeja es opcional y se degrada.

**Verificación**:

| Entorno | Antes | Ahora |
| :--- | :--- | :--- |
| Sin display (headless) | 18 errores, 18 skips | **558 ejecutadas, OK (43 skips)**, 0 errores |
| Con display | 558 OK | **558 OK**, 0 skips |

---

### 3.31 🟠 El CI no preparaba pantalla para las pruebas de UI *(encontrado al verificar la fase, 01-oct · ✅ CORREGIDO)*

**Archivo**: `.github/workflows/build.yml` (pasos de dependencias y de pruebas)

Los runners de GitHub son headless y el flujo sólo instalaba `python3-tk`. Aun con el import
arreglado (P3.30), en Linux las **43 pruebas de UI** se habrían saltado en silencio: el CI habría
estado verde sin haber ejercitado nunca la interfaz — cobertura aparente, no real.

**Corrección**: se instala `xvfb` y en Linux la suite corre bajo display virtual:

```yaml
      - name: Install system dependencies (Ubuntu)
        run: sudo apt-get install -y python3-tk xvfb

      - name: Run Automated Test Suite (Linux · display virtual para las pruebas de UI)
        if: runner.os == 'Linux'
        run: xvfb-run -a python -m unittest discover -s tests -v
```

En Windows/macOS se mantiene el comando plano; si algún runner no tuviera display, las pruebas de UI
**se saltan** en lugar de reventar (lo garantiza P3.30), así que el job no cae por el entorno.
Verificado que el YAML es válido y los pasos quedan bien condicionados (`yaml.safe_load` sobre los
14 pasos del job).

---

### 3.32 🔴 La suite de pruebas borraba la configuración real del usuario *(encontrado al verificar la fase, 01-oct · ✅ CORREGIDO + GUARDIÁN)*

**Archivo**: `tests/test_ui_widgets_coverage.py` (origen) · `scrcpy_dock/ui_widgets.py:TrustPromptModal._on_trust` (vía de escritura)

**Qué pasaba.** `test_ui_widgets_coverage.py` construía el modal con un `cfg` parcial:

```python
cfg = {...}                                             # dict de prueba, sin "profiles"
m1 = TrustPromptModal(self.root, "SER1", "Model1", "Alias1", sec, cfg)
```

y `TrustPromptModal._on_trust` guardaba **ese** `cfg` en el archivo de configuración real,
importando la función dentro del método y sin pasar por ningún callback:

```python
    def _on_trust(self):
        from .utils import save_config      # ← escribe en ~/.config/masv/config.json
        self.sec.trust_device(self.serial, self.model, self.alias)
        if self.cfg:
            save_config(self.cfg)
```

El archivo de pruebas **no** redirigía `CONFIG_FILE`/`CONFIG_DIR` (aunque su docstring afirmaba
"Redirige directorios y configuraciones a temporales"). Resultado: **cada ejecución de la suite
reescribía la configuración del usuario** con `{"trusted_devices": {}}`.

**Evidencia recogida**:

```
$ cat ~/.config/masv/config.json
{"trusted_devices": {}}                      ← 29 bytes; la del usuario tenía 2.397

$ md5sum ~/.config/masv/config.json          # antes y después de correr sólo ese archivo
9f89081d8746c52f88040dbbbab2f00f             # idéntico: escribe siempre lo mismo
$ stat -c '%y' ~/.config/masv/config.json    # pero el mtime cambia en cada corrida
2026-10-01 05:14:14  →  2026-10-01 05:14:28
```

**Impacto (Ley 10: pérdida de datos = Crítico)**: se perdieron los perfiles personalizados del
usuario y sus asociaciones de dispositivo. Se detectó porque una comprobación rutinaria del estado
de la config tras la suite empezó a fallar con `KeyError: 'profiles'`.

**Causa raíz, en dos capas** (ambas corregidas):

1. **La prueba no aislaba el entorno** — el mismo error que la auditoría original ya había
   encontrado en `test_core.py` (hallazgo A1) y que la Fase A arregló. La docstring afirmaba lo
   contrario, así que la revisión no lo vio: *una afirmación de aislamiento no es aislamiento*.
2. **El widget escribía el disco por su cuenta.** Sus hermanos (`DeviceTrustModal`,
   `TrustVaultDialog`) reciben un `save_cb` y no tocan disco; `TrustPromptModal` se importaba
   `save_config` dentro del handler y persistía el `cfg` que le dieran, **sin comprobar que fuera
   una configuración completa**. Eso es lo que convirtió un `cfg` de prueba en un borrado real.

**Correcciones aplicadas**:

- **Aislamiento del entorno en la prueba** (y de paso en `test_security.py` y
  `TestB5SeguridadUnificada`): `CONFIG_FILE`, `CONFIG_DIR` y `LOG_FILE` a un temporal, con
  `save_config` grabando en memoria. Se factorizó en `tests/ui_harness.aislar_config(tmp)` para que
  haya un único sitio que mantener.
- **`TrustPromptModal` ya no escribe en disco**: recibe `save_cb` como sus hermanos
  (`save_cb(cfg)`), y `main.py` le pasa `save_config` en sus dos puntos de construcción. El
  comportamiento de la app es idéntico; el modal ya no puede destruir nada por su cuenta.
- **Guardián permanente** `tests/test_suite_sin_efectos.py` (3 pruebas), con dos puertas:
  - *estática*: todo módulo de pruebas que pueda provocar un guardado debe aislar la config (o
    importar el arnés que lo hace);
  - *de extremo a extremo*: ejecuta en subproceso las pruebas de widgets y comprueba que el archivo
    real queda **byte a byte igual** (sha256 antes/después).
  Verificado que **muerde**: al quitarle el aislamiento a un módulo, el guardián falla.

**Recuperación de los datos**: la restauración salió de la copia antigua del usuario
(`~/.config/scrcpy-dock/config.json`, 25-jul), que conservaba su perfil **`Lalo`** completo, más las
asociaciones de dispositivo y el `last_selected_profile`. El perfil **`Frontal`** no existía en
ninguna copia local: se reconstruyó **por inferencia** (cámara frontal) y queda señalado para que el
usuario lo revise. La config restaurada tiene sus 5 perfiles y `language: "en"`. El archivo dañado
se conservó como `config.json.danado-P3.32.bak` (evidencia).

**Verificación**: `md5` de la config **idéntico antes y después** de la suite completa (561
pruebas); el guardián pasa; las 5 pruebas de la fase y las 14 de widgets siguen en verde.

---

### 3.33 🟡 La auditoría de i18n contaba 19 claves vivas como huérfanas *(encontrado al planificar la poda, 01-oct · ✅ CORREGIDO + GUARDIÁN)*

**Archivo**: `scrcpy_dock/i18n.py` · `scrcpy_dock/ui/tabs/tab_help.py:32`

Los títulos de los 19 acordeones de la FAQ no se traducen con un literal directo, sino que se
**pasan por variable** a un ayudante que traduce dentro:

```python
    def _add(title, build_fn):                      # tab_help.py
        item = AccordionItem(inner, _(title), build_fn, canvas_ref=canvas)
    ...
    _add("🚀  1. Inicio rápido — Primeros pasos con MASV", _faq_quickstart)
```

Un escaneo de `_("literal")` —el que usaron la auditoría y la propia Fase D— **no ve esos 19
títulos** y los clasifica como entradas muertas. Consecuencias reales:

- Las cifras publicadas eran un **subconteo**: «404/404» y luego «406 claves usadas» medían sólo
  literales; el número real de claves vivas es **425** (406 por literal + 19 por flujo).
- El «pendiente» decía «295 claves i18n huérfanas»: en realidad eran **275**, y una poda ingenua
  habría borrado **19 traducciones en uso** (todos los títulos de la Ayuda) sin que ninguna prueba
  ni el linter dijeran nada. Es la misma clase de trampa que P3.26, en la dirección contraria:
  una entrada muerta que gana en silencio, o una entrada viva que desaparece en silencio.

**Corrección**: la poda se hizo por **doble vía** (literales + literales que fluyen a `_()` a través
de `_add`/`_selector`), y se añadió `tests/test_i18n_integridad.py` (5 pruebas) que cierra las tres
trampas a la vez: **sin duplicadas** (contadas en el literal del AST, no en el diccionario),
**sin faltantes** y **sin huérfanas**; más una prueba que exige que la vía de flujo siga
declarada, para que nadie la olvide al añadir otra puerta hacia `_()`.

---

### 3.34 🟡 Dos etiquetas de dispositivo se pintan en balde *(encontrado al escribir la caracterización de `_on_tab_changed`, 01-oct · 📄 DOCUMENTADO)*

**Archivo**: `scrcpy_dock/ui/tabs/tab_actions.py:27`, `scrcpy_dock/ui/tabs/tab_controls.py:27`, `scrcpy_dock/main.py` (`_pintar_etiquetas_de_dispositivo`)

Las etiquetas de dispositivo de las pestañas **Acciones** y **Controles** se construyen atadas a una
variable Tk, no a un texto:

```python
    tab.refs['action_device_lbl'] = tk.Label(d_box, textvariable=tab.ctx.active_device, ...)
```

`_on_tab_changed` les asigna texto con `config(text=…)`, pero en Tk **gana la variable**: la
asignación no se ve y `cget("text")` sigue devolviendo lo que dice `ctx.active_device`. Es decir,
las dos etiquetas llevan desde antes del refactor recibiendo un pintado inerte (el nombre del
dispositivo que sí ve el usuario lo escribe `ctx.select_device`, `main.py:975`).

**Medido** (sonda sobre la app real):

| Comprobación | Resultado |
| :--- | :--- |
| `cget("textvariable")` de `action_device_lbl` y `ctrl_device_lbl` | la misma que el combo simple (`PY_VAR0`) |
| `_on_tab_changed()` con `active_device_serial="HWY9"` y alias "Mi Vivo" | el texto de la etiqueta sigue siendo `Sin dispositivo` |
| tras `ctx.select_device("HWY9", "Mi Vivo (HWY9)")` | las dos etiquetas muestran `Mi Vivo (HWY9)` ✅ (camino real) |

**Estado**: no corregido a propósito, porque la corrección es una decisión de producto, no técnica
(hay dos opciones válidas): quitar el `config(text=…)` de esas dos etiquetas —son inertes, y
eliminarlos deja el código más honesto— o quitar el `textvariable` para que gane el texto que calcula
`_on_tab_changed` (entonces el nombre con serial se recalcula al cambiar de pestaña). Mientras no se
decida, el comportamiento visible está caracterizado por
`test_las_etiquetas_de_dispositivo_siguen_a_la_variable_compartida`.

---

### 3.35 🟡 La comprobación de Modo Seguro estaba duplicada en dos handlers *(encontrado al descomponer `_toggle_scene`, 01-oct · ✅ CORREGIDO)*

**Archivo**: `scrcpy_dock/main.py` (`_toggle_scene` y `_start_otg_mode`)

El mismo bloque —"¿hay dispositivo?" + "¿el Modo Seguro lo aprueba?"— estaba **copiado literalmente** en
los dos handlers (18 líneas idénticas, incluido el modal de confianza y el `save_config`):

```python
        if self.ctx.security_mgr.is_safe_mode_enabled and not self.ctx.security_mgr.is_trusted_device(serial):
            alias = self.ctx.security_mgr.get_device_alias(serial)
            model = self.ctx.device_mgr.get_device_model(serial) or "Android"
            modal = TrustPromptModal(...)
            if not modal.result or modal.result == "cancel":
                return
            if modal.result == "trust":
                save_config(self.ctx.cfg)
                self._on_dev_select()
```

Dos consecuencias, la segunda medida:

1. **Riesgo de arreglo a medias**: cualquier corrección de seguridad (por ejemplo, tratar un cierre sin
   respuesta como no autorizado) hay que recordar hacerla en los dos sitios.
2. **Ya habían divergido sin que nadie lo notara**: `_toggle_scene` avisaba de "sin dispositivo" con
   `showerror` y `_start_otg_mode` con `showwarning` — la misma condición con dos severidades distintas.

**Corrección**: el guardián vive ahora en un solo sitio (`_dispositivo_listo_para_la_escena`, con
`_avisar_sin_dispositivo`, `_requiere_confirmacion_de_confianza` y `_pedir_confianza`), y los dos
handlers lo invocan. La diferencia de severidad **se conserva** (parámetro `critico`), porque cambiarla
sería un cambio de interfaz y no de estructura; queda como decisión de producto pendiente: ¿tiene
sentido que falte el dispositivo sea error al arrancar una sesión y sólo aviso en Modo OTG?

Efecto colateral medido: `_start_otg_mode` baja de CC 10 a **3** sin buscarlo.

---

## 4. Cobertura de pruebas — brechas concretas

Lo que **no** cubre la suite actual (269 tests) y permitió que los bugs anteriores pasaran:

| Brecha | Consecuencia |
| :--- | :--- |
| Ningún test toca `ScrcpyDockApp`/handlers de `main.py` | Bugs 3.1, 3.2, 3.3, 3.6 indetectables |
| Ningún test carga/lanza cada perfil de `DEFAULT_CONFIG` | Bug 3.5 (perfil por defecto roto) indetectable |
| Test de i18n verifica sólo 5 claves | Bug 3.12 (133 claves faltantes) indetectable |
| Test de config escribe el HOME real | Bug 3.7 (pérdida de datos) *causado por* la suite |
| No hay test del catálogo completo de `ErrorCode` | Bug 3.4 indetectable |
| `pyflakes`/linter no está en el CI | 20+ imports muertos, variables sin usar (incl. el bug 3.6) |
| CI usa `unittest discover` (correcto para esta suite) pero **no** `--failfast` ni linter | Los 269 pasan aunque queden rutas rotas |

---

## 5. Plan de acción priorizado

### Fase 0 — Correcciones críticas (1–2 h)
1. `main.py:1670` → `stop_session` (y eliminar la definición duplicada de `main.py:1660`).
2. `main.py:1710` → reconstruir el comando con `ScrcpyEngine.build_command`.
3. `main.py:1400/1458` → sustituir `get_device_model` por lectura de `device_mgr.devices` (o implementarlo).
4. `security_service.py:207` → `ErrorCode.UNKNOWN_ERROR`.
5. `main.py:667-668` → materializar `e` en variable local antes del `lambda`.
6. `tests/test_core.py` → aislar `HOME`/`CONFIG_FILE` (bug de pérdida de datos). **Hacerlo antes de volver a ejecutar la suite.**
7. Añadir `--no-video` a la whitelist **o** crear `SessionConfig.video_enabled`.

### Fase 1 — Correcciones altas (medio día)
8. `managers.py:121` → propagar `ro.product.model` (nuevo campo en `DeviceCapabilities`).
9. `ui_tabs.py:83-87` → resolución tolerante de nombres de perfil/constantes compartidas.
10. `main.py:813` → `if not parsed or not parsed[0]:`.
11. `utils.py` → `deepcopy(DEFAULT_CONFIG)` + `copy` en `load_config`.
12. Completar las 133 traducciones EN y eliminar las 6 claves duplicadas.

### Fase 2 — Calidad y deuda (1–2 días)
13. Cablear la UI al `AdbEngine` (socket aislado) y eliminar los `subprocess.run` sueltos.
14. Unificar `SecurityManager`/`SecurityService` en una sola fuente de verdad (cifrado real de la bóveda).
15. Añadir validación de transiciones a `UIStateMachine`.
16. `git rm --cached index.html style.css` + limpiar `backups/`.
17. Centralizar `APP_VERSION`; alinear FAQ, rangos de puertos y whitelist con el código.
18. Mover la terminación de procesos fuera del hilo de UI; `SO_REUSEADDR` en `SingleInstance`; terminar el proceso en `_TrackerThread.stop()`.

### Fase 3 — Infraestructura de calidad
19. Añadir al CI: `pyflakes` (o `ruff`) + `pytest -q` y un paso que falle si hay imports/variables muertos.
20. Añadir *smoke test* de UI con `tkinter` oculto que construya `ScrcpyDockApp` y ejercite: detener sesión, copiar comando, trust prompt, arranque de cada perfil por defecto.
21. Test de cobertura i18n (AST) y test de exhaustividad del `ERROR_CATALOG` (todos los `ErrorCode` con `ErrorDetail`).
22. Separar `requirements.txt` (runtime) de `requirements-dev.txt` (`pyinstaller`, `pytest`, `pyflakes`).

---

## 6. Comandos de verificación usados (reproducibles)

```bash
cd "/home/myinnervoid/Estudio Memexicanisimos/MASV"

# 1. Suite como la declara el changelog
python -m pytest -q                                    # 269 passed
python -m unittest discover -s tests -v                # 269 tests OK (runner del CI)

# 2. Análisis estático
python -m pyflakes scrcpy_dock build.py run.py tests

# 3. Comprobaciones puntuales (usadas para este informe)
python - <<'PY'
from scrcpy_dock.errors import ErrorCode
from scrcpy_dock.managers import SessionManager, DeviceManager
print(hasattr(ErrorCode, "INTERNAL_ERROR"))        # False  → bug 3.4
print(hasattr(SessionManager, "stop"))             # False  → bug 3.1
print(hasattr(SessionManager, "_build_cmd"))       # False  → bug 3.2
print(hasattr(DeviceManager, "get_device_model"))  # False  → bug 3.3
PY
```

---

## 7. Anexo — Inventario rápido

* LOC Python analizadas: **12.364** (53 ficheros; `main.py` 1.989, `ui_widgets.py` 1.201, `ui_tabs.py` 1.034, `adb_engine.py` 661, `i18n.py` 610, `managers.py` 592).
* Archivos más grandes: `main.py` (97 KB), `ui_tabs.py` (67 KB), `i18n.py` (61 KB), `ui_widgets.py` (58 KB).
* `ErrorCode`: 30 definidos / 29 usados / **1 usado-inexistente** (`INTERNAL_ERROR`, corregido en Fase A) / 11 con `ErrorDetail` en catálogo / 3 definidos sin uso.
* Claves i18n EN: 563; literales `_()` sin traducción: **133**; claves duplicadas: **6**.
* Tests: 269 (`unittest`), 0 que importen `scrcpy_dock.main`.

*(Las cifras de este anexo son la fotografía del 01-oct al inicio de la auditoría. Estado actual en el §8.)*

---

## 8. Actualización posterior — Fases A, B, C y D1 (01-oct-2026)

Los tres documentos del sistema (`ANALISIS.md`, `AUDIT_REPORT.md` y este informe) se mantienen
sincronizados con el registro de ejecución de `ANALISIS.md` §11.

| Métrica | Al redactar este informe | Tras Fases A–D (verificado) |
| :--- | :---: | :---: |
| Pruebas | 269 | **597** (597 OK con display · 62 skips y 0 errores sin display) |
| Cobertura total | 35 % | **85 %** |
| Cobertura `core/adb_engine.py` | 46 % | **100 %** |
| Módulos de negocio bajo el 80 % | 4 | **0** (mínimo 81 %) |
| Cobertura de la capa de pestañas | 0 % | **99 %** (`ui/tabs/`, 526 sentencias) |
| Cobertura `ui_widgets.py` | 16 % | **94 %** (medido; la fase declaró 81,8 %) |
| Cobertura UI (`ui_tabs.py`) | 0–3 % | **100 %** |
| Bloques con CC > 10 | 20 (máx. 63) | **5** (máx. 12; los 5 sin red, ver §11.12–11.13 de `ANALISIS.md`) |
| Bloques Rank D o F | 5 (3 D + 2 F) | **0** |
| Mutaciones cazadas en los refactores (§11.12–11.13) | — | **8/8** y **12/12** (primera medición: 4/8) |
| Umbrales de la Ley 7 en rojo | 2 | **0** |
| `ErrorCode` con `ErrorDetail` | 11 / 30 | **16 / 31** |
| Literales `_()` sin traducción EN | 133 | **0** (425 claves vivas: 406 por literal + 19 por flujo) |
| Claves i18n huérfanas | ~295 | **0** (podadas 275; las 19 falsas huérfanas de la FAQ conservadas) |
| Entradas en la tabla i18n | 700 | **425** (alineada 1:1 con el código) |
| Invocaciones ADB directas desde la UI | 17 | **0** |
| Implementaciones criptográficas | 2 (una muerta) | **1** (`SecurityService`) |
| Bóveda de confianza | Texto plano | **Cifrada (`vault.enc`)** con migración verificada |
| Defectos Críticos abiertos | 2 | **0** |
| Pruebas que escriben en la config real | 1 (§3.32) | **0** (con guardián permanente) |

**Hallazgos nuevos aparecidos al ejecutar las fases** (no estaban en §3): el motor ADB duplicado
y la pérdida del canal de logs (`ANALISIS.md` §11.3), la rama inalcanzable por la whitelist
(§11.3), la fragilidad de las pruebas de puertos cuando la app está abierta (§11.3), el hueco de
~26 ADR citados y no escritos (`DECISIONS.md`), **§3.23** (cazado por el arnés D1) y **§3.24**
(cazado al refactorizar `_on_dev_select`).

**Pendiente**: C2 (modularización de la UI, respaldada ya por D1), D2–D5, los 14 bloques CC entre 11
y 18, la cobertura de `adb_engine.py` (46 %), unificar las convenciones de fallo de los parsers de
IP, **podar las claves i18n huérfanas (hecho: 275 eliminadas, tabla alineada 1:1)** y reconstruir los ADR ausentes.

---

*Informe generado por análisis estático + ejecución real sobre el repo. Todos los hallazgos marcados con «verificado» fueron reproducidos con código, no inferidos.*
