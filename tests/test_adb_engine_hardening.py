"""D3 · Endurecimiento de `AdbEngine`: caminos de error y tracker centinela.

La capa de transporte es el corazón del hardware y era el único componente de
`core/` por debajo del umbral de la Ley 7 (46 %). Estas pruebas cubren lo que
ningún contrato tocaba:

  · los `except` de cada método (`FileNotFoundError`, `TimeoutExpired`, `OSError`)
  · `revert_tcpip` completo, incluidos los **falsos negativos de ADR-009**
    (`error: closed` tras `adb usb` = transición de transporte, no un fallo)
  · `_TrackerThread` entero: protocolo de cabecera hex, `_on_change`,
    reintentos con backoff, daemon muerto y `stop()`

Ninguna prueba abre procesos reales: `subprocess.run` va mockeado y el tracker
recibe un `Popen` falso con un guion de lecturas.

Ejecutable con: python -m unittest discover -s tests
"""
from __future__ import annotations

import io
import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scrcpy_dock.core.adb_engine import AdbEngine, _TrackerThread
from scrcpy_dock.domain.models import DeviceState
from scrcpy_dock.errors import ErrorCode

from tests.contracts.helpers import fake_completed_process

ADB = Path("/usr/bin/adb")


class _ChunkReader:
    """`stdout` que entrega lecturas guionizadas y luego EOF."""

    def __init__(self, chunks):
        self._chunks = list(chunks)
        self.lecturas: list[int] = []

    def read(self, n=-1):
        self.lecturas.append(n)
        if not self._chunks:
            return ""
        return self._chunks.pop(0)


class _FakeTrackerProc:
    """`Popen` falso para `_TrackerThread._run_once`."""

    def __init__(self, chunks=(), returncode=0, alive=False, wait_raises=False):
        self.stdout = _ChunkReader(chunks)
        self.stderr = io.StringIO("")
        self.returncode = returncode
        self._alive = alive
        self._wait_raises = wait_raises
        self.terminated = False
        self.killed = False

    def poll(self):
        return None if self._alive else self.returncode

    def terminate(self):
        self.terminated = True
        self._alive = False

    def wait(self, timeout=None):
        if self._wait_raises:
            raise subprocess.TimeoutExpired(cmd="adb", timeout=timeout)
        self._alive = False
        return self.returncode

    def kill(self):
        self.killed = True


class _FastStopEvent:
    """`Event` que nunca espera de verdad: mantiene las pruebas en milisegundos."""

    def __init__(self, early=False):
        self._set = False
        self._early = early

    def is_set(self):
        return self._set

    def set(self):
        self._set = True

    def wait(self, timeout=None):
        if self._early:
            self._set = True          # simula un stop durante el backoff
        return self._set


def _tracker(**kwargs):
    """Tracker con callbacks registradores y sin threads reales."""
    cambios: list = []
    muertes: list = []
    kwargs.setdefault("adb_binary", ADB)
    kwargs.setdefault("port", 5037)
    tracker = _TrackerThread(
        on_change=kwargs.pop("on_change", cambios.append),
        on_daemon_dead=kwargs.pop("on_daemon_dead", muertes.append),
        **kwargs,
    )
    tracker.cambios = cambios
    tracker.muertes = muertes
    return tracker


# ─────────────────────────────────────────────────────────────────────────────
# Errores de arranque del daemon
# ─────────────────────────────────────────────────────────────────────────────

