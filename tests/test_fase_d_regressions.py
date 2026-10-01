"""Pruebas de la FASE D (segunda parte): demolición de la deuda ciclomática.

Cierra los tres últimos bloques Rank D del repositorio:

  · `ProfileService.sanitize_profile_dict`  CC 28 → 2
  · `ScrcpyDockApp._exit`                   CC 23 → 1
  · `ScrcpyDockApp._on_dev_select`          CC 21 → 2

Incluye un **guardián permanente**: ninguna función del paquete puede volver a
caer en rank D/E/F. Ejecutable con:
    python -m unittest discover -s tests
"""
from __future__ import annotations

import ast
import inspect
import io
import os
import sys
import tempfile
import tkinter as tk
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

import scrcpy_dock
import scrcpy_dock.main as main_mod
from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.core.scrcpy_engine import ScrcpyEngine
from scrcpy_dock.domain.models import (
    Codec,
    ConnectionType,
    Device,
    DeviceCapabilities,
    DeviceState,
    SessionConfig,
)
from scrcpy_dock.errors import ErrorCode
from scrcpy_dock.main import ScrcpyDockApp
from scrcpy_dock.managers import DeviceManager, SessionManager
from scrcpy_dock.services.profile_service import ProfileService

from tests.ui_harness import app_en_prueba


def _textos_de(widget) -> list:
    """Todos los textos de las etiquetas de un árbol de widgets."""
    textos = []
    for hijo in widget.winfo_children():
        if isinstance(hijo, tk.Label):
            textos.append(str(hijo.cget("text")))
        textos.extend(_textos_de(hijo))
    return textos


# ─────────────────────────────────────────────────────────────────────────────
# Guardián de complejidad (Ley 7): sin bloques D/E/F en todo el paquete
# ─────────────────────────────────────────────────────────────────────────────

# Bloques que TODAVÍA superan CC 10 (Ley 7 pide ≤ 10), por `archivo método`. Es
# una lista blanca exacta, no un tope: cualquier bloque nuevo por encima de 10
# hace fallar la prueba con su nombre, sin esperar a que la deuda se acumule.
# Se compara sin número de línea a propósito: la línea cambia con cualquier
# edición del archivo y convertiría el guardián en ruido.
#
# Todos los bloques de deuda ciclomática han sido demolidos.
# La lista de bloques > 10 es ahora exactamente CERO (0) bloques.
BLOQUES_PENDIENTES: list[str] = []

class _McCabeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_IfExp(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_comprehension(self, node):
        self.complexity += 1 + len(node.ifs)
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)


def _obtener_bloques_cc(codigo: str):
    """Extrae bloques de funciones y métodos con su CC (compatible con radon)."""
    try:
        from radon.complexity import cc_visit
        from radon.visitors import Function
        return [b for b in cc_visit(ast.parse(codigo)) if isinstance(b, Function)]
    except ImportError:
        pass

    class FunctionBlock:
        def __init__(self, name, lineno, complexity):
            self.name = name
            self.lineno = lineno
            self.complexity = complexity

    tree = ast.parse(codigo)
    bloques = []

    def _medir(fn_node):
        v = _McCabeVisitor()
        for child in ast.iter_child_nodes(fn_node):
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                v.visit(child)
        return FunctionBlock(fn_node.name, fn_node.lineno, v.complexity)

    for item in tree.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bloques.append(_medir(item))
        elif isinstance(item, ast.ClassDef):
            for m in item.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    bloques.append(_medir(m))
    return bloques


class TestComplejidadSinBloquesD(unittest.TestCase):
    """Evita que la deuda ciclomática demolidа en la Fase D vuelva a crecer."""

    def test_ningun_bloque_alcanza_rank_d(self):
        peores, detalle = [], []
        raiz = Path(scrcpy_dock.__file__).parent
        for archivo in raiz.rglob("*.py"):
            rel = archivo.relative_to(raiz).as_posix()
            for bloque in _obtener_bloques_cc(archivo.read_text(encoding="utf-8")):
                if bloque.complexity <= 10:
                    continue
                peores.append(f"{rel} {bloque.name}")
                detalle.append(f"{rel}:{bloque.lineno} {bloque.name} CC={bloque.complexity}")

        # Umbral de la Ley 7 (≤ 10): el rank D empieza en 21. Se exige el umbral
        # duro (0 bloques > 10) para garantizar Rank A/B en todo el proyecto.
        self.assertEqual(
            [d for d in detalle if int(d.rsplit("CC=", 1)[1]) > 20], [],
            f"bloques Rank D o peor: {detalle}",
        )
        # La lista de bloques > 10 debe ser exactamente CERO (0) bloques.
        self.assertEqual(
            sorted(peores), sorted(BLOQUES_PENDIENTES),
            f"la lista de bloques > 10 cambió: {detalle}",
        )

    def test_los_tres_objetivos_de_la_fase_de_quedaron_planos(self):
        objetivos = {
            ("scrcpy_dock/services/profile_service.py", "sanitize_profile_dict"): 10,
            ("scrcpy_dock/main.py", "_exit"): 10,
            ("scrcpy_dock/main.py", "_on_dev_select"): 10,
        }
        for archivo in Path(scrcpy_dock.__file__).parent.rglob("*.py"):
            clave_rel = str(archivo.relative_to(Path(scrcpy_dock.__file__).parent.parent))
            for bloque in _obtener_bloques_cc(archivo.read_text(encoding="utf-8")):
                tope = objetivos.get((clave_rel, bloque.name))
                if tope is not None:
                    self.assertLessEqual(
                        bloque.complexity, tope,
                        f"{bloque.name} sigue en CC={bloque.complexity}",
                    )


# ─────────────────────────────────────────────────────────────────────────────
# sanitize_profile_dict descompuesto
# ─────────────────────────────────────────────────────────────────────────────

class TestSanitizeProfileDictDescompuesto(unittest.TestCase):

    def test_es_un_orquestador_sin_logica_propia(self):
        """El método sólo compone: toda la validación vive en los ayudantes."""
        import inspect

        fuente = inspect.getsource(ProfileService.sanitize_profile_dict)
        for nombre in ("_sanitize_codec", "_sanitize_bitrate", "_sanitize_resolution",
                       "_sanitize_video_source", "_sanitize_fps", "_sanitize_audio_source",
                       "_sanitize_flag", "_sanitize_schema_version"):
            self.assertTrue(hasattr(ProfileService, nombre), f"falta {nombre}")
            self.assertIn(nombre, fuente, f"{nombre} no se invoca desde el orquestador")
        # Sin ramas de validación propias: sólo el guard de entrada no-dict.
        self.assertLess(len(fuente.splitlines()), 40)

    def test_devuelve_exactamente_las_nueve_claves_conocidas(self):
        out = ProfileService.sanitize_profile_dict({"evil": 1, "port": 9, "name": "x"})
        self.assertEqual(
            set(out),
            {"codec", "bit_rate", "resolution", "video_source", "max_fps",
             "audio_source", "turn_screen_off", "stay_awake", "schema_version"},
        )

    def test_entrada_no_dict_no_revienta(self):
        for basura in (None, [], "texto", 42):
            with self.subTest(entrada=basura):
                out = ProfileService.sanitize_profile_dict(basura)  # type: ignore[arg-type]
                self.assertEqual(out["codec"], "h264")
                self.assertEqual(out["resolution"], "1080")

    def test_codec_acepta_el_enum_y_normaliza_mayusculas(self):
        self.assertEqual(ProfileService._sanitize_codec(Codec.H265), "h265")
        self.assertEqual(ProfileService._sanitize_codec("H265"), "h265")
        self.assertEqual(ProfileService._sanitize_codec("vp9"), "h264")
        self.assertEqual(ProfileService._sanitize_codec(None), "h264")

    def test_bitrate_rechaza_bool(self):
        """`bool` es subclase de `int`: True no puede convertirse en 1 bps."""
        self.assertEqual(ProfileService._sanitize_bitrate(True), 8_000_000)
        self.assertEqual(ProfileService._sanitize_bitrate(False), 8_000_000)
        self.assertEqual(ProfileService._sanitize_bitrate("4000000"), 4_000_000)
        self.assertEqual(ProfileService._sanitize_bitrate(None), 8_000_000)

    def test_resolucion_rechaza_bool(self):
        """Corregido en la Fase D: antes `True` se colaba como resolución 'True'."""
        self.assertEqual(ProfileService._sanitize_resolution(True), "1080")
        self.assertEqual(ProfileService._sanitize_resolution(False), "1080")
        self.assertEqual(ProfileService._sanitize_resolution("  720  "), "720")
        self.assertEqual(ProfileService._sanitize_resolution(1080), "1080")
        self.assertEqual(ProfileService._sanitize_resolution(""), "1080")
        self.assertEqual(ProfileService._sanitize_resolution("x" * 21), "1080")

    def test_video_source_se_infiere_de_extra_args(self):
        self.assertEqual(
            ProfileService._sanitize_video_source(None, "--video-source=camera"), "camera",
        )
        self.assertEqual(ProfileService._sanitize_video_source("CAMERA", None), "camera")
        self.assertEqual(ProfileService._sanitize_video_source("webcam", None), "display")

    def test_fps_rechaza_bool_y_fuera_de_rango(self):
        self.assertIsNone(ProfileService._sanitize_fps(True))
        self.assertIsNone(ProfileService._sanitize_fps(500))
        self.assertIsNone(ProfileService._sanitize_fps("no"))
        self.assertEqual(ProfileService._sanitize_fps("30"), 30.0)

    def test_flags_ausentes_son_true(self):
        self.assertIs(ProfileService._sanitize_flag(None), True)
        self.assertIs(ProfileService._sanitize_flag(False), False)
        self.assertIs(ProfileService._sanitize_flag("yes"), True)

    def test_schema_version_minimo_uno(self):
        self.assertEqual(ProfileService._sanitize_schema_version(True), 1)
        self.assertEqual(ProfileService._sanitize_schema_version(0), 1)
        self.assertEqual(ProfileService._sanitize_schema_version(2), 2)
        self.assertEqual(ProfileService._sanitize_schema_version(None), 1)


