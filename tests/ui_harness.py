"""Arnés compartido: la aplicación REAL sobre un Tk oculto, sin efectos secundarios.

Lo usan `test_ui_smoke.py` (arnés D1) y `test_fase_c2_regressions.py`. Antes vivía
dentro del primero; se extrajo para que las pruebas de C2 no duplicaran el rig.

Garantías del arnés:
  · la app se instancia de verdad (`ScrcpyDockApp`), no un doble de la ventana
  · `CONFIG_FILE`/`LOG_FILE`/`CONFIG_DIR` apuntan a un temporal (nunca a
    `~/.config/masv/` del usuario)
  · ningún handler puede abrir un proceso real: `subprocess.Popen` está doblado
    y los blindajes de seguridad (que lanzan `adb`) están sustituidos
"""
from __future__ import annotations

import copy
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock, patch

import scrcpy_dock.context as context_mod
import scrcpy_dock.main as main_mod
import scrcpy_dock.utils as utils
from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.security import SecurityManager

# Procesos que la app intentó lanzar durante una prueba (debe quedar vacío).
_LAUNCHED: list = []


class _FakePopen:
    """`subprocess.Popen` bien comportado: registra y no ejecuta nada.

    Se parchea el atributo del módulo (`subprocess.Popen`) porque `run()` lo
    resuelve internamente; por eso el doble debe implementar el protocolo que
    `run()` espera (`__enter__`/`__exit__`, `communicate`, `poll`) y devolver
    salida vacía con código 0 — así ningún camino real del código abre un
    proceso, pero `subprocess.run([...])` sigue respondiendo como si todo
    hubiera ido bien.
    """

    def __init__(self, args=None, *a, **kwargs):
        self.args = args
        self.pid = 0
        self.returncode = 0
        _LAUNCHED.append(args)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def communicate(self, input=None, timeout=None):
        return "", ""

    def poll(self):
        return 0

    def wait(self, timeout=None):
        return 0

    def terminate(self):
        pass

    def kill(self):
        pass


class _FakeProc:
    """Proceso falso con la interfaz que consume ScrcpySession."""
    pid = 43210

    def poll(self):
        return None

    def terminate(self):
        pass

    def kill(self):
        pass

    def wait(self, timeout=None):
        return 0


class _FakeAdbEngine:
    """AdbEngine sin subprocess. Registra lo que la UI le pide."""

    def __init__(self, *args, **kwargs):
        self._adb_binary = Path("/usr/bin/adb")
        self._effective_port = 5037
        self._daemon_started = True
        self._activated_by_masv: set[str] = set()
        self.calls: list = []

    # contrato del motor real que usa la app
    def start_daemon(self):
        return OperationResult.ok(5037, "fake daemon")

    def list_devices(self):
        return OperationResult.ok([], "0 dispositivo(s)")

    def get_properties(self, serial):
        return OperationResult.ok({
            "ro.build.version.sdk": "34",
            "ro.build.version.release": "14",
            "ro.product.manufacturer": "vivo",
            "ro.product.model": "V2314",
            "ro.board.platform": "qcom",
        })

    def start_tcpip(self, serial, port=5555):
        self.calls.append(("start_tcpip", serial, port))
        self._activated_by_masv.add(serial)
        return OperationResult.ok(None, "fake tcpip")

    def revert_tcpip(self, serial):
        self.calls.append(("revert_tcpip", serial))
        return OperationResult.ok(None, "fake revert")

    def connect_wifi(self, host, port=5555):
        self.calls.append(("connect_wifi", host, port))
        return OperationResult.ok(f"{host}:{port}", "fake connect")

    def connect(self, target, timeout=8):
        self.calls.append(("connect", target))
        return OperationResult.ok(target, "fake connect")

    def disconnect_wifi(self, serial):
        return OperationResult.ok(None, "fake disconnect")

    def shell(self, serial, *args, timeout=10, error_code=None):
        self.calls.append(("shell", serial, args))
        return OperationResult.ok("", "fake shell")

    def install(self, serial, apk_path, timeout=180):
        return OperationResult.ok("Success", "Success")

    def kill_server(self):
        return OperationResult.ok(None, "fake kill")

    def rebind(self, adb_binary):
        self._adb_binary = Path(adb_binary)

    def track_devices_async(self, on_change, on_daemon_dead, max_reconnect_attempts=5):
        return OperationResult.ok(None, "sin tracker en pruebas")

    def stop_tracker(self):
        pass

    @property
    def effective_socket_port(self):
        return self._effective_port