class TestArranqueDelDaemon(unittest.TestCase):

    def setUp(self):
        self.engine = AdbEngine(ADB)

    @patch("subprocess.run")
    def test_binario_ausente(self, run_mock):
        run_mock.side_effect = FileNotFoundError("no such file")
        res = self.engine._try_start_server(5037)
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.ADB_NOT_FOUND)

    @patch("subprocess.run")
    def test_timeout_de_arranque(self, run_mock):
        run_mock.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=10)
        res = self.engine._try_start_server(5037)
        self.assertEqual(res.error, ErrorCode.ADB_SERVER_FAILED)

    @patch("subprocess.run")
    def test_error_de_sistema_al_arrancar(self, run_mock):
        run_mock.side_effect = OSError("permiso denegado")
        res = self.engine._try_start_server(5037)
        self.assertEqual(res.error, ErrorCode.ADB_SERVER_FAILED)

    @patch("subprocess.run")
    def test_arranque_falla_con_mensaje(self, run_mock):
        run_mock.return_value = fake_completed_process(stderr="daemon murió", returncode=1)
        res = self.engine._try_start_server(5037)
        self.assertFalse(res.success)
        self.assertIn("daemon murió", res.message)

    @patch("subprocess.run")
    def test_error_no_bind_no_se_reintenta(self, run_mock):
        """Un binario ausente no debe provocar 4 intentos: se propaga tal cual."""
        run_mock.side_effect = FileNotFoundError("sin adb")
        res = self.engine.start_daemon()
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.ADB_NOT_FOUND)
        self.assertEqual(run_mock.call_count, 1)

    def test_bind_failure_con_mensaje_vacio(self):
        self.assertFalse(AdbEngine._is_bind_failure(None))
        self.assertFalse(AdbEngine._is_bind_failure(""))
        self.assertTrue(AdbEngine._is_bind_failure("cannot bind 'tcp:5037'"))


# ─────────────────────────────────────────────────────────────────────────────
# list_devices / _parse_device_line
# ─────────────────────────────────────────────────────────────────────────────

class TestListDevicesErrores(unittest.TestCase):

    def setUp(self):
        self.engine = AdbEngine(ADB)

    @patch("subprocess.run")
    def test_binario_ausente(self, run_mock):
        run_mock.side_effect = FileNotFoundError("x")
        self.assertEqual(self.engine.list_devices().error, ErrorCode.ADB_NOT_FOUND)

    @patch("subprocess.run")
    def test_timeout(self, run_mock):
        run_mock.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=10)
        self.assertEqual(self.engine.list_devices().error, ErrorCode.ADB_SERVER_FAILED)

    @patch("subprocess.run")
    def test_returncode_no_cero(self, run_mock):
        run_mock.return_value = fake_completed_process(stderr="daemon caído", returncode=1)
        res = self.engine.list_devices()
        self.assertFalse(res.success)
        self.assertIn("daemon caído", res.message)

    @patch("subprocess.run")
    def test_linea_con_estado_desconocido_se_ignora(self, run_mock):
        run_mock.return_value = fake_completed_process(stdout=(
            "List of devices attached\n"
            "HWY9\tdevice\n"
            "RARO\testado_raro\n"
        ))
        res = self.engine.list_devices()
        self.assertTrue(res.success)
        self.assertEqual([d.serial for d in res.data], ["HWY9"])

    def test_parser_descarta_cabecera_vacia_y_corta(self):
        self.assertIsNone(AdbEngine._parse_device_line(""))
        self.assertIsNone(AdbEngine._parse_device_line("   "))
        self.assertIsNone(AdbEngine._parse_device_line("List of devices attached"))
        self.assertIsNone(AdbEngine._parse_device_line("SOLOUNTOKEN"))
        self.assertIsNone(AdbEngine._parse_device_line("SER estado_desconocido"))

    def test_parser_toma_model_del_token(self):
        dev = AdbEngine._parse_device_line(
            "HWY9 device product:HUAWEI_Y9 model:HUAWEI_Y9_Prime device:HWY9",
        )
        self.assertEqual(dev.serial, "HWY9")
        self.assertEqual(dev.model, "HUAWEI_Y9_Prime")
        self.assertEqual(dev.state, DeviceState.DEVICE)

    def test_parser_sin_model_usa_el_serial(self):
        dev = AdbEngine._parse_device_line("HWY9 unauthorized")
        self.assertEqual(dev.model, "HWY9")
        self.assertEqual(dev.state, DeviceState.UNAUTHORIZED)


# ─────────────────────────────────────────────────────────────────────────────
# get_properties / start_tcpip
# ─────────────────────────────────────────────────────────────────────────────

