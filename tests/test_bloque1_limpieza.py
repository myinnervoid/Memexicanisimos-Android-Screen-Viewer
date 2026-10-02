"""Red del Bloque 1 · cierre mecánico (2026-10-01).

Cubre lo que el Bloque 1 cambió en el código:

  ③  código muerto y contratos fantasma — el binding inerte de cierre de ventana,
     la ruta quemada del `scrcpy-server` y la formalización de `verify_server_version`
     como mecanismo de auditoría (ADR-014), con su tabla de comparación.
  ⑪  las dos convenciones de fallo de los parsers de red, fijadas por contrato.
  ⑫  los flags de tamaño habilitados: la rama `_has_size_flag` ya es alcanzable.

Nada aquí lanza procesos reales ni toca la configuración del usuario.
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

from scrcpy_dock.core.scrcpy_engine import ScrcpyEngine
from scrcpy_dock.domain.models import ALLOWED_EXTRA_FLAGS, Codec, SessionConfig
from scrcpy_dock.errors import ErrorCode
from scrcpy_dock.managers import _resolver_servidor_scrcpy
from scrcpy_dock.security import SecurityManager
from scrcpy_dock.services.installer_service import InstallerService
from scrcpy_dock.utils import parse_ip_port

JAR_HISTORICO = Path("/usr/share/scrcpy/scrcpy-server")


def _config(extra_args: tuple = ()) -> SessionConfig:
    return SessionConfig(port=27183, codec=Codec.H264, resolution="native",
                         bit_rate=8_000_000, extra_args=extra_args)


class TestTablaDeVersiones(unittest.TestCase):
    """ADR-014 · `_compare_versions` es pura: se prueba sin binarios ni procesos."""

    def test_misma_version_coincide(self):
        res = ScrcpyEngine._compare_versions("scrcpy 4.1", "scrcpy-server 4.1")
        self.assertTrue(res.success, res.message)
        self.assertEqual(res.data, "4.1")

    def test_version_distinta_se_reporta(self):
        res = ScrcpyEngine._compare_versions("scrcpy 4.1", "scrcpy-server 3.3.1")
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.SCRCPY_SERVER_VERSION_MISMATCH)

    def test_salida_ilegible_no_se_toma_por_coincidencia(self):
        """Lo importante: no poder leer una versión **no** equivale a que cuadren."""
        for cliente, servidor in (("", "4.1"), ("4.1", ""), ("sin números", "4.1")):
            with self.subTest(cliente=cliente, servidor=servidor):
                res = ScrcpyEngine._compare_versions(cliente, servidor)
                self.assertFalse(res.success, "una salida ilegible pasó como coincidencia")
                self.assertEqual(res.error, ErrorCode.SCRCPY_SERVER_VERSION_MISMATCH)

    def test_un_parche_distinto_cuenta_como_discrepancia(self):
        """Hallazgo (ADR-014): la paridad se mide **letra a letra**, no semánticamente.

        `4.0` contra `4.0.1` se reporta como discrepancia aunque sea el mismo linaje.
        Es estricto a propósito —un servidor más nuevo que el cliente es justo el caso
        que deja pasar una comprobación indulgente— pero conviene saberlo: el aviso no
        distingue «otro linaje» de «otro parche».
        """
        res = ScrcpyEngine._compare_versions("scrcpy 4.0", "scrcpy 4.0.1")
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.SCRCPY_SERVER_VERSION_MISMATCH)

    def test_mismo_numero_con_texto_distinto_si_coincide(self):
        """Extrae el número: el resto del renglón (nombre, URL) no influye."""
        res = ScrcpyEngine._compare_versions(
            "scrcpy 4.1 <https://github.com/Genymobile/scrcpy>",
            "scrcpy-server: 4.1",
        )
        self.assertTrue(res.success, res.message)
        self.assertEqual(res.data, "4.1")


class TestVerifyServerVersion(unittest.TestCase):
    """ADR-014 · auditoría del binario externo; nunca se llama en el arranque de la GUI."""

    def setUp(self):
        self.engine = ScrcpyEngine("/usr/bin/scrcpy", str(JAR_HISTORICO))

    def _con_salida(self, code=0, stdout="", stderr=""):
        falso = mock.MagicMock(returncode=code, stdout=stdout, stderr=stderr)
        return mock.patch("scrcpy_dock.core.scrcpy_engine.subprocess.run", return_value=falso)

    def test_extrae_la_version_del_binario(self):
        with self._con_salida(stdout="scrcpy 4.1 <https://github.com/Genymobile/scrcpy>\n"):
            res = self.engine.verify_server_version()
        self.assertTrue(res.success, res.message)
        self.assertEqual(res.data, "4.1")

    def test_binario_ausente_no_lanza(self):
        with mock.patch("scrcpy_dock.core.scrcpy_engine.subprocess.run",
                        side_effect=FileNotFoundError("no existe")):
            res = self.engine.verify_server_version()
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.SCRCPY_NOT_FOUND)

    def test_salida_cero_distinto_es_error(self):
        with self._con_salida(code=1, stderr="boom"):
            res = self.engine.verify_server_version()
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.SCRCPY_NOT_FOUND)

    def test_salida_sin_version_no_se_inventa(self):
        with self._con_salida(stdout="scrcpy sin numero de version\n"):
            res = self.engine.verify_server_version()
        self.assertFalse(res.success)
        self.assertEqual(res.error, ErrorCode.SCRCPY_SERVER_VERSION_MISMATCH)

    def test_no_se_invoca_al_construir_el_motor(self):
        """El contrato dice «no en el arranque»: si alguien lo mete ahí, esto lo caza."""
        with mock.patch("scrcpy_dock.core.scrcpy_engine.subprocess.run") as run:
            ScrcpyEngine("/usr/bin/scrcpy", str(JAR_HISTORICO))
        run.assert_not_called()


class TestResolucionDelServidorScrcpy(unittest.TestCase):
    """③ · la ruta del `scrcpy-server` dejó de estar quemada en el código."""

    def test_devuelve_una_ruta_y_nunca_lanza(self):
        ruta = _resolver_servidor_scrcpy()
        self.assertIsInstance(ruta, Path)
        self.assertTrue(ruta.is_absolute() or sys.platform == "win32", ruta)

    def test_sin_servidor_suelto_cae_en_la_ruta_historica(self):
        """scrcpy 4.x lo lleva embebido: sin fichero en ninguna ruta, hay respuesta igual.

        Se simula «no hay fichero» en vez de mirar la máquina: así la prueba dice lo
        mismo en cualquier entorno (y no se salta en unos sí y en otros no, que es
        justo lo que deja pasar un mutante).
        """
        with mock.patch.object(Path, "exists", return_value=False):
            self.assertEqual(_resolver_servidor_scrcpy(),
                             Path("/usr/share/scrcpy/scrcpy-server"))

    def test_si_hay_servidor_suelto_lo_usa(self):
        """El layout gestionado gana a las rutas del sistema (ADR-019)."""
        with mock.patch.object(Path, "exists", return_value=True):
            self.assertEqual(_resolver_servidor_scrcpy(),
                             InstallerService().bin_dir / "scrcpy-server")

    def test_la_copia_quemada_ya_no_esta_en_el_codigo(self):
        fuente = Path(__file__).resolve().parent.parent / "scrcpy_dock" / "managers.py"
        self.assertNotIn('Path("/usr/local/share/scrcpy/scrcpy-server"))',
                         fuente.read_text(encoding="utf-8"),
                         "la ruta quemada sigue en la construcción del motor")


class TestContratosDeFallbackDeLosParsersDeRed(unittest.TestCase):
    """⑪ · las dos convenciones **distintas**, fijadas para que nadie las unifique mal."""

    def test_parse_ip_port_falla_con_tupla_de_nones(self):
        for entrada in ("", "   ", "no-es-ip", "999.999.1.1:5555", "1.2.3.4:0", "1.2.3.4:99999"):
            with self.subTest(entrada=entrada):
                self.assertEqual(parse_ip_port(entrada), (None, None))

    def test_la_tupla_de_fallo_es_verdadera_y_por_eso_hay_que_mirar_el_primero(self):
        ip, puerto = parse_ip_port("no-es-ip")
        self.assertIsNone(ip)
        self.assertIsNone(puerto)
        self.assertTrue((ip, puerto), "documentado: `if not parsed` NO detecta este fallo")

    def test_parse_pair_falla_con_none_suelto(self):
        for ip_puerto, codigo in (("1.2.3.4:38291", "12345"), ("1.2.3.4:38291", "abcdef"),
                                  ("1.2.3.4", "123456"), ("", ""), ("1.2.3.4:99999", "123456")):
            with self.subTest(ip_puerto=ip_puerto, codigo=codigo):
                self.assertIsNone(SecurityManager.parse_pair_ip_port_code(ip_puerto, codigo))

    def test_un_par_valido_es_verdadero_y_su_none_es_falso(self):
        """Por esto su llamador usa `if not parsed:` y el otro NO puede."""
        valido = SecurityManager.parse_pair_ip_port_code(" 192.168.1.5:41455 ", "123456")
        self.assertEqual(valido, ("192.168.1.5", "41455", "123456"))
        self.assertTrue(valido)
        self.assertFalse(SecurityManager.parse_pair_ip_port_code("", ""))

    def test_una_tupla_de_nones_seria_verdadera_y_romperia_esa_guarda(self):
        """Caracterización del motivo real de no unificar las dos convenciones.

        Una tupla de Nones **pasa** `if not parsed:` y se desempaqueta sin quejarse:
        el llamador seguiría adelante con tres valores nulos (peor que un error).
        """
        tupla_nula = (None, None, None)
        self.assertTrue(tupla_nula, "una tupla de Nones pasa `if not parsed:`")
        ip, puerto, codigo = tupla_nula
        self.assertIsNone(ip)
        self.assertIsNone(puerto)
        self.assertIsNone(codigo)


class TestFlagsDeTamanoHabilitados(unittest.TestCase):
    """⑫ · antes la whitelist vetaba el flag y la rama quedaba inalcanzable."""

    def test_la_whitelist_los_contiene(self):
        for flag in ("--max-size", "--camera-size", "-m"):
            self.assertIn(flag, ALLOWED_EXTRA_FLAGS)

    def test_el_validador_acepta_la_forma_con_igual(self):
        for args in (("--max-size=1920",), ("--camera-size=4608x3456",), ("-m=1280",)):
            with self.subTest(args=args):
                self.assertIsNone(ScrcpyEngine._validate_extra_args(_config(extra_args=args)))

    def test_la_forma_separada_la_rechaza_el_validador(self):
        """Hallazgo (⑫): el validador juzga token a token, así que `-m 1280` no pasa.

        El valor suelto (`1280`) no es un flag de la whitelist y se rechaza con un
        mensaje claro. La forma admitida es con `=`, que scrcpy entiende igual.
        """
        for args in (("--max-size", "1920"), ("-m", "1280")):
            with self.subTest(args=args):
                fallo = ScrcpyEngine._validate_extra_args(_config(extra_args=args))
                self.assertIsNotNone(fallo, f"{args} debería rechazarse")
                self.assertEqual(fallo.error, ErrorCode.INVALID_EXTRA_ARGS)

    def test_el_flag_solo_sin_valor_pasa_la_whitelist(self):
        """`-m` suelto es un token permitido: la whitelist no juzga si falta el valor."""
        self.assertIsNone(ScrcpyEngine._validate_extra_args(_config(extra_args=("-m",))))

    def test_sigue_rechazando_lo_que_no_esta_en_la_whitelist(self):
        fallo = ScrcpyEngine._validate_extra_args(_config(extra_args=("--inventado",)))
        self.assertIsNotNone(fallo)
        self.assertEqual(fallo.error, ErrorCode.INVALID_EXTRA_ARGS)

    def test_la_rama_corta_por_los_tres_flags(self):
        for extra in (["--max-size=1920"], ["--camera-size=4608x3456"], ["-m"]):
            with self.subTest(extra=extra):
                self.assertTrue(ScrcpyEngine._has_size_flag(_config(extra_args=tuple(extra))))


if __name__ == "__main__":
    unittest.main()
