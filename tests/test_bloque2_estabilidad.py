"""Bloque 2 · Estabilidad: los cuatro defectos que aún podían morder.

Cubre:

  · ② `SingleInstance` — un fallo de socket ajeno a "ya está corriendo" no puede
    bloquear el arranque, y el socket debe permitir reentrar tras un cierre abrupto.
  · ④ `_TrackerThread.stop()` — al parar, el proceso que bloquea la lectura se
    termina, de modo que el hilo **no** queda colgado en `read(4)`.
  · ⑤ `load_config()` — tocar la configuración cargada no puede mutar la plantilla
    global `DEFAULT_CONFIG` (copia superficial → `profiles`/`security` compartidos).
  · ⑥ `is_private_ip` — el gestor y el servicio deben clasificar igual: `0.0.0.0`
    y el broadcast **no** son direcciones privadas utilizables.

Las cuatro se escribieron antes del arreglo (fase RED) y se verificaron por mutación
después (fase GREEN). Ejecutable con el runner del CI:
    python -m unittest discover -s tests
"""
from __future__ import annotations

import copy
import errno
import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import scrcpy_dock.utils as utils
from scrcpy_dock.security import SecurityManager
from scrcpy_dock.services.security_service import SecurityService
from scrcpy_dock.utils import SingleInstance

from tests.test_adb_engine_hardening import _FakeTrackerProc, _tracker


