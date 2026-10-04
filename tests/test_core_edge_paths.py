"""Cierre de la Ley 7 de negocio: ramas de borde de `utils`, `security` y `tether_engine`.

Estos tres módulos eran los últimos por debajo del umbral del 80 % de cobertura.
Lo que faltaba en todos ellos eran **ramas de borde**: plataformas que no son la
de desarrollo, fallos de disco al guardar, sockets ocupados, rotación del log,
servicios caídos y caminos de rechazo (datos inválidos que deben fallar en
cerrado, nunca reventar).

Aislamiento: ninguna prueba escribe en `~/.config/masv/`. `CONFIG_FILE` y
`LOG_FILE` se redirigen a un directorio temporal en cada clase, y la prueba de
recarga por plataforma parchea `expanduser`, `makedirs` y `chmod` para que ni
siquiera se toque el HOME.

Ejecutable con: python -m unittest discover -s tests
"""
from __future__ import annotations

import copy
import importlib
import io
import json
import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scrcpy_dock.core.tether_engine as tether_engine
import scrcpy_dock.utils as utils
from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.core.tether_engine import TetherEngine
from scrcpy_dock.errors import ErrorCode
from scrcpy_dock.security import SecurityManager
from scrcpy_dock.services.security_service import SecurityService

from tests.contracts.helpers import fake_completed_process


# ─────────────────────────────────────────────────────────────────────────────
# utils · configuración
# ─────────────────────────────────────────────────────────────────────────────

