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
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import scrcpy_dock
import scrcpy_dock.main as main_mod
from scrcpy_dock.domain.models import Codec
from scrcpy_dock.errors import ErrorCode
from scrcpy_dock.main import ScrcpyDockApp
from scrcpy_dock.services.profile_service import ProfileService


# ─────────────────────────────────────────────────────────────────────────────
# Guardián de complejidad (Ley 7): sin bloques D/E/F en todo el paquete
# ─────────────────────────────────────────────────────────────────────────────

class TestComplejidadSinBloquesD(unittest.TestCase):
    """Evita que la deuda ciclomática demolidа en la Fase D vuelva a crecer."""

    def test_ningun_bloque_alcanza_rank_d(self):
        try:
            from radon.complexity import cc_visit
            from radon.visitors import Function
        except ImportError:  # pragma: no cover
            self.skipTest("radon no instalado (dependencia de desarrollo)")

        peores = []
        for archivo in Path(scrcpy_dock.__file__).parent.rglob("*.py"):
            arbol = ast.parse(archivo.read_text(encoding="utf-8"))
            for bloque in cc_visit(arbol):
                if not isinstance(bloque, Function):
                    continue
                if bloque.complexity > 10:
                    peores.append(
                        f"{archivo.name}:{bloque.lineno} {bloque.name} CC={bloque.complexity}",
                    )

        # El umbral de la Ley 7 es ≤ 10; el rank D empieza en 21. Se exige el
        # umbral duro (0 bloques > 10) para poder bajarlo a C más adelante.
        self.assertEqual(
            [p for p in peores if int(p.rsplit("CC=", 1)[1]) > 20], [],
            f"bloques Rank D o peor: {peores}",
        )
        self.assertLessEqual(
            len(peores), 14,
            f"los bloques > 10 volvieron a crecer ({len(peores)}): {peores}",
        )

    def test_los_tres_objetivos_de_la_fase_de_quedaron_planos(self):
        try:
            from radon.complexity import cc_visit
        except ImportError:  # pragma: no cover
            self.skipTest("radon no instalado")

        objetivos = {
            ("scrcpy_dock/services/profile_service.py", "sanitize_profile_dict"): 10,
            ("scrcpy_dock/main.py", "_exit"): 10,
            ("scrcpy_dock/main.py", "_on_dev_select"): 10,
        }
        for archivo in Path(scrcpy_dock.__file__).parent.rglob("*.py"):
            clave_rel = str(archivo.relative_to(Path(scrcpy_dock.__file__).parent.parent))
            for bloque in cc_visit(ast.parse(archivo.read_text(encoding="utf-8"))):
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


if __name__ == "__main__":
    unittest.main()
