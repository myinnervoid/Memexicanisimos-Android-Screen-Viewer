"""Pruebas de regresión de la FASE A del plan de evolución (ANALISIS.md v3.3).

Cada prueba corresponde a un defecto verificado en INFORME_BUGS_v1.4.1.md y a
una acción del plan (A1..A7). Se ejecutan con el runner del CI:

    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import inspect
import os
import pathlib
import re
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.core.scrcpy_engine import ScrcpyEngine
from scrcpy_dock.domain.models import (
    ALLOWED_EXTRA_FLAGS,
    Codec,
    Device,
    DeviceCapabilities,
    DeviceState,
    SessionConfig,
)
from scrcpy_dock.errors import ErrorCode
from scrcpy_dock.managers import DeviceManager, ScrcpySession, SessionManager
from scrcpy_dock.services.security_service import SecurityService
from scrcpy_dock.utils import DEFAULT_CONFIG

BIN = Path("/usr/local/bin/scrcpy")
JAR = Path("/dev/null")

MODERN_SDK = 35
LEGACY_SDK = 29


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de prueba
# ─────────────────────────────────────────────────────────────────────────────

class _StubDeviceManager:
    """DeviceManager mínimo: props reales sin tocar adb."""

    def __init__(self, sdk: int = MODERN_SDK, model: str = "V2314"):
        self.sdk = sdk
        self.model = model

    def get_device_props(self, serial: str) -> dict:
        return {
            "model": self.model,
            "android_version": self.sdk,
            "manufacturer": "vivo",
            "platform": "qcom",
        }

    def get_capabilities(self, serial: str):
        return None


def _make_engine() -> ScrcpyEngine:
    return ScrcpyEngine(BIN, JAR)


def _modern_device(sdk: int = MODERN_SDK) -> Device:
    return Device(serial="10ADCR1U6B000QF", model="V2314", android_sdk=sdk,
                  state=DeviceState.DEVICE)


def _vivo_caps(sdk: int = MODERN_SDK) -> DeviceCapabilities:
    return DeviceCapabilities(manufacturer="vivo", platform="qcom", sdk_int=sdk)


def _capture_legacy_config(profile_data: dict, sdk: int = MODERN_SDK):
    """Ejecuta start_scene_legacy con un motor simulado y devuelve el SessionConfig real."""
    mgr = SessionManager(log_q_or_adb=None, device_mgr=_StubDeviceManager(sdk))
    captured: dict = {}

    def _fake_launch(config, device, caps, **kwargs):
        captured["config"] = config
        captured["device"] = device
        captured["caps"] = caps
        proc = MagicMock()
        proc.pid = 4242
        proc.poll.return_value = None
        return OperationResult.ok(proc)

    mgr._scrcpy = MagicMock()
    mgr._scrcpy.launch.side_effect = _fake_launch

    res = mgr.start_scene_legacy("10ADCR1U6B000QF", "perfil-test", profile_data)
    return res, captured


# ─────────────────────────────────────────────────────────────────────────────
# A7 · Modo solo audio y perfiles distribuidos
# ─────────────────────────────────────────────────────────────────────────────

class TestA7PerfilesYAudioSolo(unittest.TestCase):
    """A7: los perfiles de fábrica deben construir un comando válido."""

    def test_todos_los_perfiles_por_defecto_producen_comando_valido(self):
        engine = _make_engine()

        for name, profile_data in DEFAULT_CONFIG["profiles"].items():
            with self.subTest(perfil=name):
                res, captured = _capture_legacy_config(dict(profile_data))
                self.assertTrue(res.success, f"{name}: start_scene_legacy falló: {res.message}")
                self.assertIn("config", captured)

                built = engine.build_command(captured["config"], captured["device"], captured["caps"])
                self.assertTrue(
                    built.success,
                    f"{name}: build_command rechazó el perfil → "
                    f"{built.error_code}: {built.message}",
                )

    def test_perfil_solo_audio_no_inyecta_flags_de_video(self):
        engine = _make_engine()
        profile = dict(DEFAULT_CONFIG["profiles"]["🎙️ Stream OBS (Huawei)"])

        res, captured = _capture_legacy_config(profile)
        self.assertTrue(res.success, res.message)

        config = captured["config"]
        self.assertFalse(config.video_enabled)
        self.assertNotIn("--no-video", config.extra_args)  # promovido a atributo nativo

        built = engine.build_command(config, captured["device"], captured["caps"])
        self.assertTrue(built.success, f"{built.error_code}: {built.message}")
        argv = built.data

        self.assertIn("--no-video", argv)
        self.assertEqual(argv.count("--no-video"), 1)          # no duplicado
        self.assertNotIn("--video-codec", argv)
        self.assertNotIn("--video-bit-rate", argv)
        self.assertNotIn("--video-source", argv)
        self.assertNotIn("--max-size", argv)
        self.assertNotIn("--no-downsize-on-error", argv)
        self.assertIn("--audio-source", argv)
        self.assertEqual(argv[argv.index("--audio-source") + 1], "mic")

    def test_solo_audio_con_flag_nativo_tambien_funciona(self):
        """El flag en extra_args (sin el campo no_video) también entra en modo solo audio."""
        engine = _make_engine()
        device, caps = _modern_device(), _vivo_caps()
        config = SessionConfig(
            port=27183, codec=Codec.H264, resolution="1080", bit_rate=8_000_000,
            audio_source="mic", extra_args=("--no-video",),
        )
        built = engine.build_command(config, device, caps)
        self.assertTrue(built.success, f"{built.error_code}: {built.message}")
        self.assertIn("--no-video", built.data)
        self.assertNotIn("--video-codec", built.data)

    def test_solo_audio_rechazado_en_android_10_con_mensaje_claro(self):
        """Android 10 no captura audio: --no-video + --no-audio no reproduciría nada."""
        engine = _make_engine()
        device, caps = _modern_device(LEGACY_SDK), _vivo_caps(LEGACY_SDK)
        config = SessionConfig(
            port=27183, codec=Codec.H264, resolution="1080", bit_rate=8_000_000,
            audio_source="mic", video_enabled=False,
        )
        built = engine.build_command(config, device, caps)
        self.assertFalse(built.success)
        self.assertEqual(built.error_code, ErrorCode.INVALID_INPUT)
        self.assertIn("Android 11", built.message)

    def test_solo_audio_con_audio_none_es_invalido(self):
        engine = _make_engine()
        device, caps = _modern_device(), _vivo_caps()
        config = SessionConfig(
            port=27183, codec=Codec.H264, resolution="1080", bit_rate=8_000_000,
            audio_source="none", video_enabled=False,
        )
        built = engine.build_command(config, device, caps)
        self.assertFalse(built.success)
        self.assertEqual(built.error_code, ErrorCode.INVALID_INPUT)

    def test_no_video_esta_en_la_whitelist_y_no_hay_duplicados(self):
        """A7 + de-duplicación: la whitelist es única y admite --no-video."""
        self.assertIn("--no-video", ALLOWED_EXTRA_FLAGS)
        self.assertIn("--no-audio", ALLOWED_EXTRA_FLAGS)

        import scrcpy_dock.core.scrcpy_engine as engine_mod
        self.assertIs(engine_mod.ALLOWED_EXTRA_FLAGS, ALLOWED_EXTRA_FLAGS,
                      "la whitelist debe tener una sola fuente de verdad")


# ─────────────────────────────────────────────────────────────────────────────
# A2 · Detener sesión seleccionada
# ─────────────────────────────────────────────────────────────────────────────

class _FakeTree:
    def __init__(self, rows):
        self._rows = rows
        self._sel = (0,) if rows else ()

    def selection(self):
        return self._sel

    def item(self, iid, key):
        # Tk devuelve la tupla de valores directamente (main.py hace vals[0]).
        return self._rows[iid]


class _AppStub:
    """Sustituto mínimo de ScrcpyDockApp para probar handlers sin Tk."""

    def __init__(self, session_mgr, rows=(("SERIAL1", "Perfil", 123, "00:01", "RUN"),)):
        self.ui = types.SimpleNamespace(refs={"sess_tree": _FakeTree(list(rows))})
        self.ctx = types.SimpleNamespace(
            session_mgr=session_mgr, log=lambda *a, **k: None,
            active_device_serial="SERIAL1",
        )
        self.refreshed = 0
        self.status = []
        self.root = MagicMock()

    def _refresh_table(self):
        self.refreshed += 1

    def _set_status(self, *a, **k):
        self.status.append(a)


class TestA2DetenerSesion(unittest.TestCase):
    def test_stop_selected_usa_stop_session(self):
        from scrcpy_dock.main import ScrcpyDockApp

        smgr = MagicMock()
        smgr.stop_session.return_value = OperationResult.ok("SERIAL1")
        app = _AppStub(smgr)

        ScrcpyDockApp._stop_selected(app)          # debe existir UNA sola definición

        smgr.stop_session.assert_called_once_with("SERIAL1")
        self.assertEqual(app.refreshed, 1)
        self.assertTrue(app.status)
        smgr.stop.assert_not_called() if hasattr(smgr, "stop") else None

    def test_stop_selected_tolera_evento_de_tk(self):
        """El binding <Delete> invoca el handler con un evento."""
        from scrcpy_dock.main import ScrcpyDockApp

        smgr = MagicMock()
        smgr.stop_session.return_value = OperationResult.ok("SERIAL1")
        app = _AppStub(smgr)

        ScrcpyDockApp._stop_selected(app, types.SimpleNamespace())
        smgr.stop_session.assert_called_once_with("SERIAL1")

    def test_stop_selected_sin_seleccion_no_rompe(self):
        from scrcpy_dock.main import ScrcpyDockApp

        smgr = MagicMock()
        app = _AppStub(smgr, rows=())
        ScrcpyDockApp._stop_selected(app)
        smgr.stop_session.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# A3 · Copiar comando scrcpy
# ─────────────────────────────────────────────────────────────────────────────

class TestA3CopiarComando(unittest.TestCase):
    def _session(self, serial: str = "SERIAL1") -> ScrcpySession:
        config = SessionConfig(
            port=27183, codec=Codec.H264, resolution="1080", bit_rate=8_000_000,
        )
        proc = MagicMock()
        proc.pid = 7
        proc.poll.return_value = None
        return ScrcpySession(
            serial, "Perfil", proc, assigned_port=27183,
            config=config, device=_modern_device(), caps=_vivo_caps(),
        )

    def test_build_command_for_reconstruye_argv(self):
        mgr = SessionManager(log_q_or_adb=None, device_mgr=_StubDeviceManager())
        mgr._scrcpy = _make_engine()
        mgr.sessions["SERIAL1"] = self._session()

        res = mgr.build_command_for("SERIAL1")
        self.assertTrue(res.success, res.message)
        self.assertIn("--video-codec", res.data)
        self.assertIn("-s", res.data)

    def test_build_command_for_sin_sesion_falla_limpio(self):
        mgr = SessionManager(log_q_or_adb=None, device_mgr=_StubDeviceManager())
        res = mgr.build_command_for("NO_EXISTE")
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.DEVICE_NOT_FOUND)

    def test_build_command_for_sin_contexto_falla_limpio(self):
        mgr = SessionManager(log_q_or_adb=None, device_mgr=_StubDeviceManager())
        mgr.sessions["SERIAL1"] = ScrcpySession("SERIAL1", "Perfil", MagicMock(), 27183)
        res = mgr.build_command_for("SERIAL1")
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.INVALID_INPUT)

    def test_copy_sess_cmd_no_usa_metodo_inexistente(self):
        from scrcpy_dock.main import ScrcpyDockApp

        src = inspect.getsource(ScrcpyDockApp._copy_sess_cmd)
        self.assertIn("build_command_for", src)
        self.assertNotIn("_build_cmd", src)


# ─────────────────────────────────────────────────────────────────────────────
# A4 · Modelo del dispositivo
# ─────────────────────────────────────────────────────────────────────────────

class TestA4ModeloDeDispositivo(unittest.TestCase):
    def test_get_device_model_devuelve_el_modelo_real(self):
        dm = DeviceManager(adb_engine=MagicMock())
        dm.scan_devices.__doc__  # noqa: B018  (solo referencia)
        dm.devices = [("SERIAL1", "V2314", "ok")]
        self.assertEqual(dm.get_device_model("SERIAL1"), "V2314")

    def test_get_device_model_prefiere_device_entries(self):
        from scrcpy_dock.contracts import DeviceEntry

        dm = DeviceManager(adb_engine=MagicMock())
        dm.device_entries = [DeviceEntry(serial="SERIAL1", model="V2314", state="device")]
        dm.devices = [("SERIAL1", "vivo", "ok")]  # placeholder contaminado
        self.assertEqual(dm.get_device_model("SERIAL1"), "V2314")

    def test_get_device_model_devuelve_vacio_si_no_existe(self):
        dm = DeviceManager(adb_engine=MagicMock())
        self.assertEqual(dm.get_device_model("DESCONOCIDO"), "")

    def test_toggle_scene_y_otg_usan_un_metodo_que_existe(self):
        """P3.3: los handlers llamaban a un método inexistente → AttributeError."""
        self.assertTrue(hasattr(DeviceManager, "get_device_model"))

        from scrcpy_dock.main import ScrcpyDockApp
        for handler in (ScrcpyDockApp._toggle_scene, ScrcpyDockApp._start_otg_mode):
            self.assertIn("get_device_model", inspect.getsource(handler))


# ─────────────────────────────────────────────────────────────────────────────
# A5 · Catálogo de errores
# ─────────────────────────────────────────────────────────────────────────────

class TestA5CatalogoDeErrores(unittest.TestCase):
    def test_encrypt_vault_devuelve_unknown_error_sin_attributeerror(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc = SecurityService(
                machine_id_path=Path(tmp) / "machine-id",
                salt_path=Path(tmp) / ".salt",
            )
            with patch.object(SecurityService, "_derive_fernet_key",
                              side_effect=RuntimeError("fallo simulado")):
                res = svc.encrypt_vault({"trusted_devices": []})

        self.assertFalse(res.success)
        self.assertEqual(res.error_code, ErrorCode.UNKNOWN_ERROR)

    def test_todos_los_errores_referenciados_existen_en_el_catalogo(self):
        """Regresión P3.4: ningún módulo puede referenciar un ErrorCode inexistente."""
        root = pathlib.Path(__file__).resolve().parent.parent / "scrcpy_dock"
        defined = {m.name for m in ErrorCode}
        referenced: dict[str, list[str]] = {}

        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in re.finditer(r"ErrorCode\.([A-Z][A-Z0-9_]*)", text):
                referenced.setdefault(match.group(1), []).append(path.name)

        missing = {name: files for name, files in referenced.items() if name not in defined}
        self.assertEqual(missing, {}, f"ErrorCode inexistentes referenciados: {missing}")

    def test_catalogo_detalla_al_menos_once_codigos(self):
        """Baseline actual: 11 de 30 códigos con ErrorDetail. Objetivo (Fase D): 30."""
        from scrcpy_dock.errors import ERROR_CATALOG
        self.assertGreaterEqual(len(ERROR_CATALOG), 11)


# ─────────────────────────────────────────────────────────────────────────────
# A6 · Diferido seguro en el handler de instalación
# ─────────────────────────────────────────────────────────────────────────────

class TestA6DiferidoSeguro(unittest.TestCase):
    def test_no_captura_la_variable_del_except_en_el_lambda(self):
        """Regresión P3.6: `except ... as e` se borra al salir del bloque."""
        from scrcpy_dock.main import ScrcpyDockApp

        src = inspect.getsource(ScrcpyDockApp._auto_install_deps)
        self.assertNotIn('{e}', src, "el lambda no debe capturar la variable del except")
        self.assertIn("err_msg", src, "el mensaje debe materializarse antes de root.after()")


# ─────────────────────────────────────────────────────────────────────────────
# A1 · Aislamiento de la configuración real
# ─────────────────────────────────────────────────────────────────────────────

class TestA1AislamientoDeConfig(unittest.TestCase):
    def test_la_suite_no_escribe_la_config_real(self):
        import scrcpy_dock.utils as utils

        real = utils.CONFIG_FILE
        before = None
        if os.path.exists(real):
            with open(real, "rb") as fh:
                before = fh.read()

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(utils, "CONFIG_FILE", os.path.join(tmp, "config.json")), \
                 patch.object(utils, "LOG_FILE", os.path.join(tmp, "masv.log")):
                utils.save_config({"perfil": "tmp"})
                self.assertEqual(utils.load_config().get("perfil"), "tmp")

        if before is None:
            self.assertFalse(os.path.exists(real), f"se creó la config real: {real}")
        else:
            with open(real, "rb") as fh:
                self.assertEqual(fh.read(), before, f"se modificó la config real: {real}")


if __name__ == "__main__":
    unittest.main()