# ─────────────────────────────────────────────────────────────────────────────
# _exit y _on_dev_select descompuestos (app mínima, sin Tk real)
# ─────────────────────────────────────────────────────────────────────────────

def _stub_app(**overrides):
    """Sustituto de ScrcpyDockApp con lo mínimo que tocan los handlers.

    Se enlazan los métodos reales del handler bajo prueba (no dobles): lo que se
    verifica es la descomposición —que las fases se invoquen y se aíslen—, no la
    UI real, que ya cubre el arnés de humo de D1.
    """
    app = types.SimpleNamespace()
    app.ctx = types.SimpleNamespace(
        device_mgr=MagicMock(),
        session_mgr=MagicMock(),
        security_mgr=MagicMock(),
        adb="/usr/bin/adb",
        cfg={"device_associations": {}},
        state_machine=MagicMock(),
        select_device=MagicMock(),
        save_current_config=MagicMock(),
        active_profile=MagicMock(),
    )
    app.ctx.device_mgr.devices = []
    app.ctx.security_mgr.is_trusted_device.return_value = False
    app.ctx.security_mgr.get_device_alias.return_value = "Android"
    app.ctx.profile_mgr = MagicMock()
    app.ctx.profile_mgr.get_profiles.return_value = {}
    app.ui = types.SimpleNamespace(refs={})
    app.root = MagicMock()
    app.tray_icon = None
    app.single_instance = None

    for nombre in (
        # fases de _exit
        "_shutdown_step", "_stop_device_tracking", "_apply_security_lockdown",
        "_terminate_active_sessions", "_persist_window_state", "_release_tray",
        "_release_single_instance", "_destroy_root",
        # ayudantes de _on_dev_select
        "_resolve_selected_device", "_parse_device_row", "_update_device_badges",
        "_device_state", "_set_device_info", "_apply_device_state",
        "_announce_online_device", "_apply_device_profile_association",
    ):
        atributo = inspect.getattr_static(ScrcpyDockApp, nombre)
        if isinstance(atributo, staticmethod):
            # Ya recibe (label, action): no debe quedar enlazado al stub.
            setattr(app, nombre, atributo.__func__)
        else:
            setattr(app, nombre, atributo.__get__(app))

    app.__dict__.update(overrides)
    return app


class TestExitDescompuesto(unittest.TestCase):

    def test_los_siete_pasos_del_cierre_existen(self):
        for nombre in ("_stop_device_tracking", "_apply_security_lockdown",
                       "_terminate_active_sessions", "_persist_window_state",
                       "_release_tray", "_release_single_instance", "_destroy_root"):
            self.assertTrue(hasattr(ScrcpyDockApp, nombre), f"falta {nombre}")

    def test_cierra_sesiones_y_guarda_geometria(self):
        app = _stub_app()
        with patch.object(main_mod.os, "_exit") as salir:
            ScrcpyDockApp._exit(app)

        app.ctx.device_mgr.stop_tracking.assert_called_once()
        app.ctx.session_mgr.stop_all.assert_called_once()
        app.ctx.save_current_config.assert_called_once()
        app.root.destroy.assert_called_once()
        salir.assert_called_once_with(0)

    def test_un_paso_que_falla_no_aborta_el_cierre(self):
        """Antes, un fallo en el tracker impedía cerrar sesiones y guardar."""
        app = _stub_app()
        app.tray_icon = MagicMock()
        app.tray_icon.stop.side_effect = RuntimeError("tray muerto")

        with patch.object(main_mod.os, "_exit") as salir:
            ScrcpyDockApp._exit(app)

        app.tray_icon.stop.assert_called_once()
        app.ctx.session_mgr.stop_all.assert_called_once()   # el cierre siguió
        app.ctx.save_current_config.assert_called_once()
        app.root.destroy.assert_called_once()
        salir.assert_called_once_with(0)

    def test_cierre_sin_contexto_ni_root_no_revienta(self):
        app = _stub_app()
        del app.ctx, app.root          # app a medio construir
        with patch.object(main_mod.os, "_exit") as salir:
            ScrcpyDockApp._exit(app)
        salir.assert_called_once_with(0)

    def test_lockdown_solo_con_auto_bloqueo_y_seriales(self):
        app = _stub_app()
        app.ctx.security_mgr.is_auto_lockdown_enabled = False
        ScrcpyDockApp._apply_security_lockdown(app)
        main_mod.SecurityManager.lockdown_all_devices = MagicMock()

        app.ctx.device_mgr.devices = [("SERIAL1", "V2314", "ok")]
        app.ctx.security_mgr.is_auto_lockdown_enabled = True
        with patch.object(main_mod.SecurityManager, "lockdown_all_devices") as lockdown:
            ScrcpyDockApp._apply_security_lockdown(app)
        lockdown.assert_called_once_with("/usr/bin/adb", ["SERIAL1"])


