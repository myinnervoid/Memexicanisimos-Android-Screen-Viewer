"""C2 · Partición de `ui_tabs.py` en pestañas atómicas.

Dos bloques de pruebas:

  · **Estructurales** (sin Tk, corren siempre): la partición existe, la fachada
    sigue siendo fachada, cada pestaña es su propio módulo y los constructores
    declaran el contrato `(parent, tab)`.
  · **De comportamiento** (sobre la app real del arnés): reconstruir una pestaña
    no acumula widgets — la regresión de P3.25 — y la lista de la FAQ conserva
    su identidad, que es lo que `main.py` lee por atributo.

Ejecutable con: python -m unittest discover -s tests
"""
from __future__ import annotations

import ast
import inspect
import tkinter as tk
import unittest
from pathlib import Path

import scrcpy_dock.ui_tabs as ui_tabs_mod
import scrcpy_dock.utils as utils
from scrcpy_dock.ui.tabs import (
    tab_actions,
    tab_console,
    tab_controls,
    tab_device,
    tab_help,
    tab_profile,
    tab_quickcast,
)
from scrcpy_dock.ui.tabs.common import TabContext
from scrcpy_dock.ui_tabs import UIBuilder

from tests.ui_harness import app_en_prueba

RAIZ = Path(ui_tabs_mod.__file__).resolve().parent
FACHADA = RAIZ / "ui_tabs.py"
PAQUETE = RAIZ / "ui" / "tabs"

# Pestaña → (módulo, método de la fachada), en el orden de `main.py:_select_tab`
PESTANAS = {
    "quickcast": (tab_quickcast, "build_simple_view"),
    "actions": (tab_actions, "build_tab_actions"),
    "device": (tab_device, "build_tab_device"),
    "controls": (tab_controls, "build_tab_controls"),
    "profiles": (tab_profile, "build_tab_profile"),
    "console": (tab_console, "build_tab_console"),
    "help": (tab_help, "build_tab_help"),
}
MODULOS = ["common.py"] + [f"tab_{n}.py" for n in
                           ("quickcast", "actions", "controls", "device",
                            "profile", "console", "help")]


def _descendientes(widget) -> set:
    """Nombres Tk de todos los widgets del subárbol, recursivamente."""
    vistos: set = set()
    pila = [widget]
    while pila:
        for hijo in pila.pop().winfo_children():
            vistos.add(str(hijo))
            pila.append(hijo)
    return vistos


# ─────────────────────────────────────────────────────────────────────────────
# Estructura (no necesita display)
# ─────────────────────────────────────────────────────────────────────────────

class TestParticionDeLaUI(unittest.TestCase):

    def test_existe_un_modulo_por_pestana_mas_las_piezas_comunes(self):
        presentes = sorted(p.name for p in PAQUETE.glob("*.py") if p.name != "__init__.py")
        self.assertEqual(presentes, sorted(MODULOS))

    def test_la_fachada_es_una_fachada_y_no_vuelve_a_crecer(self):
        """`ui_tabs.py` tenía 1.034 líneas; si alguien vuelve a meter widgets aquí, falla."""
        fuente = FACHADA.read_text(encoding="utf-8")
        self.assertLess(len(fuente.splitlines()), 120,
                        "la fachada volvió a crecer: el código de una pestaña debe ir en ui/tabs/")
        for construir in ("tk.Frame(", "tk.Label(", "tk.Button(", "tk.Canvas(",
                          "tk.Text(", "tk.Listbox(", "ttk.Treeview("):
            self.assertNotIn(construir, fuente, f"la fachada construye widgets ({construir})")

    def test_ningun_modulo_de_pestana_se_dispara(self):
        """Ayuda es el mayor legítimamente (19 acordeones); el techo es una red."""
        for nombre in MODULOS:
            lineas = len((PAQUETE / nombre).read_text(encoding="utf-8").splitlines())
            with self.subTest(modulo=nombre):
                self.assertLess(lineas, 400, f"{nombre} tiene {lineas} líneas")

    def test_cada_constructor_declara_el_contrato_parent_tab(self):
        for pestana, (modulo, _) in PESTANAS.items():
            with self.subTest(pestana=pestana):
                parametros = list(inspect.signature(modulo.build).parameters)
                self.assertEqual(parametros, ["parent", "tab"])

    def test_la_fachada_conserva_la_api_que_consume_main(self):
        firma = list(inspect.signature(UIBuilder.__init__).parameters)
        self.assertEqual(firma, ["self", "app_context", "callbacks"],
                         "main.py construye UIBuilder(ctx, cb)")

        fachada = UIBuilder(object(), {})
        for atributo in ("ctx", "cb", "refs", "_faq_items"):
            self.assertTrue(hasattr(fachada, atributo), f"falta UIBuilder.{atributo}")
        for _, metodo in PESTANAS.values():
            self.assertTrue(callable(getattr(fachada, metodo, None)), f"falta {metodo}()")

    def test_el_contrato_de_pestana_comparte_las_salidas_por_identidad(self):
        """Si `TabContext` copiara `refs`, la app no vería ningún widget."""
        refs: dict = {}
        faq: list = []
        tab = TabContext(object(), {}, refs, faq)

        self.assertIs(tab.refs, refs)
        self.assertIs(tab.faq_items, faq)

    def test_la_fachada_pasa_su_propio_refs_y_faq(self):
        fachada = UIBuilder(object(), {})
        self.assertIs(fachada._tabs.refs, fachada.refs)
        self.assertIs(fachada._tabs.faq_items, fachada._faq_items)