class TestPropiedadesYTcpipErrores(unittest.TestCase):

    def setUp(self):
        self.engine = AdbEngine(ADB)

    @patch("subprocess.run")
    def test_getprop_binario_ausente(self, run_mock):
        run_mock.side_effect = FileNotFoundError("x")
        self.assertEqual(self.engine.get_properties("HWY9").error, ErrorCode.ADB_NOT_FOUND)

    @patch("subprocess.run")
    def test_getprop_timeout(self, run_mock):
        run_mock.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=10)
        self.assertEqual(self.engine.get_properties("HWY9").error, ErrorCode.ADB_SERVER_FAILED)

    @patch("subprocess.run")
    def test_getprop_dispositivo_inexistente(self, run_mock):
        run_mock.return_value = fake_completed_process(stderr="device not found", returncode=1)
        res = self.engine.get_properties("HWY9")
        self.assertEqual(res.error, ErrorCode.DEVICE_NOT_FOUND)

    @patch("subprocess.run")
    def test_tcpip_binario_ausente(self, run_mock):
        run_mock.side_effect = FileNotFoundError("x")
        self.assertEqual(self.engine.start_tcpip("HWY9").error, ErrorCode.ADB_NOT_FOUND)

    @patch("subprocess.run")
    def test_tcpip_timeout(self, run_mock):
        run_mock.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=10)
        self.assertEqual(self.engine.start_tcpip("HWY9").error, ErrorCode.ADB_SERVER_FAILED)

    @patch("subprocess.run")
    def test_tcpip_fallido_no_marca_el_serial(self, run_mock):
        """Contrato: si `tcpip` falla, el revert posterior debe ser no-op."""
        run_mock.return_value = fake_completed_process(stderr="boom", returncode=1)
        self.assertFalse(self.engine.start_tcpip("HWY9").success)

        run_mock.reset_mock()
        self.assertTrue(self.engine.revert_tcpip("HWY9").success)
        run_mock.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# revert_tcpip · incluidos los falsos negativos de ADR-009
# ─────────────────────────────────────────────────────────────────────────────

class TestRevertTcpip(unittest.TestCase):

    def setUp(self):
        self.engine = AdbEngine(ADB)
        self.engine._activated_by_masv.add("HWY9")

    @patch("subprocess.run")
    def test_binario_ausente(self, run_mock):
        run_mock.side_effect = FileNotFoundError("x")
        res = self.engine.revert_tcpip("HWY9")
        self.assertEqual(res.error, ErrorCode.ADB_NOT_FOUND)

    @patch("subprocess.run")
    def test_timeout(self, run_mock):
        run_mock.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=10)
        res = self.engine.revert_tcpip("HWY9")
        self.assertEqual(res.error, ErrorCode.LOCKDOWN_FAILED)

    @patch("subprocess.run")
    def test_error_closed_es_exito_funcional(self, run_mock):
        """EMUI/Android 10: `adb usb` cierra el socket TCP y devuelve 'error: closed'.

        El efecto es el deseado (vuelve a USB), así que NO es un fallo: si se
        tratara como tal, el usuario vería un error de blindaje inexistente.
        """
        run_mock.return_value = fake_completed_process(stdout="error: closed", returncode=1)

        res = self.engine.revert_tcpip("HWY9")

        self.assertTrue(res.success, res.message)
        self.assertIn("transición", res.message)

    @patch("subprocess.run")
    def test_device_not_found_tambien_es_transicion(self, run_mock):
        run_mock.return_value = fake_completed_process(stdout="device not found", returncode=1)
        self.assertTrue(self.engine.revert_tcpip("HWY9").success)

    @patch("subprocess.run")
    def test_un_error_real_si_falla(self, run_mock):
        run_mock.return_value = fake_completed_process(stdout="permission denied", returncode=1)
        res = self.engine.revert_tcpip("HWY9")
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.LOCKDOWN_FAILED)
        self.assertIn("permission denied", res.message)

    @patch("subprocess.run")
    def test_el_serial_se_descarta_pase_lo_que_pase(self, run_mock):
        """Tras intentar el revert, MASV ya no lo declara bajo su control."""
        for stdout, returncode in (("error: closed", 1), ("permission denied", 1), ("", 0)):
            with self.subTest(salida=stdout or "ok"):
                engine = AdbEngine(ADB)
                engine._activated_by_masv.add("HWY9")
                run_mock.return_value = fake_completed_process(stdout=stdout, returncode=returncode)

                engine.revert_tcpip("HWY9")

                self.assertNotIn("HWY9", engine._activated_by_masv)

    @patch("subprocess.run")
    def test_usa_el_binario_y_el_socket_aislado(self, run_mock):
        run_mock.return_value = fake_completed_process()
        self.engine.revert_tcpip("HWY9")
        self.assertEqual(run_mock.call_args.args[0], [str(Path("/usr/bin/adb")), "-s", "HWY9", "usb"])
        self.assertIn("ADB_SERVER_SOCKET", run_mock.call_args.kwargs["env"])


