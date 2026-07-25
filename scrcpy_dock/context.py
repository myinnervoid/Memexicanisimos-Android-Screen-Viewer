import queue
import tkinter as tk
from .utils import load_config, save_config, find_portable_binaries
from .managers import ProfileManager, DeviceManager, SessionManager

class AppContext:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.log_q = queue.Queue()
        self.cfg = load_config()
        
        self.profile_mgr = ProfileManager(self.cfg)
        self.device_mgr = DeviceManager()
        self.session_mgr = SessionManager(self.log_q)
        
        self.active_device = tk.StringVar(value="Sin dispositivo")
        self.active_device_serial = None # Serial puro
        
        self.active_profile = tk.StringVar(value=self.cfg.get("last_selected_profile", "🎮 Juego Rápido"))
        
        self.adb, self.scrcpy = find_portable_binaries()
        self._subscribers = {}

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