# ─────────────────────────────────────────────────────────────────────────────
# Comportamiento sobre la app real
# ─────────────────────────────────────────────────────────────────────────────

class TestReconstruccionDePestanas(unittest.TestCase):
    """P3.25: reconstruir una pestaña encima de la anterior apilaba widgets."""

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
        # `askyesno` responde NO: así se recorre la reconstrucción en caliente
        # (el otro camino sería reiniciar la app, que aquí no interesa).
        self.sitio = app_en_prueba(self.root, answers={"askyesno": False, "askokcancel": True})
        self.addCleanup(self.sitio.cerrar)
        self.addCleanup(utils.apply_theme, "warm_stone")   # el tema es estado global del módulo

    def _censo(self) -> dict:
        return {t: len(self.sitio.app._tab_frames[t].winfo_children())
                for t in PESTANAS}

    def test_cambiar_de_tema_no_duplica_el_contenido_de_las_pestanas(self):
        """El bug: `actions`, `controls` y `profiles` crecían 2 → 4 → 6 hijos."""
        antes = self._censo()

        self.sitio.app._change_theme("cyber_obsidian")
        self.assertEqual(self._censo(), antes, "un cambio de tema duplicó widgets")

        self.sitio.app._change_theme("nordic_slate")
        self.assertEqual(self._censo(), antes, "el segundo cambio de tema volvió a duplicar")

    def test_cada_pestana_se_puede_reconstruir_sin_acumular(self):
        for pestana, (_, metodo) in PESTANAS.items():
            with self.subTest(pestana=pestana):
                frame = self.sitio.app._tab_frames[pestana]
                antes = len(frame.winfo_children())

                getattr(self.sitio.app.ui, metodo)(frame)

                self.assertEqual(len(frame.winfo_children()), antes,
                                 f"{pestana} acumuló widgets al reconstruirse")

    def test_tras_reconstruir_los_refs_apuntan_al_arbol_vivo(self):
        """El bug dejaba `refs` re-apuntado a widgets de un build que ya nadie ve."""
        self.sitio.app._change_theme("cyber_obsidian")

        vivos = _descendientes(self.sitio.app._tab_frames["profiles"])
        for clave in ("profile_listbox", "active_profile_combo", "profile_chips"):
            with self.subTest(ref=clave):
                widget = self.sitio.app.ui.refs[clave]
                self.assertTrue(widget.winfo_exists())
                self.assertIn(str(widget), vivos,
                              f"refs['{clave}'] quedó fuera del árbol visible")

    def test_la_lista_de_la_faq_conserva_su_identidad(self):
        """`main.py` hace `self.ui._faq_items[1].expand()`: si se rebinda, deja de verlas."""
        lista = self.sitio.app.ui._faq_items
        self.assertEqual(len(lista), 19, "la ayuda debe registrar sus 19 acordeones")

        self.sitio.app.ui.build_tab_help(self.sitio.app._tab_frames["help"])

        self.assertIs(self.sitio.app.ui._faq_items, lista,
                      "la lista de la FAQ se rebindó: main.py seguiría mirando la vieja")
        self.assertEqual(len(lista), 19, "tras reconstruir deben quedar 19, no 38")


class TestCazadoPorC2(unittest.TestCase):
    """Documenta el defecto que la partición destapó (P3.25)."""

    def test_todas_las_pestanas_se_construyen_sobre_un_contenedor_limpio(self):
        """La causa raíz: solo 4 de 7 limpiaban el contenedor antes de reconstruir.

        Se comprueba sobre el código, no sobre la UI: cada módulo debe llamar a
        `clear(parent)`. Sin esa llamada, `main.py:_change_theme` (que invoca los
        siete constructores sobre los MISMOS frames) apila un árbol completo.
        """
        for pestana, (modulo, _) in PESTANAS.items():
            with self.subTest(pestana=pestana):
                fuente = Path(modulo.__file__).read_text(encoding="utf-8")
                arbol = ast.parse(fuente)
                llamadas = {nodo.func.id for nodo in ast.walk(arbol)
                            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)}
                self.assertIn("clear", llamadas,
                              f"{modulo.__name__} no limpia el contenedor al reconstruirse")


if __name__ == "__main__":
    unittest.main()
