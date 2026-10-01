import tkinter as tk
from .i18n import _, set_language, get_language
from tkinter import ttk, messagebox, filedialog
import queue
import time
import sys
import os
import threading
import subprocess
try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    TRAY_AVAILABLE = True
except Exception:
    # No es sólo ImportError: sin display, `import pystray` levanta
    # `Xlib.error.DisplayNameError` (Python 3, Linux, CI headless). Si esto se
    # escapa, el módulo entero deja de importarse y ninguna prueba de UI puede
    # correr en un entorno sin pantalla. La bandeja es opcional: se desactiva.
    TRAY_AVAILABLE = False

import re
from typing import Optional, Any
from .utils import C, FONT_UI, FONT_UI_B, FONT_SM, FONT_FAMILY, SingleInstance, _extract_serial, parse_ip_port, log_msg, LOG_FILE, save_config, apply_theme
from .context import AppContext
from .ui_tabs import UIBuilder
from .ui_widgets import Toast, Tooltip, DeviceTrustModal, TrustVaultDialog, TrustPromptModal
from .security import SecurityManager
from .state import UIState
from .core.adb_engine import AdbEngine
from .errors import ErrorCode, get_error_detail

_PLAT = sys.platform
APP_NAME = "Memexicanisimos Android Screen Viewer"
APP_SHORT = "MASV"

# ── Modo Compacto vs Vista Completa (Ctrl+M) ─────────────────────────────────
# Antes vivían dentro de `_toggle_view`, mezclados con el flujo de control.
_GEOMETRIA_COMPACTA = "500x620"
_GEOMETRIA_COMPLETA = "880x680"
_MINIMO_COMPACTO = (460, 560)
_MINIMO_COMPLETO = (680, 520)
# Widgets que el Modo Compacto oculta (los que existan).
_OCULTOS_EN_COMPACTO = ("sidebar", "_sidebar_sep", "_brand_sub", "_btn_panic_lockdown")
# Cómo se vuelven a colocar: (atributo, kwargs de pack, atributo tras el cual colocarlo).
# Si el `before` no existe, el widget no se empaqueta (era el comportamiento original).
_WIDGETS_DEL_MODO_COMPLETO = (
    ("_brand_sub", {"side": "left", "pady": (2, 0)}, None),
    ("_btn_panic_lockdown", {"side": "right", "padx": (6, 0)}, "_btn_safe_mode"),
    ("sidebar", {"side": "left", "fill": "y"}, "main_content"),
    ("_sidebar_sep", {"side": "left", "fill": "y"}, "main_content"),
)
_TEXTO_ATAJOS_COMPACTO = "Ctrl+M Completo · Ctrl+I Iniciar"
_TEXTO_ATAJOS_COMPLETO = ("Ctrl+I Iniciar · Ctrl+R Refrescar · Ctrl+M Compacto · "
                          "Ctrl+B Menú · Ctrl+H Ayuda")

# ── Etiquetas de contexto que se refrescan al cambiar de pestaña ─────────────
# Ojo: los textos van dentro de `_("…")` en el punto de uso, no en una tabla.
# Metidos en una tabla, un escáner de literales los ve como claves muertas
# (la trampa de P3.33) y una poda posterior borraría traducciones vivas.
_REFS_DE_DISPOSITIVO = ("action_device_lbl", "ctrl_device_lbl")
_REFS_DE_CONFIANZA = ("action_trust_lbl", "ctrl_trust_lbl", "simple_trust_lbl")
_REFS_DE_PERFIL = ("action_profile_lbl", "ctrl_profile_lbl")

