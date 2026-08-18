import os, sys, re, time, socket, shutil, json

# ── Paleta Warm Cozy Dark — Sistema de Diseño Canónico Warm ─────────────────
# Diseño cálido personal (Warm Stone, Ámbar Dorado, Terracota y Marfil)
C = {
    # Fondos principales (Elevación por capas cálidas)
    "bg":          "#1C1917",   # Warm Stone 900 - Ventana principal
    "card":        "#262422",   # Warm Stone 850 - Tarjetas y contenedores
    "card2":       "#322E2B",   # Warm Stone 800 - Headers, toolbars, entradas
    "card3":       "#44403C",   # Warm Stone 700 - Hover sutil

    # Separadores y bordes
    "sep":         "#44403C",   # Borde de separación sutil cálido

    # Acciones primarias y acentos
    "blue":        "#D97706",   # Ámbar Cálido Primario
    "blue_hover":  "#B45309",
    "indigo":      "#F59E0B",   # Ámbar Dorado - Acento de marca
    "indigo_hover":"#D97706",

    # Peligro / Cancelar
    "red":         "#F43F5E",   # Rosa/Rojo cálido
    "red_dim":     "#4C0519",   # Fondo de alerta destructiva
    "red_hover":   "#E11D48",

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
    "disabled":    "#44403C",

    # Foco de accesibilidad (Tab)
    "focus":       "#F59E0B",

    # Badges de estado semánticos
    "state_ok":      "#10B981",
    "state_warn":    "#F59E0B",
    "state_err":     "#EF4444",
    "state_neutral": "#94A3B8",
}

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
    },
    "device_associations": {},
    "last_selected_profile": "🎮 Juego Rápido",
    "window_geometry": "880x680",
    "window_state": "normal",
    "onboarding_done": False,
    "language": "es",
}

def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG); return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            if k not in data:
                data[k] = v
        return data
    except Exception as e:
        print(f"Error loading config: {e}")
        return dict(DEFAULT_CONFIG)

def save_config(cfg: dict):
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

def find_portable_binaries():
    """Busca adb y scrcpy en la carpeta 'bin' relativa al ejecutable, en ~/.config/masv/bin, y en PATH."""
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

def parse_ip_port(raw: str):
    """Limpia y valida estrictamente la IP:PORT ingresada usando el módulo ipaddress."""
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
    """Previene que la aplicación se abra múltiples veces (Singleton por puerto local)."""
    def __init__(self, port: int = 47291):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    def acquire(self) -> bool:
        try:
            self.sock.bind(("127.0.0.1", self.port))
            return True
        except socket.error:
            return False
    def release(self):
        try: self.sock.close()
        except Exception: pass

def _extract_serial(text: str) -> str:
    """Extrae el serial del formato 'Modelo (Serial)' o devuelve el texto limpio."""
    m = re.search(r"\(([^)]+)\)$", text)
    if m:
        return m.group(1).strip()
    return text.strip()

def log_msg(level: str, msg: str):
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