def _puerto_libre() -> int:
    """Un puerto TCP libre en loopback (para no chocar con nada del sistema)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _esperar(condicion, limite: float = 3.0, paso: float = 0.01) -> bool:
    """Espera a que se cumpla una condición, sin dormir a lo bruto."""
    fin = time.monotonic() + limite
    while time.monotonic() < fin:
        if condicion():
            return True
        time.sleep(paso)
    return condicion()


# ─────────────────────────────────────────────────────────────────────────────
# ② SingleInstance
# ─────────────────────────────────────────────────────────────────────────────

class TestSingleInstanceRobusta(unittest.TestCase):
    """El cerrojo de instancia única no puede confundir "puerto ocupado" con "todo roto"."""

    def setUp(self):
        self.puerto = _puerto_libre()

    def test_la_segunda_instancia_no_entra(self):
        primera = SingleInstance(port=self.puerto)
        self.addCleanup(primera.release)
        self.assertTrue(primera.acquire())

        segunda = SingleInstance(port=self.puerto)
        self.addCleanup(segunda.release)
        self.assertFalse(segunda.acquire(), "la segunda instancia debe detectarse")

    def test_tras_liberar_puede_entrar_otra(self):
        primera = SingleInstance(port=self.puerto)
        self.assertTrue(primera.acquire())
        primera.release()

        segunda = SingleInstance(port=self.puerto)
        self.addCleanup(segunda.release)
        self.assertTrue(segunda.acquire(), "tras liberar, el puerto debe quedar libre")

    def test_el_socket_se_prepara_para_reentrar(self):
        """SO_REUSEADDR antes del bind: sin él, un cierre abrupto deja el puerto inservible."""
        instancia = SingleInstance(port=self.puerto)
        self.addCleanup(instancia.release)
        self.assertTrue(instancia.acquire())

        activo = instancia.sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)
        self.assertTrue(bool(activo), "el socket debe llevar SO_REUSEADDR")

    def test_un_error_ajeno_no_se_confunde_con_ya_en_ejecucion(self):
        """EACCES/ENOMEM/EAFNOSUPPORT no significan "la app ya está abierta".

        Bloquear el arranque por eso era el falso positivo que dejaba al usuario
        sin poder abrir MASV: ante un error distinto de EADDRINUSE se degrada
        (se arranca, con aviso) en vez de mentir.
        """
        with patch.object(socket.socket, "bind",
                          side_effect=OSError(errno.EACCES, "permiso denegado")):
            instancia = SingleInstance(port=self.puerto)
            self.addCleanup(instancia.release)
            with self.assertLogs("scrcpy_dock.utils", level="WARNING"):
                self.assertTrue(instancia.acquire(),
                                "un fallo ajeno no puede simular 'ya está en ejecución'")

    def test_stop_es_idempotente(self):
        instancia = SingleInstance(port=self.puerto)
        instancia.release()
        instancia.release()          # no debe lanzar

    def test_reentrada_con_el_puerto_en_time_wait(self):
        """El caso que motiva `SO_REUSEADDR`: puerto en TIME_WAIT tras un cierre con conexión.

        Sin `SO_REUSEADDR` **antes** del bind, el nuevo proceso recibe `EADDRINUSE` y
        el usuario ve el falso "ya está en ejecución" (caso real: `_restart_app()`).
        """
        puerto = _puerto_libre()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
            servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            servidor.bind(("127.0.0.1", puerto))
            servidor.listen(1)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente:
                cliente.connect(("127.0.0.1", puerto))
                conexion, _ = servidor.accept()
                conexion.close()        # el servidor cierra primero → TIME_WAIT
        _esperar(lambda: False, limite=0.2)   # deja asentar el estado del kernel

        instancia = SingleInstance(port=puerto)
        self.addCleanup(instancia.release)
        self.assertTrue(instancia.acquire(),
                        "el puerto en TIME_WAIT no puede bloquear el arranque")


# ─────────────────────────────────────────────────────────────────────────────
# ⑤ load_config no comparte la plantilla
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadConfigSinAlias(unittest.TestCase):
    """La config cargada es del usuario; la plantilla `DEFAULT_CONFIG` no se toca."""

    def setUp(self):
        self.plantilla_original = copy.deepcopy(utils.DEFAULT_CONFIG)
        # Si la prueba destapa el alias (fase RED), la plantilla global se habría
        # mutado: se restaura siempre para no contaminar al resto de la suite.
        self.addCleanup(lambda: utils.DEFAULT_CONFIG.clear() or
                        utils.DEFAULT_CONFIG.update(self.plantilla_original))

    def _cargar_sin_fichero(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(utils, "CONFIG_FILE", str(Path(tmp) / "config.json")):
                return utils.load_config()

    def test_mutar_la_config_cargada_no_muta_la_plantilla(self):
        cfg = self._cargar_sin_fichero()

        cfg["profiles"]["Inventado"] = {"bitrate": "1M"}
        cfg["security"]["auto_lockdown_on_exit"] = False
        cfg["theme"] = "inexistente"

        self.assertNotIn("Inventado", utils.DEFAULT_CONFIG["profiles"],
                         "profiles se está compartiendo por referencia")
        self.assertTrue(utils.DEFAULT_CONFIG["security"]["auto_lockdown_on_exit"],
                        "security se está compartiendo por referencia")
        self.assertNotEqual(utils.DEFAULT_CONFIG["theme"], "inexistente")

    def test_lo_que_injerta_la_fusion_tampoco_comparte_memoria(self):
        """§3.11-bis: con un fichero **parcial**, la fusión no injerta referencias.

        Caso real: un `config.json` de una versión anterior que no trae la clave
        `security`. La fusión con la plantilla hacía `data[k] = v`, de modo que el
        diccionario cargado **era** el sub-diccionario global: mutarlo mutaba
        `DEFAULT_CONFIG` (el mismo defecto del ⑤, por otra puerta).
        """
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "config.json"
            ruta.write_text(json.dumps({"theme": "oscuro", "security": {}}), encoding="utf-8")
            with patch.object(utils, "CONFIG_FILE", str(ruta)):
                cfg = utils.load_config()

            # `profiles` faltaba entero (rama de nivel 1) y dentro de `security` faltaban
            # todas las claves (rama de nivel 2): se ejercitan las dos.
            cfg["profiles"]["Inventado"] = {"bitrate": "1M"}
            cfg["security"]["inventado"] = True
            cfg["security"]["auto_lockdown_on_exit"] = False

            # Y lo que de verdad delata el alias de nivel 2: mutar **en el sitio** un valor
            # mutable de la plantilla (`blocked_ips` es lista, `trusted_devices` dict). Con
            # escalares inmutables, reasignar esconde la compartición.
            cfg["security"]["blocked_ips"].append("10.0.0.9")
            cfg["security"]["trusted_devices"]["SERIAL-FALSO"] = {"label": "x"}

            self.assertNotIn("Inventado", utils.DEFAULT_CONFIG["profiles"],
                             "la fusión de nivel 1 comparte por referencia")
            self.assertNotIn("inventado", utils.DEFAULT_CONFIG["security"],
                             "la fusión de nivel 2 comparte por referencia")
            self.assertTrue(utils.DEFAULT_CONFIG["security"]["auto_lockdown_on_exit"],
                            "security se está compartiendo por referencia")
            self.assertEqual(utils.DEFAULT_CONFIG["security"]["blocked_ips"], [],
                             "blocked_ips (lista) se comparte por referencia")
            self.assertNotIn("SERIAL-FALSO", utils.DEFAULT_CONFIG["security"]["trusted_devices"],
                             "trusted_devices (dict) se comparte por referencia")

    def test_config_corrupta_tampoco_contamina_la_plantilla(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "config.json"
            ruta.write_text("{esto no es json", encoding="utf-8")
            with patch.object(utils, "CONFIG_FILE", str(ruta)):
                cfg = utils.load_config()

        cfg["profiles"]["Inventado"] = {}
        self.assertNotIn("Inventado", utils.DEFAULT_CONFIG["profiles"])


# ─────────────────────────────────────────────────────────────────────────────
# ⑥ is_private_ip unificada
# ─────────────────────────────────────────────────────────────────────────────

class TestIsPrivateIpUnificada(unittest.TestCase):
    """Gestor y servicio son la misma respuesta: una sola implementación."""

    UTILIZABLES = ("192.168.1.10", "10.0.0.5", "172.16.0.1", "127.0.0.1", "[::1]", "fe80::1")
    NO_UTILIZABLES = ("0.0.0.0", "255.255.255.255", "::", "8.8.8.8", "1.1.1.1",
                      "localhost", "", "   ", None, "999.999.1.1")

    def test_ambos_coinciden_en_todas_las_entradas(self):
        for host in self.UTILIZABLES + self.NO_UTILIZABLES:
            with self.subTest(host=host):
                self.assertEqual(
                    SecurityManager.is_private_ip(host),      # type: ignore[arg-type]
                    SecurityService.is_private_ip(host),      # type: ignore[arg-type]
                    f"gestor y servicio discrepan con {host!r}",
                )

    def test_las_direcciones_no_utilizables_no_son_privadas(self):
        for host in self.NO_UTILIZABLES:
            with self.subTest(host=host):
                self.assertFalse(SecurityManager.is_private_ip(host),  # type: ignore[arg-type]
                                 f"{host!r} no es una dirección privada utilizable")

    def test_las_privadas_de_verdad_siguen_siendo_privadas(self):
        for host in self.UTILIZABLES:
            with self.subTest(host=host):
                self.assertTrue(SecurityManager.is_private_ip(host))


# ─────────────────────────────────────────────────────────────────────────────
# ④ El tracker se desbloquea al parar
# ─────────────────────────────────────────────────────────────────────────────

class _LectorQueBloquea:
    """`stdout` que se queda en `read()` hasta que el proceso muere (como un pipe real)."""

    def __init__(self):
        self.liberar = threading.Event()
        self.lecturas: list = []

    def read(self, n=-1):
        self.lecturas.append(n)
        self.liberar.wait(timeout=5.0)
        return ""


class _ProcQueBloquea(_FakeTrackerProc):
    """Proceso cuyo stdout bloquea hasta que se le termina."""

    def __init__(self):
        super().__init__(chunks=[], returncode=0, alive=True)
        self.stdout = _LectorQueBloquea()

    def terminate(self):
        super().terminate()
        self.stdout.liberar.set()          # el pipe se cierra: read() retorna EOF


class TestTrackerSeDesbloqueaAlParar(unittest.TestCase):
    """④ `stop()` no puede dejar el hilo colgado en la lectura bloqueante."""

    def test_stop_termina_el_proceso_y_libera_el_hilo(self):
        proc = _ProcQueBloquea()
        tracker = _tracker()

        with patch("subprocess.Popen", return_value=proc):
            hilo = threading.Thread(target=tracker._run_once, daemon=True)
            hilo.start()
            self.assertTrue(_esperar(lambda: bool(proc.stdout.lecturas)),
                            "el hilo no llegó a leer")
            # Está dentro del read(): ahora se pide parar.
            tracker.stop(timeout=1.0)
            hilo.join(timeout=3.0)

        self.assertFalse(hilo.is_alive(), "el hilo quedó colgado en el read() bloqueante")
        self.assertTrue(proc.terminated, "stop() debe terminar el proceso que bloquea la lectura")

    def test_parar_sin_sesion_activa_no_falla(self):
        tracker = _tracker()
        tracker.stop(timeout=0.1)          # nunca se arrancó: no debe lanzar

    def test_parar_dos_veces_no_falla(self):
        tracker = _tracker()
        tracker.stop(timeout=0.1)
        tracker.stop(timeout=0.1)

    def test_el_proceso_no_se_queda_apuntado_tras_terminar(self):
        """Tras terminar una sesión, el tracker no debe seguir guardando el proceso."""
        proc = _FakeTrackerProc(chunks=[], returncode=0, alive=False)
        tracker = _tracker()

        with patch("subprocess.Popen", return_value=proc):
            tracker._run_once()

        self.assertIsNone(getattr(tracker, "_proc", None),
                          "el proceso terminado debe soltarse (fuga de referencias)")


if __name__ == "__main__":
    unittest.main()