class _DialogRecorder:
    """Sustituye a messagebox/filedialog: registra y responde sin bloquear."""

    def __init__(self, answers: dict | None = None):
        self.calls: list[tuple] = []
        self._answers = answers or {}

    def __getattr__(self, name):
        def _call(*args, **kwargs):
            self.calls.append((name, args))
            return self._answers.get(name, False)
        return _call

    def did(self, name: str) -> bool:
        return any(c[0] == name for c in self.calls)

    def last(self, name: str):
        for call in reversed(self.calls):
            if call[0] == name:
                return call
        return None


def parches_entorno(cfg_data: dict, tmp: str) -> list:
    """Aísla el entorno del usuario y sustituye todo lo que toca hardware/red."""
    return [
        patch.object(utils, "CONFIG_FILE", str(Path(tmp, "config.json"))),
        patch.object(utils, "LOG_FILE", str(Path(tmp, "masv.log"))),
        patch.object(utils, "CONFIG_DIR", tmp),
        patch.object(context_mod, "CONFIG_DIR", tmp),
        patch.object(context_mod, "find_portable_binaries",
                     return_value=("/usr/bin/adb", "/usr/local/bin/scrcpy")),
        patch.object(context_mod, "AdbEngine", _FakeAdbEngine),
        patch.object(context_mod, "load_config", lambda: copy.deepcopy(cfg_data)),
        patch.object(utils, "save_config", lambda cfg: None),
        patch("tkinter.Misc.wait_window", lambda self, window=None: None),
        patch("tkinter.Misc.grab_set", lambda self: None),
        # Los lockdowns lanzan `adb` real: nunca desde el arnés.
        patch.object(SecurityManager, "pair_device",
                     staticmethod(lambda *a, **k: (True, "fake"))),
        patch.object(SecurityManager, "lockdown_device_tcpip",
                     staticmethod(lambda *a, **k: (True, "fake"))),
        patch.object(SecurityManager, "lockdown_all_devices",
                     staticmethod(lambda *a, **k: (0, "fake"))),
    ]


def parches_ui(dialogs: _DialogRecorder, toasts: list) -> list:
    """Ningún handler puede abrir un proceso ni un diálogo modal real."""
    return [
        patch.object(main_mod, "messagebox", dialogs),
        patch.object(main_mod, "filedialog", _DialogRecorder()),
        patch.object(main_mod, "Toast", lambda *a, **k: toasts.append(a) or MagicMock()),
        patch.object(main_mod.subprocess, "Popen", _FakePopen),
    ]


def config_de_prueba(**cambios) -> dict:
    """`DEFAULT_CONFIG` sin onboarding ni estado de ventana previo."""
    cfg = copy.deepcopy(utils.DEFAULT_CONFIG)
    cfg["onboarding_done"] = True       # evita el modal de bienvenida
    cfg["language"] = "es"
    cfg.pop("window_state", None)
    cfg.update(cambios)
    return cfg


class AppEnPrueba:
    """Ciclo de vida completo: parches, app real y limpieza.

    Uso:
        with app_en_prueba(root) as sitio:
            sitio.app.ui.
    """

    def __init__(self, root, answers=None, cfg_data=None):
        self.root = root
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg_data = cfg_data or config_de_prueba()
        self.dialogs = _DialogRecorder(answers or {"askyesno": True, "askokcancel": True})
        self.toasts: list[tuple] = []
        self.app = None
        self._parches: list = []

    def iniciar(self) -> "AppEnPrueba":
        _LAUNCHED.clear()
        self._parches = parches_entorno(self.cfg_data, self.tmp.name)
        self._parches += parches_ui(self.dialogs, self.toasts)
        for p in self._parches:
            p.start()
        from scrcpy_dock.main import ScrcpyDockApp
        self.app = ScrcpyDockApp(self.root)
        # Efectos irreversibles neutralizados también en los handlers permitidos.
        self.app._restart_app = lambda *a, **k: None
        return self

    def cerrar(self) -> None:
        for p in reversed(self._parches):
            p.stop()
        self._parches = []
        try:
            for hijo in self.root.winfo_children():
                if isinstance(hijo, tk.Toplevel):
                    hijo.destroy()
        except Exception:
            pass
        self.tmp.cleanup()


def app_en_prueba(root, answers=None, cfg_data=None) -> AppEnPrueba:
    """Atajo: `AppEnPrueba(...).iniciar()`."""
    return AppEnPrueba(root, answers=answers, cfg_data=cfg_data).iniciar()