class _UtilsAislado(unittest.TestCase):
    """Base: redirige CONFIG_FILE y LOG_FILE a un directorio temporal."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.cfg_file = self.dir / "config.json"
        self.log_file = self.dir / "masv.log"
        for nombre, valor in (("CONFIG_FILE", str(self.cfg_file)),
                              ("LOG_FILE", str(self.log_file))):
            p = patch.object(utils, nombre, valor)
            p.start()
            self.addCleanup(p.stop)


class TestConfigEdges(_UtilsAislado):

    def test_fusiona_subclaves_que_faltan_en_una_seccion_existente(self):
        """Una config vieja con la sección `security` a medias se completa sola."""
        self.cfg_file.write_text(json.dumps({
            "profiles": {},
            "security": {"blocked_ips": ["10.0.0.5"]},
        }), encoding="utf-8")

        cfg = utils.load_config()

        self.assertEqual(cfg["security"]["blocked_ips"], ["10.0.0.5"], "lo del usuario manda")
        self.assertTrue(cfg["security"]["safe_mode_enabled"], "lo que falta se rellena")
        self.assertEqual(len(cfg["profiles"]), len(utils.DEFAULT_CONFIG["profiles"]), "los perfiles de fábrica se recrean")

    def test_config_corrupta_cae_a_los_valores_de_fabrica(self):
        self.cfg_file.write_text("{esto no es json válido", encoding="utf-8")

        with patch("sys.stdout", new_callable=io.StringIO) as salida:
            cfg = utils.load_config()

        self.assertIn("Error loading config", salida.getvalue())
        self.assertEqual(cfg["language"], "es")
        self.assertEqual(cfg["theme"], "warm_stone")

    def test_una_config_que_no_es_un_diccionario_no_revienta(self):
        self.cfg_file.write_text("[1, 2, 3]", encoding="utf-8")

        with patch("sys.stdout", new_callable=io.StringIO) as salida:
            cfg = utils.load_config()

        self.assertIn("Error loading config", salida.getvalue())
        self.assertIn("profiles", cfg)

    def test_si_no_se_puede_renombrar_el_temporal_se_limpia_y_no_propaga(self):
        with patch.object(utils.os, "replace", side_effect=OSError("disco lleno")), \
             patch("sys.stdout", new_callable=io.StringIO) as salida:
            utils.save_config({"a": 1})

        self.assertIn("Error saving config", salida.getvalue())
        self.assertFalse(self.cfg_file.exists(), "no debe quedar una config a medias")
        self.assertFalse(Path(f"{self.cfg_file}.tmp").exists(), "el temporal se retira")

    def test_si_tampoco_se_puede_borrar_el_temporal_no_propaga(self):
        with patch.object(utils.os, "replace", side_effect=OSError("x")), \
             patch.object(utils.os, "remove", side_effect=OSError("y")), \
             patch("sys.stdout", new_callable=io.StringIO):
            utils.save_config({"a": 1})          # no debe lanzar

    def test_no_falla_si_no_puede_endurecer_los_permisos(self):
        """En sistemas de ficheros sin permisos POSIX el guardado debe seguir funcionando."""
        with patch.object(utils.os, "chmod", side_effect=OSError("no soportado")):
            utils.save_config({"a": 1})

        self.assertTrue(self.cfg_file.exists())
        self.assertEqual(json.loads(self.cfg_file.read_text(encoding="utf-8"))["a"], 1)

    def test_el_guardado_es_atomico_y_utf8(self):
        utils.save_config({"emoji": "🎮", "ruta": "/tmp/ñ"})
        self.assertEqual(json.loads(self.cfg_file.read_text(encoding="utf-8"))["emoji"], "🎮")


class TestUtilsPlataformas(unittest.TestCase):
    """Las ramas por plataforma sólo corren al importar: hay que reimportar el módulo.

    Sin `expanduser`/`makedirs`/`chmod` parcheados, una recarga tocaría el
    `~/.config/masv` real del usuario.
    """

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def _recargar(self, plataforma, chmod_falla=False):
        efectos = (patch.object(utils.os, "makedirs", lambda *a, **k: None),
                   patch.object(utils.os.path, "expanduser", return_value=str(self.dir)))
        chmod = patch.object(utils.os, "chmod",
                             side_effect=OSError("no permitido") if chmod_falla
                             else (lambda *a, **k: None))
        try:
            for p in (*efectos, chmod):
                p.start()
            with patch.object(utils.sys, "platform", plataforma):
                importlib.reload(utils)
                return utils.FONT_FAMILY, utils.CONFIG_DIR
        finally:
            patch.stopall()
            # Restaurar el módulo real sin efectos sobre el HOME del usuario.
            with patch.object(utils.os, "makedirs", lambda *a, **k: None), \
                 patch.object(utils.os, "chmod", lambda *a, **k: None):
                importlib.reload(utils)

    def test_tipografia_en_macos(self):
        familia, _ = self._recargar("darwin")
        self.assertEqual(familia, "SF Pro Display")

    def test_tipografia_en_windows(self):
        familia, _ = self._recargar("win32")
        self.assertEqual(familia, "Segoe UI")

    def test_tipografia_en_linux(self):
        familia, _ = self._recargar("linux")
        self.assertEqual(familia, "Ubuntu")

    def test_la_carpeta_de_configuracion_no_aborta_el_arranque_si_no_se_puede_endurecer(self):
        """Si `chmod 0700` falla (FS sin permisos POSIX) el módulo debe importarse igual."""
        _, config_dir = self._recargar("linux", chmod_falla=True)
        self.assertEqual(config_dir, str(self.dir))

    def test_modulo_restaurado_tras_las_recargas(self):
        self._recargar("darwin")
        self.assertEqual(utils.CONFIG_DIR, utils.APP_DIR)
        self.assertTrue(utils.CONFIG_DIR.replace("\\", "/").endswith(".config/masv"), utils.CONFIG_DIR)


class TestBusquedaDeBinarios(unittest.TestCase):

    def test_en_modo_empaquetado_busca_junto_al_ejecutable_y_en_el_temporal(self):
        llamadas = []

        def fake_which(nombre, path=None):
            llamadas.append(path)
            return f"/fake/{nombre}"

        with patch.object(tether_engine.sys, "frozen", True, create=True), \
             patch.object(utils.sys, "frozen", True, create=True), \
             patch.object(utils.sys, "_MEIPASS", "/tmp/_mei", create=True), \
             patch.object(utils.shutil, "which", side_effect=fake_which):
            adb, scrcpy = utils.find_portable_binaries()

        self.assertEqual((adb, scrcpy), ("/fake/adb", "/fake/scrcpy"))
        primera = llamadas[0]
        self.assertIn(os.path.join("_mei", "bin"), primera)
        self.assertIn("bin", primera)

    def test_en_modo_desarrollo_busca_en_la_raiz_del_proyecto(self):
        with patch.object(utils.sys, "frozen", False, create=True), \
             patch.object(utils.shutil, "which", return_value=None):
            adb, scrcpy = utils.find_portable_binaries()

        self.assertIsNone(adb)
        self.assertIsNone(scrcpy)


class TestParseIpPort(unittest.TestCase):

    def test_puerto_fuera_de_rango_o_no_numerico(self):
        for entrada in ("192.168.1.5:0", "192.168.1.5:70000",
                        "192.168.1.5:abc", "192.168.1.5:"):
            with self.subTest(entrada=entrada):
                self.assertEqual(utils.parse_ip_port(entrada), (None, None))

    def test_entrada_valida_con_y_sin_puerto(self):
        self.assertEqual(utils.parse_ip_port("192.168.1.5"), ("192.168.1.5", "5555"))
        self.assertEqual(utils.parse_ip_port(" 192.168.1.5:5556 "), ("192.168.1.5", "5556"))

    def test_entrada_vacia_o_basura(self):
        for entrada in ("", "   ", "no-es-una-ip", "999.999.999.999"):
            with self.subTest(entrada=entrada):
                self.assertEqual(utils.parse_ip_port(entrada), (None, None))


class TestInstanciaUnica(unittest.TestCase):

    @staticmethod
    def _puerto_libre() -> int:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
        s.close()
        return puerto

    def test_solo_una_instancia_toma_el_puerto_y_al_liberarlo_vuelve_a_estar_libre(self):
        puerto = self._puerto_libre()
        primera = utils.SingleInstance(puerto)
        self.assertEqual(primera.port, puerto)
        self.assertTrue(primera.acquire())

        segunda = utils.SingleInstance(puerto)
        self.assertFalse(segunda.acquire(), "la segunda instancia no debe tomar el puerto")

        primera.release()
        tercera = utils.SingleInstance(puerto)

        # Poll up to 1.0s to tolerate socket release latency on Windows/macOS kernels
        import time
        adquirido = False
        limite = time.time() + 1.0
        while time.time() < limite:
            if tercera.acquire():
                adquirido = True
                break
            time.sleep(0.01)

        self.assertTrue(adquirido, "liberar el puerto debe permitir reincorporarse")
        tercera.release()

    def test_release_tolera_un_socket_roto(self):
        """Un socket que ya no acepta `close()` no debe impedir el cierre de la app."""
        class _SocketRoto:
            def close(self):
                raise OSError("socket ya cerrado")

        instancia = utils.SingleInstance(self._puerto_libre())
        instancia.acquire()
        instancia.sock = _SocketRoto()

        instancia.release()          # no debe propagar


class TestLogMsg(_UtilsAislado):

    def test_escribe_con_marca_de_tiempo(self):
        with patch("sys.stdout", new_callable=io.StringIO) as salida:
            utils.log_msg("INFO", "hola mundo")

        self.assertIn("[INFO] hola mundo", salida.getvalue())
        self.assertIn("hola mundo", self.log_file.read_text(encoding="utf-8"))

    @staticmethod
    def _log_grande():
        return "x" * (5 * 1024 * 1024 + 1)

    def test_rota_el_log_cuando_supera_los_5_mb(self):
        self.log_file.write_text(self._log_grande(), encoding="utf-8")
        viejo = Path(f"{self.log_file}.1")
        viejo.write_text("anterior", encoding="utf-8")

        utils.log_msg("INFO", "nueva entrada")

        self.assertIn("nueva entrada", self.log_file.read_text(encoding="utf-8"))
        self.assertEqual(viejo.read_text(encoding="utf-8"), self._log_grande(),
                         "el .1 debe pasar a ser el log anterior")

    def test_rota_aunque_no_pueda_borrar_ni_renombrar_el_anterior(self):
        self.log_file.write_text(self._log_grande(), encoding="utf-8")
        Path(f"{self.log_file}.1").write_text("anterior", encoding="utf-8")

        with patch.object(utils.os, "remove", side_effect=OSError("x")), \
             patch.object(utils.os, "rename", side_effect=OSError("y")):
            utils.log_msg("INFO", "sigo escribiendo")

        self.assertIn("sigo escribiendo", self.log_file.read_text(encoding="utf-8"))

    def test_un_destino_imposible_no_propaga_y_sigue_imprimiendo(self):
        os.makedirs(self.log_file, exist_ok=True)      # LOG_FILE es un directorio

        with patch("sys.stdout", new_callable=io.StringIO) as salida:
            utils.log_msg("ERROR", "sigue viéndose")

        self.assertIn("sigue viéndose", salida.getvalue())


# ─────────────────────────────────────────────────────────────────────────────
# security · fachada de la bóveda y validaciones
# ─────────────────────────────────────────────────────────────────────────────

class _SecurityBase(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def _mgr(self, cfg=None, vault_dir=None) -> SecurityManager:
        return SecurityManager(copy.deepcopy(cfg if cfg is not None else {"security": {}}),
                               vault_dir=vault_dir)


class TestConfigDeSeguridad(_SecurityBase):

    def test_una_seccion_security_invalida_se_reemplaza(self):
        mgr = self._mgr({"security": "no soy un dict"})
        self.assertIsInstance(mgr.cfg["security"], dict)
        self.assertTrue(mgr.is_safe_mode_enabled)

    def test_alternar_safe_mode_y_auto_lockdown(self):
        mgr = self._mgr()
        guardados = []

        self.assertTrue(mgr.is_auto_lockdown_enabled)
        mgr.set_auto_lockdown(False, save_cb=guardados.append)
        self.assertFalse(mgr.is_auto_lockdown_enabled)
        self.assertEqual(len(guardados), 1)

        mgr.set_auto_lockdown(True)                       # sin callback
        self.assertTrue(mgr.is_auto_lockdown_enabled)

        mgr.set_safe_mode(False, save_cb=guardados.append)
        self.assertFalse(mgr.is_safe_mode_enabled)
        self.assertEqual(len(guardados), 2)


class TestBovedaCifrada(_SecurityBase):

    def test_sin_directorio_de_boveda_no_hay_cripto_ni_persistencia(self):
        mgr = self._mgr()
        self.assertIsNone(mgr._crypto_or_none())
        self.assertFalse(mgr._persist_vault())
        self.assertFalse(mgr.is_vault_encrypted)

    def test_si_la_cripto_esta_rota_la_boveda_se_declara_no_disponible(self):
        mgr = self._mgr(vault_dir=str(self.dir))
        mgr._vault_broken = True
        self.assertIsNone(mgr._crypto_or_none())
        mgr._init_vault()                                  # debe salir sin tocar nada
        self.assertFalse(mgr.is_vault_encrypted)

    def test_se_avisa_si_la_config_declara_cifrado_pero_falta_el_archivo(self):
        mgr = self._mgr({"security": {"vault_encrypted": True}}, vault_dir=str(self.dir))
        self.assertFalse(mgr.is_vault_encrypted)
        self.assertFalse(Path(mgr._vault_path).exists(), "no debe inventarse la bóveda")

    def test_si_no_se_puede_crear_la_carpeta_no_se_pierde_la_boveda(self):
        mgr = self._mgr(vault_dir=str(self.dir / "nueva"))
        mgr._trusted["HWY9"] = {"is_trusted": True}

        with patch.object(Path, "mkdir", side_effect=OSError("solo lectura")):
            self.assertFalse(mgr._persist_vault())

        self.assertFalse(mgr.is_vault_encrypted)
        self.assertEqual(mgr.get_trusted_devices(), {"HWY9": {"is_trusted": True}},
                         "la bóveda en memoria queda intacta")

    def test_si_la_escritura_cifrada_falla_no_se_retira_el_texto_plano(self):
        mgr = self._mgr(vault_dir=str(self.dir))
        mgr._trusted["HWY9"] = {"is_trusted": True}
        mgr.cfg["security"]["trusted_devices"] = {"HWY9": {"is_trusted": True}}

        with patch.object(SecurityService, "save_vault",
                          return_value=OperationResult.fail(ErrorCode.UNKNOWN_ERROR, "sin espacio")):
            self.assertFalse(mgr._persist_vault())

        self.assertFalse(mgr.is_vault_encrypted,
                         "sin escritura verificada no se declara cifrada")
        self.assertTrue(mgr.cfg["security"]["trusted_devices"], "el texto plano no se toca")

    def test_si_la_ida_y_vuelta_no_cuadra_se_conserva_la_copia_en_claro(self):
        mgr = self._mgr(vault_dir=str(self.dir))
        mgr._trusted["HWY9"] = {"is_trusted": True}
        mgr.cfg["security"]["trusted_devices"] = {"HWY9": {"is_trusted": True}}

        with patch.object(SecurityService, "save_vault", return_value=OperationResult.ok(None)), \
             patch.object(SecurityService, "load_vault",
                          return_value=OperationResult.ok({"schema_version": 1,
                                                          "trusted_devices": {"OTRO": {}}})):
            self.assertFalse(mgr._persist_vault(), "un vault que no cuadra no es un vault")

        self.assertFalse(mgr.is_vault_encrypted)
        self.assertEqual(mgr.cfg["security"]["trusted_devices"], {"HWY9": {"is_trusted": True}})

    def test_la_boveda_se_persiste_y_se_puede_releer(self):
        cfg = {"security": {"trusted_devices": {"HWY9": {"is_trusted": True, "alias": "Mi Vivo"}}}}
        mgr = self._mgr(cfg, vault_dir=str(self.dir))

        self.assertTrue(mgr._persist_vault())
        self.assertTrue(mgr.is_vault_encrypted)
        self.assertEqual(mgr.cfg["security"]["trusted_devices"], {},
                         "el texto plano se retira SOLO tras verificar la ida y vuelta")

        otra = self._mgr({"security": {}}, vault_dir=str(self.dir))
        self.assertTrue(otra.is_vault_encrypted)
        self.assertEqual(otra.get_trusted_devices()["HWY9"]["alias"], "Mi Vivo")

    def test_si_no_se_puede_copiar_la_config_previa_la_operacion_sigue(self):
        (self.dir / "config.json").write_text("{}", encoding="utf-8")
        mgr = self._mgr(vault_dir=str(self.dir))

        with patch("shutil.copy2", side_effect=OSError("permiso denegado")):
            self.assertIsNone(mgr._backup_plaintext_config())

    def test_la_copia_previa_se_hace_una_sola_vez(self):
        (self.dir / "config.json").write_text('{"security": {}}', encoding="utf-8")
        mgr = self._mgr(vault_dir=str(self.dir))

        primera = mgr._backup_plaintext_config()
        self.assertIsNotNone(primera)
        self.assertTrue(Path(primera).exists())
        self.assertIsNone(mgr._backup_plaintext_config(), "ya existe: no se reescribe")


class TestBovedaDeConfianza(_SecurityBase):

    def test_confirmar_revocar_y_eliminar(self):
        mgr = self._mgr()
        guardados = []

        res = mgr.trust_device("HWY9", model="V2314", alias="Mi Vivo",
                               save_cb=guardados.append)
        self.assertTrue(res.success)
        self.assertTrue(mgr.is_trusted_device("HWY9"))
        self.assertEqual(mgr.get_device_alias("HWY9"), "Mi Vivo")
        self.assertEqual(len(guardados), 1)

        self.assertTrue(mgr.untrust_device("HWY9", save_cb=guardados.append).success)
        self.assertFalse(mgr.is_trusted_device("HWY9"))
        self.assertEqual(mgr.get_device_alias("HWY9"), "Mi Vivo",
                         "revocar conserva el alias")

        self.assertTrue(mgr.remove_device_from_vault("HWY9").success)
        self.assertEqual(mgr.get_device_alias("HWY9"), "Android")

    def test_serial_vacio_se_rechaza(self):
        mgr = self._mgr()
        res = mgr.trust_device("")
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.INVALID_INPUT)
        self.assertFalse(mgr.is_trusted_device(""))
        self.assertFalse(mgr.is_trusted_device(None))

    def test_operaciones_sobre_un_serial_que_no_esta_son_idempotentes(self):
        mgr = self._mgr()
        self.assertTrue(mgr.untrust_device("FANTASMA").success)
        self.assertTrue(mgr.remove_device_from_vault("FANTASMA").success)
        self.assertEqual(mgr.get_device_alias("FANTASMA", default_model="Tablet"), "Tablet")

    def test_un_dispositivo_sin_alias_cae_al_modelo(self):
        mgr = self._mgr()
        mgr.trust_device("HWY9", model="V2314", alias="   ")
        self.assertEqual(mgr.get_device_alias("HWY9"), "V2314")
        self.assertEqual(mgr.get_trusted_devices()["HWY9"]["alias"], "V2314")


class TestValidacionesDeRed(_SecurityBase):

    def test_is_private_ip_con_entradas_invalidas(self):
        for entrada in ("", "   ", None, "no-es-ip", "999.1.1.1"):
            with self.subTest(entrada=entrada):
                self.assertFalse(SecurityManager.is_private_ip(entrada))

    def test_is_private_ip_acepta_rangos_locales(self):
        for entrada in ("192.168.1.5", "10.0.0.7", "172.16.3.9", "127.0.0.1", "169.254.1.1"):
            with self.subTest(entrada=entrada):
                self.assertTrue(SecurityManager.is_private_ip(entrada))

    def test_is_private_ip_rechaza_una_ip_publica(self):
        self.assertFalse(SecurityManager.is_private_ip("8.8.8.8"))

    def test_emparejamiento_con_datos_invalidos(self):
        casos = [
            ("", "123456"),                      # sin IP
            ("192.168.1.5:5555", ""),            # sin código
            ("192.168.1.5:5555", "12345"),       # código corto
            ("192.168.1.5:5555", "abcdef"),      # código no numérico
            ("192.168.1.5", "123456"),           # sin puerto
            ("192.168.1.5:0", "123456"),         # puerto fuera de rango
            ("no-es-ip:5555", "123456"),         # host no parseable
        ]
        for ip, codigo in casos:
            with self.subTest(ip=ip, codigo=codigo):
                self.assertIsNone(SecurityManager.parse_pair_ip_port_code(ip, codigo))

    def test_emparejamiento_con_datos_validos(self):
        self.assertEqual(
            SecurityManager.parse_pair_ip_port_code(" 192.168.1.5:41455 ", "123456"),
            ("192.168.1.5", "41455", "123456"),
        )

    def test_sanitize_text_input_limpia_controles_y_saltos(self):
        self.assertEqual(SecurityManager.sanitize_text_input(""), "")
        self.assertEqual(SecurityManager.sanitize_text_input("hola\nmundo\t!"), "hola mundo !")
        self.assertEqual(SecurityManager.sanitize_text_input("a\x00b\x07c"), "abc")

    def test_extra_args_peligrosos_se_rechazan(self):
        for crudo in ("; rm -rf /", "a && b", "a | b", "`whoami`", "$(id)", "a > f", "a < f"):
            with self.subTest(args=crudo):
                res = SecurityManager.validate_extra_arguments(crudo)
                self.assertFalse(res.success)
                self.assertEqual(res.error, ErrorCode.UNSAFE_ARGUMENT_DETECTED)

    def test_extra_args_con_comillas_sin_cerrar_se_rechazan(self):
        res = SecurityManager.validate_extra_arguments('--crop "1920x1080')
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.INVALID_INPUT)

    def test_extra_args_validos_o_vacios(self):
        self.assertEqual(SecurityManager.validate_extra_arguments("").data, [])
        self.assertEqual(SecurityManager.validate_extra_arguments("   ").data, [])
        self.assertEqual(
            SecurityManager.validate_extra_arguments("--turn-screen-off --max-fps 30").data,
            ["--turn-screen-off", "--max-fps", "30"],
        )


class TestEmparejarYBlindar(_SecurityBase):

    def test_pair_sin_binario_adb(self):
        res = SecurityManager.pair_device("", "192.168.1.5", "41455", "123456")
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.ADB_NOT_FOUND)

    @patch("subprocess.run")
    def test_pair_correcto(self, run_mock):
        run_mock.return_value = fake_completed_process(stdout="Successfully paired to 192.168.1.5:41455")
        res = SecurityManager.pair_device("/usr/bin/adb", "192.168.1.5", "41455", "123456")
        self.assertTrue(res.success)
        self.assertIn("paired", res.data.lower())

    @patch("subprocess.run")
    def test_pair_rechazado_por_el_telefono(self, run_mock):
        run_mock.return_value = fake_completed_process(stderr="wrong password", returncode=1)
        res = SecurityManager.pair_device("/usr/bin/adb", "192.168.1.5", "41455", "000000")
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.PAIRING_FAILED)
        self.assertIn("wrong password", res.message)

    @patch("subprocess.run")
    def test_pair_agota_el_tiempo(self, run_mock):
        import subprocess
        run_mock.side_effect = subprocess.TimeoutExpired(cmd="adb pair", timeout=15)
        res = SecurityManager.pair_device("/usr/bin/adb", "192.168.1.5", "41455", "123456")
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.PAIRING_TIMEOUT)

    @patch("subprocess.run")
    def test_pair_con_un_fallo_inesperado(self, run_mock):
        run_mock.side_effect = OSError("no se pudo lanzar")
        res = SecurityManager.pair_device("/usr/bin/adb", "192.168.1.5", "41455", "123456")
        self.assertEqual(res.error, ErrorCode.UNKNOWN_ERROR)

    def test_lockdown_con_parametros_invalidos(self):
        for adb, serial in (("", "HWY9"), ("/usr/bin/adb", "")):
            with self.subTest(adb=adb, serial=serial):
                res = SecurityManager.lockdown_device_tcpip(adb, serial)
                self.assertFalse(res.success)
                self.assertEqual(res.error, ErrorCode.INVALID_INPUT)

    @patch("subprocess.run")
    def test_lockdown_correcto(self, run_mock):
        run_mock.return_value = fake_completed_process(stdout="restarting in USB mode")
        res = SecurityManager.lockdown_device_tcpip("/usr/bin/adb", "HWY9")
        self.assertTrue(res.success)
        self.assertEqual(res.data, "HWY9")

    @patch("subprocess.run")
    def test_lockdown_fallido(self, run_mock):
        run_mock.return_value = fake_completed_process(stderr="device offline", returncode=1)
        res = SecurityManager.lockdown_device_tcpip("/usr/bin/adb", "HWY9")
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.LOCKDOWN_FAILED)
        self.assertIn("device offline", res.message)

    @patch("subprocess.run")
    def test_lockdown_con_un_fallo_inesperado(self, run_mock):
        run_mock.side_effect = OSError("boom")
        res = SecurityManager.lockdown_device_tcpip("/usr/bin/adb", "HWY9")
        self.assertEqual(res.error, ErrorCode.UNKNOWN_ERROR)

    def test_lockdown_masivo_sin_binario_no_hace_nada(self):
        con_exito = patch.object(SecurityManager, "lockdown_device_tcpip")
        with con_exito as lockdown:
            self.assertEqual(SecurityManager.lockdown_all_devices("", ["A", "B"]), 0)
            lockdown.assert_not_called()

    def test_lockdown_masivo_cuenta_solo_los_exitos(self):
        resultados = [OperationResult.ok("A"), OperationResult.fail(ErrorCode.LOCKDOWN_FAILED, "no"),
                      OperationResult.ok("C"), OperationResult.ok("D")]
        with patch.object(SecurityManager, "lockdown_device_tcpip", side_effect=resultados):
            self.assertEqual(
                SecurityManager.lockdown_all_devices("/usr/bin/adb", ["A", "B", "C", "D"]), 3,
            )

    def test_kill_server_sin_binario(self):
        self.assertFalse(SecurityManager.kill_adb_server(""))

    @patch("subprocess.run")
    def test_kill_server_correcto(self, run_mock):
        run_mock.return_value = fake_completed_process()
        self.assertTrue(SecurityManager.kill_adb_server("/usr/bin/adb"))
        self.assertEqual(run_mock.call_args.args[0], [str(Path("/usr/bin/adb")), "kill-server"])

    @patch("subprocess.run")
    def test_kill_server_con_adb_ausente(self, run_mock):
        run_mock.side_effect = FileNotFoundError("sin adb")
        self.assertFalse(SecurityManager.kill_adb_server("/usr/bin/adb"))


# ─────────────────────────────────────────────────────────────────────────────
# tether_engine · gnirehtet
# ─────────────────────────────────────────────────────────────────────────────

class TestTetherEngine(unittest.TestCase):

    def test_sin_binario_configurado_las_dos_operaciones_lo_dicen(self):
        with patch.object(tether_engine.shutil, "which", return_value=None):
            engine = TetherEngine()

        self.assertIsNone(engine._binary_path)
        for res in (engine.start("HWY9"), engine.stop("HWY9")):
            with self.subTest(accion=res.message):
                self.assertFalse(res.success)
                self.assertEqual(res.error, ErrorCode.BINARY_NOT_FOUND)
                self.assertIn("gnirehtet", res.message)

    @patch("subprocess.Popen")
    @patch("subprocess.run")
    def test_un_binario_inexistente_falla_al_lanzarlo_con_el_motivo_del_sistema(self, run_mock, popen_mock):
        """MASV no pre-valida la ruta: el fallo llega del SO y se muestra tal cual."""
        run_mock.side_effect = FileNotFoundError("No such file or directory")
        popen_mock.side_effect = FileNotFoundError("No such file or directory")
        engine = TetherEngine("/ruta/que/no/existe")

        arranque = engine.start("HWY9")
        parada = engine.stop("HWY9")

        self.assertEqual(arranque.error, ErrorCode.PROCESS_SPAWN_ERROR)
        self.assertIn("No such file", arranque.message)
        self.assertEqual(parada.error, ErrorCode.UNKNOWN_ERROR)
        self.assertIn("No such file", parada.message)

    @patch("subprocess.run")
    def test_stop_correcto(self, run_mock):
        run_mock.return_value = fake_completed_process()
        engine = TetherEngine("/fake/gnirehtet")
        res = engine.stop("HWY9")
        self.assertTrue(res.success)
        self.assertEqual(run_mock.call_args.args[0], ["/fake/gnirehtet", "stop", "HWY9"])

    @patch("subprocess.run")
    def test_stop_fallido_reporta_el_motivo(self, run_mock):
        run_mock.return_value = fake_completed_process(stderr="device not connected", returncode=1)
        res = TetherEngine("/fake/gnirehtet").stop("HWY9")
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.UNKNOWN_ERROR)
        self.assertIn("device not connected", res.message)

    @patch("subprocess.run")
    def test_stop_con_un_fallo_inesperado(self, run_mock):
        run_mock.side_effect = OSError("binario no ejecutable")
        res = TetherEngine("/fake/gnirehtet").stop("HWY9")
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.UNKNOWN_ERROR)

    @patch("subprocess.Popen")
    def test_start_lanza_gnirehtet_en_primer_plano(self, popen_mock):
        popen_mock.return_value = object()
        res = TetherEngine("/fake/gnirehtet").start("HWY9")
        self.assertTrue(res.success)
        self.assertEqual(popen_mock.call_args.args[0], ["/fake/gnirehtet", "run", "HWY9"])

    @patch("subprocess.Popen")
    def test_start_que_no_puede_lanzar_el_proceso(self, popen_mock):
        popen_mock.side_effect = OSError("binario no ejecutable")
        res = TetherEngine("/fake/gnirehtet").start("HWY9")
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.PROCESS_SPAWN_ERROR)
        self.assertIn("binario no ejecutable", res.message)

    def test_busqueda_en_modo_empaquetado(self):
        with patch.object(tether_engine.sys, "frozen", True, create=True), \
             patch.object(tether_engine.sys, "_MEIPASS", "/tmp/_mei", create=True), \
             patch.object(tether_engine.shutil, "which", return_value="/fake/gnirehtet") as which:
            engine = TetherEngine()

        self.assertEqual(engine._binary_path, "/fake/gnirehtet")
        rutas = which.call_args.kwargs["path"]
        self.assertIn(os.path.join("_mei", "bin"), rutas)
        self.assertIn(utils.CONFIG_DIR, rutas, "también busca en la carpeta del usuario")

    def test_sin_gnirehtet_en_ninguna_ruta(self):
        with patch.object(tether_engine.shutil, "which", return_value=None):
            self.assertIsNone(TetherEngine()._binary_path)


if __name__ == "__main__":
    unittest.main()
