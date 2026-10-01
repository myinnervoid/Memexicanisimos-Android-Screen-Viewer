import queue
import tkinter as tk
from pathlib import Path
from typing import Optional
from .utils import load_config, save_config, find_portable_binaries, CONFIG_DIR
from .managers import ProfileManager, DeviceManager, SessionManager
from .security import SecurityManager
from .state import UIStateMachine, UIState
from .i18n import set_language

from .core.adb_engine import AdbEngine
from .core.tether_engine import TetherEngine
from .services.tether_service import TetherService

class AppContext:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.log_q = queue.Queue()
        self.cfg = load_config()

        # Binarios y motor ADB ANTES de los managers: debe existir UNA sola
        # instancia del motor (un único socket aislado y un único registro de
        # tcpip activado por MASV) compartida por todos ellos. Antes cada
        # manager construía su propio AdbEngine, con estado divergente.
        self.adb, self.scrcpy = find_portable_binaries()
        self.adb_engine: Optional[AdbEngine] = AdbEngine(Path(self.adb)) if self.adb else None

        self.state_machine = UIStateMachine(UIState.IDLE)
        self.profile_mgr = ProfileManager(self.cfg)
        self.device_mgr = DeviceManager(adb_engine=self.adb_engine)
        self.session_mgr = SessionManager(
            self.log_q, device_mgr=self.device_mgr, adb_engine=self.adb_engine,
        )
        self.security_mgr = SecurityManager(self.cfg, vault_dir=CONFIG_DIR)
        self.tether_engine = TetherEngine()
        self.tether_service = TetherService(self.tether_engine)
        
        self.active_device = tk.StringVar(value="Sin dispositivo")
        self.active_device_serial = None # Serial puro
        
        self.active_profile = tk.StringVar(value=self.cfg.get("last_selected_profile", "🎮 Juego Rápido"))
        
        self._subscribers = {}

        # Set language from config
        lang = self.cfg.get("language", "es")
        set_language(lang)

    def set_adb_binary(self, adb_path) -> None:
        """Re-apunta el binario `adb` y el motor (p. ej. tras instalarlo)."""
        self.adb = adb_path
        if self.adb_engine is not None:
            self.adb_engine.rebind(adb_path)

    def subscribe(self, event: str, callback):
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(callback)

    def notify(self, event: str, data=None):
        for cb in self._subscribers.get(event, []):
            try:
                cb(data)
            except Exception as e:
                self.log("ERROR", f"Observer error [{event}]: {e}")
        
    def log(self, level: str, msg: str):
        self.log_q.put((level, msg))
        
    def save_current_config(self):
        self.cfg["last_selected_profile"] = self.active_profile.get()
        save_config(self.cfg)

    def select_device(self, serial: str, display_name: str):
        self.active_device_serial = serial
        self.active_device.set(display_name)