class TestOnDevSelectDescompuesto(unittest.TestCase):

    def test_los_ayudantes_existen(self):
        for nombre in ("_resolve_selected_device", "_parse_device_row",
                       "_update_device_badges", "_device_state", "_set_device_info",
                       "_apply_device_state", "_announce_online_device",
                       "_apply_device_profile_association"):
            self.assertTrue(hasattr(ScrcpyDockApp, nombre), f"falta {nombre}")

    @staticmethod
    def _fila(serial: str, model: str, state: str, alias: str = "") -> str:
        """Formato EXACTO que escribe `_update_devs_ui` para cada estado."""
        if state == "ok":
            return f"  🟢 🛡️  {alias or model}  ({serial})"
        if state == "unauth":
            return f"  🟠 ⚠️  {serial}  (Sin autorizar en pantalla)"
        if state == "offline":
            return f"  🔴 ⚠️  {serial}  (Desconectado / Offline)"
        return f"  ⚫  {serial}  [{state}]"

    def _app_con_listbox(self, dispositivos, seleccion=(0,), alias=""):
        """Monta el listbox como lo deja `_update_devs_ui` (filas + registro)."""
        app = _stub_app()
        tree = MagicMock()
        tree.curselection.return_value = seleccion
        tree.get.side_effect = lambda i: self._fila(*dispositivos[i], alias=alias)
        app.ui.refs["dev_listbox"] = tree
        app._devices_shown = list(dispositivos)
        app._on_tab_changed = MagicMock()
        app._hint = MagicMock()
        app.ctx.device_mgr.devices = list(dispositivos)
        return app

    def test_sin_seleccion_no_hace_nada(self):
        app = self._app_con_listbox([("HWY9", "V2314", "ok")], seleccion=())
        app.ctx.security_mgr.is_trusted_device.reset_mock()

        ScrcpyDockApp._on_dev_select(app)

        app.ctx.security_mgr.is_trusted_device.assert_not_called()
        app.ctx.select_device.assert_not_called()

    def test_dispositivo_confiado_y_operativo(self):
        app = self._app_con_listbox([("HWY9", "V2314", "ok")], alias="Mi Vivo")
        app.ctx.security_mgr.is_trusted_device.return_value = True
        app.ctx.security_mgr.get_device_alias.return_value = "Mi Vivo"

        ScrcpyDockApp._on_dev_select(app)

        app.ctx.select_device.assert_called_once_with("HWY9", "Mi Vivo (HWY9)")
        app._hint.assert_called_once()
        app._on_tab_changed.assert_called_once()

    # ── P3.24: el serial no se puede leer de la etiqueta ──────────────

    def test_el_serial_no_sobrevive_en_las_filas_de_estado_anomalo(self):
        """Documenta la causa raíz: el paréntesis no siempre lleva el serial."""
        from scrcpy_dock.utils import _extract_serial

        self.assertEqual(_extract_serial(self._fila("HWY9", "V2314", "ok", "Mi Vivo")), "HWY9")
        # Aquí el paréntesis lleva un mensaje, no el serial:
        self.assertEqual(
            _extract_serial(self._fila("HWY9", "V2314", "unauth")),
            "Sin autorizar en pantalla",
        )
        self.assertEqual(
            _extract_serial(self._fila("HWY9", "V2314", "offline")),
            "Desconectado / Offline",
        )

    def test_resuelve_el_serial_correcto_en_estados_anomalos(self):
        for state in ("unauth", "offline", "other"):
            with self.subTest(estado=state):
                app = self._app_con_listbox([("HWY9", "V2314", state)])
                self.assertEqual(
                    ScrcpyDockApp._resolve_selected_device(app, None), ("HWY9", "V2314"),
                )

    def test_dispositivo_no_autorizado_pasa_a_fault(self):
        app = self._app_con_listbox([("HWY9", "V2314", "unauth")])

        ScrcpyDockApp._on_dev_select(app)

        codigo = app.ctx.state_machine.set_fault.call_args.args[1]
        self.assertEqual(codigo, ErrorCode.DEVICE_UNAUTHORIZED)
        app.ctx.select_device.assert_called_once_with("HWY9", "Android (HWY9)")

    def test_dispositivo_offline_pasa_a_fault(self):
        app = self._app_con_listbox([("HWY9", "V2314", "offline")])

        ScrcpyDockApp._on_dev_select(app)

        codigo = app.ctx.state_machine.set_fault.call_args.args[1]
        self.assertEqual(codigo, ErrorCode.DEVICE_OFFLINE)

    def test_los_avisos_anomalos_llegan_al_panel(self):
        for state, esperado in (("unauth", "Acepta el permiso"),
                                ("offline", "desconectado")):
            with self.subTest(estado=state):
                app = self._app_con_listbox([("HWY9", "V2314", state)])
                panel = MagicMock()
                app.ui.refs["dev_info_lbl"] = panel

                ScrcpyDockApp._on_dev_select(app)

                texto = panel.config.call_args.kwargs["text"]
                self.assertIn(esperado, texto)

    def test_respaldo_para_filas_ajenas_al_registro(self):
        """Filas que no vienen de `_update_devs_ui` se interpretan por texto."""
        app = _stub_app()
        tree = MagicMock()
        tree.curselection.return_value = (0,)
        tree.get.return_value = "  🟢 🛡️  Mi Vivo  (HWY9)"
        app.ui.refs["dev_listbox"] = tree
        app._devices_shown = []

        self.assertEqual(
            ScrcpyDockApp._resolve_selected_device(app, None), ("HWY9", "Mi Vivo"),
        )

    def test_los_tres_indicadores_de_confianza_se_pintan_igual(self):
        app = _stub_app()
        badges = {}
        for key in ("action_trust_lbl", "ctrl_trust_lbl", "simple_trust_lbl"):
            badges[key] = MagicMock()
            app.ui.refs[key] = badges[key]

        ScrcpyDockApp._update_device_badges(app, True)

        for key, widget in badges.items():
            with self.subTest(indicador=key):
                widget.config.assert_called_once()
                self.assertIn("Confiable", widget.config.call_args.kwargs["text"])

    def test_asociacion_de_perfil_solo_si_existe(self):
        app = _stub_app()
        app.ctx.cfg["device_associations"] = {"HWY9": "Fantasma"}
        app.ctx.profile_mgr.get_profiles.return_value = {"Otro": {}}

        ScrcpyDockApp._apply_device_profile_association(app, "HWY9")
        app.ctx.active_profile.set.assert_not_called()

        app.ctx.profile_mgr.get_profiles.return_value = {"Fantasma": {}}
        ScrcpyDockApp._apply_device_profile_association(app, "HWY9")
        app.ctx.active_profile.set.assert_called_once_with("Fantasma")

    def test_el_combo_simple_tambien_resuelve_serial(self):
        app = _stub_app()
        combo = MagicMock()
        combo.get.return_value = "Mi Vivo (HWY9)"
        app.ui.refs["simple_dev_combo"] = combo
        event = types.SimpleNamespace(widget=combo)

        self.assertEqual(
            ScrcpyDockApp._resolve_selected_device(app, event), ("HWY9", "Mi Vivo"),
        )

    def test_combo_con_texto_vacio_devuelve_none(self):
        app = _stub_app()
        combo = MagicMock()
        combo.get.return_value = "Sin dispositivo"
        app.ui.refs["simple_dev_combo"] = combo
        event = types.SimpleNamespace(widget=combo)

        self.assertIsNone(ScrcpyDockApp._resolve_selected_device(app, event))


# ─────────────────────────────────────────────────────────────────────────────
# La red de los 7 refactores de complejidad: 4 mutaciones que sobrevivían
# ─────────────────────────────────────────────────────────────────────────────
#
# Al descomponer los 7 bloques con cobertura se comprobó la red con mutaciones
# deliberadas (`mutar_los_siete.py`): 4 de 8 sobrevivieron. Es decir, esos cuatro
# métodos tenían **cobertura de líneas pero no anclaje de comportamiento**: se
# podía invertir el conmutador de vista, cambiar el sello de confianza, comerse
# un chip o dejar de cortar la sesión del tracker sin que fallara nada.
#
# Cada prueba de aquí mata una de esas mutaciones. Cobertura ≠ red.

