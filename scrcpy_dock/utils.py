import os, sys, re, time, socket, shutil, json

# ── Paleta Slate Dark — Sistema de Diseño Canónico ──────────────────────────
# Teoría de Color para Apps Profesionales (Vercel / Linear / Raycast style)
# Fondo Slate profundo, tarjetas con elevación por capas y contraste WCAG AAA.
C = {
    # Fondos principales (Elevación por capas)
    "bg":          "#0F172A",   # Slate 900 - Ventana principal
    "card":        "#1E293B",   # Slate 800 - Tarjetas y contenedores
    "card2":       "#334155",   # Slate 700 - Headers, toolbars, entradas
    "card3":       "#475569",   # Slate 600 - Hover sutil

    # Separadores y bordes
    "sep":         "#334155",   # Borde de separación sutil

    # Acciones primarias y acentos
    "blue":        "#0284C7",   # Sky 600
    "blue_hover":  "#0369A1",
    "indigo":      "#6366F1",   # Indigo 500 - Acento principal de marca
    "indigo_hover":"#4F46E5",

    # Peligro / Cancelar (Rojo elegante, no deslumbrante)
    "red":         "#EF4444",   # Red 500
    "red_dim":     "#451A1A",   # Fondo de alerta destructiva
    "red_hover":   "#DC2626",

    # Éxito / Estado Activo
    "green":       "#10B981",   # Emerald 500
    "green_dim":   "#064E3B",   # Fondo de estado OK
    "green_hover": "#059669",

    # Advertencia
    "orange":      "#F59E0B",   # Amber 500
    "orange_hover":"#D97706",

    # Acento / Perfiles
    "purple":      "#A855F7",   # Purple 500
    "purple_dim":  "#3B0764",
    "purple_hover":"#9333EA",

    # Información / WiFi
    "cyan":        "#38BDF8",   # Sky 400

    # Tipografía — Legibilidad comprobada (WCAG AAA)
    "text":        "#F8FAFC",   # Slate 50 - Texto primario
    "text2":       "#E2E8F0",   # Slate 200 - Texto secundario
    "muted":       "#94A3B8",   # Slate 400 - Etiquetas y pistas

    # Estados desactivados
    "disabled":    "#334155",

    # Foco de accesibilidad (Tab)
    "focus":       "#38BDF8",

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
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")

def find_portable_binaries():
    """Busca adb y scrcpy en la carpeta 'bin' relativa al ejecutable, en ~/.config/masv/bin, y en PATH."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    bin_path1 = os.path.join(base_path, "bin")
    bin_path2 = os.path.join(APP_DIR, "bin")
    search_path = f"{bin_path1}{os.pathsep}{bin_path2}"

    adb_path    = shutil.which("adb",    path=search_path) or shutil.which("adb")
    scrcpy_path = shutil.which("scrcpy", path=search_path) or shutil.which("scrcpy")
    return adb_path, scrcpy_path

def parse_ip_port(raw: str):
    """Limpia la IP:PORT ingresada, usa puerto 5555 por defecto."""
    clean = raw.strip()
    if not clean: return None, None
    if ":" in clean:
        parts = clean.split(":", 1)
        return parts[0].strip(), parts[1].strip()
    return clean, "5555"

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
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
