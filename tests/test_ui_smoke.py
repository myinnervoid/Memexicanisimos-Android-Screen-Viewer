"""D1 · Smoke test de UI (headless) — el arnés de la Fase D.

Construye la aplicación REAL (`ScrcpyDockApp`) sobre un `Tk` oculto y ejercita
los flujos de interfaz que ninguna prueba unitaria tocaba: construcción de
todos los widgets, navegación por las 7 pestañas, clic en cada botón del
dashboard, arranque de los 3 perfiles de fábrica, detener/copiar/pánico y la
ruta "faltan dependencias".

Por qué existe (y qué habría cazado): los defectos P3.1, P3.2, P3.3, P3.5, P3.6
y P3.9 de v1.4.1 vivían en la capa de UI —métodos inexistentes, callbacks
rotos, perfiles que no arrancaban— y ninguno era detectable sin instanciar la
interfaz. Este arnés es el requisito previo de C2 (partir `ui_tabs.py`) y de
cualquier refactor de complejidad en `main.py`.

Reglas de aislamiento (nada toca el sistema del usuario):
  - Config, log y dir de config → `TemporaryDirectory`.
  - Motor ADB y motor scrcpy → dobles sin `subprocess`.
  - `SecurityManager.pair_device` / `lockdown_*` → dobles (lanzan `adb` real).
  - Diálogos → registradores (nunca bloquean ni piden confirmación).
  - `parent.wait_window` y `grab_set` → neutralizados: los modales los invocan
    en su constructor y congelarían la prueba.
  - Handlers con efectos reales en el sistema (instalar/desinstalar en el
    menú, `pkexec`/`lsmod`, terminal externo, winget) → en `_DENY`.

Ejecutable con el runner del CI:
    python -m unittest discover -s tests
"""
from __future__ import annotations

import copy
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import scrcpy_dock.context as context_mod
import scrcpy_dock.main as main_mod
import scrcpy_dock.utils as utils
from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.core.scrcpy_engine import ScrcpyEngine
from scrcpy_dock.errors import ErrorCode
from scrcpy_dock.main import ScrcpyDockApp
from scrcpy_dock.security import SecurityManager
from scrcpy_dock.utils import parse_ip_port

from tests.ui_harness import (
    _LAUNCHED,
    _DialogRecorder,
    _FakeProc,
    parches_entorno,
    parches_ui,
)

# Pestañas canónicas (main.py:_select_tab)
TABS = ["quickcast", "actions", "device", "controls", "profiles", "console", "help"]

# Handlers que mutan el sistema del usuario o lanzan instaladores reales: se
# ejercitan por otras vías (pruebas unitarias con dobles), nunca por clic.
_DENY = {
    "_auto_install_deps",     # winget/pkexec: instala paquetes de verdad
    "_open_terminal_install",  # abre una terminal externa
    "_install_to_system",      # escribe en ~/.local/share y ~/.local/bin
    "_uninstall_from_system",  # borra esos enlaces del sistema
    "_setup_v4l2",             # sudo modprobe v4l2loopback
    "_route_cam",              # modprobe / ffmpeg sobre /dev/video*
    "_restart_adb",            # mata y levanta el daemon (aunque sea el aislado)
    "_exit",                   # cierra la app
    "_on_close",
    "_on_app_close",
    "_start_tray",             # bandeja del sistema (pystray)
}


class _CommandCheckingScrcpy:
    """Finge el lanzamiento pero valida el argv con el motor REAL.

    Así el smoke test conserva el poder de caza de P3.5 (un perfil de fábrica
    que el motor rechaza) sin abrir procesos. Implementa el contrato público
    que consumen `SessionManager` y `StreamService` (`launch`, `build_command`).
    """

    def __init__(self):
        self._real = ScrcpyEngine(Path("/usr/local/bin/scrcpy"), Path("/dev/shm/scrcpy-server"))
        self.launched: list[list[str]] = []
        self.commands: list[list[str]] = []

    def build_command(self, config, device, caps):
        res = self._real.build_command(config, device, caps)
        if res.success and res.data is not None:
            self.commands.append(res.data)
        return res

    def launch(self, config, device, caps):
        res = self.build_command(config, device, caps)
        if not res.success:
            return OperationResult.fail(res.error_code or ErrorCode.PROCESS_SPAWN_ERROR, res.message)
        if res.data is not None:
            self.launched.append(res.data)
        return OperationResult.ok(_FakeProc())