# ─────────────────────────────────────────────────────────────────────────────
# connect_wifi / disconnect_wifi / _run / instalación
# ─────────────────────────────────────────────────────────────────────────────

class TestWifiYPrimitivas(unittest.TestCase):

    def setUp(self):
        self.engine = AdbEngine(ADB)

    @patch("subprocess.run")
    def test_connect_binario_ausente(self, run_mock):
        run_mock.side_effect = FileNotFoundError("x")
        self.assertEqual(self.engine.connect_wifi("1.2.3.4").error, ErrorCode.ADB_NOT_FOUND)

    @patch("subprocess.run")
    def test_connect_timeout(self, run_mock):
        run_mock.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=15)
        self.assertEqual(self.engine.connect_wifi("1.2.3.4").error, ErrorCode.CONNECTION_REFUSED)

    @patch("subprocess.run")
    def test_connect_returncode_no_cero(self, run_mock):
        run_mock.return_value = fake_completed_process(stderr="refused", returncode=1)
        self.assertEqual(self.engine.connect_wifi("1.2.3.4").error, ErrorCode.CONNECTION_REFUSED)

    @patch("subprocess.run")
    def test_connect_con_unable_to_connect_y_codigo_cero(self, run_mock):
        """`adb connect` puede devolver 0 y no haber conectado: hay que mirar stdout."""
        run_mock.return_value = fake_completed_process(
            stdout="unable to connect to 1.2.3.4:5555", returncode=0,
        )
        res = self.engine.connect_wifi("1.2.3.4")
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.CONNECTION_REFUSED)

    @patch("subprocess.run")
    def test_disconnect_errores(self, run_mock):
        run_mock.side_effect = FileNotFoundError("x")
        self.assertEqual(self.engine.disconnect_wifi("HWY9").error, ErrorCode.ADB_NOT_FOUND)

        run_mock.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=10)
        self.assertEqual(self.engine.disconnect_wifi("HWY9").error, ErrorCode.CONNECTION_REFUSED)

        run_mock.side_effect = None
        run_mock.return_value = fake_completed_process(stderr="offline", returncode=1)
        self.assertEqual(self.engine.disconnect_wifi("HWY9").error, ErrorCode.CONNECTION_REFUSED)

    @patch("subprocess.run")
    def test_disconnect_ok(self, run_mock):
        run_mock.return_value = fake_completed_process(stdout="disconnected")
        self.assertTrue(self.engine.disconnect_wifi("HWY9").success)

    @patch("subprocess.run")
    def test_run_error_de_sistema(self, run_mock):
        run_mock.side_effect = OSError("permiso denegado")
        self.assertEqual(self.engine._run(["devices"]).error, ErrorCode.ADB_SERVER_FAILED)

        run_mock.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=10)
        self.assertEqual(self.engine._run(["devices"]).error, ErrorCode.ADB_SERVER_FAILED)

    @patch("subprocess.run")
    def test_shell_hereda_el_fallo_del_motor_y_respeta_el_codigo_pedido(self, run_mock):
        run_mock.side_effect = OSError("boom")
        self.assertEqual(self.engine.shell("HWY9", "ls").error, ErrorCode.ADB_SERVER_FAILED)

        run_mock.side_effect = None
        run_mock.return_value = fake_completed_process(stderr="muy mal", returncode=1)
        res = self.engine.shell("HWY9", "ls", error_code=ErrorCode.APK_INSTALL_FAILED)
        self.assertEqual(res.error, ErrorCode.APK_INSTALL_FAILED)
        self.assertIn("muy mal", res.message)

    @patch("subprocess.run")
    def test_install_con_el_motor_caido(self, run_mock):
        run_mock.side_effect = FileNotFoundError("x")
        self.assertEqual(self.engine.install("HWY9", "/tmp/a.apk").error, ErrorCode.ADB_NOT_FOUND)

    @patch("subprocess.run")
    def test_kill_server_con_el_motor_caido_y_fallido(self, run_mock):
        run_mock.side_effect = FileNotFoundError("x")
        self.assertEqual(self.engine.kill_server().error, ErrorCode.ADB_NOT_FOUND)

        run_mock.side_effect = None
        run_mock.return_value = fake_completed_process(stderr="no puedo", returncode=1)
        res = self.engine.kill_server()
        self.assertFalse(res.success)
        self.assertIn("no puedo", res.message)


