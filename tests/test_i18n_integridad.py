"""Integridad de la tabla de traducciones: sin huérfanas, sin faltantes, sin duplicadas.

Tres trampas que ya han aparecido en este proyecto, ahora imposibles de repetir sin
que falle una prueba:

1. **Sin huérfanas** — una entrada que nadie usa es una trampa de mantenimiento:
   quien la edite para corregir lo que ve el usuario no verá ningún efecto (fue el
   caso de P3.26: 6 claves duplicadas donde ganaba la última y la primera era
   inalcanzable).
2. **Sin faltantes** — toda cadena que pase por `_()` debe tener traducción inglesa.
3. **Sin duplicadas** — se cuentan las claves del **literal del AST**, no las del
   diccionario resultante: en un dict la última gana y el duplicado desaparece sin
   dejar rastro.

Cómo se calcula lo "usado": por **dos vías**, porque una sola miente.
  · *estática*: literales pasados directamente a `_("…")`;
  · *de flujo*: literales que llegan a `_()` a través de otra función — hoy el único
    caso es `_add("título", …)`, cuyo primer argumento acaba en `_(title)`
    (`ui/tabs/tab_help.py`). Sin esta vía, los 19 títulos de la FAQ parecían
    huérfanos y una poda ingenua los habría borrado estando vivos.

Si se añade una nueva puerta de entrada a `_()`, hay que declararla en `VIAS_DE_FLUJO`.

Ejecutable con: python -m unittest discover -s tests
"""
from __future__ import annotations

import ast
import importlib
import unittest
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
I18N = RAIZ / "scrcpy_dock" / "i18n.py"
FUENTES = [f for f in (RAIZ / "scrcpy_dock").rglob("*.py") if f.name != "i18n.py"]

# Funciones propias que reenvían su primer literal a `_()`.
VIAS_DE_FLUJO = ("_add", "_selector")


def _tablas_del_literal() -> tuple[list[str], list[str]]:
    """Claves del literal `_translations['en']` y de `_EN_EXTRA`, tal como están escritas."""
    arbol = ast.parse(I18N.read_text(encoding="utf-8"))
    en, extra = [], []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Assign) and isinstance(nodo.value, ast.Dict):
            nombres = [t.id for t in nodo.targets if isinstance(t, ast.Name)]
            if nombres == ["_translations"]:
                for k, v in zip(nodo.value.keys, nodo.value.values):
                    if isinstance(k, ast.Constant) and k.value == "en" and isinstance(v, ast.Dict):
                        en = [ast.literal_eval(x) for x in v.keys]
            elif nombres == ["_EN_EXTRA"]:
                extra = [ast.literal_eval(x) for x in nodo.value.keys]
    return en, extra


def _claves_usadas() -> dict[str, list[str]]:
    """Clave → archivos que la usan, por las dos vías."""
    usadas: dict[str, list[str]] = {}

    def anota(valor, archivo):
        usadas.setdefault(valor, []).append(archivo)

    for f in FUENTES:
        rel = f.relative_to(RAIZ).as_posix()
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                literales = [a.value for a in n.args
                             if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                if n.func.id == "_":
                    for valor in literales:
                        anota(valor, rel)
                elif n.func.id in VIAS_DE_FLUJO:
                    for valor in literales:
                        anota(valor, rel)
    return usadas


class TestIntegridadDeLaTablaDeTraducciones(unittest.TestCase):

    def setUp(self):
        en, extra = _tablas_del_literal()
        self.literal = en + extra
        self.tabla = set(self.literal)
        self.usadas = _claves_usadas()

    def test_no_hay_claves_duplicadas_en_el_literal(self):
        """P3.26: en un dict la última gana, así que el duplicado es invisible al leer."""
        repetidas = {k: n for k, n in Counter(self.literal).items() if n > 1}
        self.assertEqual(repetidas, {}, f"claves repetidas en el literal: {list(repetidas)}")

    def test_toda_cadena_usada_tiene_traduccion(self):
        faltan = sorted(k for k in self.usadas if k not in self.tabla)
        self.assertEqual(
            faltan, [],
            "estas cadenas pasan por _() y no tienen traducción inglesa",
        )

    def test_no_quedan_claves_huerfanas(self):
        """Una entrada que nadie usa es una trampa: editarla no surte efecto."""
        huerfanas = sorted(self.tabla - set(self.usadas))
        self.assertEqual(
            huerfanas, [],
            f"{len(huerfanas)} claves en la tabla que ningún módulo usa "
            f"(poda con `podar_i18n.py` o añade la vía de flujo que falte en VIAS_DE_FLUJO)",
        )

    def test_la_via_de_flujo_sigue_siendo_necesaria(self):
        """Blinda el caso que casi provoca 19 borrados: los títulos de la FAQ."""
        titulos = [k for k, archivos in self.usadas.items()
                   if any("tab_help" in a for a in archivos)]
        self.assertGreaterEqual(len(titulos), 19,
                                "los títulos de la FAQ deben contarse como usados")

    def test_ninguna_entrada_esta_vacia(self):
        """Una entrada vacía no traduce nada y pasaría desapercibida.

        Nota: que el inglés coincida con el español **no** es un defecto — es lo
        normal en siglas, marcas y rótulos con icono ("ADB", "Error", "🔊 Audio").
        Por eso aquí sólo se comprueba que haya texto.
        """
        i18n = importlib.import_module("scrcpy_dock.i18n")
        tabla = i18n._translations["en"]

        vacias = [k for k, v in tabla.items() if not isinstance(v, str) or not v.strip()]
        self.assertEqual(vacias, [], "hay entradas sin texto de traducción")


if __name__ == "__main__":
    unittest.main()
