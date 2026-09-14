"""Verificación estructural de services/ · Cierre del Paso 3.

Reglas arquitectónicas (ADR maestro sección 4.2):
  PROHIBIDO en services/*.py:
    - subprocess, socket crudo, os.system
    - tkinter o cualquier import de scrcpy_dock.ui
    - scrcpy_dock.managers (los services son consumidos por managers)
    - scrcpy_dock.core (services son dominio, no infraestructura)
  PERMITIDO en services/*.py:
    - stdlib (json, ipaddress, secrets, shutil, os, logging, textwrap)
    - scrcpy_dock.domain.*
    - scrcpy_dock.contracts, scrcpy_dock.errors
    - cryptography.* (solo en security_service)
"""
from __future__ import annotations
import ast
import unittest
from pathlib import Path


SERVICES_DIR = (
    Path(__file__).resolve().parents[2]
    / "scrcpy_dock" / "services"
)

FORBIDDEN_MODULES = frozenset({
    "subprocess",
    "scrcpy_dock.managers",
    "scrcpy_dock.core",
    "scrcpy_dock.ui",
})

FORBIDDEN_PREFIXES = ("tkinter", "scrcpy_dock.ui")


def _service_files() -> list[Path]:
    """Todos los .py de services/ excepto __init__.py."""
    return sorted(
        p for p in SERVICES_DIR.glob("*.py") if p.name != "__init__.py"
    )


def _all_imports(tree: ast.AST) -> list[tuple[int, str]]:
    """Extrae (lineno, module) de todos los imports."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.append((node.lineno, node.module))
    return found


class ServicesIsolationContract(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.files = _service_files()
        assert cls.files, "no se encontraron archivos en services/"
        cls.parsed = {}
        for f in cls.files:
            cls.parsed[f] = ast.parse(f.read_text(encoding="utf-8"))

    def test_services_dir_contains_expected_modules(self):
        names = {f.name for f in self.files}
        self.assertIn("security_service.py", names)
        self.assertIn("profile_service.py", names)
        self.assertIn("installer_service.py", names)

    def test_no_forbidden_exact_modules(self):
        for path, tree in self.parsed.items():
            for lineno, module in _all_imports(tree):
                self.assertNotIn(
                    module, FORBIDDEN_MODULES,
                    f"{path.name}:{lineno} importa '{module}' (prohibido)",
                )

    def test_no_forbidden_prefixes(self):
        for path, tree in self.parsed.items():
            for lineno, module in _all_imports(tree):
                for prefix in FORBIDDEN_PREFIXES:
                    self.assertFalse(
                        module == prefix or module.startswith(prefix + "."),
                        f"{path.name}:{lineno} importa '{module}' "
                        f"(prefijo prohibido '{prefix}')",
                    )

    def test_no_attribute_access_to_subprocess(self):
        for path, tree in self.parsed.items():
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name) \
                       and node.value.id == "subprocess":
                        self.fail(
                            f"{path.name}:{node.lineno} accede a "
                            f"subprocess.{node.attr}",
                        )

    def test_no_os_system_call(self):
        for path, tree in self.parsed.items():
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name) \
                       and node.value.id == "os" \
                       and node.attr in ("system", "popen", "spawnv"):
                        self.fail(
                            f"{path.name}:{node.lineno} usa os.{node.attr}",
                        )


class ServicesAllowedDependenciesContract(unittest.TestCase):
    """Verifica que los imports de services vienen de la capa permitida."""

    ALLOWED_TOP_LEVEL = frozenset({
        # stdlib explícito (whitelist, no blacklist)
        "json", "os", "logging", "ipaddress", "secrets", "shutil",
        "textwrap", "stat", "tempfile", "pathlib", "dataclasses",
        "typing", "base64", "abc", "datetime", "collections",
        # dependencias externas declaradas
        "cryptography",
        # módulos internos
        "scrcpy_dock",
        "__future__",
    })

    def test_all_imports_from_allowed_roots(self):
        for path in _service_files():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for lineno, module in _all_imports(tree):
                root = module.split(".")[0]
                self.assertIn(
                    root, self.ALLOWED_TOP_LEVEL,
                    f"{path.name}:{lineno} importa '{module}' desde raíz "
                    f"'{root}' no declarada en la whitelist. "
                    f"Si es legítimo, añadir a ALLOWED_TOP_LEVEL con "
                    f"justificación en ADR.",
                )


class ServicesIndependenceContract(unittest.TestCase):
    """Verifica que services/ no importa entre sí (independientes)."""

    def test_no_cross_service_imports(self):
        for path in _service_files():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for lineno, module in _all_imports(tree):
                if module.startswith("scrcpy_dock.services."):
                    self.fail(
                        f"{path.name}:{lineno} importa otro service "
                        f"('{module}'). Los services deben ser "
                        f"independientes entre sí.",
                    )

    def test_init_is_empty_or_docstring_only(self):
        init = SERVICES_DIR / "__init__.py"
        if not init.exists():
            self.skipTest("services/__init__.py no existe")
        tree = ast.parse(init.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Expr) \
               and isinstance(node.value, ast.Constant):
                continue   # docstring
            self.fail(
                f"services/__init__.py contiene código ejecutable: "
                f"{ast.dump(node)[:80]}",
            )


if __name__ == "__main__":
    unittest.main()
