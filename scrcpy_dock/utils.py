import copy
import errno
import logging
import os, sys, re, time, socket, shutil, json
from typing import Optional

log = logging.getLogger(__name__)

# ── Paleta Warm Modern Dark — Sistema de Diseño Canónico MASV ────────────────
# Diseño cálido personal (Warm Stone Deep, Ámbar Dorado, Terracota y Marfil)
C = {
    # Fondos principales (Elevación por capas cálidas profundas)
    "bg":          "#141210",   # Warm Stone Deep 950 - Ventana principal
    "card":        "#1E1B18",   # Warm Stone 900 - Tarjetas y contenedores
    "card2":       "#282522",   # Warm Stone 850 - Headers, toolbars, entradas
    "card3":       "#35312D",   # Warm Stone 800 - Hover sutil
    "card_border": "#383430",   # Borde de tarjeta moderno de 1px

    # Separadores y bordes
    "sep":         "#2F2B27",   # Borde de separación sutil cálido

    # Navegación por pastillas (Pill Navigation)
    "pill_bg":     "#221F1C",   # Fondo de barra de pastillas
    "pill_btn":    "#2C2825",   # Botón de pastilla inactivo
    "pill_hover":  "#38332E",   # Hover de pastilla
    "pill_active": "#D97706",   # Pastilla activa (Ámbar)
    "pill_text":   "#A8A29E",   # Texto inactivo
    "pill_text_act":"#141210",  # Texto activo (WCAG AA sobre pill_active)

    # Acciones primarias y acentos
    "blue":        "#D97706",   # Ámbar Cálido Primario
    "blue_hover":  "#B45309",
    "indigo":      "#F59E0B",   # Ámbar Dorado - Acento de marca
    "indigo_hover":"#D97706",

    # Peligro / Cancelar
    "red":         "#E11D48",   # Rosa/Rojo moderno
    "red_dim":     "#3B0D18",   # Fondo de alerta sutil
    "red_hover":   "#BE123C",

    # Éxito / Estado Activo
    "green":       "#10B981",   # Esmeralda cálido
    "green_dim":   "#064E3B",   # Fondo de estado OK
    "green_hover": "#059669",

    # Advertencia / Terracota
    "orange":      "#EA580C",   # Terracota cálido
    "orange_hover":"#C2410C",

    # Acento / Perfiles
    "purple":      "#F59E0B",   # Ámbar Dorado
    "purple_dim":  "#451A03",
    "purple_hover":"#D97706",

    # Información / WiFi
    "cyan":        "#FBBF24",   # Dorado brillante

    # Tipografía — Legibilidad cálida (WCAG AAA)
    "text":        "#FAFAF9",   # Off-white cálido
    "text2":       "#E7E5E4",   # Stone 200 - Texto secundario
    "muted":       "#A8A29E",   # Stone 400 - Etiquetas y pistas

    # Estados desactivados
    "disabled":    "#383430",

    # Foco de accesibilidad (Tab)
    "focus":       "#F59E0B",

    # Badges de estado semánticos
    "state_ok":      "#10B981",
    "state_warn":    "#F59E0B",
    "state_err":     "#EF4444",
    "state_neutral": "#78716C",
}


