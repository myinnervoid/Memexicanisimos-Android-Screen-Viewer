"""Pruebas de regresión de la FASE B del plan de evolución (ANALISIS.md v3.3).

  B1 · UIStateMachine valida transiciones (Ley 6)
  B2 · la UI enruta el estado por la FSM
  B3 · get_error_detail cableado a la consola
  B4 · modelo real del dispositivo (P3.8) en DeviceCapabilities
  B5 · una sola fuente de verdad de seguridad + bóveda cifrada

Ejecutable con el runner del CI:
    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import inspect
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.core.scrcpy_engine import ScrcpyEngine
from scrcpy_dock.domain.models import Codec, Device, DeviceCapabilities, SessionConfig
from scrcpy_dock.errors import ERROR_CATALOG, ErrorCode, get_error_detail
from scrcpy_dock.managers import DeviceManager
from scrcpy_dock.security import SecurityManager
from scrcpy_dock.services.security_service import SecurityService
from scrcpy_dock.state import UIState, UIStateMachine

VIVO_PROPS = {
    "ro.build.version.sdk": "35",
    "ro.build.version.release": "15",
    "ro.product.manufacturer": "vivo",
    "ro.product.model": "V2314",
    "ro.board.platform": "qcom",
}


# ─────────────────────────────────────────────────────────────────────────────
# B1 · Autómata que valida transiciones (Ley 6)
# ─────────────────────────────────────────────────────────────────────────────

class TestB1FSMValidaTransiciones(unittest.TestCase):
    def test_idle_a_success_se_rechaza_sin_mutar_estado(self):
        sm = UIStateMachine(UIState.IDLE)
        notificaciones = []
        sm.subscribe(lambda s, m, e: notificaciones.append(s))

        self.assertFalse(sm.set_success("no debería aplicarse"))
        self.assertEqual(sm.current_state, UIState.IDLE)
        self.assertIsNone(sm.previous_state)
        self.assertEqual(notificaciones, [], "una transición rechazada no debe notificar")

    def test_ciclo_de_vida_valido_se_aplica(self):
        sm = UIStateMachine(UIState.IDLE)
        self.assertTrue(sm.set_pending("escaneando"))
        self.assertTrue(sm.set_success("activo"))
        self.assertTrue(sm.set_empty("sin dispositivos"))
        self.assertTrue(sm.set_fault("boom", ErrorCode.PROCESS_CRASH))
        self.assertTrue(sm.set_idle("listo"))
        self.assertEqual(sm.current_state, UIState.IDLE)

    def test_can_transition_to_expone_el_grafo(self):
        sm = UIStateMachine(UIState.IDLE)
        self.assertTrue(sm.can_transition_to(UIState.PENDING))
        self.assertFalse(sm.can_transition_to(UIState.SUCCESS))
        sm.set_pending("x")
        self.assertTrue(sm.can_transition_to(UIState.SUCCESS))

    def test_auto_transicion_y_recuperacion_desde_fault(self):
        sm = UIStateMachine(UIState.IDLE)
        self.assertTrue(sm.set_idle("sigue idle"))          # auto-transición
        sm.set_pending("x")
        sm.set_fault("boom", ErrorCode.UNKNOWN_ERROR)
        self.assertTrue(sm.set_idle("recuperado"))          # FAULT→IDLE permitido
        # Desde IDLE la regla canónica sigue aplicando: no se salta a SUCCESS.
        self.assertFalse(sm.set_success("salto inválido"))
        self.assertTrue(sm.set_pending("reintento"))
        self.assertTrue(sm.set_success("reintento correcto"))

    def test_salir_de_fault_limpia_el_error(self):
        sm = UIStateMachine(UIState.IDLE)
        sm.set_pending("x")
        sm.set_fault("boom", ErrorCode.CONFIG_CORRUPT)
        self.assertEqual(sm.error_code, ErrorCode.CONFIG_CORRUPT)
        sm.set_success("ok")
        self.assertEqual(sm.current_state, UIState.SUCCESS)
        self.assertIsNone(sm.error_code, "al salir de FAULT se limpia el error")


# ─────────────────────────────────────────────────────────────────────────────
# B2 · La UI enruta el estado por la FSM
# ─────────────────────────────────────────────────────────────────────────────

class _StubTree:
    def __init__(self, rows):
        self._rows = rows
        self._sel = (0,) if rows else ()

    def selection(self):
        return self._sel

    def item(self, iid, key):
        return self._rows[iid]


class _StubApp:
    """Sustituto mínimo de ScrcpyDockApp (sin Tk)."""

    def __init__(self, session_mgr=None, rows=(("SERIAL1", "P", 1, "00:00", "RUN"),)):
        self.state_machine = UIStateMachine()
        self.logged = []
        self.hints = []
        self.ui = types.SimpleNamespace(refs={"sess_tree": _StubTree(list(rows))})
        self.ctx = types.SimpleNamespace(
            session_mgr=session_mgr or MagicMock(),
            log=lambda lvl, msg: self.logged.append((lvl, msg)),
            active_device_serial="SERIAL1",
            state_machine=self.state_machine,
            active_profile=types.SimpleNamespace(get=lambda: "Perfil X"),
            save_current_config=lambda: None,
        )
        self.refreshed = 0
        self.root = MagicMock()

    def _refresh_table(self):
        self.refreshed += 1

    def _hint(self, msg, color=None):
        self.hints.append(msg)


class TestB2UIEnrutadaPorFSM(unittest.TestCase):
    def test_set_status_quedan_solo_el_renderizador_y_hint(self):
        from scrcpy_dock import main as main_mod

        src = inspect.getsource(main_mod)
        # definición + llamada en _on_ui_state_change + llamada en _hint
        self.assertLessEqual(src.count("_set_status("), 4)

    def test_hint_existe_y_es_el_unico_canal_alternativo(self):
        from scrcpy_dock.main import ScrcpyDockApp

        self.assertTrue(hasattr(ScrcpyDockApp, "_hint"))
        self.assertIn("_set_status", inspect.getsource(ScrcpyDockApp._hint),
                      "_hint debe delegar en el único renderizador (_set_status)")

    def test_stop_selected_transiciona_a_idle(self):
        from scrcpy_dock.main import ScrcpyDockApp

        smgr = MagicMock()
        smgr.stop_session.return_value = OperationResult.ok("SERIAL1")
        app = _StubApp(smgr)
        app.state_machine.set_pending("arrancando")   # simula sesión activa

        ScrcpyDockApp._stop_selected(app)

        self.assertEqual(app.state_machine.current_state, UIState.IDLE)
        self.assertIn("SERIAL1", app.state_machine.message)

    def test_handler_informativo_usa_hint_y_no_la_fsm(self):
        from scrcpy_dock.main import ScrcpyDockApp

        app = _StubApp()
        app._sync_profile_selection = lambda name: None

        ScrcpyDockApp._on_active_profile_change(app)

        self.assertEqual(app.hints, ["Perfil activo: Perfil X"])
        self.assertEqual(app.state_machine.current_state, UIState.IDLE,
                         "un mensaje informativo no debe cambiar el estado operativo")


# ─────────────────────────────────────────────────────────────────────────────
# B3 · get_error_detail cableado a la consola
# ─────────────────────────────────────────────────────────────────────────────

class TestB3RemediacionEnConsola(unittest.TestCase):
    def _app(self):
        from scrcpy_dock.main import ScrcpyDockApp

        app = _StubApp()
        app._set_status = lambda *a, **k: None
        app._log_error_remediation = ScrcpyDockApp._log_error_remediation.__get__(app)
        return app

    def test_fault_registra_codigo_y_remediacion(self):
        from scrcpy_dock.i18n import set_language
        from scrcpy_dock.main import ScrcpyDockApp

        set_language("es")
        app = self._app()
        ScrcpyDockApp._on_ui_state_change(app, UIState.FAULT, "falló", ErrorCode.PAIRING_FAILED)

        texto = " ".join(msg for _, msg in app.logged)
        self.assertIn(ErrorCode.PAIRING_FAILED.value, texto)
        self.assertIn(get_error_detail(ErrorCode.PAIRING_FAILED).title_es, texto)
        self.assertIn(get_error_detail(ErrorCode.PAIRING_FAILED).remediation_es, texto)

    def test_remediacion_en_ingles(self):
        from scrcpy_dock.i18n import set_language
        from scrcpy_dock.main import ScrcpyDockApp

        set_language("en")
        try:
            app = self._app()
            ScrcpyDockApp._on_ui_state_change(app, UIState.FAULT, "failed", ErrorCode.LOCKDOWN_FAILED)
            texto = " ".join(msg for _, msg in app.logged)
            self.assertIn(get_error_detail(ErrorCode.LOCKDOWN_FAILED).remediation_en, texto)
        finally:
            set_language("es")

    def test_get_error_detail_ya_no_es_import_muerto(self):
        from scrcpy_dock import main as main_mod

        src = inspect.getsource(main_mod)
        self.assertIn("get_error_detail(", src.replace("from .errors import", ""))

    def test_catalogo_crecio_con_los_codigos_que_faltaban(self):
        for code in (ErrorCode.APK_INSTALL_FAILED, ErrorCode.DEVICE_OFFLINE,
                     ErrorCode.LOCKDOWN_FAILED, ErrorCode.CONFIG_CORRUPT,
                     ErrorCode.INVALID_EXTRA_ARGS):
            self.assertIn(code, ERROR_CATALOG, f"{code} sin ErrorDetail")
        self.assertGreaterEqual(len(ERROR_CATALOG), 16)


# ─────────────────────────────────────────────────────────────────────────────
# B4 · Modelo real del dispositivo (P3.8)
# ─────────────────────────────────────────────────────────────────────────────

class _FakeAdb:
    def __init__(self, props=VIVO_PROPS):
        self.props = props

    def get_properties(self, serial):
        return OperationResult.ok(dict(self.props))


class TestB4ModeloDelDispositivo(unittest.TestCase):
    def test_device_capabilities_transporta_model(self):
        caps = DeviceCapabilities(manufacturer="vivo", platform="qcom", model="V2314")
        self.assertEqual(caps.model, "V2314")

    def test_get_device_props_devuelve_el_modelo_no_el_fabricante(self):
        dm = DeviceManager(adb_engine=_FakeAdb())
        props = dm.get_device_props("SERIAL1")
        self.assertEqual(props["model"], "V2314")
        self.assertEqual(props["manufacturer"], "vivo")
        self.assertNotEqual(props["model"], props["manufacturer"])

    def test_get_device_props_cae_a_adb_devices_si_ro_product_model_falta(self):
        props = dict(VIVO_PROPS)
        props["ro.product.model"] = ""
        dm = DeviceManager(adb_engine=_FakeAdb(props))
        dm.device_entries = [types.SimpleNamespace(serial="SERIAL1", model="V2314")]
        self.assertEqual(dm.get_device_props("SERIAL1")["model"], "V2314")

    def test_titulo_de_ventana_usa_el_modelo_real(self):
        engine = ScrcpyEngine(Path("/usr/local/bin/scrcpy"), Path("/dev/null"))
        device = Device(serial="SERIAL1", model="V2314", android_sdk=35)
        caps = DeviceCapabilities(manufacturer="vivo", platform="qcom", model="V2314")
        config = SessionConfig(port=27183, codec=Codec.H264, resolution="1080",
                               bit_rate=8_000_000)
        res = engine.build_command(config, device, caps)
        self.assertTrue(res.success, res.message)
        argv = res.data
        idx = argv.index("--window-title")
        self.assertEqual(argv[idx + 1], "MASV: V2314")
        self.assertNotIn("vivo", argv[idx + 1])


# ─────────────────────────────────────────────────────────────────────────────
# B5 · Una sola fuente de verdad de seguridad + bóveda cifrada
# ─────────────────────────────────────────────────────────────────────────────

def _empty_cfg(vault_encrypted: bool = False, trusted=None) -> dict:
    return {
        "security": {
            "safe_mode_enabled": True,
            "auto_lockdown_exit": True,
            "trusted_devices": trusted if trusted is not None else {},
            "blocked_ips": [],
            "vault_encrypted": vault_encrypted,
        }
    }


class TestB5SeguridadUnificada(unittest.TestCase):
    def test_la_criptografia_vive_solo_en_security_service(self):
        from scrcpy_dock import security as sec_mod

        src = inspect.getsource(sec_mod)
        self.assertNotIn("Fernet", src, "SecurityManager no debe implementar criptografía")
        self.assertNotIn("PBKDF2", src)
        self.assertIn("SecurityService", src, "debe delegar en el servicio")

    def test_migra_texto_plano_a_boveda_cifrada_y_recarga(self):
        with tempfile.TemporaryDirectory() as tmp:
            trusted = {"SERIAL1": {"serial": "SERIAL1", "alias": "Mi Vivo", "is_trusted": True}}
            cfg = _empty_cfg(trusted=trusted)

            sec = SecurityManager(cfg, vault_dir=tmp)

            vault = Path(tmp) / SecurityService.VAULT_FILENAME
            self.assertTrue(vault.exists(), "debe crearse vault.enc")
            self.assertTrue(sec.is_vault_encrypted)
            self.assertEqual(cfg["security"]["trusted_devices"], {},
                             "el texto plano se retira tras verificar el vault")
            self.assertTrue(sec.is_trusted_device("SERIAL1"))
            self.assertEqual(sec.get_device_alias("SERIAL1"), "Mi Vivo")

            # El vault se puede releer desde cero (simula reapertura de la app).
            cfg2 = _empty_cfg(vault_encrypted=True)
            sec2 = SecurityManager(cfg2, vault_dir=tmp)
            self.assertTrue(sec2.is_vault_encrypted)
            self.assertTrue(sec2.is_trusted_device("SERIAL1"))
            self.assertEqual(sec2.get_device_alias("SERIAL1"), "Mi Vivo")

    def test_mutar_la_boveda_la_persiste_cifrada(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _empty_cfg()
            sec = SecurityManager(cfg, vault_dir=tmp)
            guardados = []
            res = sec.trust_device("SERIAL9", "Pixel 8", "Mi Pixel", save_cb=guardados.append)

            self.assertTrue(res.success)
            self.assertTrue(guardados, "save_cb debe invocarse")
            self.assertTrue(sec.is_trusted_device("SERIAL9"))
            self.assertEqual(cfg["security"]["trusted_devices"], {})

            sec2 = SecurityManager(_empty_cfg(vault_encrypted=True), vault_dir=tmp)
            self.assertTrue(sec2.is_trusted_device("SERIAL9"))

            sec.untrust_device("SERIAL9", save_cb=None)
            self.assertFalse(sec.is_trusted_device("SERIAL9"))
            self.assertEqual(sec.remove_device_from_vault("SERIAL9").success, True)

    def test_backup_del_texto_plano_antes_de_migrar(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "config.json").write_text('{"security": {"trusted_devices": {}}}')
            cfg = _empty_cfg(trusted={"S": {"serial": "S", "is_trusted": True}})
            SecurityManager(cfg, vault_dir=tmp)
            self.assertTrue(Path(tmp, "config.json.pre-vault.bak").exists())

    def test_sin_vault_dir_mantiene_el_comportamiento_en_claro(self):
        cfg = _empty_cfg()
        sec = SecurityManager(cfg)                     # sin vault_dir
        guardados = []
        sec.trust_device("SERIAL1", "Vivo", "Alias", save_cb=guardados.append)

        self.assertFalse(sec.is_vault_encrypted)
        self.assertTrue(guardados)
        self.assertIn("SERIAL1", cfg["security"]["trusted_devices"],
                      "sin bóveda cifrada se conserva el almacenamiento en config.json")

    def test_is_whitelisted_device_acepta_dict_y_lista(self):
        svc = SecurityService()
        self.assertTrue(svc.is_whitelisted_device("S1", {"trusted_devices": {"S1": {}}}))
        self.assertTrue(svc.is_whitelisted_device(
            "S1", {"trusted_devices": [{"serial": "S1"}]}))
        self.assertFalse(svc.is_whitelisted_device("S2", {"trusted_devices": {"S1": {}}}))
        self.assertFalse(svc.is_whitelisted_device("S1", {"trusted_devices": "basura"}))

    def test_vault_corrupto_no_destruye_el_texto_plano(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, SecurityService.VAULT_FILENAME).write_bytes(b"no-es-un-token-fernet")
            cfg = _empty_cfg(trusted={"SERIAL1": {"serial": "SERIAL1", "is_trusted": True}})

            sec = SecurityManager(cfg, vault_dir=tmp)

            self.assertFalse(sec.is_vault_encrypted)
            self.assertTrue(sec.is_trusted_device("SERIAL1"),
                            "si el vault no se puede descifrar, la config en claro sigue siendo válida")
            self.assertIn("SERIAL1", cfg["security"]["trusted_devices"])


if __name__ == "__main__":
    unittest.main()
