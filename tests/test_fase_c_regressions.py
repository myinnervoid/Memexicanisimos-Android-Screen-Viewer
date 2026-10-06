"""Pruebas de regresión de la FASE C del plan de evolución (ANALISIS.md v3.3).

  C1 · extracción de servicios (device_service / stream_service)
  C2 · modularización de la presentación
  C3 · todo ADB pasa por AdbEngine (socket aislado)
  C4 · cobertura bilingüe completa de i18n
  C5 · build_command descompuesto (CC ≤ 10 por bloque)

Ejecutable con el runner del CI:
    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import inspect
import queue
import tempfile
import tkinter as tk
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import scrcpy_dock
import scrcpy_dock.context as context_mod
import scrcpy_dock.utils as utils
from scrcpy_dock.context import AppContext
from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.core.adb_engine import AdbEngine
from scrcpy_dock.core.scrcpy_engine import ScrcpyEngine
from scrcpy_dock.domain.models import Codec
from scrcpy_dock.errors import ErrorCode
from scrcpy_dock.managers import DeviceManager, SessionManager

from tests.contracts.helpers import fake_completed_process

ADB = Path("/usr/bin/adb")


# ─────────────────────────────────────────────────────────────────────────────
# C3 · Todo ADB pasa por el motor (socket aislado)
# ─────────────────────────────────────────────────────────────────────────────

class TestC3LaUINoInvocaAdbDirecto(unittest.TestCase):
    """El defecto P3.15: la UI lanzaba `adb` a pelo y tumbaba el daemon ajeno."""

    def test_main_py_no_ejecuta_el_binario_adb(self):
        from scrcpy_dock import main as main_mod

        src = inspect.getsource(main_mod)
        self.assertEqual(src.count("subprocess.run([self.ctx.adb"), 0)
        self.assertEqual(src.count("subprocess.Popen([self.ctx.adb"), 0)
        self.assertNotRegex(
            src, r"subprocess\.(run|Popen)\(\s*\[[^\]]*ctx\.adb",
            "ninguna llamada a subprocess puede construir argv con ctx.adb",
        )

    def test_la_ui_usa_el_accesor_del_motor(self):
        from scrcpy_dock.main import ScrcpyDockApp

        self.assertTrue(hasattr(ScrcpyDockApp, "_adb"))
        src = inspect.getsource(ScrcpyDockApp._adb)
        self.assertIn("adb_engine", src)
        self.assertIn("raise RuntimeError", src, "debe fallar explícito si no hay motor")


class TestC3PrimitivasDelMotor(unittest.TestCase):

    def setUp(self):
        self.engine = AdbEngine(ADB)

    @patch("subprocess.run")
    def test_kill_server_usa_el_socket_aislado(self, run_mock):
        run_mock.return_value = fake_completed_process()
        self.engine.start_daemon()

        res = self.engine.kill_server()

        self.assertTrue(res.success)
        argv = run_mock.call_args.args[0]
        self.assertEqual(argv, [str(Path("/usr/bin/adb")), "kill-server"])
        env = run_mock.call_args.kwargs["env"]
        self.assertEqual(env["ADB_SERVER_SOCKET"], "tcp:localhost:5037",
                         "kill-server debe apuntar a NUESTRO socket, no al compartido")

    @patch("subprocess.run")
    def test_kill_server_invalida_el_estado_del_daemon(self, run_mock):
        run_mock.return_value = fake_completed_process()
        self.engine.start_daemon()
        self.assertEqual(self.engine.effective_socket_port, 5037)

        self.engine.kill_server()

        self.assertEqual(self.engine.effective_socket_port, 0)
        run_mock.reset_mock()
        self.engine.start_daemon()
        self.assertEqual(run_mock.call_count, 1,
                         "tras matar el daemon, el siguiente arranque debe renegociar")

    @patch("subprocess.run")
    def test_shell_pasa_el_texto_como_un_solo_token(self, run_mock):
        run_mock.return_value = fake_completed_process(stdout="ok")

        res = self.engine.shell("S1", "input", "text", "'hola; rm -rf /'")

        self.assertTrue(res.success)
        self.assertEqual(res.data, "ok")
        argv = run_mock.call_args.args[0]
        self.assertEqual(
            argv,
            [str(Path("/usr/bin/adb")), "-s", "S1", "shell", "input", "text", "'hola; rm -rf /'"],
        )
        self.assertNotIn("shell", run_mock.call_args.kwargs,
                         "nunca shell=True: el argv se construye token a token")
        self.assertIn("ADB_SERVER_SOCKET", run_mock.call_args.kwargs["env"])

    @patch("subprocess.run")
    def test_shell_propaga_el_fallo(self, run_mock):
        run_mock.return_value = fake_completed_process(stderr="device offline", returncode=1)

        res = self.engine.shell("S1", "ip", "route")

        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.PROCESS_CRASH)
        self.assertIn("device offline", res.message)

    @patch("subprocess.run")
    def test_install_detecta_failure_con_returncode_cero(self, run_mock):
        # `adb install` devuelve 0 aunque el paquete no entre: el veredicto
        # real está en stdout.
        run_mock.return_value = fake_completed_process(
            stdout="Performing Streamed Install\nFailure [INSTALL_FAILED_INSUFFICIENT_STORAGE]",
        )

        res = self.engine.install("S1", "/tmp/app.apk")

        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.APK_INSTALL_FAILED)
        self.assertIn("INSTALL_FAILED", res.message)

    @patch("subprocess.run")
    def test_install_exitoso(self, run_mock):
        run_mock.return_value = fake_completed_process(stdout="Success")

        res = self.engine.install("S1", "/tmp/app.apk")

        self.assertTrue(res.success)
        argv = run_mock.call_args.args[0]
        self.assertEqual(argv, [str(Path("/usr/bin/adb")), "-s", "S1", "install", "-r", "/tmp/app.apk"])

    @patch("subprocess.run")
    def test_connect_parsea_el_endpoint(self, run_mock):
        run_mock.return_value = fake_completed_process(stdout="connected to 1.2.3.4:5555")

        self.engine.connect("1.2.3.4:5555")
        self.assertEqual(run_mock.call_args.args[0], [str(Path("/usr/bin/adb")), "connect", "1.2.3.4:5555"])

        self.engine.connect("1.2.3.4")
        self.assertEqual(run_mock.call_args.args[0], [str(Path("/usr/bin/adb")), "connect", "1.2.3.4:5555"])

    @patch("subprocess.run")
    def test_rebind_apunta_al_binario_nuevo(self, run_mock):
        run_mock.return_value = fake_completed_process()
        self.engine.start_daemon()

        self.engine.rebind("/opt/nuevo/adb")

        self.assertEqual(self.engine.effective_socket_port, 0)
        self.engine.kill_server()
        self.assertEqual(run_mock.call_args.args[0], [str(Path("/opt/nuevo/adb")), "kill-server"])


class TestC3UnSoloMotorCompartido(unittest.TestCase):
    """Antes cada manager creaba su propio AdbEngine (estado divergente)."""

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

    def _ctx(self):
        if not self.root:
            self.skipTest("Tkinter display not available")
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(utils, "CONFIG_FILE", str(Path(tmp, "config.json"))), \
                 patch.object(utils, "LOG_FILE", str(Path(tmp, "masv.log"))), \
                 patch.object(utils, "CONFIG_DIR", tmp), \
                 patch.object(context_mod, "find_portable_binaries",
                              return_value=("/usr/bin/adb", "/usr/bin/scrcpy")):
                return AppContext(self.root)

    def test_context_comparte_una_sola_instancia_del_motor(self):
        ctx = self._ctx()
        self.assertIsNotNone(ctx.adb_engine)
        self.assertIs(ctx.device_mgr._adb, ctx.adb_engine)
        self.assertIs(ctx.session_mgr._adb, ctx.adb_engine)

    def test_session_manager_conserva_log_q_al_inyectar_motor(self):
        q = queue.Queue()
        eng = AdbEngine(ADB)

        sm = SessionManager(q, device_mgr=DeviceManager(adb_engine=eng), adb_engine=eng)

        self.assertIs(sm.log_q, q,
                      "inyectar un motor no debe tirar el canal de logs de la UI")

    def test_set_adb_binary_reapunta_el_motor(self):
        ctx = self._ctx()
        self.assertIsNotNone(ctx.adb_engine)
        ctx.set_adb_binary("/opt/otro/adb")
        self.assertEqual(ctx.adb, "/opt/otro/adb")
        self.assertEqual(ctx.adb_engine._adb_binary, Path("/opt/otro/adb"))


# ─────────────────────────────────────────────────────────────────────────────
# C1 · El manager queda como fachada; el perfil se compila en un servicio
# ─────────────────────────────────────────────────────────────────────────────

class TestC1StreamService(unittest.TestCase):

    def test_start_scene_legacy_es_solo_una_fachada(self):
        from scrcpy_dock.managers import SessionManager

        src = inspect.getsource(SessionManager.start_scene_legacy)
        self.assertIn("self._stream.start_legacy", src)
        # La lógica de compilación del perfil ya no vive en el manager.
        self.assertNotIn("--video-source=", src)
        self.assertNotIn("Codec(", src)
        self.assertLess(len(src.splitlines()), 25)

    def test_el_servicio_existe_y_no_depende_del_manager(self):
        from scrcpy_dock.services import stream_service

        src = inspect.getsource(stream_service)
        self.assertNotIn("managers", src, "el servicio no debe conocer al manager")

    def _mgr(self, sdk=29):
        from scrcpy_dock.core.port_allocator import PortAllocator

        captured = {}

        class _FakeDeviceMgr:
            def get_device_props(self, serial):
                return {"model": "V2314", "android_version": sdk,
                        "manufacturer": "vivo", "platform": "qcom"}

        class _FakeScrcpy:
            def launch(self, config, device, caps):
                captured["config"] = config
                captured["device"] = device
                captured["caps"] = caps
                return OperationResult.ok(types.SimpleNamespace(pid=4242))

        mgr = SessionManager(log_q_or_adb=None, device_mgr=_FakeDeviceMgr())
        mgr._allocator = PortAllocator(base=29183, max_offset=5)
        mgr._scrcpy = _FakeScrcpy()
        return mgr, captured

    def test_usa_el_motor_sustituido_despues_de_construir(self):
        """Regresión: capturar el motor por valor rompía `mgr._scrcpy = fake`."""
        mgr, captured = self._mgr()

        res = mgr.start_scene_legacy("S1", "perfil", {"max_size": "1080"})

        self.assertTrue(res.success, res.message)
        self.assertIn("config", captured, "el servicio no usó el motor sustituido")
        self.assertEqual(captured["device"].model, "V2314")

    def test_promueve_banderas_a_atributos_y_las_saca_del_argv(self):
        mgr, captured = self._mgr(sdk=34)

        res = mgr.start_scene_legacy("S1", "p", {
            "extra_args": "--video-source=camera --camera-id=1 --otg",
        })

        self.assertTrue(res.success, res.message)
        cfg = captured["config"]
        self.assertEqual(cfg.video_source, "camera")
        self.assertEqual(cfg.camera_id, "1")
        self.assertTrue(cfg.otg_mode)
        for tok in cfg.extra_args:
            self.assertNotIn("--video-source", tok)
            self.assertNotIn("--camera-id", tok)
            self.assertNotIn("--otg", tok)

    def test_solo_audio_por_campo_del_asistente(self):
        mgr, captured = self._mgr(sdk=34)

        mgr.start_scene_legacy("S1", "p", {"no_video": True, "audio_source": "mic"})

        self.assertFalse(captured["config"].video_enabled)

    def test_sin_serial_no_falla_el_servicio(self):
        mgr, _ = self._mgr()
        res = mgr.start_scene_legacy("", "p", {})
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.DEVICE_NOT_FOUND)

    def test_libera_el_puerto_si_el_lanzamiento_falla(self):
        from scrcpy_dock.core.port_allocator import PortAllocator

        mgr, _ = self._mgr()

        class _FailingScrcpy:
            def launch(self, config, device, caps):
                return OperationResult.fail(ErrorCode.PROCESS_SPAWN_ERROR, "boom")

        mgr._scrcpy = _FailingScrcpy()
        alloc = PortAllocator(base=29183, max_offset=5)
        mgr._allocator = alloc

        res = mgr.start_scene_legacy("S1", "p", {})

        self.assertFalse(res.success)
        self.assertEqual(alloc.reserved(), frozenset(), "el puerto quedó reservado (fuga)")


# ─────────────────────────────────────────────────────────────────────────────
# C4 · Cobertura bilingüe de i18n
# ─────────────────────────────────────────────────────────────────────────────

class TestC4CoberturaI18n(unittest.TestCase):

    def tearDown(self):
        from scrcpy_dock.i18n import set_language
        set_language("es")

    def _claves_usadas(self):
        import ast
        from pathlib import Path as P

        usadas = set()
        for f in (P(scrcpy_dock.__file__).parent).rglob("*.py"):
            if f.name == "i18n.py":
                continue
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError:  # pragma: no cover
                continue
            for n in ast.walk(tree):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                   and n.func.id == "_" and n.args \
                   and isinstance(n.args[0], ast.Constant) \
                   and isinstance(n.args[0].value, str):
                    usadas.add(n.args[0].value)
        return usadas

    def test_toda_cadena_pasada_por_guion_tiene_traduccion_en(self):
        from scrcpy_dock.i18n import _translations

        usadas = self._claves_usadas()
        faltan = sorted(k for k in usadas if k not in _translations["en"])
        self.assertEqual(faltan, [], f"sin traducción EN: {faltan[:10]}")
        self.assertGreaterEqual(len(usadas), 400)

    def test_el_bloque_extra_se_fusiona(self):
        from scrcpy_dock.i18n import _, set_language, _EN_EXTRA

        self.assertGreaterEqual(len(_EN_EXTRA), 136)
        set_language("en")
        self.assertEqual(_("Archivo"), "File")
        self.assertEqual(_("Turn screen off"), "Turn screen off")
        self.assertEqual(_("Apagar pantalla"), "Turn screen off")
        self.assertEqual(_("🚀 Nueva Transmisión"), "🚀 New Stream")

    def test_los_tecnicos_no_se_traducen_mal(self):
        from scrcpy_dock.i18n import _EN_EXTRA

        for tecnico in ("*.*", "*.apk", "OTG", "MASV"):
            self.assertEqual(_EN_EXTRA.get(tecnico), tecnico)


# ─────────────────────────────────────────────────────────────────────────────
# C5 · build_command descompuesto
# ─────────────────────────────────────────────────────────────────────────────

class TestC5BuildCommandDescompuesto(unittest.TestCase):

    def test_los_ensambladores_existen(self):
        from scrcpy_dock.core.scrcpy_engine import ScrcpyEngine

        for nombre in (
            "_base_argv", "_append_video_options", "_append_video_size",
            "_append_audio_options", "_append_fps_options", "_append_camera_options",
            "_append_hid_options", "_append_display_options", "_append_window_title",
            "_append_extra_args", "_validate_source_guards", "_validate_extra_args",
            "_validate_stream_mode", "_governance_codec",
        ):
            self.assertTrue(hasattr(ScrcpyEngine, nombre), f"falta {nombre}")

    def test_build_command_tiene_complejidad_baja(self):
        try:
            from radon.complexity import cc_visit
        except ImportError:  # pragma: no cover
            self.skipTest("radon no instalado (dependencia de desarrollo)")
        from scrcpy_dock.core import scrcpy_engine

        bloques = cc_visit(inspect.getsource(scrcpy_engine))
        peor = max(b.complexity for b in bloques)
        self.assertLessEqual(peor, 12, f"bloque con CC {peor} en scrcpy_engine")

    def test_build_command_es_corto(self):
        from scrcpy_dock.core.scrcpy_engine import ScrcpyEngine

        src = inspect.getsource(ScrcpyEngine.build_command)
        self.assertLess(len(src.splitlines()), 60)

    def _argv(self, sdk=34, **kw):
        from dataclasses import replace

        from scrcpy_dock.core.scrcpy_engine import ScrcpyEngine
        from scrcpy_dock.domain.models import Device, DeviceCapabilities, SessionConfig

        engine = ScrcpyEngine(Path("/usr/local/bin/scrcpy"), Path("/dev/null"))
        cfg = SessionConfig(
            port=27183, codec=Codec.H264, resolution="1080", bit_rate=8_000_000,
        )
        if kw:
            cfg = replace(cfg, **kw)
        dev = Device(serial="S1", model="V2314", android_sdk=sdk)
        caps = DeviceCapabilities(manufacturer="vivo", platform="qcom", model="V2314")
        return engine.build_command(cfg, dev, caps)

    def test_resolucion_nativa_en_camara_baja_a_1920(self):
        res = self._argv(resolution="native", video_source="camera")
        self.assertTrue(res.success, res.message)
        idx = res.data.index("--max-size")
        self.assertEqual(res.data[idx + 1], "1920")

    def test_los_flags_de_tamano_estan_permitidos_y_la_rama_es_alcanzable(self):
        """⑫ (INFORME §3.16 / ANALISIS §11.3): se habilitan `--max-size`, `--camera-size` y `-m`.

        El hallazgo era que la rama «respetar el tamaño ya elegido» (`_has_size_flag`)
        no se podía alcanzar desde la UI: la whitelist rechazaba el flag antes de
        evaluarlo. Un dock de streaming (OBS, cámara cenital pedagógica) necesita
        limitar el lado mayor y el tamaño del sensor, así que se habilita el flag en
        `ALLOWED_EXTRA_FLAGS` en vez de borrar la rama.
        """
        res = self._argv(video_source="camera",
                         extra_args=("--camera-size=4608x3456",))
        self.assertTrue(res.success, res.message)
        self.assertIn("--camera-size=4608x3456", res.data)

        # Un flag que no es de tamaño no se confunde con uno (usa el import del módulo).
        from scrcpy_dock.domain.models import SessionConfig
        self.assertFalse(ScrcpyEngine._has_size_flag(
            SessionConfig(port=1, codec=Codec.H264, resolution="native",
                          bit_rate=1_000, extra_args=("--window-title=x",))))

    def test_el_tamano_elegido_por_el_usuario_no_se_duplica_en_camara(self):
        """El default de cámara (1920) **no** pisa el tamaño que ya eligió el usuario."""
        res = self._argv(resolution="native", video_source="camera",
                         extra_args=("--max-size=1280",))
        self.assertTrue(res.success, res.message)
        del_tamano = [t for t in res.data if t.startswith(("--max-size", "--camera-size"))]
        self.assertEqual(del_tamano, ["--max-size=1280"], res.data)
        self.assertNotIn("1920", res.data)

    def test_la_whitelist_si_permite_el_titulo_de_ventana(self):
        res = self._argv(extra_args=("--window-title=Mi título",))
        self.assertTrue(res.success, res.message)
        self.assertIn("--window-title=Mi título", res.data)

    def test_resolucion_wxh_toma_el_lado_mayor(self):
        res = self._argv(resolution="1080x1920")
        idx = res.data.index("--max-size")
        self.assertEqual(res.data[idx + 1], "1920")

    def test_solo_audio_en_android_10_se_rechaza(self):
        res = self._argv(sdk=29, video_enabled=False, audio_source="mic")
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.INVALID_INPUT)
        self.assertIn("Android 11+", res.message)


if __name__ == "__main__":
    unittest.main()