class TestRedDeCaracterizacionDeLosRefactores(unittest.TestCase):
    """Ancla los comportamientos que la cobertura no sujetaba (medido por mutación)."""

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
        self.sitio = app_en_prueba(self.root)
        self.app = self.sitio.app

    def tearDown(self):
        if getattr(self, "sitio", None) is not None:
            self.sitio.cerrar()

    # Mutación que sobrevivía: invertir las ramas de `_toggle_view`.

    def test_el_conmutador_de_vista_cambia_de_modo_y_vuelve(self):
        app = self.app
        app.is_advanced_view = True

        app._toggle_view()

        self.assertFalse(app.is_advanced_view, "el primer Ctrl+M debe pasar a Modo Compacto")
        self.assertTrue(getattr(app, "_saved_geometry", ""),
                        "debe recordar la geometría de la Vista Completa")

        app._toggle_view()

        self.assertTrue(app.is_advanced_view, "el segundo Ctrl+M debe volver a la Vista Completa")

    # Mutación que sobrevivía: cambiar el sello de confianza.

    def test_el_sello_de_confianza_dice_confiable_o_no_verificado(self):
        app = self.app
        app.ctx.active_device_serial = "HWY9"

        with patch.object(app.ctx.security_mgr, "is_trusted_device", return_value=True):
            app._on_tab_changed()
        self.assertEqual(app.ui.refs["action_trust_lbl"].cget("text"), " [🛡️ Confiable]",
                         "un dispositivo de confianza debe llevar el sello verde")

        with patch.object(app.ctx.security_mgr, "is_trusted_device", return_value=False):
            app._on_tab_changed()
        self.assertEqual(app.ui.refs["action_trust_lbl"].cget("text"), " [⚠️ No Verificado]",
                         "un dispositivo sin verificar debe avisarse, no callarse")

        app.ctx.active_device_serial = None
        app._on_tab_changed()
        self.assertEqual(app.ui.refs["action_trust_lbl"].cget("text"), "",
                         "sin dispositivo no hay sello que mostrar")

    def test_las_etiquetas_de_dispositivo_siguen_a_la_variable_compartida(self):
        """Las etiquetas de dispositivo y el combo simple comparten `ctx.active_device`.

        Se caracteriza el camino que el usuario ve de verdad: la variable que mueve
        `ctx.select_device`. El `config(text=…)` de `_on_tab_changed` sobre estas
        dos etiquetas es **inerte** (están construidas con `textvariable`, que gana),
        un resto que viene de antes del refactor.
        """
        app = self.app
        variable = str(app.ui.refs["simple_dev_combo"].cget("textvariable"))
        for ref in ("action_device_lbl", "ctrl_device_lbl"):
            self.assertEqual(str(app.ui.refs[ref].cget("textvariable")), variable,
                             f"{ref} debe seguir atada a la variable compartida")

        app.ctx.select_device("HWY9", "Mi Vivo (HWY9)")
        for ref in ("action_device_lbl", "ctrl_device_lbl"):
            self.assertEqual(app.ui.refs[ref].cget("text"), "Mi Vivo (HWY9)")
        self.assertEqual(app.ui.refs["simple_dev_combo"].get(), "Mi Vivo (HWY9)")

        app.ctx.select_device(None, "Sin dispositivo")
        self.assertEqual(app.ui.refs["action_device_lbl"].cget("text"), "Sin dispositivo")

    # Mutación que sobrevivía: comerse el chip condicional del perfil.

    def test_los_chips_del_perfil_incluyen_los_condicionales(self):
        from scrcpy_dock.ui_widgets import ProfileChipsView

        base = {"max_size": "1920", "max_fps": "60", "bitrate": "8M", "video_codec": "h264"}
        vista = ProfileChipsView(self.root)

        vista.set_profile("Perfil", dict(base))
        textos = _textos_de(vista)
        self.assertNotIn("🔑 EMUI Keyevent", textos, "sin el flag no debe aparecer el chip EMUI")
        self.assertIn("📺 Resolución", textos)

        vista.set_profile("Perfil", {**base, "force_screen_off_keyevent": True})
        self.assertIn("🔑 EMUI Keyevent", _textos_de(vista),
                      "con force_screen_off_keyevent el chip EMUI es obligatorio")

        vista.set_profile("Perfil", {**base, "no_video": True})
        self.assertIn("🎙️ Solo Audio", _textos_de(vista))

        vista.set_profile("Perfil", {**base, "extra_args": "--camera-id=1"})
        self.assertIn("--camera-id=1", _textos_de(vista))

        vista.destroy()

    def test_sin_perfil_avisa_en_vez_de_quedarse_vacio(self):
        from scrcpy_dock.ui_widgets import ProfileChipsView

        vista = ProfileChipsView(self.root)
        vista.set_profile("", {})
        self.assertTrue(any("Selecciona un perfil" in t for t in _textos_de(vista)))
        vista.destroy()

    # Mutación que sobrevivía: una cabecera truncada ya no cortaba la sesión.

    def test_cabecera_truncada_corta_la_sesion_del_tracker(self):
        """Con cabecera truncada NO se reintenta: si se reintentara, procesaría lo siguiente."""
        from tests.test_adb_engine_hardening import _FakeTrackerProc, _tracker

        payload = "HWY9\tdevice\n"
        # Basura truncada + un evento válido detrás: si el tracker reintentara en
        # vez de cortar, acabaría notificando ese dispositivo.
        proc = _FakeTrackerProc(
            chunks=["00", f"{len(payload):04x}", payload, ""], returncode=0,
        )
        tracker = _tracker()

        with patch("subprocess.Popen", return_value=proc):
            tracker._run_once()

        self.assertEqual(tracker.cambios, [],
                         "una cabecera truncada debe cortar la sesión, no reintentar")


# ─────────────────────────────────────────────────────────────────────────────
# La red de los 2 bloques más peligrosos: `main()` (CC 15) y `_toggle_scene` (CC 18)
# ─────────────────────────────────────────────────────────────────────────────
#
# `main()` tenía 57 líneas de arranque que ninguna prueba ejecutaba (--install,
# --uninstall, --purge, instancia única). `_toggle_scene` tenía 11 sin cubrir y
# es el corazón operativo del producto. Se caracterizan ANTES de tocarlos.