# ─────────────────────────────────────────────────────────────────────────────
# tracker centinela: protocolo, reintentos y parada
# ─────────────────────────────────────────────────────────────────────────────

class TestParserPorDefectoDelTracker(unittest.TestCase):

    def test_descarta_lineas_invalidas(self):
        tracker = _tracker(parse_line=None)
        self.assertIsNone(tracker._default_parse_line(""))
        self.assertIsNone(tracker._default_parse_line("SOLOUNO"))
        self.assertIsNone(tracker._default_parse_line("HWY9 estado_raro"))

    def test_acepta_estado_conocido(self):
        tracker = _tracker(parse_line=None)
        dev = tracker._default_parse_line("HWY9\toffline")
        self.assertEqual(dev.serial, "HWY9")
        self.assertEqual(dev.model, "HWY9", "track-devices no trae model:")
        self.assertEqual(dev.state, DeviceState.OFFLINE)

    def test_usa_el_parser_inyectado(self):
        parser = MagicMock(return_value=None)
        tracker = _tracker(parse_line=parser)
        tracker._default_parse_line("x")
        parser.assert_not_called()          # el inyectado sustituye al de defecto
        tracker._parse_line("HWY9 device")
        parser.assert_called_once_with("HWY9 device")


class TestTrackerRunOnce(unittest.TestCase):

    def _run_once(self, proc, **kwargs):
        tracker = _tracker(**kwargs)
        with patch("subprocess.Popen", return_value=proc):
            return tracker._run_once(), tracker

    def test_eof_inmediato_limpio(self):
        proc = _FakeTrackerProc(chunks=[], returncode=0, alive=False)
        limpio, tracker = self._run_once(proc)
        self.assertTrue(limpio)
        self.assertEqual(tracker.cambios, [])

    def test_proceso_no_arranca(self):
        tracker = _tracker()
        with patch("subprocess.Popen", side_effect=FileNotFoundError("sin adb")):
            self.assertFalse(tracker._run_once())

    def test_cabecera_incompleta_se_descarta(self):
        proc = _FakeTrackerProc(chunks=["00"], returncode=0)
        limpio, tracker = self._run_once(proc)
        self.assertTrue(limpio)
        self.assertEqual(tracker.cambios, [])

    def test_cabecera_no_hexadecimal_se_salta(self):
        proc = _FakeTrackerProc(chunks=["ZZZZ", ""], returncode=0)
        _, tracker = self._run_once(proc)
        self.assertEqual(tracker.cambios, [])

    def test_longitud_cero_notifica_lista_vacia(self):
        proc = _FakeTrackerProc(chunks=["0000", ""], returncode=0)
        _, tracker = self._run_once(proc)
        self.assertEqual(tracker.cambios, [[]])

    def test_payload_con_dispositivos(self):
        payload = "HWY9\tdevice\nSM1\tunauthorized\n"
        proc = _FakeTrackerProc(chunks=[f"{len(payload):04x}", payload, ""], returncode=0)

        _, tracker = self._run_once(proc)

        self.assertEqual(len(tracker.cambios), 1)
        seriales = [d.serial for d in tracker.cambios[0]]
        self.assertEqual(seriales, ["HWY9", "SM1"])
        self.assertEqual(tracker.cambios[0][1].state, DeviceState.UNAUTHORIZED)

    def test_payload_ilegible_corta_el_bucle(self):
        proc = _FakeTrackerProc(chunks=["0010", ""], returncode=0)
        _, tracker = self._run_once(proc)
        self.assertEqual(tracker.cambios, [])

    def test_lineas_no_parseables_se_filtran(self):
        payload = "BASURA\nHWY9\tdevice\n"
        proc = _FakeTrackerProc(chunks=[f"{len(payload):04x}", payload, ""], returncode=0)
        _, tracker = self._run_once(proc)
        self.assertEqual([d.serial for d in tracker.cambios[0]], ["HWY9"])

    def test_callback_que_revienta_no_mata_el_hilo(self):
        def explosivo(_devices):
            raise RuntimeError("la UI murió")

        payload = "HWY9\tdevice\n"
        proc = _FakeTrackerProc(chunks=[f"{len(payload):04x}", payload, ""], returncode=0)
        limpio, _ = self._run_once(proc, on_change=explosivo)
        self.assertTrue(limpio)

    def test_proceso_vivo_se_termina_en_el_finally(self):
        proc = _FakeTrackerProc(chunks=[], returncode=0, alive=True)
        limpio, _ = self._run_once(proc)
        self.assertTrue(proc.terminated)
        self.assertFalse(proc.killed)
        self.assertTrue(limpio)

    def test_si_no_termina_se_mata(self):
        proc = _FakeTrackerProc(chunks=[], returncode=0, alive=True, wait_raises=True)
        self._run_once(proc)
        self.assertTrue(proc.terminated)
        self.assertTrue(proc.killed, "un proceso que ignora terminate debe recibir kill")

    def test_codigo_de_salida_no_cero_no_es_eof_limpio(self):
        proc = _FakeTrackerProc(chunks=[], returncode=1, alive=False)
        limpio, _ = self._run_once(proc)
        self.assertFalse(limpio)