THEMES = {
    'warm_stone': {
        "bg":          "#141210",
        "card":        "#1E1B18",
        "card2":       "#282522",
        "card3":       "#35312D",
        "card_border": "#383430",
        "sep":         "#2F2B27",
        "pill_bg":     "#221F1C",
        "pill_btn":    "#2C2825",
        "pill_hover":  "#38332E",
        "pill_active": "#D97706",
        "pill_text":   "#A8A29E",
        "pill_text_act":"#141210",
        "blue":        "#D97706",
        "blue_hover":  "#B45309",
        "indigo":      "#F59E0B",
        "indigo_hover":"#D97706",
        "red":         "#E11D48",
        "red_dim":     "#3B0D18",
        "red_hover":   "#BE123C",
        "green":       "#10B981",
        "green_dim":   "#064E3B",
        "green_hover": "#059669",
        "orange":      "#EA580C",
        "orange_hover":"#C2410C",
        "purple":      "#F59E0B",
        "purple_dim":  "#451A03",
        "purple_hover":"#D97706",
        "cyan":        "#FBBF24",
        "text":        "#FAFAF9",
        "text2":       "#E7E5E4",
        "muted":       "#A8A29E",
        "disabled":    "#383430",
        "focus":       "#F59E0B",
        "state_ok":      "#10B981",
        "state_warn":    "#F59E0B",
        "state_err":     "#EF4444",
        "state_neutral": "#78716C",
    },
    'cyber_obsidian': {
        "bg":          "#0B0D13",
        "card":        "#12151F",
        "card2":       "#1A1F2C",
        "card3":       "#222A3A",
        "card_border": "#2E364F",
        "sep":         "#1E2436",
        "pill_bg":     "#0F121C",
        "pill_btn":    "#161A26",
        "pill_hover":  "#242B42",
        "pill_active": "#00F0FF",
        "pill_text":   "#94A3B8",
        "pill_text_act":"#0B0D13",
        "blue":        "#00F0FF",
        "blue_hover":  "#00C2CF",
        "indigo":      "#3B82F6",
        "indigo_hover":"#2563EB",
        "red":         "#FF0055",
        "red_dim":     "#330011",
        "red_hover":   "#CC0044",
        "green":       "#10B981",
        "green_dim":   "#022C22",
        "green_hover": "#059669",
        "orange":      "#F59E0B",
        "orange_hover":"#D97706",
        "purple":      "#8B5CF6",
        "purple_dim":  "#2E1065",
        "purple_hover":"#7C3AED",
        "cyan":        "#06B6D4",
        "text":        "#F1F5F9",
        "text2":       "#CBD5E1",
        "muted":       "#64748B",
        "disabled":    "#334155",
        "focus":       "#00F0FF",
        "state_ok":      "#10B981",
        "state_warn":    "#F59E0B",
        "state_err":     "#FF0055",
        "state_neutral": "#64748B",
    },
    'nordic_slate': {
        "bg":          "#0F172A",
        "card":        "#1E293B",
        "card2":       "#334155",
        "card3":       "#475569",
        "card_border": "#475569",
        "sep":         "#334155",
        "pill_bg":     "#1E293B",
        "pill_btn":    "#334155",
        "pill_hover":  "#475569",
        "pill_active": "#38BDF8",
        "pill_text":   "#94A3B8",
        "pill_text_act":"#0F172A",
        "blue":        "#38BDF8",
        "blue_hover":  "#0EA5E9",
        "indigo":      "#6366F1",
        "indigo_hover":"#4F46E5",
        "red":         "#EF4444",
        "red_dim":     "#450A0A",
        "red_hover":   "#DC2626",
        "green":       "#34D399",
        "green_dim":   "#064E3B",
        "green_hover": "#10B981",
        "orange":      "#F97316",
        "orange_hover":"#EA580C",
        "purple":      "#A855F7",
        "purple_dim":  "#3B0764",
        "purple_hover":"#9333EA",
        "cyan":        "#22D3EE",
        "text":        "#F8FAFC",
        "text2":       "#E2E8F0",
        "muted":       "#94A3B8",
        "disabled":    "#475569",
        "focus":       "#38BDF8",
        "state_ok":      "#34D399",
        "state_warn":    "#FBBF24",
        "state_err":     "#EF4444",
        "state_neutral": "#94A3B8",
    }
}

def apply_theme(theme_name: str) -> None:
    if theme_name in THEMES:
        C.update(THEMES[theme_name])


_PLAT = sys.platform
if _PLAT == "darwin":
    FONT_FAMILY = "SF Pro Display"
elif _PLAT == "win32":
    FONT_FAMILY = "Segoe UI"
else:
    FONT_FAMILY = "Ubuntu"

FONT_UI    = (FONT_FAMILY, 10)
FONT_UI_B  = (FONT_FAMILY, 10, "bold")
FONT_SM    = (FONT_FAMILY, 9)
FONT_LG    = (FONT_FAMILY, 13, "bold")
FONT_XL    = (FONT_FAMILY, 16, "bold")
FONT_CARD  = (FONT_FAMILY, 12, "bold")

# Tokens de espaciado estandarizados
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 20
FONT_MONO  = ("JetBrains Mono", 9) if _PLAT != "win32" else ("Consolas", 9)

# ── Rutas ──────────────────────────────────────────────────────────────────
CONFIG_DIR  = os.path.expanduser("~/.config/masv")
APP_DIR     = CONFIG_DIR
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
LOG_FILE    = os.path.join(CONFIG_DIR, "masv.log")
os.makedirs(CONFIG_DIR, exist_ok=True)
if sys.platform != "win32":
    try: os.chmod(CONFIG_DIR, 0o700)
    except Exception: pass