class TestRedDeMain(unittest.TestCase):
    """`main()`: despacho de CLI y arranque de la GUI.

    No necesita display: son las únicas rutas de arranque que el CI headless
    puede ejercitar de verdad, y las que más silencio tenían.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        (self.raiz / "bin").mkdir()
        (self.raiz / "assets").mkdir()

        self.svc = MagicMock()
        self.svc.bin_dir = self.raiz / "bin"
        self.svc.assets_dir = self.raiz / "assets"
        self.svc.bin_symlink_path = self.raiz / "bin" / "MASV"
        self.svc.desktop_entry_path = self.raiz / "masv.desktop"
        self.svc.ensure_layout.return_value = OperationResult.ok(None, "layout listo")
        self.svc.write_desktop_entry.return_value = OperationResult.ok(None, "lanzador escrito")
        self.svc.uninstall.return_value = OperationResult.ok(None, "desinstalado")

    def _patch_installer(self):
        """`main()` importa `InstallerService` dentro de la rama: se parchea en su módulo."""
        return patch(
            "scrcpy_dock.services.installer_service.InstallerService",
            return_value=self.svc,
        )

    def _main(self, argv):
        """Ejecuta `main(argv)` y devuelve (código de salida, stdout)."""
        salida = io.StringIO()
        with redirect_stdout(salida):
            with self.assertRaises(SystemExit) as ctx:
                main_mod.main(argv)
        return ctx.exception.code, salida.getvalue()

    # ── --install ────────────────────────────────────────────────────────

    def test_install_congelado_copia_binario_y_icono(self):
        """Empaquetado (PyInstaller): el binario y el logo acaban en la carpeta gestionada."""
        origen = self.raiz / "MASV-real"
        origen.write_text("#!/bin/sh\n", encoding="utf-8")
        bundle = self.raiz / "bundle"
        (bundle / "assets").mkdir(parents=True)
        (bundle / "assets" / "logo.png").write_bytes(b"\x89PNG\r\n")

        with self._patch_installer(), \
                patch.object(sys, "frozen", True, create=True), \
                patch.object(sys, "executable", str(origen)), \
                patch.object(sys, "_MEIPASS", str(bundle), create=True):
            with redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    main_mod.main(["--install"])

        self.assertEqual(ctx.exception.code, 0)
        self.svc.ensure_layout.assert_called_once()
        copiado = self.svc.bin_dir / "MASV"
        self.assertTrue(copiado.exists(), "el binario debe quedar en la carpeta gestionada")
        self.assertTrue(copiado.stat().st_mode & 0o111, "el binario copiado debe ser ejecutable")

        destino, icono = self.svc.write_desktop_entry.call_args.args
        self.assertEqual(destino, copiado, "el lanzador debe apuntar al binario instalado")
        self.assertEqual(icono, self.svc.assets_dir / "logo.png")
        self.assertTrue((self.svc.assets_dir / "logo.png").exists(), "el logo debe copiarse")

    def test_install_sin_congelar_no_copia_nada(self):
        """Ejecutando desde el código fuente se registra el propio `argv[0]`."""
        with self._patch_installer():
            codigo, salida = self._main(["masv", "--install"])

        self.assertEqual(codigo, 0)
        self.assertIn("Instalación completada con éxito", salida)
        self.assertFalse((self.svc.bin_dir / "MASV").exists(), "sin congelar no se copia nada")
        destino, _ = self.svc.write_desktop_entry.call_args.args
        self.assertEqual(destino, Path(os.path.abspath("masv")).resolve())

    def test_install_con_copia_fallida_instala_el_original(self):
        """Si no se puede copiar el binario, la instalación sigue con el ejecutable actual."""
        with self._patch_installer(), \
                patch.object(sys, "frozen", True, create=True), \
                patch.object(sys, "executable", str(self.raiz / "MASV-real")), \
                patch("shutil.copy2", side_effect=OSError("disco lleno")):
            codigo, _ = self._main(["--install"])

        self.assertEqual(codigo, 0)
        destino, _ = self.svc.write_desktop_entry.call_args.args
        self.assertEqual(destino, Path(str(self.raiz / "MASV-real")).resolve())

    def test_install_fallido_sale_1(self):
        self.svc.write_desktop_entry.return_value = OperationResult.fail(
            ErrorCode.UNKNOWN_ERROR, "sin permisos",
        )
        with self._patch_installer():
            codigo, salida = self._main(["--install"])

        self.assertEqual(codigo, 1)
        self.assertIn("Error al instalar", salida)

    # ── --uninstall / --purge ────────────────────────────────────────────

    def test_uninstall_sin_purge_conserva_los_datos(self):
        with self._patch_installer():
            codigo, salida = self._main(["--uninstall"])

        self.assertEqual(codigo, 0)
        self.svc.uninstall.assert_called_once_with(purge=False)
        self.assertIn("Desinstalación completada con éxito", salida)
        self.assertNotIn("purgados", salida, "sin --purge no se pueden borrar los datos")

    def test_uninstall_con_purge_lo_dice(self):
        with self._patch_installer():
            codigo, salida = self._main(["--uninstall", "--purge"])

        self.assertEqual(codigo, 0)
        self.svc.uninstall.assert_called_once_with(purge=True)
        self.assertIn("purgados", salida)

    def test_uninstall_fallido_sale_1(self):
        self.svc.uninstall.return_value = OperationResult.fail(
            ErrorCode.UNKNOWN_ERROR, "enlace ocupado",
        )
        with self._patch_installer():
            codigo, salida = self._main(["--uninstall"])

        self.assertEqual(codigo, 1)
        self.assertIn("Error al desinstalar", salida)

    def test_install_tiene_prioridad_sobre_uninstall(self):
        """Con las dos banderas gana --install (se comprueba en este orden)."""
        with self._patch_installer():
            codigo, _ = self._main(["--install", "--uninstall"])

        self.assertEqual(codigo, 0)
        self.svc.uninstall.assert_not_called()

    def test_sin_argv_usa_sys_argv(self):
        with self._patch_installer(), patch.object(sys, "argv", ["masv", "--uninstall"]):
            codigo, _ = self._main(None)

        self.assertEqual(codigo, 0)
        self.svc.uninstall.assert_called_once_with(purge=False)

    # ── arranque de la GUI e instancia única ─────────────────────────────

    def test_arranque_normal_cuelga_la_app_del_root_y_libera(self):
        """La app se cuelga del `root` a propósito: si no, el GC se la lleva."""
        instancia = MagicMock()
        instancia.acquire.return_value = True
        root_falso, app_falsa = MagicMock(), MagicMock()

        with patch.object(main_mod, "SingleInstance", return_value=instancia), \
                patch.object(main_mod, "ScrcpyDockApp", return_value=app_falsa) as app_ctor, \
                patch("tkinter.Tk", return_value=root_falso):
            resultado = main_mod.main([])

        self.assertIsNone(resultado, "el arranque normal no devuelve código de error")
        self.assertIs(root_falso.masv_app, app_falsa, "la app debe colgar de root.masv_app")
        root_falso.mainloop.assert_called_once()
        self.assertIs(app_ctor.call_args.kwargs["single_instance"], instancia)
        instancia.release.assert_called_once()

    def test_segunda_instancia_avisa_y_sale_1(self):
        instancia = MagicMock()
        instancia.acquire.return_value = False

        with patch.object(main_mod, "SingleInstance", return_value=instancia), \
                patch.object(main_mod, "messagebox") as dialogs, \
                patch("tkinter.Tk") as tk_ctor:
            with self.assertRaises(SystemExit) as ctx:
                main_mod.main([])

        self.assertEqual(ctx.exception.code, 1)
        self.assertTrue(dialogs.showwarning.called, "debe avisar de que ya está abierta")
        tk_ctor.assert_not_called()
        instancia.release.assert_not_called()

    def test_si_el_bucle_de_eventos_revienta_se_libera_la_instancia(self):
        """El `finally` de la instancia única es lo que permite reabrir la app tras un fallo."""
        instancia = MagicMock()
        instancia.acquire.return_value = True
        root_falso = MagicMock()
        root_falso.mainloop.side_effect = KeyboardInterrupt()

        with patch.object(main_mod, "SingleInstance", return_value=instancia), \
                patch.object(main_mod, "ScrcpyDockApp", return_value=MagicMock()), \
                patch("tkinter.Tk", return_value=root_falso):
            with self.assertRaises(KeyboardInterrupt):
                main_mod.main([])

        instancia.release.assert_called_once()


class TestRedDeParchesPrevios(unittest.TestCase):
    """El keyevent 26 previo al arranque: función pura, sin Tk (corre en CI headless).

    El perfil de fábrica de OBS cumple **las dos** condiciones del `or`, así que
    cada camino se prueba por separado: con el perfil real, una mutación que
    anulara uno de los dos pasaría desapercibida (medido con el mutador).
    """

    def test_el_keyevent_previo_tiene_dos_motivos_independientes(self):
        previo = ScrcpyDockApp._necesita_keyevent_previo

        self.assertTrue(previo({"force_screen_off_keyevent": True}),
                        "el flag EMUI del perfil basta por sí solo")
        self.assertTrue(previo({"audio_source": "mic", "extra_args": "--no-video"}),
                        "el micrófono sin vídeo basta por sí solo")
        self.assertFalse(previo({"audio_source": "mic", "extra_args": "--max-fps=30"}),
                         "micrófono con vídeo no necesita el empujón")
        self.assertFalse(previo({"audio_source": "playback", "extra_args": ""}),
                         "un perfil normal no manda keyevent")
        self.assertFalse(previo({}), "un perfil vacío tampoco")


class TestRedDeToggleScene(unittest.TestCase):
    """`_toggle_scene()`: el camino de arranque/parada de la transmisión (CC 18)."""

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
        self.sitio = app_en_prueba(self.root)
        self.app = self.sitio.app
        self.app.ctx.security_mgr = MagicMock()
        self.app.ctx.security_mgr.is_safe_mode_enabled = False
        self.app.ctx.security_mgr.is_trusted_device.return_value = True
        self.app.ctx.security_mgr.get_device_alias.return_value = "Mi Vivo"
        self.ctx = self.app.ctx

    def tearDown(self):
        if getattr(self, "sitio", None) is not None:
            self.sitio.cerrar()

    def _con_arranque_espia(self, resultado=None):
        """Espía el arranque de sesión y devuelve el espía (para leer el perfil pasado).

        Ojo con `resultado or …`: un `OperationResult.fail` es falsy, así que el
        espía devolvería un éxito y la prueba del fallo no probaría nada.
        """
        if resultado is None:
            resultado = OperationResult.ok(None, "sesión viva")
        espia = MagicMock(return_value=resultado)
        self.ctx.session_mgr.start_scene = espia
        return espia

    # ── sin dispositivo / modo seguro ────────────────────────────────────

    def test_sin_dispositivo_avisa_y_lleva_a_la_pestana_dispositivo(self):
        self.ctx.active_device_serial = None
        self.app._nb = MagicMock()

        self.app._toggle_scene()

        self.assertTrue(self.sitio.dialogs.did("showwarning"))
        self.assertIn("Sin dispositivo", str(self.sitio.dialogs.last("showwarning")))
        self.app._nb.select.assert_called_once_with(2)   # pestaña Dispositivo

    def test_modo_seguro_cancelado_no_arranca(self):
        self.ctx.active_device_serial = "NUEVO"
        self.ctx.security_mgr.is_safe_mode_enabled = True
        self.ctx.security_mgr.is_trusted_device.return_value = False
        so_falso = MagicMock()
        so_falso.result = "cancel"
        espia = self._con_arranque_espia()

        with patch.object(main_mod, "TrustPromptModal", return_value=so_falso), \
                patch.object(main_mod, "save_config") as guardar:
            self.app._toggle_scene()

        guardar.assert_not_called()
        espia.assert_not_called()
        self.assertEqual(self.ctx.session_mgr.sessions, {}, "no puede arrancar sin aprobación")

    def test_modo_seguro_cerrado_sin_elegir_no_arranca(self):
        """Cerrar el aviso sin responder NO puede equivaler a confiar en el dispositivo."""
        self.ctx.active_device_serial = "NUEVO"
        self.ctx.security_mgr.is_safe_mode_enabled = True
        self.ctx.security_mgr.is_trusted_device.return_value = False
        so_falso = MagicMock()
        so_falso.result = None
        espia = self._con_arranque_espia()

        with patch.object(main_mod, "TrustPromptModal", return_value=so_falso), \
                patch.object(main_mod, "save_config") as guardar:
            self.app._toggle_scene()

        guardar.assert_not_called()
        espia.assert_not_called()

    def test_modo_seguro_aprobado_persiste_y_arranca(self):
        self.ctx.active_device_serial = "NUEVO"
        self.ctx.security_mgr.is_safe_mode_enabled = True
        self.ctx.security_mgr.is_trusted_device.return_value = False
        so_falso = MagicMock()
        so_falso.result = "trust"
        espia = self._con_arranque_espia()

        with patch.object(main_mod, "TrustPromptModal", return_value=so_falso), \
                patch.object(main_mod, "save_config") as guardar, \
                patch.object(self.app, "_on_dev_select") as refrescar:
            self.app._toggle_scene()

        guardar.assert_called_once_with(self.ctx.cfg)
        refrescar.assert_called_once()
        espia.assert_called_once()

    def test_sesion_viva_se_detiene_en_vez_de_rearrancar(self):
        self.ctx.active_device_serial = "HWY9"
        self.ctx.session_mgr.sessions["HWY9"] = MagicMock()
        espia = self._con_arranque_espia()

        with patch.object(self.app, "_stop_current") as detener:
            self.app._toggle_scene()

        detener.assert_called_once()
        espia.assert_not_called()

    # ── arranque: perfil, extras de Vista Simple y parches previos ───────

    def test_arranca_con_el_perfil_activo_y_la_llamada_queda_en_pendiente(self):
        self.ctx.active_device_serial = "HWY9"
        self.ctx.active_profile.set("🎮 Juego Rápido")
        espia = self._con_arranque_espia()

        self.app._toggle_scene()

        serial, nombre, datos, callback = espia.call_args.args
        self.assertEqual(serial, "HWY9")
        self.assertEqual(nombre, "🎮 Juego Rápido")
        self.assertIsInstance(datos, dict)
        self.assertEqual(datos, dict(self.ctx.cfg["profiles"]["🎮 Juego Rápido"]),
                         "el perfil debe llegar tal cual, sin mutar la config")
        self.assertTrue(callable(callback))
        self.assertEqual(self.ctx.state_machine.current_state.value, "PENDING")

    def test_vista_simple_fusiona_los_argumentos_extra(self):
        self.ctx.active_device_serial = "HWY9"
        self.ctx.active_profile.set("🎮 Juego Rápido")
        self.app.is_advanced_view = False
        entrada = self.app.ui.refs.get("simple_extra_cmd_var")
        self.assertIsNotNone(entrada, "el mini-dock debe exponer simple_extra_cmd_var")
        entrada.set("--max-fps=30")
        espia = self._con_arranque_espia()

        self.app._toggle_scene()

        datos = espia.call_args.args[2]
        self.assertIn("--max-fps=30", datos["extra_args"])
        self.assertNotIn("--max-fps=30",
                         self.ctx.cfg["profiles"]["🎮 Juego Rápido"].get("extra_args", ""),
                         "los extras de la vista simple no deben escribirse en la config")

    def test_vista_avanzada_ignora_los_argumentos_extra(self):
        self.ctx.active_device_serial = "HWY9"
        self.ctx.active_profile.set("🎮 Juego Rápido")
        self.app.is_advanced_view = True
        entrada = self.app.ui.refs.get("simple_extra_cmd_var")
        if entrada is not None:
            entrada.set("--max-fps=30")
        espia = self._con_arranque_espia()

        self.app._toggle_scene()

        datos = espia.call_args.args[2]
        self.assertNotIn("--max-fps=30", datos.get("extra_args", ""))

    def test_emui_manda_el_keyevent_antes_de_arrancar(self):
        perfil = "🎙️ Stream OBS (Huawei)"
        self.ctx.active_device_serial = "HWY9"
        self.ctx.active_profile.set(perfil)
        self.ctx.cfg["profiles"][perfil] = dict(
            self.ctx.cfg["profiles"].get(perfil, {}), force_screen_off_keyevent=True,
        )
        espia = self._con_arranque_espia()

        with patch.object(main_mod.time, "sleep") as dormir:
            self.app._toggle_scene()

        llamadas = [c for c in self.ctx.adb_engine.calls if c[0] == "shell"]
        self.assertTrue(
            any(c[1] == "HWY9" and "26" in str(c[2]) for c in llamadas),
            f"falta el keyevent 26 previo: {llamadas}",
        )
        dormir.assert_called_once_with(0.3)
        espia.assert_called_once()

    def test_sin_flag_no_manda_ningun_keyevent(self):
        self.ctx.active_device_serial = "HWY9"
        self.ctx.active_profile.set("🎮 Juego Rápido")
        self.ctx.cfg["profiles"]["🎮 Juego Rápido"] = dict(
            self.ctx.cfg["profiles"]["🎮 Juego Rápido"], force_screen_off_keyevent=False,
        )
        self._con_arranque_espia()

        self.app._toggle_scene()

        self.assertEqual([c for c in self.ctx.adb_engine.calls if c[0] == "shell"], [])

    # ── callbacks del arranque ───────────────────────────────────────────

    def test_al_arrancar_pasa_a_la_pestana_acciones_y_queda_en_verde(self):
        self.ctx.active_device_serial = "HWY9"
        self.ctx.active_profile.set("🎮 Juego Rápido")
        espia = self._con_arranque_espia()
        self.app._nb = MagicMock()

        self.app._toggle_scene()
        espia.call_args.args[3]()          # la propia app invoca este callback al registrar

        self.assertEqual(self.ctx.state_machine.current_state.value, "SUCCESS")
        self.app._nb.select.assert_called_once_with(0)   # pestaña Acciones
        self.assertIn("🎮 Juego Rápido", self.ctx.state_machine.message)

    def test_arranque_fallido_deja_la_fsm_en_fallo(self):
        self.ctx.active_device_serial = "HWY9"
        self.ctx.active_profile.set("🎮 Juego Rápido")
        fallo = OperationResult.fail(ErrorCode.PROCESS_SPAWN_ERROR, "scrcpy no está")
        self._con_arranque_espia(fallo)

        self.app._toggle_scene()

        self.assertEqual(self.ctx.state_machine.current_state.value, "FAULT")
        self.assertIn("scrcpy no está", self.ctx.state_machine.message)


# ─────────────────────────────────────────────────────────────────────────────
# Caracterización (Pinning) de los 5 bloques finales de complejidad
# ─────────────────────────────────────────────────────────────────────────────

class TestDeviceManagerScanPinning(unittest.TestCase):
    """Caracterización completa de DeviceManager.scan_devices antes de refactor."""

    def test_scan_devices_con_fallo_adb_y_callbacks(self):
        fake_adb = MagicMock()
        fake_adb.list_devices.return_value = OperationResult.fail(ErrorCode.ADB_NOT_FOUND, "adb ausente")
        dm = DeviceManager(adb_engine=fake_adb)

        logs = []
        ui_updates = []
        res = dm.scan_devices(
            callback_update_ui=lambda d: ui_updates.append(d),
            log_cb=lambda lvl, msg: logs.append((lvl, msg)),
        )

        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.ADB_NOT_FOUND)
        self.assertEqual(ui_updates, [[]])
        self.assertEqual(logs, [("ERROR", "Escaneo ADB falló: adb ausente")])

    def test_scan_devices_con_fallo_adb_sin_callbacks(self):
        fake_adb = MagicMock()
        fake_adb.list_devices.return_value = OperationResult.fail(ErrorCode.ADB_SERVER_FAILED, "error server")
        dm = DeviceManager(adb_engine=fake_adb)

        res = dm.scan_devices(callback_update_ui=None, log_cb=None)
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.ADB_SERVER_FAILED)

    def test_scan_devices_mapea_estados_device_unauth_offline_y_other(self):
        fake_adb = MagicMock()
        devices = [
            Device(serial="DEV_OK", model="Pixel 7", android_sdk=33, state=DeviceState.DEVICE, connection_type=ConnectionType.USB),
            Device(serial="DEV_UNAUTH", model="Galaxy", android_sdk=30, state=DeviceState.UNAUTHORIZED, connection_type=ConnectionType.USB),
            Device(serial="DEV_OFFLINE", model="Moto", android_sdk=29, state=DeviceState.OFFLINE, connection_type=ConnectionType.WIFI),
            Device(serial="DEV_RECOVERY", model="Xiaomi", android_sdk=28, state="recovery", connection_type=ConnectionType.USB),
        ]
        fake_adb.list_devices.return_value = OperationResult.ok(devices)
        dm = DeviceManager(adb_engine=fake_adb)

        ui_updates = []
        res = dm.scan_devices(callback_update_ui=lambda d: ui_updates.append(d))

        self.assertTrue(res.success)
        self.assertEqual(len(ui_updates), 1)
        found = ui_updates[0]
        self.assertEqual(len(found), 4)

        # 1. Device OK
        self.assertEqual(found[0], ("DEV_OK", "Pixel 7", "ok"))
        self.assertEqual(dm.device_entries[0].serial, "DEV_OK")
        self.assertEqual(dm.device_entries[0].model, "Pixel 7")
        self.assertEqual(dm.device_entries[0].state, "device")
        self.assertEqual(dm.device_entries[0].android_version, 33)
        self.assertEqual(dm.device_entries[0].connection_type, "usb")

        # 2. Unauthorized
        self.assertEqual(found[1], ("DEV_UNAUTH", "⚠  Acepta el permiso en el teléfono", "unauth"))
        self.assertEqual(dm.device_entries[1].serial, "DEV_UNAUTH")
        self.assertEqual(dm.device_entries[1].state, "unauthorized")

        # 3. Offline
        self.assertEqual(found[2], ("DEV_OFFLINE", "🔌  Dispositivo desconectado (offline)", "offline"))
        self.assertEqual(dm.device_entries[2].serial, "DEV_OFFLINE")
        self.assertEqual(dm.device_entries[2].state, "offline")

        # 4. Other (ej. "recovery")
        self.assertEqual(found[3], ("DEV_RECOVERY", "[recovery]", "other"))
        self.assertEqual(dm.device_entries[3].serial, "DEV_RECOVERY")
        self.assertEqual(dm.device_entries[3].state, "recovery")

        self.assertEqual(dm.devices, found)


class TestSessionManagerLaunchFallbackPinning(unittest.TestCase):
    """Caracterización completa de SessionManager._launch_with_fallback antes de refactor."""

    def setUp(self):
        self.device = Device(serial="HWY9", model="STK-LX3", android_sdk=29)
        self.caps = DeviceCapabilities(manufacturer="HUAWEI", platform="kirin710", model="STK-LX3", sdk_int=29)
        self.config = SessionConfig(port=27183, codec=Codec.H264, resolution="1080", bit_rate=8_000_000)

    def test_build_command_fail_releases_port(self):
        fake_alloc = MagicMock()
        fake_scrcpy = MagicMock()
        fake_scrcpy.build_command.return_value = OperationResult.fail(ErrorCode.INVALID_INPUT, "argumento invalido")

        sm = SessionManager(log_q_or_adb=MagicMock(), scrcpy_engine=fake_scrcpy, allocator=fake_alloc)
        res = sm._launch_with_fallback(self.device, self.caps, self.config)

        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.INVALID_INPUT)
        fake_alloc.release.assert_called_once_with(27183)

    def test_launch_fail_releases_port(self):
        fake_alloc = MagicMock()
        fake_scrcpy = MagicMock()
        fake_scrcpy.build_command.return_value = OperationResult.ok(["scrcpy", "-s", "HWY9"])
        fake_scrcpy.launch.return_value = OperationResult.fail(ErrorCode.PROCESS_SPAWN_ERROR, "error spawn")

        sm = SessionManager(log_q_or_adb=MagicMock(), scrcpy_engine=fake_scrcpy, allocator=fake_alloc)
        res = sm._launch_with_fallback(self.device, self.caps, self.config)

        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.PROCESS_SPAWN_ERROR)
        fake_alloc.release.assert_called_once_with(27183)

    def test_handshake_timeout_con_proceso_muerto_no_se_da_por_vivo(self):
        """Si el proceso muere justo al agotarse el tiempo, la sesión NO está viva.

        `wait()` lanza cuando el tiempo se agota, pero el proceso puede haberse
        muerto en ese instante: hay que mirar `poll()`. Darlo por vivo anunciaría
        "Transmisión activa" sin ningún scrcpy detrás.
        """
        murio = MagicMock()
        murio.wait.side_effect = TimeoutError("agotado")
        murio.poll.return_value = 1
        self.assertFalse(SessionManager._verificar_handshake(murio, 0.1))

        vivo = MagicMock()
        vivo.wait.side_effect = TimeoutError("agotado")
        vivo.poll.return_value = None
        self.assertTrue(SessionManager._verificar_handshake(vivo, 0.1))

    def test_handshake_alive_registers_session(self):
        fake_alloc = MagicMock()
        fake_scrcpy = MagicMock()
        fake_scrcpy.build_command.return_value = OperationResult.ok(["scrcpy"])
        mock_proc = MagicMock()
        # En timeout de wait, levanta excepción (proceso sigue vivo)
        mock_proc.wait.side_effect = TimeoutError("still running")
        mock_proc.poll.return_value = None
        fake_scrcpy.launch.return_value = OperationResult.ok(mock_proc)

        sm = SessionManager(log_q_or_adb=MagicMock(), scrcpy_engine=fake_scrcpy, allocator=fake_alloc)
        res = sm._launch_with_fallback(self.device, self.caps, self.config)

        self.assertTrue(res.success)
        self.assertEqual(res.data.port, 27183)
        self.assertIn("HWY9", sm.sessions)
        self.assertEqual(sm.sessions["HWY9"].assigned_port, 27183)
        fake_alloc.release.assert_not_called()

    def test_handshake_crash_h264_no_fallback(self):
        fake_alloc = MagicMock()
        fake_scrcpy = MagicMock()
        fake_scrcpy.build_command.return_value = OperationResult.ok(["scrcpy"])
        mock_proc = MagicMock()
        # Proceso termina inmediatamente (wait retorna 1)
        mock_proc.wait.return_value = 1
        mock_proc.poll.return_value = 1
        fake_scrcpy.launch.return_value = OperationResult.ok(mock_proc)

        sm = SessionManager(log_q_or_adb=MagicMock(), scrcpy_engine=fake_scrcpy, allocator=fake_alloc)
        res = sm._launch_with_fallback(self.device, self.caps, self.config)

        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.PROCESS_CRASH)
        fake_alloc.release.assert_called_once_with(27183)

    def test_handshake_crash_with_h265_retries_with_h264(self):
        fake_alloc = MagicMock()
        fake_alloc.acquire.return_value = OperationResult.ok(27184)
        fake_scrcpy = MagicMock()
        fake_scrcpy.build_command.return_value = OperationResult.ok(["scrcpy"])
        fake_scrcpy.is_codec_failure.return_value = True

        proc_crash = MagicMock()
        proc_crash.wait.return_value = 1
        proc_crash.poll.return_value = 1

        proc_alive = MagicMock()
        proc_alive.wait.side_effect = TimeoutError("vivo")
        proc_alive.poll.return_value = None

        fake_scrcpy.launch.side_effect = [
            OperationResult.ok(proc_crash),
            OperationResult.ok(proc_alive),
        ]

        cfg_h265 = SessionConfig(port=27183, codec=Codec.H265, resolution="1080", bit_rate=8_000_000)
        sm = SessionManager(log_q_or_adb=MagicMock(), scrcpy_engine=fake_scrcpy, allocator=fake_alloc)
        res = sm._launch_with_fallback(self.device, self.caps, cfg_h265)

        self.assertTrue(res.success)
        self.assertEqual(res.data.port, 27184)
        fake_alloc.release.assert_called_once_with(27183)
        fake_alloc.acquire.assert_called_once()
        self.assertEqual(sm.sessions["HWY9"].assigned_port, 27184)

    def test_handshake_crash_fallback_port_exhausted(self):
        fake_alloc = MagicMock()
        fake_alloc.acquire.return_value = OperationResult.fail(ErrorCode.PORT_POOL_EXHAUSTED, "sin puertos")
        fake_scrcpy = MagicMock()
        fake_scrcpy.build_command.return_value = OperationResult.ok(["scrcpy"])
        fake_scrcpy.is_codec_failure.return_value = True

        proc_crash = MagicMock()
        proc_crash.wait.return_value = 1
        proc_crash.poll.return_value = 1
        fake_scrcpy.launch.return_value = OperationResult.ok(proc_crash)

        cfg_h265 = SessionConfig(port=27183, codec=Codec.H265, resolution="1080", bit_rate=8_000_000)
        sm = SessionManager(log_q_or_adb=MagicMock(), scrcpy_engine=fake_scrcpy, allocator=fake_alloc)
        res = sm._launch_with_fallback(self.device, self.caps, cfg_h265)

        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.PORT_POOL_EXHAUSTED)


class TestScrcpyEngineCodecsPinning(unittest.TestCase):
    """Caracterización completa de ScrcpyEngine.get_compatible_codecs."""

    def setUp(self):
        self.engine = ScrcpyEngine("/usr/bin/scrcpy", "/usr/share/scrcpy/scrcpy-server")

    def test_sdk_menor_a_29_retorna_solo_h264(self):
        dev = Device(serial="D_OLD", model="OldDevice", android_sdk=26)
        caps = DeviceCapabilities(manufacturer="Sony", platform="msm8996", model="Old", sdk_int=26)
        res = self.engine.get_compatible_codecs(dev, caps)
        self.assertTrue(res.success)
        self.assertEqual(res.data, [Codec.H264])

    def test_kirin_con_prefijo_en_plataforma_fuerza_h264(self):
        dev = Device(serial="HW", model="Honor", android_sdk=31)
        caps = DeviceCapabilities(manufacturer="Honor", platform="kirin710", model="Honor 20", sdk_int=31)
        res = self.engine.get_compatible_codecs(dev, caps)
        self.assertTrue(res.success)
        self.assertEqual(res.data, [Codec.H264])

    def test_kirin_fabricante_huawei_y_prefijo_kirin(self):
        dev = Device(serial="HW2", model="Huawei Nova", android_sdk=30)
        caps = DeviceCapabilities(manufacturer="HUAWEI", platform="kirin710f", model="Nova", sdk_int=30)
        res = self.engine.get_compatible_codecs(dev, caps)
        self.assertTrue(res.success)
        self.assertEqual(res.data, [Codec.H264])

    def test_no_kirin_sdk_34_retorna_todos(self):
        dev = Device(serial="PIX", model="Pixel 8", android_sdk=34)
        caps = DeviceCapabilities(manufacturer="Google", platform="zuma", model="Pixel 8", sdk_int=34)
        res = self.engine.get_compatible_codecs(dev, caps)
        self.assertTrue(res.success)
        self.assertEqual(res.data, [Codec.AV1, Codec.H265, Codec.H264])


class TestChangeThemePinning(unittest.TestCase):
    """Caracterización de ScrcpyDockApp._change_theme con aislamiento de config."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception:
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
            self.skipTest("Tkinter sin display")
        # El aislamiento de config/log ya lo hace el arnés (`app_en_prueba`), que
        # redirige CONFIG_FILE/CONFIG_DIR/LOG_FILE a un temporal.
        self.sitio = app_en_prueba(self.root)
        self.app = self.sitio.app

    def tearDown(self):
        if getattr(self, "sitio", None) is not None:
            self.sitio.cerrar()

    def test_change_theme_con_reinicio_guarda_y_llama_restart(self):
        with patch.object(main_mod.messagebox, "askyesno", return_value=True), \
             patch.object(self.app, "_restart_app") as restart_mock:
            self.app._change_theme("light")
        self.assertEqual(self.app.ctx.cfg["theme"], "light")
        restart_mock.assert_called_once()

    def test_change_theme_sin_reinicio_conserva_la_pestana_activa(self):
        """Sin reinicio se reconstruyen las pestañas… sin devolver al usuario al Mini-Dock.

        `_reconstruir_pestanas_en_caliente` leía `active_tab_id`, pero nadie
        escribía ese atributo: el cambio de tema saltaba siempre a `quickcast`.
        """
        self.app._select_tab("controls")

        with patch.object(main_mod.messagebox, "askyesno", return_value=False), \
             patch.object(main_mod, "Toast"):
            self.app._change_theme("dracula")

        self.assertEqual(self.app.ctx.cfg["theme"], "dracula")
        self.assertEqual(self.app.active_tab_id, "controls",
                         "tras cambiar de tema debe seguirse viendo la misma pestaña")