class TestTrackerRun(unittest.TestCase):

    def test_agota_reintentos_y_avisa_del_daemon_muerto(self):
        tracker = _tracker(max_attempts=3)
        tracker._stop_event = _FastStopEvent()

        with patch.object(tracker, "_run_once", return_value=False) as run_once:
            tracker.run()

        self.assertEqual(run_once.call_count, 3)
        self.assertEqual(tracker.muertes, [ErrorCode.ADB_DAEMON_DEAD])

    def test_una_salida_limpia_inicial_no_penaliza_backoff(self):
        """`track-devices` que sale limpio tras un evento normal no es un fallo real."""
        intentos = {"n": 0}

        def run_once():
            intentos["n"] += 1
            return True          # siempre EOF limpio

        tracker = _tracker(max_attempts=2)
        tracker._stop_event = _FastStopEvent()
        with patch.object(tracker, "_run_once", side_effect=run_once):
            tracker.run()

        # 2 intentos declarados, pero el primero no penaliza: se hicieron ≥ 3 pasadas
        self.assertGreaterEqual(intentos["n"], 2)

    def test_el_stop_durante_el_backoff_corta_sin_avisar(self):
        tracker = _tracker(max_attempts=5)
        tracker._stop_event = _FastStopEvent(early=True)

        with patch.object(tracker, "_run_once", return_value=False) as run_once:
            tracker.run()

        self.assertEqual(run_once.call_count, 1)
        self.assertEqual(tracker.muertes, [], "un stop deliberado no es 'daemon muerto'")

    def test_un_stop_previo_no_lanza_nada(self):
        tracker = _tracker(max_attempts=5)
        tracker._stop_event = _FastStopEvent()
        tracker._stop_event.set()

        with patch.object(tracker, "_run_once") as run_once:
            tracker.run()

        run_once.assert_not_called()

    def test_el_stop_dentro_de_run_once_corta_de_inmediato(self):
        """Si el cierre llega mientras se lee el stream, no cuenta como reintento."""
        tracker = _tracker(max_attempts=5)
        tracker._stop_event = _FastStopEvent()

        def run_once():
            tracker._stop_event.set()
            return False

        with patch.object(tracker, "_run_once", side_effect=run_once):
            tracker.run()

        self.assertEqual(tracker.muertes, [])

    def test_callback_de_muerte_que_revienta_no_propaga(self):
        def explosivo(_code):
            raise RuntimeError("la UI murió")

        tracker = _tracker(max_attempts=1, on_daemon_dead=explosivo)
        tracker._stop_event = _FastStopEvent()
        with patch.object(tracker, "_run_once", return_value=False):
            tracker.run()          # no debe propagar la excepción del callback

    def test_stop_es_idempotente_y_no_espera_si_no_arranco(self):
        tracker = _tracker()
        tracker.stop()
        tracker.stop()
        self.assertTrue(tracker._stop_event.is_set())
        self.assertFalse(tracker.is_alive())

    def test_stop_espera_al_hilo_vivo(self):
        tracker = _tracker()
        with patch.object(tracker, "is_alive", return_value=True), \
             patch.object(tracker, "join") as join:
            tracker.stop(timeout=1.5)

        join.assert_called_once_with(timeout=1.5)
        self.assertTrue(tracker._stop_event.is_set())