DEFAULT_CONFIG = {
    "profiles": {
        "🎮 Juego Rápido": {
            "bitrate": "16M", "max_size": "1920", "max_fps": "60",
            "audio_source": "playback", "camera_id": "0", "video_codec": "h264",
            "turn_screen_off": True,  "force_screen_off_keyevent": False,
            "stay_awake": True, "extra_args": ""
        },
        "🎙️ Stream OBS (Huawei)": {
            "bitrate": "4M", "max_size": "1080", "max_fps": "30",
            "audio_source": "mic", "camera_id": "0", "video_codec": "h264",
            "turn_screen_off": True,  "force_screen_off_keyevent": True,
            "stay_awake": True, "extra_args": "--no-video"
        },
        "📷 Cámara HD": {
            "bitrate": "12M", "max_size": "1920", "max_fps": "30",
            "audio_source": "mic", "camera_id": "0", "video_codec": "h264",
            "turn_screen_off": False, "force_screen_off_keyevent": False,
            "stay_awake": True, "extra_args": "--video-source=camera"
        },
        "📷 Cámara Frontal": {
            "bitrate": "12M", "max_size": "1920", "max_fps": "30",
            "audio_source": "mic", "camera_id": None, "video_codec": "h264",
            "turn_screen_off": False, "force_screen_off_keyevent": False,
            "stay_awake": True, "extra_args": "--video-source=camera --camera-facing=front"
        },
    },
    "device_associations": {},
    "last_selected_profile": "🎮 Juego Rápido",
    "window_geometry": "880x680",
    "window_state": "normal",
    "onboarding_done": False,
    "language": "es",
    "theme": "warm_stone",
    "security": {
        "safe_mode_enabled": True,
        "auto_lockdown_on_exit": True,
        "trusted_devices": {},
        "blocked_ips": []
    }
}

