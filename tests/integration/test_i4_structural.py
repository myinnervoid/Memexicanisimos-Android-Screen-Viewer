"""I4 · Verificación estructural · managers.py no debe usar subprocess."""
from __future__ import annotations
import ast
import unittest
from pathlib import Path


MANAGERS_PATH = Path(__file__).resolve().parents[2] / "scrcpy_dock" / "managers.py"


class ManagersNoSubprocessContract(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = MANAGERS_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_no_import_subprocess(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotEqual(
                        alias.name, "subprocess",
                        "managers.py no debe importar subprocess directamente",
                    )
            elif isinstance(node, ast.ImportFrom):
                self.assertNotEqual(
                    node.module, "subprocess",
                    "managers.py no debe hacer 'from subprocess import ...'",
                )

    def test_no_subprocess_attribute_access(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name) \
                   and node.value.id == "subprocess":
                    self.fail(
                        f"managers.py:{node.lineno} accede a subprocess."
                        f"{node.attr}",
                    )

    def test_no_shell_true_flag(self):
        """Ningún call con shell=True (defensa en profundidad)."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant):
                        self.assertNotEqual(kw.value.value, True)


class ManagersImportsEnginesContract(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = MANAGERS_PATH.read_text(encoding="utf-8")

    def test_imports_adb_engine(self):
        self.assertIn("AdbEngine", self.source)

    def test_imports_scrcpy_engine(self):
        self.assertIn("ScrcpyEngine", self.source)

    def test_imports_port_allocator(self):
        self.assertIn("PortAllocator", self.source)


if __name__ == "__main__":
    unittest.main()