class TestEngineGestionaElTracker(unittest.TestCase):

    def setUp(self):
        self.engine = AdbEngine(ADB)

    def test_arranca_y_registra_el_tracker(self):
        with patch.object(_TrackerThread, "start", return_value=None) as start:
            res = self.engine.track_devices_async(lambda d: None, lambda c: None)

        self.assertTrue(res.success)
        self.assertIs(self.engine._tracker, res.data)
        start.assert_called_once()

    def test_un_tracker_vivo_no_se_duplica(self):
        vivo = MagicMock()
        vivo.is_alive.return_value = True
        self.engine._tracker = vivo

        res = self.engine.track_devices_async(lambda d: None, lambda c: None)

        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.DEVICE_BUSY)

    def test_stop_tracker_es_idempotente(self):
        self.engine.stop_tracker()          # sin tracker: no-op silencioso

        tracker = MagicMock()
        self.engine._tracker = tracker
        self.engine.stop_tracker()

        tracker.stop.assert_called_once_with(timeout=2.0)
        self.assertIsNone(self.engine._tracker)

    def test_el_tracker_usa_el_puerto_efectivo(self):
        self.engine._effective_port = 5038
        capturado = {}

        def _captura(**kwargs):
            capturado.update(kwargs)
            return MagicMock(is_alive=lambda: False)

        with patch("scrcpy_dock.core.adb_engine._TrackerThread", side_effect=_captura), \
             patch.object(_TrackerThread, "start", return_value=None):
            self.engine.track_devices_async(lambda d: None, lambda c: None)

        self.assertEqual(capturado["port"], 5038)
        self.assertEqual(capturado["adb_binary"], ADB)
        self.assertIs(capturado["parse_line"], self.engine._parse_device_line)

class TestAdbEngineDegradadoSinBinario(unittest.TestCase):
    """Verifica el contrato degradado de AdbEngine en una máquina virgen (ADR-007)."""

    def test_adb_engine_none_no_lanza_y_degrada_a_simbolico(self):
        engine = AdbEngine(None)
        self.assertEqual(engine._adb_binary, Path("adb"))

    def test_adb_engine_rebind_none_no_lanza(self):
        engine = AdbEngine("/usr/bin/adb")
        engine.rebind(None)
        self.assertEqual(engine._adb_binary, Path("adb"))

    def test_device_manager_y_session_manager_sin_adb_no_revientan(self):
        with patch("scrcpy_dock.managers.find_portable_binaries", return_value=(None, None)):
            from scrcpy_dock.managers import DeviceManager, SessionManager
            dm = DeviceManager(adb_engine=None)
            self.assertEqual(dm._adb._adb_binary, Path("adb"))
            sm = SessionManager(log_q_or_adb=None, adb_engine=None)
            self.assertEqual(sm._adb._adb_binary, Path("adb"))


if __name__ == "__main__":
    unittest.main()