def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG); return copy.deepcopy(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # La fusión con la plantilla **copia** lo que injerta (§3.11-bis): si el fichero
        # del usuario no trae una clave (p. ej. `security` en un config.json de una
        # versión anterior), `data[k] = v` dejaba al diccionario cargado compartiendo el
        # sub-diccionario global — y mutar lo cargado mutaba `DEFAULT_CONFIG`.
        for k, v in DEFAULT_CONFIG.items():
            if k not in data:
                data[k] = copy.deepcopy(v)
            elif isinstance(v, dict) and isinstance(data[k], dict):
                for sub_k, sub_v in v.items():
                    if sub_k not in data[k]:
                        data[k][sub_k] = copy.deepcopy(sub_v)
        return data
    except Exception as e:
        print(f"Error loading config: {e}")
        return copy.deepcopy(DEFAULT_CONFIG)

def save_config(cfg: dict) -> None:
    tmp_file = f"{CONFIG_FILE}.tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, CONFIG_FILE)
        if sys.platform != "win32":
            try: os.chmod(CONFIG_FILE, 0o600)
            except Exception: pass
    except Exception as e:
        print(f"Error saving config: {e}")
        if os.path.exists(tmp_file):
            try: os.remove(tmp_file)
            except Exception: pass

def find_portable_binaries() -> tuple[Optional[str], Optional[str]]:
    """Busca adb y scrcpy en la carpeta 'bin' relativa al ejecutable, en ~/.config/masv/bin, y en PATH.

    Devuelve `(adb, scrcpy)`; el que no aparezca llega como `None` (nunca se inventa
    una ruta): los llamadores deciden el respaldo — `managers.py` usa
    `/usr/local/bin/scrcpy` y `adb` se resuelve por separado.
    """
    search_paths = []

    if getattr(sys, 'frozen', False):
        # 1. Si está empaquetado, buscar en la carpeta donde está el binario ejecutable
        exe_dir = os.path.dirname(sys.executable)
        search_paths.append(os.path.join(exe_dir, "bin"))
        # 2. Buscar en la carpeta temporal de PyInstaller
        search_paths.append(os.path.join(sys._MEIPASS, "bin"))
    else:
        # Modo desarrollo
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        search_paths.append(os.path.join(base_path, "bin"))

    # 3. Buscar en la carpeta de configuración del usuario
    search_paths.append(os.path.join(CONFIG_DIR, "bin"))

    search_path_str = os.pathsep.join(search_paths)

    adb_path    = shutil.which("adb",    path=search_path_str) or shutil.which("adb")
    scrcpy_path = shutil.which("scrcpy", path=search_path_str) or shutil.which("scrcpy")
    return adb_path, scrcpy_path

import ipaddress

def parse_ip_port(raw: str) -> tuple[Optional[str], Optional[str]]:
    """Limpia y valida estrictamente la IP:PORT ingresada usando el módulo ipaddress.

    Contrato de fallo (⑪): entrada inválida → `(None, None)`, **nunca** `None` suelto
    y nunca una excepción, porque los llamadores desempaquetan la tupla directamente
    (`ip, port = parse_ip_port(...)`).

    ⚠️ Esa tupla de fallo es **verdadera**: `if not parsed` NO la detecta. Hay que
    mirar `parsed[0]` (ver `main.py::_connect_by_ip`). El otro parser de red del
    proyecto, `SecurityManager.parse_pair_ip_port_code`, usa la convención contraria
    (`None` suelto) porque su llamador comprueba `if not parsed:` — y una tupla de
    Nones también sería verdadera y pasaría la guarda.

    Sin puerto explícito se asume 5555; el puerto debe estar entre 1 y 65535.
    """
    clean = raw.strip()
    if not clean:
        return None, None
    
    port = "5555"
    ip_str = clean
    
    if ":" in clean:
        parts = clean.split(":", 1)
        ip_str = parts[0].strip()
        port_str = parts[1].strip()
        if port_str.isdigit() and 1 <= int(port_str) <= 65535:
            port = port_str
        else:
            return None, None

    try:
        ip_obj = ipaddress.ip_address(ip_str)
        return str(ip_obj), port
    except ValueError:
        return None, None

class SingleInstance:
    """Previene que la aplicación se abra múltiples veces (Singleton por puerto local).

    Es una comodidad para el usuario, no un candado de seguridad: si el socket falla
    por un motivo **distinto** de "puerto ocupado", la app arranca igual (con aviso)
    en lugar de mostrar el falso "ya está en ejecución" que dejaba sin poder abrirla.
    """

    def __init__(self, port: int = 47291):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._adquirido = False

    def acquire(self) -> bool:
        """True si esta instancia puede arrancar (es la única, o el socket no es fiable).

        Tres propiedades medidas (ver `INFORME_BUGS` §3.21 y ADR-045):

          · **exclusión** — la segunda instancia recibe `EADDRINUSE`;
          · **reentrada limpia** — tras `release()` el puerto queda libre al instante;
          · **reentrada con TIME_WAIT** — si el puerto quedó en TIME_WAIT (tras
            `_restart_app()` o un cierre abrupto con conexión), se puede volver a ligar.

        Las tres exigen `SO_REUSEADDR` **antes** del `bind` **y** `listen(1)`:
        `SO_REUSEADDR` solo (sin `listen`) permite el segundo bind y rompe la
        exclusión; y con el `bind` antes de la opción se pierde la reentrada con
        TIME_WAIT (probado: la variante sin `listen` falla con `EADDRINUSE`).
        """
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("127.0.0.1", self.port))
            self.sock.listen(1)
            self._adquirido = True
            return True
        except OSError as e:
            addr_in_use = (
                errno.EADDRINUSE,
                getattr(errno, "WSAEADDRINUSE", 10048),
                getattr(errno, "WSAEACCES", 10013),
            )
            if e.errno in addr_in_use or getattr(e, "winerror", None) in addr_in_use:
                return False          # ya hay otra instancia: es el caso legítimo
            log.warning(
                "instancia única: no se pudo reservar el puerto %s (%s); se arranca igual",
                self.port, e,
            )
            return True

    def release(self):
        try:
            self.sock.close()
        except Exception:
            pass
        self._adquirido = False

def _extract_serial(text: str) -> str:
    """Extrae el serial del formato 'Modelo (Serial)' o devuelve el texto limpio."""
    m = re.search(r"\(([^)]+)\)", text)
    if m:
        return m.group(1).strip()
    return text.strip()

def log_msg(level: str, msg: str) -> None:
    ts   = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}\n"
    print(line, end="")
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 5 * 1024 * 1024:
            old_file = f"{LOG_FILE}.1"
            if os.path.exists(old_file):
                try: os.remove(old_file)
                except Exception: pass
            try: os.rename(LOG_FILE, old_file)
            except Exception: pass
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
