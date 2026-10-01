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
* `errors.py` — `ERROR_CATALOG` cubre **13 de 30** códigos; `BLOCKED_IP_ACCESS`, `DEVICE_OFFLINE`, `V4L2_LOOPBACK_ERROR` **nunca se usan**.
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
* `ErrorCode`: 30 definidos / 29 usados / **1 usado-inexistente** (`INTERNAL_ERROR`) / 13 con `ErrorDetail` en catálogo / 3 definidos sin uso.
* Claves i18n EN: 563; literales `_()` sin traducción: **133**; claves duplicadas: **6**.
* Tests: 269 (`unittest`), 0 que importen `scrcpy_dock.main`.

---

*Informe generado por análisis estático + ejecución real sobre el repo. Todos los hallazgos marcados con «verificado» fueron reproducidos con código, no inferidos.*
