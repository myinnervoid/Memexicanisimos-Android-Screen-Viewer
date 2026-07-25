import os, sys, re, time, socket, shutil, json

# ── Paleta iOS DARK — Tokens de diseño canónicos ──────────────────────────
# TODOS los colores de la interfaz DEBEN referenciar estas claves.
# NO usar colores hexadecimales directos fuera de este diccionario.
C = {
    # Fondos
    "bg":          "#121212",   # Fondo principal de la aplicación
    "card":        "#1C1C1E",   # Tarjetas, secciones, headers
    "card2":       "#2C2C2E",   # Fondos secundarios, toolbars, console
    "card3":       "#383838",   # Hover sutil / separación terciaria

    # Separadores
    "sep":         "#3A3A3C",

    # Acciones primarias
    "blue":        "#0A84FF",
    "blue_hover":  "#0077ED",

    # Peligro / Cancelar
    "red":         "#FF453A",
    "red_hover":   "#D70015",

    # Éxito / Activo
    "green":       "#32D74B",
    "green_dim":   "#1C3A27",   # Fondo de toast success
    "green_hover": "#28B83E",

    # Advertencia
    "orange":      "#FF9F0A",
    "orange_hover":"#E08C00",

    # Acento / Perfiles
    "purple":      "#BF5AF2",
    "purple_dim":  "#3A0CA3",   # Fondo de tarjeta de perfil seleccionado
    "purple_hover":"#9b44d1",

    # Información / WiFi / Escaneando
    "cyan":        "#64D2FF",

    # Texto
    "text":        "#FFFFFF",
    "text2":       "#EBEBF5",   # Texto secundario sobre cards
    "muted":       "#8E8E93",   # Texto desactivado / labels de campo

    # Estados desactivados
    "disabled":    "#3A3A3C",

    # Foco (accesibilidad)
    "focus":       "#0A84FF",   # Borde de foco visible al navegar con Tab

    # Badges de estado semánticos (usados en notificaciones y status bar)
    "state_ok":      "#32D74B",
    "state_warn":    "#FF9F0A",
    "state_err":     "#FF453A",
    "state_neutral": "#8E8E93",
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
FONT_MONO  = ("Courier New", 9)

# ── Rutas ──────────────────────────────────────────────────────────────────
CONFIG_DIR  = os.path.expanduser("~/.config/masv")
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
    "window_geometry": "860x680",
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
    """Busca adb y scrcpy primero en la carpeta 'bin' relativa al ejecutable, luego en PATH."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    bin_path = os.path.join(base_path, "bin")
    adb_path    = shutil.which("adb",    path=bin_path) or shutil.which("adb")
    scrcpy_path = shutil.which("scrcpy", path=bin_path) or shutil.which("scrcpy")
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
