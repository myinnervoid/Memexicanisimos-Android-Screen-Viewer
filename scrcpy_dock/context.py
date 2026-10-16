import queue
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .utils import load_config, save_config, find_portable_binaries, CONFIG_DIR
from .managers import ProfileManager, DeviceManager, SessionManager
from .security import SecurityManager
from .state import UIStateMachine, UIState
from .i18n import set_language

from .core.adb_engine import AdbEngine
from .core.tether_engine import TetherEngine
from .services.tether_service import TetherService


@dataclass
class AppContext:
    """
    Contexto global de la aplicación que administra el estado, dependencias y ciclo de vida.

    Esta clase centraliza la inicialización de los motores (AdbEngine, TetherEngine),
    los gestores de dispositivos, perfiles, sesiones y seguridad, además de manejar
    el sistema de pub/sub para eventos y registros (logs) de la aplicación.

    Attributes:
        root: Ventana principal de tkinter.
        log_q: Cola thread-safe para mensajes de registro.
        cfg: Diccionario de configuración global de la aplicación.
        adb: Ruta al binario adb (si fue encontrado).
        scrcpy: Ruta al binario scrcpy (si fue encontrado).
        adb_engine: Motor de ejecución de comandos ADB.
        state_machine: Máquina de estados de la interfaz de usuario.
        profile_mgr: Gestor de perfiles de conexión.
        device_mgr: Gestor de dispositivos conectados.
        session_mgr: Gestor de sesiones scrcpy activas.
        security_mgr: Gestor de seguridad y bóveda de confianza.
        tether_engine: Motor de comandos para gnirehtet.
        tether_service: Servicio de orquestación de tethering inverso.
        active_device: Variable tkinter con el nombre a mostrar del dispositivo activo.
        active_device_serial: Serial puro del dispositivo activo.
        active_profile: Variable tkinter con el perfil actualmente seleccionado.
    """
    root: tk.Tk
    log_q: queue.Queue = field(init=False)
    cfg: Dict[str, Any] = field(init=False)
    
    adb: Optional[str] = field(init=False)
    scrcpy: Optional[str] = field(init=False)
    adb_engine: Optional[AdbEngine] = field(init=False)
    
    state_machine: UIStateMachine = field(init=False)
    profile_mgr: ProfileManager = field(init=False)
    device_mgr: DeviceManager = field(init=False)
    session_mgr: SessionManager = field(init=False)
    security_mgr: SecurityManager = field(init=False)
    tether_engine: TetherEngine = field(init=False)
    tether_service: TetherService = field(init=False)
    
    active_device: tk.StringVar = field(init=False)
    active_device_serial: Optional[str] = field(init=False, default=None)
    active_profile: tk.StringVar = field(init=False)
    
    _subscribers: Dict[str, List[Callable]] = field(init=False)

    def __post_init__(self):
        """
        Inicializa dependencias, binarios y variables de estado del contexto
        después de que se asigne la ventana principal (root).
        """
        self.log_q = queue.Queue()
        self.cfg = load_config()

        # Binarios y motor ADB ANTES de los managers: debe existir UNA sola
        # instancia del motor (un único socket aislado y un único registro de
        # tcpip activado por MASV) compartida por todos ellos. Antes cada
        # manager construía su propio AdbEngine, con estado divergente.
        self.adb, self.scrcpy = find_portable_binaries()
        self.adb_engine = AdbEngine(Path(self.adb)) if self.adb else None

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

    def set_adb_binary(self, adb_path: str) -> None:
        """
        Re-apunta el binario `adb` y el motor (p. ej. tras instalarlo).

        Args:
            adb_path: Ruta al nuevo ejecutable de adb.
        """
        self.adb = adb_path
        if self.adb_engine is not None:
            self.adb_engine.rebind(adb_path)

    def subscribe(self, event: str, callback: Callable) -> None:
        """
        Registra un suscriptor (callback) para un evento específico.

        Args:
            event: Nombre del evento al que suscribirse.
            callback: Función a ejecutar cuando el evento sea notificado.
        """
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(callback)

    def notify(self, event: str, data: Any = None) -> None:
        """
        Notifica a los suscriptores sobre un evento y les transmite información.

        Args:
            event: Nombre del evento emitido.
            data: Información u objeto asociado al evento a pasar a los callbacks.
        """
        for cb in self._subscribers.get(event, []):
            try:
                cb(data)
            except Exception as e:
                self.log("ERROR", f"Observer error [{event}]: {e}")
        
    def log(self, level: str, msg: str) -> None:
        """
        Inserta un mensaje en la cola global de registros.

        Args:
            level: Nivel de severidad del mensaje (ej. 'INFO', 'ERROR').
            msg: Contenido o cuerpo del mensaje de registro.
        """
        self.log_q.put((level, msg))
        
    def save_current_config(self) -> None:
        """
        Guarda el estado actual de la configuración, incluyendo el perfil seleccionado.
        """
        self.cfg["last_selected_profile"] = self.active_profile.get()
        save_config(self.cfg)

    def select_device(self, serial: str, display_name: str) -> None:
        """
        Actualiza el dispositivo activo en la interfaz de usuario.

        Args:
            serial: Serial puro del dispositivo (ej. '192.168.1.10:5555').
            display_name: Nombre legible del dispositivo a mostrar en la interfaz.
        """
        self.active_device_serial = serial
        self.active_device.set(display_name)
