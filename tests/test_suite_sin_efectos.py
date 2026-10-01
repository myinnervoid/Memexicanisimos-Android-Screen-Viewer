"""Guardián: la suite de pruebas no puede tocar la configuración real del usuario.

**Por qué existe (P3.32).** `tests/test_ui_widgets_coverage.py` construía
`TrustPromptModal` con un `cfg` parcial y sin redirigir las rutas. El modal hacía
`save_config(self.cfg)` por su cuenta, así que **cada ejecución de la suite
reescribía `~/.config/masv/config.json`** con `{"trusted_devices": {}}`: se perdió
la configuración del usuario (perfiles personalizados incluidos). La docstring del
archivo de pruebas *afirmaba* que redirigía las configuraciones a temporales, y no
lo hacía — de ahí que pasara desapercibido en la revisión.

Este módulo cierra las dos puertas:
  1. **Estática**: todo archivo de pruebas que pueda provocar un guardado debe
     contener pruebas de aislamiento (o importar el arnés compartido, que las pone).
  2. **De extremo a extremo**: ejecutar en un subproceso las pruebas de widgets
     —las de mayor riesgo— y comprobar que el archivo real queda byte a byte igual.

Ejecutable con: python -m unittest discover -s tests
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tkinter as tk
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CONFIG_REAL = Path.home() / ".config" / "masv" / "config.json"

# Construcciones que pueden terminar en un guardado en disco.
RIESGO = (
    "SecurityManager(",
    "ScrcpyDockApp(",
    "TrustPromptModal(",
    "TrustVaultDialog(",
    "ProfileWizard(",
)
# Todo lo que sirve como prueba de aislamiento: redirigir las rutas o usar el arnés.
AISLAMIENTO = ("CONFIG_FILE", "CONFIG_DIR", "ui_harness")
# El propio guardián menciona las construcciones de riesgo en su texto.
EXENTOS = {"test_suite_sin_efectos.py", "ui_harness.py"}

# Módulos que se ejecutan en subproceso en la comprobación de extremo a extremo.
ALTO_RIESGO = ["tests.test_ui_widgets_coverage"]


def _hay_display() -> bool:
    try:
        raiz = tk.Tk()
        raiz.destroy()
        return True
    except Exception:
        return False


def _huella(ruta: Path) -> str | None:
    if not ruta.exists():
        return None
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


class TestLaSuiteNoTocaLaConfigReal(unittest.TestCase):

    def test_todo_modulo_que_pueda_guardar_aisla_la_config(self):
        """Estático: quien pueda provocar un guardado debe traer su aislamiento."""
        sin_aislamiento = []
        for archivo in sorted((RAIZ / "tests").rglob("*.py")):
            if archivo.name in EXENTOS:
                continue
            fuente = archivo.read_text(encoding="utf-8")
            if any(r in fuente for r in RIESGO) and not any(a in fuente for a in AISLAMIENTO):
                sin_aislamiento.append(str(archivo.relative_to(RAIZ)))

        self.assertEqual(
            sin_aislamiento, [],
            "estos módulos pueden escribir en la config real y no la aíslan "
            "(redirige CONFIG_FILE/CONFIG_DIR a un temporal o usa tests/ui_harness.py)",
        )

    def test_ejecutar_las_pruebas_de_widgets_no_modifica_la_config_real(self):
        """De extremo a extremo: el archivo real queda idéntico tras la ejecución."""
        if not _hay_display():
            self.skipTest("requiere display para que las pruebas de widgets corran de verdad")

        antes = _huella(CONFIG_REAL)
        entorno = dict(os.environ)

        for modulo in ALTO_RIESGO:
            with self.subTest(modulo=modulo):
                proc = subprocess.run(
                    [sys.executable, "-m", "unittest", modulo],
                    cwd=RAIZ, env=entorno, capture_output=True, text=True, timeout=300,
                )
                self.assertEqual(
                    proc.returncode, 0,
                    f"{modulo} no pasa:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}",
                )
                self.assertEqual(
                    _huella(CONFIG_REAL), antes,
                    f"{modulo} modificó {CONFIG_REAL}: hay una fuga de aislamiento",
                )

    def test_el_propio_guardian_detecta_un_modulo_sin_aislamiento(self):
        """Verifica que la regla estática muerde (si no, no protegería de nada)."""
        fuente_ficticia = (
            "import unittest\n"
            "from scrcpy_dock.security import SecurityManager\n"
            "class T(unittest.TestCase):\n"
            "    def test_algo(self):\n"
            "        sec = SecurityManager({'security': {}})\n"
        )
        tiene_riesgo = any(r in fuente_ficticia for r in RIESGO)
        tiene_aislamiento = any(a in fuente_ficticia for a in AISLAMIENTO)

        self.assertTrue(tiene_riesgo, "la regla no reconocería este caso")
        self.assertFalse(tiene_aislamiento, "la regla lo daría por aislado y no lo está")


if __name__ == "__main__":
    unittest.main()