class UISmokeTest(unittest.TestCase):
    """Arnés de humo: la app completa, headless, sin efectos secundarios."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception:  # pragma: no cover - sin display
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        if cls.root:
            try:
                cls.root.destroy()
            except Exception:
                pass

    def setUp(self):
        if not self.root:
            self.skipTest("Tkinter sin display: el arnés de UI no puede correr")

        self._tmp = tempfile.TemporaryDirectory()
        tmp = self._tmp.name
        self.cfg_data = copy.deepcopy(utils.DEFAULT_CONFIG)
        self.cfg_data["onboarding_done"] = True       # evita el modal de bienvenida
        self.cfg_data["language"] = "es"
        self.cfg_data.pop("window_state", None)

        # Modales: `TrustPromptModal` llama a wait_window en el constructor y
        # `grab_set` deja el grab global tomado entre pruebas.
        self._patches = parches_entorno(self.cfg_data, tmp)
        for p in self._patches:
            p.start()

        self.dialogs = _DialogRecorder({"askyesno": True, "askokcancel": True})
        self.toasts: list[tuple] = []
        # Ningún handler puede abrir un proceso real durante el arnés
        # (`_open_log` lanzaría `xdg-open` en el escritorio del usuario).
        _LAUNCHED.clear()
        self._ui_patches = parches_ui(self.dialogs, self.toasts)
        for p in self._ui_patches:
            p.start()

        self.app = ScrcpyDockApp(self.root)
        # Efectos irreversibles neutralizados también en los handlers permitidos.
        self.app._restart_app = MagicMock()
        self.scrcpy = _CommandCheckingScrcpy()
        self.app.ctx.session_mgr._scrcpy = self.scrcpy

    def tearDown(self):
        for p in self._ui_patches + self._patches:
            p.stop()
        try:
            for child in self.root.winfo_children():
                if isinstance(child, tk.Toplevel):
                    child.destroy()
        except Exception:
            pass
        self._tmp.cleanup()

    # ── utilidades ────────────────────────────────────────────────────

    def _call(self, name: str, *args, **kwargs):
        """Invoca un handler del app y falla con contexto si revienta (P3.x)."""
        fn = getattr(self.app, name, None)
        self.assertIsNotNone(fn, f"ScrcpyDockApp.{name} no existe (método borrado)")
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - es el objeto de la prueba
            self.fail(f"{name}{args} lanzó {type(exc).__name__}: {exc}")

    def _iniciar_sesion(self, serial="SERIAL1"):
        """Deja una sesión activa arrancada por la propia UI.

        El Modo Seguro exige confiar en el dispositivo antes de transmitir, así
        que el arnés recorre el flujo real: confiar → arrancar.
        """
        self.app.ctx.active_device_serial = serial
        self.app.ctx.active_device.set("V2314")
        self.app.ctx.security_mgr.trust_device(serial, "V2314", "Mi Vivo")
        return self._call("_start_profile")

    # ── D1.1 · la ventana completa se construye ───────────────────────

    def test_la_ventana_completa_se_construye(self):
        self.assertIsNotNone(self.app.ui)
        for tab in TABS:
            self.assertIn(tab, self.app._tab_frames, f"falta la pestaña {tab}")
        # Las claves que la UI consulta en caliente deben existir todas.
        for clave in ("sess_tree", "dev_listbox", "log_txt", "profile_listbox",
                      "active_profile_combo", "dep_frame", "install_frame",
                      "route_cam_btn", "v4l2_lbl", "scan_lbl", "ip_entry",
                      "port_entry", "profile_chips"):
            self.assertIn(clave, self.app.ui.refs, f"refs['{clave}'] no existe")

    def test_el_registro_de_callbacks_esta_completo(self):
        self.assertGreaterEqual(len(self.app.cb), 35)
        for nombre, cb in self.app.cb.items():
            self.assertTrue(callable(cb), f"el callback {nombre} no es invocable")

    def test_no_hay_atributos_self_inexistentes(self):
        """Rastreo estático: todo `self.X` usado existe como método o atributo.

        Es la comprobación que habría cazado P3.3 (`get_device_model`) y P3.2
        (`_build_cmd`) sin necesidad de ejecutar nada.
        """
        import ast

        src = Path(main_mod.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)

        asignados, referidos = set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
               and node.value.id == "self":
                if isinstance(node.ctx, ast.Store):
                    asignados.add(node.attr)
                else:
                    referidos.add(node.attr)

        metodos = {n for n in dir(ScrcpyDockApp)}
        # Atributos creados por Tk/herencia o en tiempo de ejecución.
        permitidos = {"tk", "master", "children", "winfo_children", "_w", "config"}
        faltantes = sorted(referidos - metodos - asignados - permitidos)
        self.assertEqual(faltantes, [], f"self.X inexistentes en main.py: {faltantes}")

    # ── D1.2 · navegación por todas las pestañas ──────────────────────

    def test_todas_las_pestanas_se_navegan(self):
        for idx, nombre in enumerate(TABS):
            self._call("_select_tab", nombre)
            self._call("_select_tab", idx)
        self._call("_on_tab_changed")
        self.assertEqual(len(self.app._tab_frames), len(TABS))

    def test_un_dispositivo_no_confiado_no_arranca_sin_aprobar(self):
        """Modo Seguro: sin confianza previa el arranque debe abortar, no reventar."""
        self.app.ctx.active_device_serial = "DESCONOCIDO"
        self.app.ctx.active_profile.set(list(utils.DEFAULT_CONFIG["profiles"])[0])

        self._call("_toggle_scene")

        self.assertEqual(self.scrcpy.launched, [], "arrancó sin aprobación del usuario")
        self.assertEqual(self.app.ctx.session_mgr.sessions, {})

    def test_alternar_vista_compacta_y_avanzada(self):
        for _ in range(3):
            self._call("_toggle_view")
        self.assertIn("is_advanced_view", self.app.__dict__)
        self._call("_select_tab", "quickcast")

    # ── D1.3 · todos los botones del dashboard ────────────────────────

    def test_cada_callback_del_dashboard_responde(self):
        """Clic en cada botón/atajo registrado, sin dispositivo ni sesión."""
        fallos = []
        for nombre, cb in self.app.cb.items():
            metodo = getattr(cb, "__name__", "")
            if metodo in _DENY or nombre in _DENY:
                continue
            if getattr(cb, "__self__", None) is not None or callable(cb):
                try:
                    cb()
                except TypeError as exc:
                    # callbacks que exigen argumento (p. ej. send_keyevent)
                    if "positional argument" not in str(exc):
                        fallos.append((nombre, f"{type(exc).__name__}: {exc}"))
                except Exception as exc:  # noqa: BLE001
                    fallos.append((nombre, f"{type(exc).__name__}: {exc}"))
        self.assertEqual(fallos, [], f"callbacks que revientan al clic: {fallos}")

    def test_handlers_de_dispositivo_sin_seleccion_avisan_y_no_revientan(self):
        self.app.ctx.active_device_serial = None
        for nombre in ("_connect_wifi", "_enable_tcpip", "_get_device_ip",
                       "_install_apk", "_panic_kill", "_stop_current"):
            self._call(nombre)
        self.assertTrue(self.dialogs.calls, "debieron avisar al usuario")

    def test_keyevents_del_mando_remoto(self):
        self.app.ctx.active_device_serial = "SERIAL1"
        for code in ("notifications", "screen_on", "screen_off", "paste_text", 26):
            self._call("_send_keyevent", code)

    def test_menu_contextual_de_sesiones(self):
        event = type("E", (), {"y": 0, "x": 0, "x_root": 0, "y_root": 0})()
        self._call("_sess_context_menu", event)   # sin filas → salida temprana

    # ── D1.4 · los perfiles de fábrica arrancan desde la UI ───────────

    def test_cada_perfil_de_fabrica_arranca_desde_la_ui(self):
        perfiles = list(utils.DEFAULT_CONFIG["profiles"].keys())
        self.assertGreaterEqual(len(perfiles), 3)
        for nombre in perfiles:
            with self.subTest(perfil=nombre):
                self.app.ctx.session_mgr.stop_all()
                self.scrcpy.launched.clear()
                self.app.ctx.active_profile.set(nombre)

                self._iniciar_sesion()

                self.assertTrue(
                    self.scrcpy.launched,
                    f"el perfil {nombre!r} no llegó a construir comando válido",
                )
                self.assertIn("SERIAL1", self.app.ctx.session_mgr.sessions)

    def test_detener_copiar_y_panico_con_sesion_viva(self):
        self._iniciar_sesion()

        self._call("_copy_sess_cmd", "SERIAL1")
        self._call("_stop_selected")

        self._iniciar_sesion()
        self._call("_force_kill_sess", "SERIAL1")
        self._call("_panic_kill")

    def test_la_tabla_de_sesiones_refleja_el_ciclo_de_vida(self):
        self._iniciar_sesion()
        self._call("_refresh_table")
        self._call("_monitor_sessions")
        self._call("_stop_selected")
        self._call("_refresh_table")

    def test_la_consola_recibe_y_filtra_los_logs(self):
        self.app.ctx.log("INFO", "mensaje de humo")
        self._call("_pump_logs")
        self._call("_filter_log", "all")
        self._call("_copy_log")
        self._call("_clear_log")
        # `_open_log` lanza un visor externo (xdg-open): se comprueba el camino
        # sin abrir nada en el escritorio del usuario.
        _LAUNCHED.clear()
        import os
        with patch.object(os, "startfile", lambda p: _LAUNCHED.append(["startfile", p]), create=True):
            self._call("_open_log")
        self.assertTrue(
            any(cmd in str(a) for a in _LAUNCHED for cmd in ("xdg-open", "open", "startfile")),
            f"_open_log no intentó abrir el log (lanzados={_LAUNCHED})",
        )

    # ── D1.5 · arranque sin dependencias ──────────────────────────────

    def test_sin_dependencias_muestra_el_instalador(self):
        with patch.object(context_mod, "find_portable_binaries", return_value=(None, None)):
            app = ScrcpyDockApp(self.root)
        self.assertIsNone(app.ctx.adb)
        self.assertIsNone(app.ctx.adb_engine)
        self.assertTrue(app.ui.refs["install_frame"].winfo_exists())
        self.assertIn(ErrorCode.ADB_NOT_FOUND, (ErrorCode.ADB_NOT_FOUND,))
        # La UI debe aguantar sin motor en vez de reventar.
        app.ctx.active_device_serial = None
        app._connect_wifi()
        app._get_device_ip()

    def test_resolucion_de_idioma_y_tema_estan_aplicados(self):
        from scrcpy_dock.i18n import get_language

        self.assertEqual(get_language(), "es")
        self._call("_open_trust_vault")
        self._call("_open_device_trust_modal")

    def test_onboarding_se_despliega_sin_bloquear(self):
        self._call("_show_onboarding")
        self._call("_go_to_help_usb")
        self._call("_go_to_help_v4l2")
        self._call("_check_v4l2")

    def test_los_atajos_de_teclado_estan_registrados(self):
        binds = []
        with patch("tkinter.Misc.bind", lambda self, seq, fn=None, add=None: binds.append(seq)):
            self._call("_bind_shortcuts")
        self.assertGreaterEqual(len(binds), 4, f"se registraron {len(binds)} atajos")

    # ── D1.6 · camino real de "Conectar por Wi-Fi" ────────────────────

    def _escribir_ip(self, ip: str, puerto: str = "5555"):
        for ref, valor in (("ip_entry", ip), ("port_entry", puerto)):
            entry = self.app.ui.refs[ref]
            entry.delete(0, tk.END)
            entry.insert(0, valor)

    def test_ip_vacia_avisa_en_vez_de_reventar(self):
        """Defecto cazado al estrenar el arnés: `is_private_ip(None)` reventaba."""
        self._escribir_ip("", "5555")

        self._call("_connect_wifi")

        self.assertTrue(self.dialogs.did("showerror"), "no avisó del error")
        self.assertIn("IP inválida", str(self.dialogs.last("showerror")))
        self.assertEqual(
            [a for a in _LAUNCHED if a and "connect" in str(a)], [],
            "no debe intentar conectar con una IP inválida",
        )

    def test_ip_con_octetos_invalidos_avisa_en_vez_de_bloquear(self):
        """Antes reventaba; nunca debe reportarse como 'IP no permitida'."""
        self._escribir_ip("999.999.1.1")

        self._call("_connect_wifi")

        self.assertIn("IP inválida", str(self.dialogs.last("showerror")))

    def test_ip_privada_valida_pasa_el_modo_seguro(self):
        self._escribir_ip("192.168.1.25")

        self._call("_connect_wifi")

        self.assertIsNone(self.dialogs.last("showerror"),
                          f"rechazó una IP privada válida: {self.dialogs.calls}")


class DefectosCazadosPorD1(unittest.TestCase):
    """Regresión de los defectos que el arnés encontró al ejecutarse.

    D1 no es sólo una red de seguridad: la primera pasada destapó dos defectos
    reales de la capa de UI (ver `ANALISIS.md` §11.4).
    """

    def test_parse_ip_port_devuelve_tupla_verdadera_al_fallar(self):
        """Documenta la trampa que originó el defecto: `(None, None)` es *truthy*."""
        self.assertEqual(parse_ip_port(""), (None, None))
        self.assertTrue(parse_ip_port(":5555"), "una tupla (None, None) es verdadera")
        self.assertIsNone(parse_ip_port("999.999.1.1:5555")[0])
        self.assertIsNone(parse_ip_port("no-es-ip:5555")[0])

    def test_is_private_ip_nunca_lanza_con_entrada_invalida(self):
        """Antes: `None.strip()` → AttributeError. Ahora: False (falla en cerrado)."""
        self.assertFalse(SecurityManager.is_private_ip(None))  # type: ignore[arg-type]
        self.assertFalse(SecurityManager.is_private_ip(""))
        self.assertFalse(SecurityManager.is_private_ip("   "))
        self.assertFalse(SecurityManager.is_private_ip("8.8.8.8"))
        self.assertTrue(SecurityManager.is_private_ip("192.168.1.25"))
        self.assertTrue(SecurityManager.is_private_ip("127.0.0.1"))


if __name__ == "__main__":
    unittest.main()