class TestSelectTabPinning(unittest.TestCase):
    """Caracterización de ScrcpyDockApp._select_tab."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception:
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
            self.skipTest("Tkinter sin display")
        self.sitio = app_en_prueba(self.root)
        self.app = self.sitio.app

    def tearDown(self):
        if getattr(self, "sitio", None) is not None:
            self.sitio.cerrar()

    def test_select_tab_por_indice_valido_e_invalido(self):
        self.app._select_tab(1)  # "actions"
        self.assertEqual(self.app.active_tab_id, "actions")

        # Índice fuera de rango: no debe mutar la pestaña activa
        self.app._select_tab(99)
        self.assertEqual(self.app.active_tab_id, "actions")

        self.app._select_tab(-1)
        self.assertEqual(self.app.active_tab_id, "actions")

    def test_select_tab_alias_simple(self):
        self.app._select_tab("actions")
        self.app._select_tab("simple")
        self.assertEqual(self.app.active_tab_id, "quickcast")

    def test_select_tab_profiles_sincroniza(self):
        """Seleccionar Perfiles sincroniza el listado de perfiles.

        Se comprueba el efecto, no el conteo exacto: el cuerpo de `_select_tab` se
        ejecuta **dos veces** por una llamada re-entrante (el callback de la barra
        lateral, `lambda tid, idx: self._select_tab(tid)`, vuelve a invocarlo).
        """
        with patch.object(self.app, "_sync_profile_selection") as sync_mock:
            self.app._select_tab("profiles")

        self.assertEqual(self.app.active_tab_id, "profiles")
        self.assertGreaterEqual(sync_mock.call_count, 1,
                                "seleccionar Perfiles debe sincronizar la selección")

    def test_select_tab_recuerda_la_pestana_mostrada(self):
        """Sin esto, reconstruir la interfaz (cambio de tema) volvía al Mini-Dock."""
        self.app._select_tab("console")
        self.assertEqual(self.app.active_tab_id, "console")

        # Un tab_id inexistente oculta todos los frames, pero no reescribe el recordado.
        self.app._select_tab("no-existe")
        self.assertEqual(self.app.active_tab_id, "console")


if __name__ == "__main__":
    unittest.main()