class ScrcpyDockApp:
    def __init__(self, root: tk.Tk, single_instance: Any = None):
        self.root = root
        self.single_instance = single_instance
        self.root.title(APP_NAME)
        self.root.minsize(880, 600)
        self.root.configure(bg=C["bg"])

        self.ctx = AppContext(root)

        # Load and apply language from config
        saved_lang = self.ctx.cfg.get("language", "es")
        set_language(saved_lang)

        # Load and apply theme from config
        saved_theme = self.ctx.cfg.get("theme", "warm_stone")
        apply_theme(saved_theme)
        self.root.configure(bg=C["bg"])

        self._setup_styles()
        self._build_menu_bar()

        # ── Restaurar geometría guardada ───────────────────────
        geo = self.ctx.cfg.get("window_geometry", "860x680")
        self.root.geometry(geo)
        if self.ctx.cfg.get("window_state") == "zoomed":
            try: self.root.state("zoomed")
            except Exception: pass

        self.root.protocol("WM_DELETE_WINDOW", self._on_app_close)

        # ── Icono de ventana ───────────────────────────────────
        try:
            _ico = _make_tray_icon(32)
            _ico_tk = ImageTk.PhotoImage(_ico, master=root)
            self.root.iconphoto(True, _ico_tk)
            self._icon_ref = _ico_tk  # evitar GC
        except Exception:
            pass

        self.cb = {
            'auto_install_deps':     self._auto_install_deps,
            'copy_install_cmd':      self._copy_install_cmd,
            'open_terminal_install': self._open_terminal_install,
            'refresh_devices':       self._refresh_devices,
            'on_dev_select':         self._on_dev_select,
            'connect_wifi':          self._connect_wifi,
            'enable_tcpip':          self._enable_tcpip,
            'get_device_ip':         self._get_device_ip,
            'setup_v4l2':            self._setup_v4l2,
            'route_cam':             self._route_cam,
            'v4l2_help':             self._v4l2_help,
            'go_to_help_usb':        self._go_to_help_usb,
            'go_to_help_v4l2':       self._go_to_help_v4l2,

            'on_profile_listbox_sel':  self._on_profile_listbox_sel,
            'open_wizard':             self._open_wizard,
            'delete_profile':          self._delete_profile,
            'on_active_profile_change':self._on_active_profile_change,
            'start_profile':           self._start_profile,

            'toggle_scene':     self._toggle_scene,
            'stop_current':     self._stop_current,
            'panic_kill':       self._panic_kill,
            'restart_adb':      self._restart_adb,
            'go_to_wifi':       lambda: self._nb.select(2),
            'stop_selected':    self._stop_selected,
            'sess_context_menu':self._sess_context_menu,
            'send_keyevent':    self._send_keyevent,
            'install_apk':       self._install_apk,
            'toggle_tethering':  self._toggle_tethering,
            'start_otg_mode':    self._start_otg_mode,

            # Callbacks de Seguridad & Bóveda de Confianza
            'open_trust_vault':        self._open_trust_vault,
            'open_device_trust_modal': self._open_device_trust_modal,
            'pair_wifi':               self._pair_wifi,
            'lockdown_tcpip':          self._lockdown_tcpip,
            'panic_lockdown':          self._panic_lockdown,

            'clear_log':  self._clear_log,
            'open_log':   self._open_log,
            'filter_log': self._filter_log,
            'copy_log':   self._copy_log,
        }

        self.ui = UIBuilder(self.ctx, self.cb)
        self._build_ui()

        # Suscribir a cambios del autómata de estados
        self.ctx.state_machine.subscribe(self._on_ui_state_change)

        self._check_deps()
        self._refresh_devices()
        self._pump_logs()
        self._monitor_sessions()
        self._bind_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Onboarding primera vez
        if not self.ctx.cfg.get("onboarding_done"):
            self.root.after(800, self._show_onboarding)

    def _build_menu_bar(self):
        menubar = tk.Menu(self.root, bg=C["card"], fg=C["text"], activebackground=C["blue"], activeforeground="#FFF")

        file_menu = tk.Menu(menubar, tearoff=0, bg=C["card"], fg=C["text"], activebackground=C["blue"], activeforeground="#FFF")
        file_menu.add_command(label=_("🚀 Nueva Transmisión"), command=self._toggle_scene, accelerator="Ctrl+I")
        file_menu.add_command(label=_("🔄 Refrescar Dispositivos"), command=self._refresh_devices, accelerator="Ctrl+R")
        file_menu.add_command(label=_("⏹ Detener Todas las Sesiones"), command=self._stop_current)
        file_menu.add_separator()
        file_menu.add_command(label=_("📥 Instalar en Sistema (Menú y Terminal)"), command=self._install_to_system)
        file_menu.add_command(label=_("🗑️ Desinstalar del Sistema"), command=self._uninstall_from_system)
        file_menu.add_separator()
        file_menu.add_command(label=_("🚪 Salir"), command=self._on_app_close, accelerator="Ctrl+Q")
        menubar.add_cascade(label=_("Archivo"), menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0, bg=C["card"], fg=C["text"], activebackground=C["blue"], activeforeground="#FFF")
        edit_menu.add_command(label=_("✨ Crear Nuevo Perfil..."), command=self._open_wizard)
        edit_menu.add_command(label=_("📋 Copiar Registro de Consola"), command=self._copy_log)
        edit_menu.add_command(label=_("🧹 Limpiar Consola"), command=self._clear_log)
        menubar.add_cascade(label=_("Editar"), menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0, bg=C["card"], fg=C["text"], activebackground=C["blue"], activeforeground="#FFF")
        view_menu.add_command(label=_("🔀 Alternar Vista (Simple / Avanzada)"), command=self._toggle_view)
        view_menu.add_command(label=_("🖥 Ir a Consola de Registros"), command=lambda: self._nb.select(4))

        theme_menu = tk.Menu(view_menu, tearoff=0, bg=C["card"], fg=C["text"], activebackground=C["blue"], activeforeground="#FFF")
        theme_menu.add_command(label="Warm Stone (Default)", command=lambda: self._change_theme("warm_stone"))
        theme_menu.add_command(label="Cyber Obsidian (Dark)", command=lambda: self._change_theme("cyber_obsidian"))
        theme_menu.add_command(label="Nordic Slate (Minimal)", command=lambda: self._change_theme("nordic_slate"))
        view_menu.add_cascade(label=_("Tema Visual"), menu=theme_menu)

        lang_menu = tk.Menu(view_menu, tearoff=0, bg=C["card"], fg=C["text"], activebackground=C["blue"], activeforeground="#FFF")
        lang_menu.add_command(label="Español (🇲🇽)", command=lambda: self._select_language("es"))
        lang_menu.add_command(label="English (🇺🇸)", command=lambda: self._select_language("en"))
        view_menu.add_cascade(label=_("Idioma / Language"), menu=lang_menu)

        menubar.add_cascade(label=_("Ver"), menu=view_menu)

        dev_menu = tk.Menu(menubar, tearoff=0, bg=C["card"], fg=C["text"], activebackground=C["blue"], activeforeground="#FFF")
        dev_menu.add_command(label=_("⚡ Reiniciar Servidor ADB"), command=self._restart_adb)
        dev_menu.add_command(label=_("📶 Conectar por Wi-Fi"), command=lambda: self._nb.select(2))
        dev_menu.add_command(label=_("🛡️ Bóveda de Dispositivos Confiables"), command=self._open_trust_vault)
        dev_menu.add_command(label=_("🛡️ Blindar TCP/IP (Cerrar puerto 5555)"), command=self._lockdown_tcpip)
        dev_menu.add_command(label=_("📦 Instalar APK en Teléfono"), command=self._install_apk)
        dev_menu.add_command(label=_("📷 Configurar Webcam Virtual (v4l2)"), command=self._setup_v4l2)
        dev_menu.add_separator()
        dev_menu.add_command(label=_("⌨️ Modo OTG (Control por Teclado/Ratón USB)"), command=self._start_otg_mode)
        dev_menu.add_command(label=_("🌐 Compartir Internet (Reverse Tethering)"), command=self._toggle_tethering)
        menubar.add_cascade(label=_("Dispositivo"), menu=dev_menu)

        help_menu = tk.Menu(menubar, tearoff=0, bg=C["card"], fg=C["text"], activebackground=C["blue"], activeforeground="#FFF")
        help_menu.add_command(label=_("📖 Guía de Depuración USB"), command=self._go_to_help_usb, accelerator="Ctrl+H")
        help_menu.add_command(label=_("💡 Ver Asistente de Inicio (Onboarding)"), command=self._show_onboarding)
        help_menu.add_command(label=_("ℹ️ Acerca de MASV v1.4"), command=lambda: messagebox.showinfo(APP_NAME, "MASV v1.4 — Memexicanisimos Android Screen Viewer\n\nHerramienta nativa de transmisión y control de pantalla para Android.\nDesarrollada con Python, Tkinter y el núcleo de scrcpy."))
        menubar.add_cascade(label=_("Ayuda"), menu=help_menu)

        self.root.config(menu=menubar)

    def _select_language(self, lang_code: str):
        """Cambia el idioma de la aplicación y ofrece reinicio inmediato."""
        if get_language() == lang_code:
            return
        set_language(lang_code)
        self.ctx.cfg["language"] = lang_code
        save_config(self.ctx.cfg)
        if messagebox.askyesno(
            _("Cambiar Idioma"),
            _("El idioma se ha guardado exitosamente.\n\n¿Deseas reiniciar MASV ahora para aplicar los cambios?")
        ):
            self._restart_app()
        else:
            Toast(self.root, _("El nuevo idioma se aplicará la próxima vez que inicies MASV."), "info")

    def _restart_app(self):
        """Reinicia limpiamente el proceso de MASV liberando instancias y sesiones previas."""
        try:
            self.ctx.session_mgr.stop_all()
        except Exception:
            pass
        if self.single_instance:
            try:
                self.single_instance.release()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass
        is_frozen = getattr(sys, 'frozen', False)
        exe = sys.executable
        if is_frozen:
            os.execl(exe, exe, *sys.argv[1:])
        else:
            os.execl(exe, exe, *sys.argv)

    _TAB_BUILDER_METHODS = {
        "quickcast": "build_simple_view",
        "actions": "build_tab_actions",
        "device": "build_tab_device",
        "controls": "build_tab_controls",
        "profiles": "build_tab_profile",
        "console": "build_tab_console",
        "help": "build_tab_help",
    }

    def _reconstruir_pestanas_en_caliente(self):
        """Reconstruye los frames de pestañas con la nueva paleta de colores."""
        self._setup_styles()
        self.root.config(bg=C["bg"])
        tab_frames = getattr(self, '_tab_frames', {})
        for tid, frame in tab_frames.items():
            builder_name = self._TAB_BUILDER_METHODS.get(tid)
            if builder_name and hasattr(self.ui, builder_name):
                getattr(self.ui, builder_name)(frame)
        active_tid = getattr(self, 'active_tab_id', 'quickcast') or "quickcast"
        self._select_tab(active_tid)

    def _change_theme(self, theme_name: str):
        self.ctx.cfg["theme"] = theme_name
        save_config(self.ctx.cfg)
        apply_theme(theme_name)
        if messagebox.askyesno(
            _("Cambiar Tema"),
            _("Tema guardado exitosamente.\n\n¿Deseas reiniciar MASV ahora para aplicar todos los contrastes a la perfección?")
        ):
            self._restart_app()
            return
        self._reconstruir_pestanas_en_caliente()
        Toast(self.root, f"Tema aplicado: {theme_name}", "success")

    def _install_to_system(self):
        from .services.installer_service import InstallerService
        from pathlib import Path
        import shutil
        svc = InstallerService()
        svc.ensure_layout()
        is_frozen = getattr(sys, 'frozen', False)
        exe_src = Path(sys.executable if is_frozen else os.path.abspath(sys.argv[0])).resolve()
        target_exe = svc.bin_dir / "MASV"

        if is_frozen and exe_src != target_exe.resolve():
            try:
                shutil.copy2(exe_src, target_exe)
                target_exe.chmod(0o755)
                exe_to_reg = target_exe
            except Exception:
                exe_to_reg = exe_src
        else:
            exe_to_reg = exe_src

        icon_path = Path(__file__).parent.parent / "assets" / "logo.png"
        if is_frozen and hasattr(sys, '_MEIPASS'):
            icon_path = Path(sys._MEIPASS) / "assets" / "logo.png"
        target_icon = svc.assets_dir / "logo.png"

        if icon_path.exists():
            try:
                shutil.copy2(icon_path, target_icon)
                res = svc.write_desktop_entry(exe_to_reg, target_icon)
            except Exception:
                res = svc.write_desktop_entry(exe_to_reg, icon_path)
        else:
            res = svc.write_desktop_entry(exe_to_reg, exe_to_reg)

        if res.success:
            messagebox.showinfo(_("Instalación exitosa"), _("MASV se ha instalado en tu sistema con éxito.\n\n• Acceso creado en el Menú de Aplicaciones.\n• Comando 'MASV' listo en Terminal.\n• Ya puedes mover o borrar la carpeta descargada."))
        else:
            messagebox.showerror(_("Error"), f"No se pudo completar la instalación: {res.message}")

    def _uninstall_from_system(self):
        if messagebox.askyesno(_("Confirmar desinstalación"), _("¿Deseas desinstalar MASV y eliminar los accesos directos del sistema?")):
            from .services.installer_service import InstallerService
            svc = InstallerService()
            res = svc.uninstall(purge=False)
            if res.success:
                messagebox.showinfo(_("Desinstalado"), _("MASV ha sido retirado del menú y terminal."))
            else:
                messagebox.showerror(_("Error"), f"Error en desinstalación: {res.message}")

    def _bind_shortcuts(self):
        self.root.bind("<Control-q>", lambda _: self._on_close())
        self.root.bind("<Control-r>", lambda _: self._refresh_devices())
        self.root.bind("<Control-i>", lambda _: self._toggle_scene())
        self.root.bind("<Control-m>", lambda _: self._toggle_view())
        self.root.bind("<Control-M>", lambda _: self._toggle_view())
        self.root.bind("<F10>", lambda _: self._toggle_view())
        self.root.bind("<Control-h>", lambda _: self._select_tab("help"))
        self.root.bind("<Control-b>", lambda _: self.sidebar.toggle_collapse())

        for i in range(7):
            self.root.bind(f"<Alt-Key-{i+1}>", lambda _, idx=i: self._select_tab(idx))

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=C["bg"], foreground=C["text"],
                    fieldbackground=C["card"], font=FONT_UI)
        s.configure("TFrame",      background=C["bg"])
        s.configure("TLabel",      background=C["bg"], foreground=C["text"])
        s.configure("TCombobox", fieldbackground=C["card2"], foreground=C["text"],
                    background=C["card2"], arrowcolor=C["blue"], padding=4)
        s.map("TCombobox",
              fieldbackground=[("readonly", C["card2"]), ("focus", C["card2"])],
              foreground=[("readonly", C["text"])],
              highlightcolor=[("focus", C["focus"])])
        s.configure("TEntry", fieldbackground=C["card2"], foreground=C["text"],
                    insertcolor=C["text"], padding=4)
        s.map("TEntry", highlightcolor=[("focus", C["focus"])])
        s.configure("TCheckbutton", background=C["card"], foreground=C["text2"])
        s.map("TCheckbutton", background=[("active", C["card"])])
        s.configure("Treeview", background=C["card2"], foreground=C["text"],
                    fieldbackground=C["card2"], rowheight=28, borderwidth=0)
        s.configure("Treeview.Heading", background=C["card3"],
                    foreground=C["text2"], font=FONT_UI_B, relief="flat")
        s.map("Treeview",
              background=[("selected", C["blue"])],
              foreground=[("selected", "#FFFFFF")])
        s.configure("TScrollbar", background=C["card3"], troughcolor=C["card"],
                    arrowcolor=C["muted"], borderwidth=0)

        def _btn(name, bg, fg, hover, dis_bg=C["disabled"], dis_fg=C["muted"]):
            s.configure(name, background=bg, foreground=fg, borderwidth=0,
                        focusthickness=1, focuscolor=C["focus"],
                        padding=(10, 5), font=FONT_UI_B, relief="flat")
            s.map(name,
                  background=[("active", hover), ("disabled", dis_bg),
                               ("focus", bg)],
                  foreground=[("disabled", dis_fg)],
                  relief=[("focus", "solid")])

        _btn("Primary.TButton",   C["indigo"], "#FFF", C["indigo_hover"])
        _btn("Danger.TButton",    C["red"],    "#FFF", C["red_hover"])
        _btn("Secondary.TButton", C["card2"],  C["text2"], C["card3"])
        _btn("Green.TButton",     C["green"],  "#FFF", C["green_hover"])
        _btn("Warn.TButton",      C["orange"], "#FFF", C["orange_hover"])
        _btn("Ghost.TButton",     C["card"],   C["cyan"], C["card2"])
        _btn("Purple.TButton",    C["purple"], "#FFF", C["purple_hover"])

    def _build_ui(self):
        # ── Header Superior ──────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=C["card"], height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Marca & Título
        brand = tk.Frame(hdr, bg=C["card"])
        brand.pack(side="left", padx=(14, 10), pady=6)
        tk.Label(brand, text=_("MASV"), bg=C["card"], fg=C["indigo"],
                 font=(FONT_FAMILY, 16, "bold")).pack(side="left")
        self._brand_sub = tk.Label(brand, text=_("  Memexicanisimos Android Screen Viewer"),
                                   bg=C["card"], fg=C["muted"], font=FONT_SM)
        self._brand_sub.pack(side="left", pady=(2, 0))

        # Lado derecho del Header
        right_hdr = tk.Frame(hdr, bg=C["card"])
        right_hdr.pack(side="right", padx=12)

        # Botón de Blindaje Rápido
        self._btn_panic_lockdown = tk.Button(right_hdr, text="🔒 " + _("Blindar Red"),
                                             bg=C["red_dim"], fg=C["red"], font=FONT_SM,
                                             relief="flat", bd=0, padx=10, pady=4,
                                             cursor="hand2", command=self._panic_lockdown)
        self._btn_panic_lockdown.pack(side="right", padx=(6, 0))
        Tooltip(self._btn_panic_lockdown, "Cierra inmediatamente todas las sesiones y revoca el puerto 5555 en los teléfonos.")

        # Switch de Modo Seguro
        is_safe = self.ctx.security_mgr.is_safe_mode_enabled
        safe_txt = "🛡️ " + (_("Modo Seguro: ON") if is_safe else _("Modo Seguro: OFF"))
        safe_fg = C["green"] if is_safe else C["orange"]
        self._btn_safe_mode = tk.Button(right_hdr, text=safe_txt, bg=C["card2"], fg=safe_fg,
                                        font=FONT_SM, relief="flat", bd=0, padx=10, pady=4,
                                        cursor="hand2", command=self._toggle_safe_mode)
        self._btn_safe_mode.pack(side="right", padx=(6, 0))
        Tooltip(self._btn_safe_mode, "Bloquea conexiones a IPs públicas y previene intromisiones en equipos no verificados.")

        # Switch Modo Compacto (Mini-Dock) / Vista Completa
        self._btn_mode_toggle = tk.Button(right_hdr, text="🔲 " + _("Modo Compacto"),
                                          bg=C["card2"], fg=C["text2"], font=FONT_SM,
                                          relief="flat", bd=0, padx=8, pady=4,
                                          cursor="hand2", command=self._toggle_view)
        self._btn_mode_toggle.pack(side="right", padx=(6, 0))
        Tooltip(self._btn_mode_toggle, _("Alternar entre Modo Compacto (Mini-Dock) y Modo Avanzado completo (Ctrl+M)"))

        self._sess_count_lbl = tk.Label(right_hdr, text="", bg=C["card"], fg=C["green"], font=FONT_SM)
        self._sess_count_lbl.pack(side="right", padx=(6, 0))
        self._dep_lbl = tk.Label(right_hdr, text="", bg=C["card"], fg=C["muted"], font=FONT_SM)
        self._dep_lbl.pack(side="right")

        tk.Frame(self.root, bg=C["sep"], height=1).pack(fill="x")

        # ── Cuerpo Principal: Barra Lateral + Área de Contenido ──────
        body = tk.Frame(self.root, bg=C["bg"])
        body.pack(fill="both", expand=True)

        from .ui_widgets import DashboardSidebar
        nav_items = [
            ("quickcast", "🚀", _("Quick Cast"),     "Alt+1"),
            ("actions",   "⚡", _("Transmisión"),    "Alt+2"),
            ("device",    "📱", _("Dispositivos"),   "Alt+3"),
            ("controls",  "🎮", _("Mando Remoto"),   "Alt+4"),
            ("profiles",  "⚙️", _("Perfiles"),       "Alt+5"),
            ("console",   "🖥", _("Consola"),        "Alt+6"),
            ("help",      "❓", _("Ayuda / FAQ"),    "Alt+7"),
        ]

        self.sidebar = DashboardSidebar(body, nav_items, lambda tid, idx: self._select_tab(tid))
        self.sidebar.pack(side="left", fill="y")

        self._sidebar_sep = tk.Frame(body, bg=C["card_border"], width=1)
        self._sidebar_sep.pack(side="left", fill="y")

        # Área de Contenido Principal
        self.main_content = tk.Frame(body, bg=C["bg"])
        self.main_content.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        self._tab_frames = {
            "quickcast": tk.Frame(self.main_content, bg=C["bg"]),
            "actions":   tk.Frame(self.main_content, bg=C["bg"]),
            "device":    tk.Frame(self.main_content, bg=C["bg"]),
            "controls":  tk.Frame(self.main_content, bg=C["bg"]),
            "profiles":  tk.Frame(self.main_content, bg=C["bg"]),
            "console":   tk.Frame(self.main_content, bg=C["bg"]),
            "help":      tk.Frame(self.main_content, bg=C["bg"]),
        }

        self.ui.build_simple_view(self._tab_frames["quickcast"])
        self.ui.build_tab_actions(self._tab_frames["actions"])
        self.ui.build_tab_device(self._tab_frames["device"])
        self.ui.build_tab_controls(self._tab_frames["controls"])
        self.ui.build_tab_profile(self._tab_frames["profiles"])
        self.ui.build_tab_console(self._tab_frames["console"])
        self.ui.build_tab_help(self._tab_frames["help"])

        # Adaptador para compatibilidad de callbacks anteriores
        class NotebookAdapter:
            def __init__(self, select_fn):
                self._select_fn = select_fn
            def select(self, target):
                self._select_fn(target)

        self._nb = NotebookAdapter(self._select_tab)

        # Iniciar en Quick Cast Dashboard por defecto
        self.is_advanced_view = True
        self._select_tab("quickcast")

        # ── Barra de Estado Inferior (Footer) ────────────────────────
        bar = tk.Frame(self.root, bg=C["card2"], height=30)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self._status_lbl = tk.Label(bar, text="Listo", bg=C["card2"],
                                    fg=C["muted"], font=FONT_SM, anchor="w")
        self._status_lbl.pack(side="left", padx=12, fill="x", expand=True)

        self._footer_shortcuts_lbl = tk.Label(bar, text="Ctrl+I Iniciar · Ctrl+R Refrescar · Ctrl+M Compacto · Ctrl+B Menú · Ctrl+H Ayuda",
                                              bg=C["card2"], fg=C["muted"], font=FONT_SM)
        self._footer_shortcuts_lbl.pack(side="left", padx=6)

        # Language switcher
        lang_btn = tk.Button(bar, text="🇺🇸" if get_language() == "es" else "🇲🇽",
                             bg=C["card2"], fg=C["text"], bd=0, relief="flat", cursor="hand2", font=FONT_SM)
        lang_btn.pack(side="right", padx=(4, 12))
        Tooltip(lang_btn, _("Cambiar idioma (Español / English)"))

        def _toggle_language():
            new_lang = "en" if get_language() == "es" else "es"
            self._select_language(new_lang)

        lang_btn.config(command=_toggle_language)

        tk.Label(bar, text="v1.4", bg=C["card2"], fg=C["muted"], font=FONT_SM).pack(side="right", padx=4)

        if 'profile_listbox' in self.ui.refs:
            self.ui.refs['profile_listbox'].bind("<<ListboxSelect>>", self._on_profile_listbox_sel)
            self._refresh_profile_listbox()

    _TAB_KEYS = ("quickcast", "actions", "device", "controls", "profiles", "console", "help")

    def _resolver_tab_id(self, tab_id_or_idx: Any) -> Optional[str]:
        """Resuelve un índice entero o alias a un tab_id canónico."""
        if isinstance(tab_id_or_idx, int):
            if 0 <= tab_id_or_idx < len(self._TAB_KEYS):
                return self._TAB_KEYS[tab_id_or_idx]
            return None
        tid = str(tab_id_or_idx)
        return "quickcast" if tid == "simple" else tid

    def _mostrar_frame_de_tab(self, tab_id: str) -> None:
        """Oculta los demás frames y empaqueta el frame de la pestaña activa."""
        tab_frames = getattr(self, '_tab_frames', {})
        for f in tab_frames.values():
            f.pack_forget()
        if tab_id in tab_frames:
            tab_frames[tab_id].pack(fill="both", expand=True)

    def _select_tab(self, tab_id_or_idx):
        tab_id = self._resolver_tab_id(tab_id_or_idx)
        if not tab_id:
            return

        self._mostrar_frame_de_tab(tab_id)

        if hasattr(self, 'sidebar') and self.sidebar.active_id != tab_id:
            self.sidebar.select(tab_id)

        if tab_id == "profiles":
            self._sync_profile_selection()

        self._on_tab_changed()

    def _toggle_view(self):
        """Alterna entre Vista Completa (sidebar, 880x680) y Modo Compacto (mini-dock 500x620)."""
        if self.is_advanced_view:
            self._pasar_a_modo_compacto()
        else:
            self._pasar_a_vista_completa()

    def _pasar_a_modo_compacto(self):
        """Mini-dock: oculta barra lateral y cabecera, y encoge la ventana."""
        self.is_advanced_view = False
        self._saved_geometry = self.root.geometry()

        for nombre in _OCULTOS_EN_COMPACTO:
            widget = getattr(self, nombre, None)
            if widget is not None:
                widget.pack_forget()
        self._texto_de_atajos(_TEXTO_ATAJOS_COMPACTO)

        self._select_tab("quickcast")
        self.root.minsize(*_MINIMO_COMPACTO)
        self.root.geometry(_GEOMETRIA_COMPACTA)
        self._texto_del_boton_de_modo("🗖 " + _("Vista Completa"), C["blue"])
        self._hint(_("Modo Compacto activo (Ctrl+M para expandir)"), C["cyan"])

    def _pasar_a_vista_completa(self):
        """Restaura barra lateral, cabecera y la geometría previa."""
        self.is_advanced_view = True

        self._restaurar_widgets_del_modo_completo()
        self._texto_de_atajos(_TEXTO_ATAJOS_COMPLETO)
        self.root.minsize(*_MINIMO_COMPLETO)
        self.root.geometry(getattr(self, "_saved_geometry", _GEOMETRIA_COMPLETA))
        self._texto_del_boton_de_modo("🔲 " + _("Modo Compacto"), C["text2"])
        self._hint(_("Vista Completa activa"), C["muted"])

    def _restaurar_widgets_del_modo_completo(self):
        """Reempaqueta los widgets del modo completo en su orden original.

        Si el widget de referencia (`before`) no existe, el widget no se empaqueta:
        era el comportamiento anterior y evita reordenar lo que no se puede ordenar.
        """
        for nombre, kwargs, antes in _WIDGETS_DEL_MODO_COMPLETO:
            widget = getattr(self, nombre, None)
            if widget is None:
                continue
            argumentos = dict(kwargs)
            if antes:
                referencia = getattr(self, antes, None)
                if referencia is None:
                    continue
                argumentos["before"] = referencia
            widget.pack(**argumentos)

    def _texto_de_atajos(self, texto: str):
        """Actualiza el pie con los atajos, si el widget existe."""
        pie = getattr(self, "_footer_shortcuts_lbl", None)
        if pie is not None:
            pie.config(text=texto)

    def _texto_del_boton_de_modo(self, texto: str, color: str):
        """Actualiza el botón conmutador de modo, si el widget existe."""
        boton = getattr(self, "_btn_mode_toggle", None)
        if boton is not None:
            boton.config(text=texto, fg=color)

    def _on_app_close(self):
        """Detiene sesiones, desactiva servicios y cierra la aplicación de forma limpia y completa."""
        self._exit()

    def _set_status(self, msg: str, color: str = None):
        """Renderizador único de la barra de estado.

        Es el ÚNICO punto que pinta texto en la barra: lo invoca
        `_on_ui_state_change` (FSM) o `_hint` (mensajes informativos).
        """
        self._status_lbl.config(text=msg, fg=color or C["muted"])

    def _hint(self, msg: str, color: str = None):
        """Mensaje informativo transitorio que NO representa un estado operativo.

        Canal alternativo a la FSM, reservado a textos descriptivos (modo de
        vista, selección de dispositivo, perfil activo) que no encajan en los
        cinco estados canónicos. Todo mensaje de estado real debe pasar por
        `self.ctx.state_machine`.
        """
        self._set_status(msg, color)

    def _adb(self) -> AdbEngine:
        """Motor ADB único de la aplicación (socket aislado, ADR-006).

        Es el único camino permitido para hablar con `adb`: la UI ya no invoca
        el binario directamente, así no se tumba el daemon compartido del
        usuario ni se pierde el socket aislado. Todos los llamadores verifican
        `self.ctx.adb` antes, y `AppContext` construye el motor junto con el
        binario, por lo que aquí siempre existe.
        """
        eng = self.ctx.adb_engine
        if eng is None:  # pragma: no cover - invariante de AppContext
            raise RuntimeError("Motor ADB no disponible: instala adb primero")
        return eng

    def _on_ui_state_change(self, state: UIState, message: str, error_code: Optional[ErrorCode] = None):
        """Receptor canónico del Autómata Finito de Interfaz."""
        state_colors = {
            UIState.IDLE: C["muted"],
            UIState.PENDING: C["cyan"],
            UIState.SUCCESS: C["green"],
            UIState.EMPTY: C["orange"],
            UIState.FAULT: C["red"],
        }
        color = state_colors.get(state, C["muted"])
        if message:
            self._set_status(message, color)
        if state == UIState.FAULT and error_code is not None:
            self._log_error_remediation(error_code)

    def _log_error_remediation(self, error_code: ErrorCode):
        """Traduce un ErrorCode a título + acción de recuperación en la consola.

        Cablea `errors.get_error_detail()` (antes importado y nunca usado) al
        flujo de fallos de la FSM: el usuario recibe la remediación, no solo el
        texto crudo del subproceso.
        """
        detail = get_error_detail(error_code)
        spanish = get_language() == "es"
        title = detail.title_es if spanish else detail.title_en
        remediation = detail.remediation_es if spanish else detail.remediation_en
        try:
            self.ctx.log("ERROR", f"[{error_code.value}] {title}")
            if remediation:
                self.ctx.log("INFO", f"→ {remediation}")
        except Exception:
            pass

    # ── Utils & Dependencies ──────────────────────────────────────────
    def _start_daemon_async(self):
        """Arranca el daemon ADB por el motor (socket aislado, no el compartido)."""
        def task():
            eng = getattr(self.ctx, "adb_engine", None)
            if eng is None:
                return
            res = eng.start_daemon()
            self.ctx.log("INFO" if res.success else "ERROR", f"ADB daemon: {res.message}")
        threading.Thread(target=task, daemon=True).start()

    def _check_deps(self):
        missing = []
        if not self.ctx.adb:
            missing.append("adb")
        else:
            self.ctx.log("INFO", f"ADB   : {self.ctx.adb}")
            self._start_daemon_async()
        if not self.ctx.scrcpy:
            missing.append("scrcpy")
        else:
            self.ctx.log("INFO", f"scrcpy: {self.ctx.scrcpy}")

        if missing:
            self._dep_lbl.config(text=f"⚠  Falta: {', '.join(missing)}", fg=C["red"])
            err_code = ErrorCode.ADB_NOT_FOUND if "adb" in missing else ErrorCode.SCRCPY_NOT_FOUND
            self.ctx.state_machine.set_fault(f"⚠  Instala las dependencias: {', '.join(missing)}", err_code)
            self.ui.refs['dep_frame'].pack_forget()
            self.ui.refs['install_frame'].pack(fill="both", expand=True, padx=20, pady=20)
        else:
            self._dep_lbl.config(text=_("✔  ADB + scrcpy OK"), fg=C["green"])
            self.ctx.state_machine.set_idle(_("✔  Dependencias OK. Conecta un dispositivo."))
            self.ui.refs['install_frame'].pack_forget()
            self.ui.refs['dep_frame'].pack(fill="both", expand=True)
            self.root.after(700, self._check_v4l2)

    def _auto_install_deps(self):
        """Instala automáticamente scrcpy y adb sin requerir comandos manuales en la terminal."""
        import urllib.request, zipfile, shutil
        from .utils import CONFIG_DIR, find_portable_binaries
        target_bin_dir = os.path.join(CONFIG_DIR, "bin")
        os.makedirs(target_bin_dir, exist_ok=True)

        Toast(self.root, _("Iniciando descarga e instalación automática de scrcpy..."), "info", duration=5000)

        def task():
            try:
                if _PLAT == "win32":
                    r = subprocess.run(["winget", "install", "Genymobile.scrcpy", "--silent", "--accept-source-agreements", "--accept-package-agreements"], capture_output=True, text=True)
                    if r.returncode != 0:
                        url = "https://github.com/Genymobile/scrcpy/releases/download/v2.4/scrcpy-win64-v2.4.zip"
                        zip_path = os.path.join(CONFIG_DIR, "scrcpy_temp.zip")
                        urllib.request.urlretrieve(url, zip_path)
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            for member in zip_ref.namelist():
                                filename = os.path.basename(member)
                                if not filename: continue
                                source = zip_ref.open(member)
                                target = open(os.path.join(target_bin_dir, filename), "wb")
                                with source, target:
                                    shutil.copyfileobj(source, target)
                        if os.path.exists(zip_path):
                            os.remove(zip_path)
                else:
                    subprocess.run(["pkexec", "apt-get", "install", "-y", "adb", "scrcpy"])

                adb_path, scrcpy_path = find_portable_binaries()
                if adb_path and scrcpy_path:
                    self.ctx.set_adb_binary(adb_path)
                    self.ctx.scrcpy = scrcpy_path
                    self.root.after(0, self._on_deps_installed_success)
                else:
                    self.root.after(0, lambda: Toast(self.root, _("No se pudo completar la instalación automática."), "error"))
            except Exception as exc:
                # `as exc` se borra al salir del except: hay que materializarlo
                # en una variable estable antes de diferirlo con root.after().
                err_msg = f"Error en instalación: {exc}"
                self.root.after(0, lambda msg=err_msg: Toast(self.root, msg, "error"))

        threading.Thread(target=task, daemon=True).start()

    def _on_deps_installed_success(self):
        if 'install_frame' in self.ui.refs:
            self.ui.refs['install_frame'].pack_forget()
        if 'dep_frame' in self.ui.refs:
            self.ui.refs['dep_frame'].pack(fill="both", expand=True)
        self._dep_lbl.config(text=_("✔  ADB + scrcpy OK"), fg=C["green"])
        Toast(self.root, _("¡scrcpy y adb instalados con éxito! Ya puedes conectar tu teléfono."), "success", duration=5000)
        self._refresh_devices()

    def _copy_install_cmd(self):
        self.root.clipboard_clear()
        self.root.clipboard_append("sudo apt install adb scrcpy")
        messagebox.showinfo(_("Copiado ✔"), _("Comando copiado al portapapeles.\n\nPégalo en tu terminal con Ctrl+Shift+V."))

    def _open_terminal_install(self):
        cmd_str = "sudo apt install adb scrcpy"
        terminals = [
            ["x-terminal-emulator", "-e", cmd_str],
            ["gnome-terminal", "--", "bash", "-c", f"{cmd_str}; read -p 'Presiona Enter...'"],
            ["konsole", "-e", cmd_str],
            ["xterm", "-e", cmd_str],
        ]
        for tc in terminals:
            try:
                subprocess.Popen(tc)
                return
            except FileNotFoundError:
                continue
        messagebox.showinfo("Abre tu terminal", f"No se encontró un emulador de terminal automático.\n\nAbre una terminal y ejecuta:\n\n  {cmd_str}")

    # ── Devices Tab ───────────────────────────────────────────────────
    def _refresh_devices(self):
        self.ui.refs['scan_lbl'].config(text=_("Buscando…"), fg=C["cyan"])
        self.ctx.state_machine.set_pending(_("🔄  Escaneando dispositivos ADB…"))
        self.ctx.device_mgr.scan_devices(self._update_devs_ui, self.ctx.log)

    def _update_devs_ui(self, found: list):
        listbox = self.ui.refs['dev_listbox']
        # Fuente de verdad para la selección: el índice de la fila apunta a este
        # registro. Antes se reconstruía el serial **parseando la etiqueta**, y
        # las filas de "sin autorizar"/"offline"/"otro" no llevan el serial
        # entre paréntesis, así que se leía basura (P3.24).
        self._devices_shown = list(found)
        listbox.delete(0, tk.END)
        for serial, model, state in found:
            is_trusted = self.ctx.security_mgr.is_trusted_device(serial)
            alias = self.ctx.security_mgr.get_device_alias(serial, model)
            if state == "ok":
                if is_trusted:
                    listbox.insert(tk.END, f"  🟢 🛡️  {alias}  ({serial})")
                else:
                    listbox.insert(tk.END, f"  🟢 ⚠️  {alias}  ({serial}) [No Verificado]")
            elif state == "unauth":
                listbox.insert(tk.END, f"  🟠 ⚠️  {serial}  (Sin autorizar en pantalla)")
            elif state == "offline":
                listbox.insert(tk.END, f"  🔴 ⚠️  {serial}  (Desconectado / Offline)")
            else:
                listbox.insert(tk.END, f"  ⚫  {serial}  [{state}]")

        simple_combo = self.ui.refs.get('simple_dev_combo')
        if simple_combo:
            simple_combo['values'] = [f"{self.ctx.security_mgr.get_device_alias(serial, model)} ({serial})" for serial, model, state in found]

        if found:
            listbox.selection_set(0)
            self._on_dev_select()
            self.ui.refs['scan_lbl'].config(text=f"{len(found)} dispositivo(s)", fg=C["green"])
            self.ctx.state_machine.set_idle(f"✔  {len(found)} dispositivo(s) detectado(s).")
        else:
            self.ctx.active_device_serial = None
            self.ctx.active_device.set("Sin dispositivo")
            self.ui.refs['dev_info_lbl'].config(text=_("Sin dispositivos. Conecta un cable USB o activa ADB WiFi."), fg=C["orange"])
            self.ui.refs['scan_lbl'].config(text=_("Sin dispositivos"), fg=C["orange"])
            self.ctx.state_machine.set_empty(_("Sin dispositivos. Conecta un cable USB y activa la Depuración USB."))
            if simple_combo:
                simple_combo.set("Sin dispositivo")

    # ── Selección de dispositivo (descompuesta: resolver → pintar → estado) ──

    @staticmethod
    def _parse_device_row(raw: str):
        """Respaldo: interpreta una fila del formato '… ({serial})'.

        Sólo se usa si la lista se rellenó por una vía distinta a
        `_update_devs_ui` (que es la que mantiene `_devices_shown`).
        """
        clean = raw.strip().lstrip("🟢🟠🔴⚫ 🛡️⚠️").split("  (")[0].strip()
        return _extract_serial(raw), clean

    def _resolve_selected_device(self, event):
        """Devuelve `(serial, modelo)` del combo simple o del listbox, o None.

        El listbox se resuelve por **índice contra `_devices_shown`**, no
        leyendo su texto: el formato de la fila cambia según el estado y no
        siempre contiene el serial.
        """
        combo = self.ui.refs.get('simple_dev_combo')
        if event and combo and event.widget == combo:
            raw = combo.get()
            if not raw or raw == "Sin dispositivo":
                return None
            return _extract_serial(raw), raw.split(" (")[0].strip()

        listbox = self.ui.refs['dev_listbox']
        selection = listbox.curselection()
        if not selection:
            return None

        index = selection[0]
        shown = getattr(self, "_devices_shown", [])
        if 0 <= index < len(shown):
            serial, model, _state = shown[index]
            return serial, model
        return self._parse_device_row(listbox.get(index))

    def _update_device_badges(self, is_trusted: bool) -> None:
        """Pinta los tres indicadores de confianza (Acciones, Controles, Simple)."""
        text, color = (
            ("[🛡️ Confiable]", C["green"]) if is_trusted
            else ("[⚠️ No Verificado]", C["orange"])
        )
        for key in ("action_trust_lbl", "ctrl_trust_lbl", "simple_trust_lbl"):
            label = self.ui.refs.get(key)
            if label:
                label.config(text=text, fg=color)

    def _device_state(self, serial: str) -> str:
        """Estado ADB del serial según el último escaneo."""
        return next(
            (state for sr, _model, state in self.ctx.device_mgr.devices if sr == serial),
            "other",
        )

    def _set_device_info(self, text: str, color: str) -> None:
        label = self.ui.refs.get('dev_info_lbl')
        if label:
            label.config(text=text, fg=color)

    def _apply_device_state(self, state: str, serial: str, model: str,
                            alias: str, is_trusted: bool) -> None:
        """Traduce el estado ADB a mensaje de panel + estado del autómata."""
        if state == "unauth":
            self._set_device_info(
                f"🟠 ⚠️  {serial}  —  ¡Acepta el permiso de depuración en la pantalla del teléfono!",
                C["orange"],
            )
            self.ctx.state_machine.set_fault(
                _("⚠  Dispositivo no autorizado. Acepta el diálogo en el teléfono."),
                ErrorCode.DEVICE_UNAUTHORIZED,
            )
        elif state == "offline":
            self._set_device_info(
                f"🔴  {serial}  —  El dispositivo está desconectado (offline). Reinicia ADB.",
                C["red"],
            )
            self.ctx.state_machine.set_fault(
                _("⚠  Dispositivo offline. Desconecta y vuelve a conectar."),
                ErrorCode.DEVICE_OFFLINE,
            )
        elif state == "ok":
            self._announce_online_device(serial, model, alias, is_trusted)

    def _announce_online_device(self, serial: str, model: str, alias: str,
                                is_trusted: bool) -> None:
        if is_trusted:
            self._set_device_info(
                f"🟢 🛡️  {alias}  ({serial})  —  Conectado y Autorizado.", C["green"],
            )
            self._hint(f"✔  {alias}  —  {serial}", C["green"])
        else:
            self._set_device_info(
                f"🟢 ⚠️  {model}  ({serial})  —  Dispositivo no verificado en la bóveda.",
                C["orange"],
            )
            self._hint(f"⚠️  {model}  —  {serial} (No verificado)", C["orange"])

        self._apply_device_profile_association(serial)

    def _apply_device_profile_association(self, serial: str) -> None:
        """Carga el perfil asociado al dispositivo, si todavía existe."""
        associated = self.ctx.cfg.get("device_associations", {}).get(serial)
        if not associated or associated not in self.ctx.profile_mgr.get_profiles():
            return
        self.ctx.active_profile.set(associated)
        label = self.ui.refs.get('assoc_lbl')
        if label:
            label.config(
                text=f"↳  Perfil '{associated}' cargado automáticamente para este dispositivo.",
                fg=C["muted"],
            )

    def _on_dev_select(self, event=None):
        selected = self._resolve_selected_device(event)
        if selected is None:
            return
        serial, model = selected

        is_trusted = self.ctx.security_mgr.is_trusted_device(serial)
        alias = self.ctx.security_mgr.get_device_alias(serial, model)

        self.ctx.select_device(serial, f"{alias} ({serial})")
        self._update_device_badges(is_trusted)
        self._apply_device_state(self._device_state(serial), serial, model, alias, is_trusted)

        self._on_tab_changed()

    def _connect_wifi(self):
        ip_raw   = self.ui.refs['ip_entry'].get().strip()
        port_raw = self.ui.refs['port_entry'].get().strip() or "5555"
        parsed   = parse_ip_port(f"{ip_raw}:{port_raw}")
        # `parse_ip_port` NUNCA devuelve algo falso: ante una entrada inválida
        # retorna la tupla `(None, None)`, que es *verdadera*. Comprobar sólo
        # `if not parsed` dejaba pasar `ip = None` y reventaba en
        # `is_private_ip(None)` con AttributeError (defecto reproducido por D1).
        if not parsed or not parsed[0]:
            messagebox.showerror(_("IP inválida"), f"'{ip_raw}:{port_raw}' no es válida.\nEjemplo: 192.168.1.25:5555")
            return
        ip, port = parsed

        # Validación de seguridad: no permitir conexiones a IPs públicas si Modo Seguro está activo
        if self.ctx.security_mgr.is_safe_mode_enabled and not SecurityManager.is_private_ip(ip):
            messagebox.showerror(
                _("IP no permitida"),
                _("El Modo Seguro bloquea conexiones a IPs públicas o externas fuera de la red local.")
                + f"\n\n{_('Dirección ingresada:')} {ip}"
            )
            return

        target   = f"{ip}:{port}"
        self.ctx.log("ADB", f"Conectando a {target}…")
        self.ctx.state_machine.set_pending(f"Conectando a {target}…")
        def task():
            try:
                res_conn = self._adb().connect(target)
                self.ctx.log("ADB", res_conn.message)
                self.root.after(800, self._refresh_devices)
            except Exception as e:
                self.ctx.log("ERROR", f"WiFi: {e}")
        threading.Thread(target=task, daemon=True).start()

    def _pair_wifi(self):
        """Empareja un dispositivo Android 11+ de forma segura mediante 'adb pair'."""
        pair_ip_raw = self.ui.refs['pair_ip_entry'].get().strip()
        code_raw = self.ui.refs['pair_code_entry'].get().strip()

        parsed = SecurityManager.parse_pair_ip_port_code(pair_ip_raw, code_raw)
        if not parsed:
            messagebox.showerror(
                _("Error"),
                _("Código o IP inválidos para emparejar.\n\nFormato esperado:\nIP:Puerto: ej. 192.168.1.50:38291\nCódigo: 6 dígitos numéricos (ej. 123456)")
            )
            return

        ip, port, code = parsed

        if self.ctx.security_mgr.is_safe_mode_enabled and not SecurityManager.is_private_ip(ip):
            messagebox.showerror(
                _("IP no permitida"),
                _("El Modo Seguro bloquea conexiones a IPs públicas o externas fuera de la red local.")
            )
            return

        self.ctx.log("ADB", f"Emparejando con {ip}:{port}…")
        self.ctx.state_machine.set_pending(f"Emparejando con {ip}:{port}…")

        def task():
            ok, msg = SecurityManager.pair_device(self.ctx.adb, ip, port, code)
            if ok:
                self.ctx.log("OK", f"Emparejamiento exitoso con {ip}:{port}")
                # Auto-confiar en la bóveda
                self.ctx.security_mgr.trust_device(f"{ip}:{port}", "Android WiFi", f"Android {ip}", save_config)
                self.root.after(0, lambda: [
                    self.ctx.state_machine.set_success(_("Emparejamiento exitoso")),
                    Toast(self.root, f"✔ Emparejado con éxito con {ip}:{port}", "success"),
                    self._refresh_devices()
                ])
            else:
                self.ctx.log("ERROR", f"Error de emparejamiento: {msg}")
                self.root.after(0, lambda: [
                    self.ctx.state_machine.set_fault(_("Error al emparejar"), ErrorCode.PAIRING_FAILED),
                    messagebox.showerror(_("Error al emparejar"), f"No se pudo emparejar con el dispositivo:\n\n{msg}")
                ])

        threading.Thread(target=task, daemon=True).start()

    def _lockdown_tcpip(self):
        """Cierra el puerto TCP/IP 5555 en el dispositivo activo devolviéndolo a modo USB seguro."""
        serial = self.ctx.active_device_serial
        if not serial or not self.ctx.adb:
            messagebox.showwarning(_("Sin dispositivo"), _("Selecciona un dispositivo activo en la lista primero."))
            return
        self.ctx.log("SEC", f"[{serial}] Cerrando puerto TCP/IP 5555 con 'adb usb'…")
        self.ctx.state_machine.set_pending(_("Blindando dispositivo…"))
        def task():
            ok, msg = SecurityManager.lockdown_device_tcpip(self.ctx.adb, serial)
            if ok:
                self.ctx.log("OK", f"[{serial}] {msg}")
                self.root.after(0, lambda: [
                    self.ctx.state_machine.set_success(_("✔ Puerto TCP/IP cerrado.")),
                    Toast(self.root, _("✔ Dispositivo blindado: Puerto TCP/IP cerrado."), "success"),
                    self._refresh_devices()
                ])
            else:
                self.ctx.log("ERROR", f"[{serial}] Lockdown: {msg}")
                self.root.after(0, lambda: [
                    self.ctx.state_machine.set_fault(_("Error al blindar"), ErrorCode.LOCKDOWN_FAILED),
                    messagebox.showwarning(_("Aviso"), f"No se pudo restaurar el modo USB:\n\n{msg}")
                ])
        threading.Thread(target=task, daemon=True).start()

    def _panic_lockdown(self):
        """Detiene todas las sesiones y revoca los puertos TCP/IP en todos los dispositivos conectados."""
        if messagebox.askyesno(_("Blindar Red / Cerrar Puertos"),
                               _("¿Deseas cerrar inmediatamente todas las transmisiones activas y revocar el puerto TCP/IP 5555 en todos los dispositivos conectados?")):
            # Detener todas las sesiones
            self.ctx.session_mgr.stop_all()
            # Obtener seriales conectados
            serials = [s for s, m, st in self.ctx.device_mgr.devices]
            if serials and self.ctx.adb:
                def task():
                    n = SecurityManager.lockdown_all_devices(self.ctx.adb, serials)
                    self.ctx.log("SEC", f"Lockdown ejecutado en {n} dispositivo(s).")
                    self.root.after(0, lambda: [
                        self._refresh_devices(),
                        self.ctx.state_machine.set_success(_("🔒 Red blindada y puertos cerrados.")),
                        Toast(self.root, _("🔒 Red blindada: todas las sesiones detenidas y puertos cerrados."), "success")
                    ])
                threading.Thread(target=task, daemon=True).start()
            else:
                self._refresh_devices()
                self.ctx.state_machine.set_success(_("🔒 Red blindada."))
                Toast(self.root, _("🔒 Todas las sesiones detenidas."), "success")

    def _toggle_safe_mode(self):
        """Conmuta el estado de Modo Seguro y actualiza los indicadores visuales."""
        current = self.ctx.security_mgr.is_safe_mode_enabled
        new_state = not current
        self.ctx.security_mgr.set_safe_mode(new_state, save_config)
        safe_txt = "🛡️ " + (_("Modo Seguro: ON") if new_state else _("Modo Seguro: OFF"))
        safe_fg = C["green"] if new_state else C["orange"]
        if hasattr(self, '_btn_safe_mode'):
            self._btn_safe_mode.config(text=safe_txt, fg=safe_fg)
        status_msg = "Modo Seguro Activado" if new_state else "Modo Seguro Desactivado"
        Toast(self.root, f"🛡️ {status_msg}", "success" if new_state else "warning")
        self.ctx.log("SEC", f"{status_msg}: Protección de red y bóveda de confianza {'activada' if new_state else 'desactivada'}.")

    def _open_trust_vault(self):
        """Abre la ventana modal para gestionar todos los dispositivos confiables."""
        TrustVaultDialog(self.root, self.ctx.security_mgr, save_config, self._refresh_devices)

    def _open_device_trust_modal(self):
        """Abre la ventana modal para editar el estado de confianza y alias del dispositivo activo."""
        serial = self.ctx.active_device_serial
        if not serial:
            messagebox.showwarning(_("Sin dispositivo"), _("Selecciona un dispositivo activo en la lista primero."))
            return
        model = next((m for s, m, st in self.ctx.device_mgr.devices if s == serial), "Android")
        DeviceTrustModal(self.root, serial, model, self.ctx.security_mgr, save_config, self._refresh_devices)

    def _enable_tcpip(self):
        serial = self.ctx.active_device_serial
        if not serial or not self.ctx.adb:
            messagebox.showerror(_("Error"), _("Selecciona un dispositivo USB primero."))
            return
        self.ctx.log("ADB", f"[{serial}] TCP/IP 5555…")
        def task():
            try:
                r_tcp = self._adb().start_tcpip(serial, 5555)
                self.ctx.log("ADB", r_tcp.message)
                self.ctx.log(_("OK"), _("Puerto 5555 abierto. Desconecta el cable."))
                self.root.after(0, lambda: messagebox.showinfo(
                    "TCP/IP habilitado",
                    f"Dispositivo {serial} listo en el puerto 5555.\n"
                    f"Desconecta el cable USB y conecta por IP.\n\n"
                    f"💡 Recuerda pulsar '🛡️ Blindar TCP/IP' al terminar para cerrar el puerto."))
            except Exception as e:
                self.ctx.log("ERROR", f"TCP/IP: {e}")
        threading.Thread(target=task, daemon=True).start()

    def _get_device_ip(self):
        """Consulta la IP WiFi del dispositivo seleccionado vía ADB y la pega en el campo."""
        serial = self.ctx.active_device_serial
        if not serial or not self.ctx.adb:
            messagebox.showwarning("Sin dispositivo",
                                   "Selecciona un dispositivo en la lista primero.")
            return
        self.ctx.state_machine.set_pending(_("Obteniendo IP del dispositivo…"))
        def task():
            ip = None
            try:
                # Método 1: ip route (funciona en la mayoría de romés)
                r = self._adb().shell(serial, "ip", "route", timeout=8)
                for line in (r.data or "").splitlines():
                    m = re.search(r"src (\d+\.\d+\.\d+\.\d+)", line)
                    if m:
                        ip = m.group(1)
                        break
                # Método 2: ifconfig wlan0
                if not ip:
                    r2 = self._adb().shell(serial, "ifconfig", "wlan0", timeout=8)
                    out2 = r2.data or ""
                    m2 = re.search(r"inet addr:(\d+\.\d+\.\d+\.\d+)", out2)
                    if not m2:
                        m2 = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", out2)
                    if m2:
                        ip = m2.group(1)
            except Exception as e:
                self.ctx.log("ERROR", f"Obtener IP: {e}")

            def apply():
                if ip:
                    entry = self.ui.refs.get('ip_entry')
                    if entry:
                        entry.delete(0, tk.END)
                        entry.insert(0, ip)
                    self.ctx.state_machine.set_success(f"IP detectada: {ip}")
                    Toast(self.root, f"IP del dispositivo: {ip}", "success")
                else:
                    self._hint(_("No se detectó IP WiFi."), C["orange"])
                    Toast(self.root, _("No se pudo detectar la IP. ¿Está conectado por WiFi?"), "warning")
            self.root.after(0, apply)
        threading.Thread(target=task, daemon=True).start()

    def _go_to_help_usb(self):
        """Cambia a la pestaña Ayuda y expande el FAQ de depuración USB."""
        self._nb.select(5)
        try:
            if len(self.ui._faq_items) > 1:
                self.ui._faq_items[1].expand()
        except Exception:
            pass

    def _go_to_help_v4l2(self):
        """Cambia a la pestaña Ayuda y expande la FAQ de Webcam Virtual v4l2loopback."""
        self._nb.select(5)
        try:
            if len(self.ui._faq_items) > 5:
                self.ui._faq_items[5].expand()
        except Exception:
            pass

    def _send_keyevent(self, code):
        """Envía un keyevent de control remoto al dispositivo activo vía ADB de forma segura."""
        serial = self.ctx.active_device_serial
        if not serial or not self.ctx.adb:
            messagebox.showwarning(_("Sin dispositivo"), _("Selecciona un dispositivo activo en la lista primero."))
            return
        def task():
            try:
                if code == "notifications":
                    self._adb().shell(serial, "cmd", "statusbar", "expand-notifications", timeout=5)
                elif code == "paste_text":
                    try:
                        text = self.root.clipboard_get()
                        if text:
                            clean_text = SecurityManager.sanitize_text_input(text)
                            if not clean_text:
                                return
                            # Si Modo Seguro está activo y el texto es largo, pedir confirmación rápida
                            if self.ctx.security_mgr.is_safe_mode_enabled and len(clean_text) > 80:
                                if not messagebox.askyesno(_("Confirmar"), f"¿Pegar texto ({len(clean_text)} caracteres) en el dispositivo '{serial}'?"):
                                    return
                            # `adb shell` concatena argv con espacios, así que el
                            # texto debe viajar YA entrecomillado (un solo token)
                            # para que el shell del dispositivo no lo parta.
                            escaped_text = clean_text.replace("'", "'\\''")
                            self._adb().shell(serial, "input", "text", f"'{escaped_text}'", timeout=5)
                    except tk.TclError:
                        pass # Clipboard empty
                elif code == "screen_on":
                    self._adb().shell(serial, "input", "keyevent", "224", timeout=5)
                elif code == "screen_off":
                    self._adb().shell(serial, "input", "keyevent", "223", timeout=5)
                else:
                    self._adb().shell(serial, "input", "keyevent", str(code), timeout=5)
            except Exception as e:
                self.ctx.log("ERROR", f"Keyevent {code}: {e}")
        threading.Thread(target=task, daemon=True).start()

    def _install_apk(self):
        """Abre un diálogo para seleccionar un APK e instalarlo vía ADB con confirmación de seguridad."""
        serial = self.ctx.active_device_serial
        if not serial or not self.ctx.adb:
            messagebox.showwarning(_("Sin dispositivo"), _("Selecciona un dispositivo activo en la lista primero."))
            return
        apk_path = filedialog.askopenfilename(
            title="Seleccionar archivo APK para instalar",
            filetypes=[(_("Archivos Android APK"), _("*.apk")), (_("Todos los archivos"), _("*.*"))]
        )
        if not apk_path:
            return
        apk_name = os.path.basename(apk_path)
        is_trusted = self.ctx.security_mgr.is_trusted_device(serial)
        alias = self.ctx.security_mgr.get_device_alias(serial)

        # Si el Modo Seguro está activo o el dispositivo es desconocido, solicitar confirmación explícita
        if self.ctx.security_mgr.is_safe_mode_enabled or not is_trusted:
            if not messagebox.askyesno(
                _("Confirmar Instalación de APK"),
                f"¿Deseas instalar '{apk_name}' en el dispositivo '{alias}' ({serial})?"
            ):
                return

        self.ctx.log("ADB", f"[{serial}] Instalando APK: {apk_name}…")
        self.ctx.state_machine.set_pending(f"Instalando {apk_name}…")
        Toast(self.root, f"Instalando {apk_name}...", "info")
        def task():
            try:
                inst = self._adb().install(serial, apk_path)
                output = inst.message or ""
                if inst.success:
                    self.ctx.log("OK", f"[{serial}] Instalación exitosa: {apk_name}")
                    self.root.after(0, lambda: [
                        self.ctx.state_machine.set_success(f"✔ APK instalada: {apk_name}"),
                        Toast(self.root, f"✔ APK instalada con éxito: {apk_name}", "success")
                    ])
                else:
                    self.ctx.log("ERROR", f"[{serial}] Error al instalar {apk_name}: {output.strip()}")
                    self.root.after(0, lambda: [
                        self.ctx.state_machine.set_fault(_("❌ Error al instalar APK"), ErrorCode.APK_INSTALL_FAILED),
                        messagebox.showerror("Error al instalar APK", f"No se pudo instalar {apk_name}:\n\n{output.strip()}")
                    ])
            except Exception as e:
                self.ctx.log("ERROR", f"Instalar APK: {e}")
        threading.Thread(target=task, daemon=True).start()

    def _check_v4l2(self):
        if _PLAT != "linux":
            if 'v4l2_lbl' in self.ui.refs:
                self.ui.refs['v4l2_lbl'].config(text=_("Solo disponible en Linux."), fg=C["muted"])
            return
        if os.path.exists("/sys/module/v4l2loopback"):
            devs = sorted(d for d in os.listdir("/dev") if re.match(r"video\d+", d))
            self.ui.refs['v4l2_lbl'].config(text=f"✔  v4l2loopback activo  —  {', '.join(devs) or 'sin /dev/videoX'}", fg=C["green"])
            self.ui.refs['route_cam_btn'].config(state="normal")
        else:
            self.ui.refs['v4l2_lbl'].config(text=_("✘  v4l2loopback no cargado."), fg=C["red"])
            self.ui.refs['route_cam_btn'].config(state="disabled")

    def _setup_v4l2(self):
        if _PLAT != "linux":
            messagebox.showerror(_("Error"), _("Solo funciona en Linux."))
            return
        try:
            if "v4l2loopback" in subprocess.run(["lsmod"],capture_output=True,text=True).stdout:
                self.ctx.log("OK","v4l2loopback ya cargado.")
                self._check_v4l2()
                return
        except Exception:
            pass
        self.ctx.log("INFO","Cargando v4l2loopback con pkexec…")
        def task():
            try:
                r = subprocess.run(
                    ["pkexec","modprobe","v4l2loopback", "devices=1","video_nr=9", "card_label=Scrcpy Virtual Camera","exclusive_caps=1"],
                    capture_output=True,text=True,timeout=30)
                if r.returncode == 0:
                    self.ctx.log("OK","Módulo v4l2loopback cargado en /dev/video9.")
                else:
                    self.ctx.log("ERROR", f"Error: {r.stderr.strip() or r.stdout.strip()}\nManual: sudo modprobe v4l2loopback devices=1 video_nr=9 card_label='Scrcpy Virtual Camera' exclusive_caps=1")
            except FileNotFoundError:
                self.ctx.log("ERROR","pkexec no encontrado. Usa sudo en terminal.")
            except Exception as e:
                self.ctx.log("ERROR",f"v4l2loopback: {e}")
            self.root.after(600, self._check_v4l2)
        threading.Thread(target=task, daemon=True).start()

    def _abrir_camara_en_pantalla_directa(self, serial: str, camid: Any, profile: dict) -> None:
        """Abre la cámara en una ventana directa de scrcpy si no hay v4l2."""
        cam_cfg = dict(profile)
        cam_cfg["video_source"] = "camera"
        cam_cfg["camera_id"] = str(camid)
        cam_cfg["max_size"] = "1920"
        res = self.ctx.session_mgr.start_scene(
            serial, f"Cámara: {serial}", cam_cfg,
            lambda: Toast(self.root, _("Cámara activa en ventana."), "success")
        )
        if not res.success:
            messagebox.showerror(_("Error"), res.message)
        self._refresh_table()

    def _lanzar_camara_v4l2(self, serial: str, camid: Any) -> None:
        """Enruta la cámara hacia /dev/video9 vía v4l2sink."""
        cmd = [self.ctx.scrcpy, "-s", serial, "--video-source=camera", "--camera-id", str(camid), "--max-size", "1920", "--v4l2-sink=/dev/video9", "--no-playback"]
        self.ctx.log("INFO", f"[{serial}] Enrutando cámara:\n  {' '.join(cmd)}")
        try:
            kw = {}
            if _PLAT != "win32":
                kw["preexec_fn"] = os.setsid
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, **kw)
            from .managers import ScrcpySession
            sess = ScrcpySession(serial, "Webcam Loopback", proc)
            self.ctx.session_mgr.sessions[serial + "_cam"] = sess
            self._refresh_table()

            def _read_stream(stream, sr):
                try:
                    for line in iter(stream.readline, ""):
                        if not line: break
                        s = line.strip()
                        if s: self.ctx.log("INFO", f"[{sr}] {s}")
                except Exception: pass

            for stream in [proc.stdout, proc.stderr]:
                threading.Thread(target=_read_stream, args=(stream, serial), daemon=True).start()
            messagebox.showinfo(_("Cámara enrutada"), _("Feed en /dev/video9 activo.\n\nEn OBS Studio:\n  + Fuente → Dispositivo de captura de vídeo (V4L2)\n  → Selecciona 'Scrcpy Virtual Camera'"))
        except Exception as e:
            self.ctx.log("ERROR", f"Enrutar cámara: {e}")

    def _route_cam(self):
        serial = self.ctx.active_device_serial
        if not serial or not self.ctx.scrcpy:
            messagebox.showerror(_("Error"), _("Selecciona un dispositivo activo."))
            return
        p = self.ctx.profile_mgr.get_profiles().get(self.ctx.active_profile.get(), {})
        camid = p.get("camera_id", "0")

        # Si /dev/video9 no existe en Linux, preguntar si se desea abrir la cámara en pantalla directa
        if _PLAT != "win32" and not os.path.exists("/dev/video9"):
            ans = messagebox.askyesno(
                _("v4l2loopback no detectado"),
                _("El dispositivo virtual /dev/video9 no está activo en el sistema.\n"
                  "(Se requiere 'sudo modprobe v4l2loopback video_nr=9' para OBS).\n\n"
                  "¿Deseas abrir la cámara directamente en una ventana en pantalla?")
            )
            if ans:
                self._abrir_camara_en_pantalla_directa(serial, camid, p)
            else:
                self._v4l2_help()
            return

        self._lanzar_camara_v4l2(serial, camid)

    def _v4l2_help(self):
        messagebox.showinfo(_("Instrucciones v4l2loopback"), _("Instalación:\n\n  sudo apt install v4l2loopback-dkms v4l2loopback-utils\n\nCargar módulo manualmente:\n\n  sudo modprobe v4l2loopback devices=1 video_nr=9 \\\n    card_label='Scrcpy Virtual Camera' exclusive_caps=1\n\nPara cargar en cada arranque, crea:\n  /etc/modprobe.d/v4l2loopback.conf\nCon el contenido:\n  options v4l2loopback devices=1 video_nr=9 \\\n    card_label='Scrcpy Virtual Camera' exclusive_caps=1\n\nY añade 'v4l2loopback' a /etc/modules."))

    # ── Profiles Tab ───────────────────────────────────────────────────
    def _refresh_profile_listbox(self):
        listbox = self.ui.refs['profile_listbox']
        empty_lbl = self.ui.refs.get('profile_empty_lbl')
        listbox.delete(0, tk.END)
        profiles = self.ctx.profile_mgr.get_profiles()
        for name in profiles:
            listbox.insert(tk.END, f"  {name}")

        # Mostrar/ocultar empty state
        if empty_lbl:
            if profiles:
                empty_lbl.pack_forget()
                listbox.pack(fill="both", expand=True)
            else:
                listbox.pack_forget()
                empty_lbl.pack(fill="x", expand=True)

        # Actualizar combobox de perfiles activos
        names = list(profiles.keys())
        combo = self.ui.refs.get('active_profile_combo')
        if combo:
            combo['values'] = names

        simple_combo = self.ui.refs.get('simple_prof_combo')
        if simple_combo:
            simple_combo['values'] = names

        self._sync_profile_selection()

    def _sync_profile_selection(self, target_name: str = None):
        """Sincroniza bidireccionalmente el listbox y las fichas de detalle con el perfil activo."""
        listbox = self.ui.refs.get('profile_listbox')
        if not listbox: return
        profiles = self.ctx.profile_mgr.get_profiles()
        if not profiles: return

        name = target_name or self.ctx.active_profile.get()
        if name not in profiles:
            name = list(profiles.keys())[0]
            self.ctx.active_profile.set(name)

        names = list(profiles.keys())
        if name in names:
            idx = names.index(name)
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(idx)
            listbox.activate(idx)
            listbox.see(idx)

        # Actualizar las fichas de detalle (chips) inmediatamente
        p = profiles[name]
        if 'profile_chips' in self.ui.refs:
            self.ui.refs['profile_chips'].set_profile(name, p)

    def _on_profile_listbox_sel(self, event=None):
        listbox = self.ui.refs['profile_listbox']
        sel = listbox.curselection()
        if not sel: return
        raw = listbox.get(sel[0]).strip()
        profiles = self.ctx.profile_mgr.get_profiles()
        if raw not in profiles: return
        p = profiles[raw]
        if 'profile_chips' in self.ui.refs:
            self.ui.refs['profile_chips'].set_profile(raw, p)
        self.ctx.active_profile.set(raw)
        combo = self.ui.refs.get('active_profile_combo')
        if combo:
            combo.set(raw)
        simple_combo = self.ui.refs.get('simple_prof_combo')
        if simple_combo:
            simple_combo.set(raw)
        self.ctx.save_current_config()

    def _open_wizard(self):
        from .utils import save_config
        from .ui_widgets import Toast
        def on_save(data: dict):
            name = data.pop("name")
            self.ctx.cfg["profiles"][name] = data
            if self.ctx.active_device_serial:
                self.ctx.cfg.setdefault("device_associations", {})[self.ctx.active_device_serial] = name
            save_config(self.ctx.cfg)
            self._refresh_profile_listbox()
            self.ui.refs['active_profile_combo'].config(values=list(self.ctx.cfg["profiles"].keys()))
            self.ctx.active_profile.set(name)
            self.ctx.save_current_config()
            self._sync_profile_selection(name)
            self.ctx.log("OK", f"Perfil '{name}' creado desde el asistente.")
            Toast(self.root, f"Perfil '{name}' creado correctamente.", "success")
        from .ui_widgets import ProfileWizard
        ProfileWizard(self.root, on_save)

    def _start_profile(self):
        """Lanza la transmisión con el perfil seleccionado en el listbox o en el combobox activo."""
        listbox = self.ui.refs.get('profile_listbox')
        name = None
        if listbox:
            sel = listbox.curselection()
            if sel:
                name = listbox.get(sel[0]).strip()

        # Fallback resiliente: combobox o perfil activo global
        if not name:
            combo = self.ui.refs.get('active_profile_combo')
            if combo and combo.get().strip():
                name = combo.get().strip()
            else:
                name = self.ctx.active_profile.get().strip()

        profiles = self.ctx.profile_mgr.get_profiles()
        if not name or name not in profiles:
            if profiles:
                name = list(profiles.keys())[0]
            else:
                from .ui_widgets import Toast
                Toast(self.root, _("No hay perfiles disponibles. Crea uno primero."), "warning")
                return

        self.ctx.active_profile.set(name)
        self.ctx.save_current_config()
        self._sync_profile_selection(name)

        if not self.ctx.active_device_serial:
            from .ui_widgets import Toast
            Toast(self.root, _("Selecciona un dispositivo en la pestaña Dispositivos."), "warning")
            self._select_tab("device")
            return

        self._toggle_scene()

    def _delete_profile(self):
        from .utils import save_config
        listbox = self.ui.refs['profile_listbox']
        sel = listbox.curselection()
        if not sel:
            messagebox.showwarning(_("Atención"), _("Selecciona un perfil en la lista."))
            return
        name = listbox.get(sel[0]).strip()
        if len(self.ctx.profile_mgr.get_profiles()) <= 1:
            messagebox.showerror(_("Error"), _("Debe existir al menos un perfil."))
            return
        if messagebox.askyesno("Confirmar", f"¿Eliminar el perfil '{name}'?"):
            self.ctx.cfg["profiles"].pop(name, None)
            save_config(self.ctx.cfg)
            self._refresh_profile_listbox()
            pl = list(self.ctx.cfg["profiles"].keys())
            self.ui.refs['active_profile_combo'].config(values=pl)
            self.ctx.active_profile.set(pl[0])
            self._sync_profile_selection(pl[0])
            self.ctx.log("INFO", f"Perfil '{name}' eliminado.")

    def _on_active_profile_change(self, event=None):
        name = self.ctx.active_profile.get()
        self.ctx.save_current_config()
        self._sync_profile_selection(name)
        self._hint(f"Perfil activo: {name}", C["cyan"])

    # ── Actions Tab ───────────────────────────────────────────────────
    def _start_otg_mode(self):
        """Inicia una sesión de control USB directo por hardware (HID) con teclado y ratón sin ventana de video."""
        serial = self.ctx.active_device_serial
        if not self._dispositivo_listo_para_la_escena(serial, critico=False):
            return

        otg_cfg = {
            "extra_args": "--otg",
            "audio_source": "none",
            "turn_screen_off": False,
            "stay_awake": True
        }
        res = self.ctx.session_mgr.start_scene(
            serial, "Modo OTG (HID)", otg_cfg,
            lambda: Toast(self.root, _("Modo OTG activo: Teclado y Ratón PC conectados al teléfono."), "success")
        )
        if not res.success:
            messagebox.showerror(_("Error"), res.message)
        else:
            self._refresh_table()

    def _toggle_tethering(self):
        """Activa o desactiva el túnel de internet inverso (Reverse Tethering) mediante gnirehtet."""
        serial = self.ctx.active_device_serial
        if not serial:
            messagebox.showwarning(_("Sin dispositivo"), _("Selecciona un dispositivo activo en la lista primero."))
            return
        if self.ctx.tether_service.is_tethering_active(serial):
            res = self.ctx.tether_service.stop_tethering(serial)
            if res.success:
                Toast(self.root, _("Internet compartido detenido para el dispositivo."), "info")
            else:
                messagebox.showerror(_("Error"), res.message)
        else:
            if not self.ctx.tether_engine._binary_path:
                messagebox.showinfo(
                    _("gnirehtet no encontrado"),
                    _("Para compartir internet de tu PC al teléfono por USB se requiere la herramienta 'gnirehtet'.\n\nPuedes colocar el ejecutable 'gnirehtet' en tu PATH o dentro de la carpeta bin de MASV.")
                )
                return
            res = self.ctx.tether_service.start_tethering(serial)
            if res.success:
                Toast(self.root, _("Compartiendo internet de la PC al teléfono por USB."), "success")
            else:
                messagebox.showerror(_("Error"), res.message)

    def _toggle_scene(self):
        """Inicia o detiene la transmisión del dispositivo seleccionado."""
        serial = self.ctx.active_device_serial
        if not self._dispositivo_listo_para_la_escena(serial):
            return

        if serial in self.ctx.session_mgr.sessions:
            self._stop_current()
            return

        self._arrancar_escena(serial)

    def _dispositivo_listo_para_la_escena(self, serial, critico: bool = True) -> bool:
        """Comprueba que hay dispositivo y que el Modo Seguro lo aprueba.

        `critico` distingue el aviso de "sin dispositivo" de arrancar una sesión
        (error) del de Modo OTG (aviso): la diferencia venía de antes y se conserva.
        """
        if not serial:
            self._avisar_sin_dispositivo(critico)
            return False

        if self._requiere_confirmacion_de_confianza(serial):
            return self._pedir_confianza(serial)
        return True

    def _avisar_sin_dispositivo(self, critico: bool = True):
        """Avisa de que no hay dispositivo y lleva a la pestaña Dispositivo."""
        aviso = messagebox.showerror if critico else messagebox.showwarning
        aviso(_("Sin dispositivo"),
              _("Selecciona un dispositivo en la pestaña Dispositivo."))
        self._nb.select(2)

    def _requiere_confirmacion_de_confianza(self, serial) -> bool:
        """True si el Modo Seguro está activo y el dispositivo no es de confianza."""
        return (self.ctx.security_mgr.is_safe_mode_enabled
                and not self.ctx.security_mgr.is_trusted_device(serial))

    def _pedir_confianza(self, serial) -> bool:
        """Muestra el aviso de confianza. True si el usuario autoriza el arranque.

        Cerrar el aviso sin elegir o cancelar NO equivale a confiar.
        """
        alias = self.ctx.security_mgr.get_device_alias(serial)
        model = self.ctx.device_mgr.get_device_model(serial) or "Android"
        modal = TrustPromptModal(self.root, serial, model, alias,
                                 self.ctx.security_mgr, self.ctx.cfg, save_config)
        if not modal.result or modal.result == "cancel":
            return False
        if modal.result == "trust":
            save_config(self.ctx.cfg)
            self._on_dev_select()
        return True

    def _arrancar_escena(self, serial):
        """Arranca la sesión de scrcpy con el perfil activo."""
        profile_name, profile_data = self._perfil_para_arrancar()

        self.ctx.state_machine.set_pending(f"Iniciando sesión: {profile_name}...")
        self._parches_previos_al_arranque(serial, profile_data)

        def on_started():
            self._refresh_table()
            self._nb.select(0)   # pestaña Acciones
            self.ctx.state_machine.set_success(f"✔ Transmisión activa: {profile_name}")

        res = self.ctx.session_mgr.start_scene(serial, profile_name, profile_data, on_started)
        if not res.success:
            self.ctx.state_machine.set_fault(
                res.message, res.error_code or ErrorCode.PROCESS_SPAWN_ERROR,
            )

    def _perfil_para_arrancar(self) -> tuple:
        """(nombre, datos) del perfil activo, con los argumentos del mini-dock si toca."""
        profile_name = self.ctx.active_profile.get()
        profile_data = dict(self.ctx.cfg["profiles"].get(profile_name, {}))

        if hasattr(self, "is_advanced_view") and not self.is_advanced_view:
            extra = self._extras_de_la_vista_simple()
            if extra:
                previos = profile_data.get("extra_args", "")
                profile_data["extra_args"] = f"{previos} {extra}".strip()
        return profile_name, profile_data

    def _extras_de_la_vista_simple(self) -> str:
        """Argumentos escritos en el mini-dock (vacío si no hay campo)."""
        var = self.ui.refs.get("simple_extra_cmd_var")
        return var.get().strip() if var else ""

    def _parches_previos_al_arranque(self, serial, profile_data):
        """Manda el keyevent 26 antes de arrancar cuando el perfil lo necesita."""
        if not self._necesita_keyevent_previo(profile_data):
            return
        self.ctx.log("ADB", f"[{serial}] keyevent 26…")
        self._adb().shell(serial, "input", "keyevent", "26", timeout=5)
        time.sleep(0.3)

    @staticmethod
    def _necesita_keyevent_previo(profile_data: dict) -> bool:
        """EMUI no apaga la pantalla por su cuenta; el micrófono sin vídeo necesita el empujón."""
        if profile_data.get("force_screen_off_keyevent"):
            return True
        return (profile_data.get("audio_source") == "mic"
                and "--no-video" in profile_data.get("extra_args", ""))

    def _stop_current(self):
        serial = self.ctx.active_device_serial
        if not serial or serial not in self.ctx.session_mgr.sessions:
            messagebox.showinfo(_("Sin sesión"), _("No hay ninguna sesión activa para el dispositivo seleccionado."))
            return
        self.ctx.session_mgr.stop_session(serial)
        self._refresh_table()
        self.ctx.state_machine.set_idle(_("Sesión detenida."))

    def _panic_kill(self):
        if not self.ctx.session_mgr.sessions:
            messagebox.showinfo(_("Sin sesiones"), _("No hay sesiones activas."))
            return
        if messagebox.askyesno(_("Confirmar"), _("¿Cerrar TODAS las sesiones de scrcpy?")):
            self.ctx.session_mgr.stop_all()
            self._refresh_table()
            self.ctx.log(_("WARNING"), _("Pánico: todas las sesiones cerradas."))
            self.ctx.state_machine.set_idle(_("Todas las sesiones cerradas."))

    def _restart_adb(self):
        if not self.ctx.adb: return
        self.ctx.log(_("ADB"), _("Reiniciando servidor ADB…"))
        self.ctx.state_machine.set_pending(_("Reiniciando ADB…"))
        def task():
            kill = self._adb().kill_server()
            if not kill.success:
                self.ctx.log("ERROR", f"kill-server: {kill.message}")
            time.sleep(0.5)
            start = self._adb().start_daemon()
            if not start.success:
                self.ctx.log("ERROR", f"start-server: {start.message}")
            self.ctx.log(_("OK"), _("Servidor ADB reiniciado."))
            self.root.after(600, self._refresh_devices)
        threading.Thread(target=task, daemon=True).start()

    def _stop_selected(self, _=None):
        """Detiene la sesión seleccionada en la tabla (o invocada por el atajo Supr).

        Firma tolerante a evento: el binding <Delete> de Tk invoca con un evento.
        Debe existir UNA sola definición (antes había dos, y la activa llamaba
        a SessionManager.stop(), que no existe).
        """
        tree = self.ui.refs['sess_tree']
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        if not vals:
            return
        serial = str(vals[0])
        res = self.ctx.session_mgr.stop_session(serial)
        self._refresh_table()
        if res.success:
            self.ctx.log("INFO", f"[{serial}] Sesión detenida por el usuario.")
            self.ctx.state_machine.set_idle(f"Sesión detenida: {serial}")
        else:
            messagebox.showwarning(_("Atención"), res.message)

    def _on_tab_changed(self, event=None):
        """Refresca las etiquetas de contexto (dispositivo, confianza y perfil activo)."""
        serial = self.ctx.active_device_serial
        self._pintar_etiquetas_de_dispositivo(serial)
        self._pintar_etiquetas_de_confianza(serial)
        self._pintar_etiquetas_de_perfil()

    def _pintar_etiquetas_de_dispositivo(self, serial):
        """Nombre del dispositivo (o el aviso de que no hay ninguno) en cada pestaña."""
        if not serial:
            self._pintar_etiqueta("action_device_lbl", _("📱  Sin dispositivo seleccionado"), C["muted"])
            self._pintar_etiqueta("ctrl_device_lbl", _("📱  Sin dispositivo"), C["muted"])
            return

        alias = self.ctx.security_mgr.get_device_alias(serial)
        texto = f"📱  {alias} ({serial})"
        for ref in _REFS_DE_DISPOSITIVO:
            self._pintar_etiqueta(ref, texto, C["text"])

    def _pintar_etiqueta(self, ref: str, texto: str, color: str):
        """Pinta una etiqueta si existe: no todos los refs están en todos los modos de vista."""
        etiqueta = self.ui.refs.get(ref)
        if etiqueta is not None:
            etiqueta.config(text=texto, fg=color)

    def _pintar_etiquetas_de_confianza(self, serial):
        """Sello de confianza del dispositivo activo, allí donde se muestre."""
        texto, color = self._sello_de_confianza(serial)
        for ref in _REFS_DE_CONFIANZA:
            self._pintar_etiqueta(ref, texto, color)

    def _sello_de_confianza(self, serial) -> tuple:
        """(texto, color) del sello: verde si es de confianza; naranja si no, o si no hay."""
        if not serial:
            return "", C["orange"]
        if self.ctx.security_mgr.is_trusted_device(serial):
            return " [🛡️ Confiable]", C["green"]
        return " [⚠️ No Verificado]", C["orange"]

    def _pintar_etiquetas_de_perfil(self):
        """Perfil activo en cada pestaña que lo muestre."""
        perfil = f"⚙️  {self.ctx.active_profile.get()}"
        for ref in _REFS_DE_PERFIL:
            self._pintar_etiqueta(ref, perfil, C["cyan"])

    # ── Logging Tab ───────────────────────────────────────────────────
    def _pump_logs(self):
        try:
            while True:
                lvl, msg = self.ctx.log_q.get_nowait()
                self._write_log(lvl, msg)
                self.ctx.log_q.task_done()
        except queue.Empty:
            pass
        self.root.after(100, self._pump_logs)

    def _write_log(self, level: str, msg: str):
        log_msg(level, msg)
        log_txt = self.ui.refs['log_txt']
        log_txt.config(state="normal")
        ts = time.strftime("%H:%M:%S")
        log_txt.insert(tk.END, f"[{ts}] [{level}] {msg}\n", level)
        log_txt.see(tk.END)
        if int(log_txt.index("end-1c").split(".")[0]) > 600:
            log_txt.delete(_("1.0"), _("100.0"))
        log_txt.config(state="disabled")

    def _clear_log(self):
        self.ui.refs['log_txt'].config(state="normal")
        self.ui.refs['log_txt'].delete("1.0", tk.END)
        self.ui.refs['log_txt'].config(state="disabled")

    def _open_log(self):
        try:
            if _PLAT == "linux":    subprocess.Popen(["xdg-open", LOG_FILE])
            elif _PLAT == "win32":  os.startfile(LOG_FILE)
            elif _PLAT == "darwin": subprocess.Popen(["open", LOG_FILE])
        except Exception as e:
            self.ctx.log("ERROR", f"Abrir log: {e}")

    def _filter_log(self, filter_key: str):
        log_txt = self.ui.refs['log_txt']
        try:
            with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return

        log_txt.config(state="normal")
        log_txt.delete("1.0", tk.END)
        for line in lines[-500:]:
            if filter_key == "ALL" or f"[{filter_key}]" in line:
                level = "ERROR" if "[ERROR]" in line else "WARNING" if "[WARNING]" in line else "ADB" if "[ADB]" in line else "INFO"
                log_txt.insert(tk.END, line, level)
        log_txt.see(tk.END)
        log_txt.config(state="disabled")

    def _copy_log(self):
        log_txt = self.ui.refs['log_txt']
        content = log_txt.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        from .ui_widgets import Toast
        Toast(self.root, _("Consola copiada al portapapeles"), "success")

    # ── Sessions Monitor ──────────────────────────────────────────────
    def _refresh_table(self):
        tree = self.ui.refs['sess_tree']
        for item in tree.get_children():
            tree.delete(item)
        for serial, sess in self.ctx.session_mgr.sessions.items():
            tag = "RUN" if sess.active else "STP"
            tree.insert("", "end", tags=(tag,), values=(
                serial, sess.profile_name, sess.pid,
                sess.uptime(), "▶ CORRIENDO" if sess.active else "■ DETENIDO"))
        n = len(self.ctx.session_mgr.sessions)
        self._sess_count_lbl.config(
            text=f"● {n} sesión{'es' if n!=1 else ''} activa{'s' if n!=1 else ''}" if n else "", fg=C["green"])

    def _monitor_sessions(self):
        sessions = self.ctx.session_mgr.sessions
        dead = [s for s, sess in sessions.items() if sess.process.poll() is not None]
        for serial in dead:
            sess = sessions.pop(serial)
            self.ctx.log("WARNING", f"[{serial}] Sesión terminada (PID {sess.pid}).")
            if self.ctx.active_device_serial == serial:
                self.root.after(0, lambda: self.ctx.state_machine.set_idle(
                    f"Sesión finalizada: {sess.profile_name}"))
        if dead or sessions:
            self._refresh_table()
        self.root.after(2000, self._monitor_sessions)

    def _sess_context_menu(self, event):
        """Menú contextual (clic derecho) en la tabla de sesiones."""
        tree = self.ui.refs['sess_tree']
        iid  = tree.identify_row(event.y)
        if not iid:
            return
        tree.selection_set(iid)
        vals = tree.item(iid, 'values')
        serial = str(vals[0]) if vals else ""

        menu = tk.Menu(self.root, tearoff=0, bg=C["card2"],
                       fg=C["text"], activebackground=C["blue"],
                       activeforeground="#FFFFFF", relief="flat",
                       font=(FONT_FAMILY, 10))
        menu.add_command(label="■  Detener sesión (Supr)",
                         command=self._stop_selected)
        menu.add_separator()
        menu.add_command(label="📋  Copiar serial",
                         command=lambda: (self.root.clipboard_clear(),
                                         self.root.clipboard_append(serial)))
        menu.add_command(label="📋  Copiar comando scrcpy",
                         command=lambda: self._copy_sess_cmd(serial))
        menu.add_separator()
        menu.add_command(label="⚠  Forzar cierre (kill)",
                         command=lambda: self._force_kill_sess(serial))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _copy_sess_cmd(self, serial: str):
        """Copia el argv real de la sesión, reconstruido por el motor."""
        res = self.ctx.session_mgr.build_command_for(serial)
        if not res.success or not res.data:
            Toast(self.root, res.message or _("No se pudo reconstruir el comando."), "warning")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(" ".join(res.data))
        Toast(self.root, _("Comando copiado al portapapeles"), "success")

    def _force_kill_sess(self, serial: str):
        sess = self.ctx.session_mgr.sessions.get(serial)
        if sess:
            try: sess.process.kill()
            except Exception: pass
            self.ctx.session_mgr.sessions.pop(serial, None)
            self._refresh_table()
            self.ctx.state_machine.set_idle(f"Proceso forzado a cerrar: {serial}")
            Toast(self.root, f"Sesión {serial} cerrada forzosamente.", "warning")

    def _show_onboarding(self):
        """Tutorial de bienvenida la primera vez que se abre la app."""
        win = tk.Toplevel(self.root)
        win.title("Bienvenido a MASV")
        win.geometry("500x420")
        win.configure(bg=C["bg"])
        win.resizable(False, False)
        win.grab_set()

        steps = [
            ("👋", "Bienvenido a MASV",
             "Memexicanisimos Android Screen Viewer.\n\n"
             "Esta app te permite transmitir la pantalla de tu Android\n"
             "a tu PC en alta calidad, crear perfiles y conectar por WiFi."),
            ("📱", "Pestaña Dispositivo",
             "Conecta tu teléfono por USB.\n\n"
             "Pulsa  🔄 Buscar dispositivos  para detectarlo.\n"
             "Asegúrate de haber activado la Depuración USB."),
            ("⚙️", "Pestaña Perfiles",
             "Crea un perfil con el asistente paso a paso.\n\n"
             "Elige resolución, FPS, bitrate y fuente de audio\n"
             "según el uso que le darás (juego, stream, webcam)."),
            ("🚀", "Pestaña Acciones",
             "Pulsa  ▶ Iniciar  o usa el atajo  Ctrl+I  para lanzar\n"
             "scrcpy con el perfil y dispositivo seleccionados.\n\n"
             "La tabla inferior muestra las sesiones activas."),
            ("✅", "Listo",
             "Revisa la pestaña  \u2753 Ayuda  para preguntas frecuentes.\n\n"
             "Atajos importantes:\n"
             "  Ctrl+I  → Iniciar/detener\n"
             "  Ctrl+R  → Buscar dispositivos\n"
             "  Ctrl+H  → Abrir Ayuda"),
        ]
        self._ob_step  = 0
        self._ob_steps = steps
        self._ob_win   = win

        ico_l  = tk.Label(win, text="", bg=C["bg"], fg=C["text"], font=(FONT_FAMILY, 42))
        ico_l.pack(pady=(28, 6))
        title_l = tk.Label(win, text="", bg=C["bg"], fg=C["purple"], font=(FONT_FAMILY, 15, "bold"))
        title_l.pack()
        body_l  = tk.Label(win, text="", bg=C["bg"], fg=C["text2"], font=FONT_UI,
                           justify="center", wraplength=400)
        body_l.pack(pady=(10, 20), padx=30)

        prog_f = tk.Frame(win, bg=C["bg"])
        prog_f.pack()
        dots = []
        for _idx in range(len(steps)):
            d = tk.Label(prog_f, text=_("●"), bg=C["bg"], fg=C["sep"], font=(FONT_FAMILY, 8))
            d.pack(side="left", padx=3)
            dots.append(d)

        nav = tk.Frame(win, bg=C["card2"])
        nav.pack(fill="x", side="bottom", pady=(20, 0))
        skip_btn = tk.Button(nav, text=_("Omitir"), bg=C["card2"], fg=C["text2"],
                             font=FONT_SM, relief="flat", bd=0, padx=12, pady=8)
        skip_btn.pack(side="left", padx=8, pady=6)
        next_btn = tk.Button(nav, text=_("Siguiente  ▶"), bg=C["blue"], fg="#FFF",
                             font=FONT_UI_B, relief="flat", bd=0, padx=16, pady=8)
        next_btn.pack(side="right", padx=8, pady=6)

        def show_step(i):
            ico, title, body = steps[i]
            ico_l.config(text=ico)
            title_l.config(text=title)
            body_l.config(text=body)
            for j, d in enumerate(dots):
                d.config(fg=C["blue"] if j <= i else C["sep"])
            last = (i == len(steps) - 1)
            next_btn.config(text=_("🎉  ¡Comenzar!") if last else "Siguiente  ▶",
                            bg=C["green"] if last else C["blue"])

        def next_step():
            if self._ob_step < len(steps) - 1:
                self._ob_step += 1
                show_step(self._ob_step)
            else:
                close_ob()

        def close_ob():
            self.ctx.cfg["onboarding_done"] = True
            save_config(self.ctx.cfg)
            win.destroy()

        next_btn.config(command=next_step)
        skip_btn.config(command=close_ob)
        win.protocol("WM_DELETE_WINDOW", close_ob)
        show_step(0)

    # ── System Tray & Close ───────────────────────────────────────────
    def _on_close(self):
        # Guardar geometría antes de cerrar/minimizar
        try:
            state = self.root.state()
            self.ctx.cfg["window_state"] = state
            if state == "normal":
                self.ctx.cfg["window_geometry"] = self.root.geometry()
            save_config(self.ctx.cfg)
        except Exception:
            pass

        if TRAY_AVAILABLE and self.ctx.session_mgr.sessions:
            self.root.withdraw()
            self._start_tray()
            self.ctx.log(_("INFO"), _("App minimizada a la bandeja del sistema."))
        else:
            self._exit()

    def _start_tray(self):
        try:
            img = _make_tray_icon()
        except Exception:
            img = None
        n = len(self.ctx.session_mgr.sessions)
        def show(icon, _): icon.stop(); self.root.after(0, self.root.deiconify)
        def quit_(icon, _): icon.stop(); self.root.after(0, self._exit)
        menu = pystray.Menu(
            pystray.MenuItem(f"Sesiones activas: {n}", None, enabled=False),
            pystray.MenuItem("Abrir MASV", show),
            pystray.MenuItem("Cerrar todo y salir", quit_),
        )
        self.tray_icon = pystray.Icon(
            "masv", img or Image.new("RGBA", (64, 64), "#0A84FF"),
            APP_SHORT, menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    # ── Cierre ordenado (descompuesto: un paso, una responsabilidad) ──

    @staticmethod
    def _shutdown_step(label: str, action) -> bool:
        """Ejecuta un paso del cierre sin que su fallo aborte los siguientes.

        Un cierre "determinista absoluto" no puede depender de que todos los
        pasos salgan bien: si el tracker revienta, las sesiones deben cerrarse
        igual, y la ventana guardarse igual.
        """
        try:
            action()
            return True
        except Exception as exc:  # noqa: BLE001 - el cierre nunca debe abortar
            print(f"Error durante el cierre ({label}): {exc}")
            return False

    def _stop_device_tracking(self) -> None:
        """Detiene el tracker del motor ADB (si existe)."""
        ctx = getattr(self, "ctx", None)
        if ctx is None or not getattr(ctx, "device_mgr", None):
            return
        ctx.device_mgr.stop_tracking()

    def _apply_security_lockdown(self) -> None:
        """Revoca los puertos TCP/IP abiertos si el auto-bloqueo está activo."""
        ctx = getattr(self, "ctx", None)
        if ctx is None or not getattr(ctx, "device_mgr", None):
            return
        if not (ctx.security_mgr and ctx.security_mgr.is_auto_lockdown_enabled and ctx.adb):
            return
        serials = [serial for serial, _model, _st in ctx.device_mgr.devices]
        if serials:
            SecurityManager.lockdown_all_devices(ctx.adb, serials)

    def _terminate_active_sessions(self) -> None:
        """Cierra todas las sesiones scrcpy activas."""
        ctx = getattr(self, "ctx", None)
        if ctx is None or not getattr(ctx, "session_mgr", None):
            return
        ctx.session_mgr.stop_all()

    def _persist_window_state(self) -> None:
        """Guarda la geometría actual antes de destruir la ventana."""
        ctx = getattr(self, "ctx", None)
        root = getattr(self, "root", None)
        if ctx is None or root is None:
            return
        ctx.cfg["window_geometry"] = root.geometry()
        ctx.save_current_config()

    def _release_tray(self) -> None:
        tray = getattr(self, "tray_icon", None)
        if tray:
            tray.stop()

    def _release_single_instance(self) -> None:
        lock = getattr(self, "single_instance", None)
        if lock:
            lock.release()

    def _destroy_root(self) -> None:
        root = getattr(self, "root", None)
        if root is not None:
            root.destroy()

    def _exit(self):
        """Cierre determinista absoluto: trackers, sesiones, tray y procesos residuales.

        Cada fase va aislada (`_shutdown_step`), así que un fallo puntual no
        deja sesiones scrcpy vivas ni la geometría sin guardar.
        """
        self._shutdown_step("trackers", self._stop_device_tracking)
        self._shutdown_step("lockdown", self._apply_security_lockdown)
        self._shutdown_step("sesiones", self._terminate_active_sessions)
        self._shutdown_step("geometría", self._persist_window_state)
        self._shutdown_step("tray", self._release_tray)
        self._shutdown_step("single-instance", self._release_single_instance)
        self._shutdown_step("root", self._destroy_root)

        os._exit(0)

def _make_tray_icon(size: int = 64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    d.ellipse([2, 2, size - 2, size - 2], fill="#BF5AF2")
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf", size // 3)
    except Exception:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size // 3)
        except Exception:
            font = ImageFont.load_default()
    text = "M"
    try:
        bb = d.textbbox((0, 0), text, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
    except Exception:
        tw, th = size // 4, size // 4
    d.text(((size - tw) // 2, (size - th) // 2 - 2), text, fill="#FFFFFF", font=font)
    return img

def _cli_install(argv) -> int:
    """Instala MASV en el sistema (`--install`). Devuelve el código de salida."""
    from .services.installer_service import InstallerService

    svc = InstallerService()
    svc.ensure_layout()
    exe_to_reg = _copiar_al_sistema(svc, argv[0])
    res = _escribir_lanzador(svc, exe_to_reg, _icono_a_registrar())

    if not res.success:
        print(f"[MASV] Error al instalar: {res.message}")
        return 1

    print("[MASV] Instalación completada con éxito.")
    print(f"[MASV] Enlace en terminal: {svc.bin_symlink_path}")
    print(f"[MASV] Acceso de escritorio: {svc.desktop_entry_path}")
    return 0


def _copiar_al_sistema(svc, programa):
    """Copia el ejecutable a la carpeta gestionada cuando vamos empaquetados.

    Fuera del empaquetado (o si ya se está ejecutando el binario instalado) se
    registra el ejecutable actual. Si la copia falla, la instalación sigue
    adelante con el original en vez de abortar.
    """
    import shutil
    from pathlib import Path

    congelado = getattr(sys, "frozen", False)
    origen = Path(sys.executable if congelado else os.path.abspath(programa)).resolve()
    if not congelado:
        return origen

    destino = svc.bin_dir / "MASV"
    if origen == destino.resolve():
        return origen
    try:
        shutil.copy2(origen, destino)
        destino.chmod(0o755)
        return destino
    except Exception:
        return origen


def _icono_a_registrar():
    """El logo a registrar: dentro del bundle cuando vamos empaquetados."""
    from pathlib import Path

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets" / "logo.png"
    return Path(__file__).parent.parent / "assets" / "logo.png"


def _escribir_lanzador(svc, exe_path, icono):
    """Copia el logo a la carpeta gestionada y escribe el `.desktop`.

    Sin logo, el lanzador se registra usando el propio ejecutable como icono.
    Si la copia del logo falla, se registra el original.
    """
    import shutil

    if not icono.exists():
        return svc.write_desktop_entry(exe_path, exe_path)

    destino_icono = svc.assets_dir / "logo.png"
    try:
        shutil.copy2(icono, destino_icono)
        return svc.write_desktop_entry(exe_path, destino_icono)
    except Exception:
        return svc.write_desktop_entry(exe_path, icono)


def _cli_uninstall(purge: bool) -> int:
    """Desinstala MASV (`--uninstall`); con `--purge` borra también los datos."""
    from .services.installer_service import InstallerService

    res = InstallerService().uninstall(purge=purge)
    if not res.success:
        print(f"[MASV] Error al desinstalar: {res.message}")
        return 1

    msg = "[MASV] Desinstalación completada con éxito."
    if purge:
        msg += " (Configuraciones y datos purgados)."
    print(msg)
    return 0


def _run_gui(single_inst=None) -> None:
    """Arranca la interfaz: cerrojo de instancia única, ventana y bucle de eventos."""
    single_inst = single_inst or SingleInstance()
    if not single_inst.acquire():
        messagebox.showwarning("MASV",
                               "La aplicación ya está en ejecución.\nBusca el icono en la bandeja del sistema.")
        sys.exit(1)

    try:
        root = tk.Tk()
        # La instancia se cuelga del `root` a propósito: el bucle de eventos corre
        # dentro de `mainloop()` y la app debe seguir viva mientras tanto. Sin esta
        # referencia, el único que la sostendría sería el registro de callbacks de Tk.
        root.masv_app = ScrcpyDockApp(root, single_instance=single_inst)
        root.mainloop()
    finally:
        single_inst.release()


def main(argv=None):
    """Punto de entrada: instalación/desinstalación por CLI, o arranque de la GUI.

    `argv` es inyectable para poder caracterizar el arranque; sin argumento usa
    `sys.argv` (comportamiento de siempre).
    """
    argv = sys.argv if argv is None else argv

    if "--install" in argv:
        sys.exit(_cli_install(argv))
    if "--uninstall" in argv:
        sys.exit(_cli_uninstall("--purge" in argv))

    _run_gui()

if __name__ == "__main__":
    main()
