import tkinter as tk
from .i18n import _
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
except ImportError:
    TRAY_AVAILABLE = False

import re
from .utils import C, FONT_UI, FONT_UI_B, FONT_SM, FONT_LG, FONT_MONO, FONT_FAMILY, SingleInstance, _extract_serial, parse_ip_port, log_msg, LOG_FILE, save_config
from .context import AppContext
from .ui_tabs import UIBuilder
from .ui_widgets import _recolor, Toast

_PLAT = sys.platform
APP_NAME = "Memexicanisimos Android Screen Viewer"
APP_SHORT = "MASV"

class ScrcpyDockApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.minsize(780, 580)
        self.root.configure(bg=C["bg"])

        self.ctx = AppContext(root)
        self._setup_styles()

        # ── Restaurar geometría guardada ───────────────────────
        geo = self.ctx.cfg.get(_("window_geometry"), _("860x680"))
        self.root.geometry(geo)
        if self.ctx.cfg.get("window_state") == "zoomed":
            try: self.root.state("zoomed")
            except Exception: pass

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

            'clear_log':  self._clear_log,
            'open_log':   self._open_log,
            'filter_log': self._filter_log,
            'copy_log':   self._copy_log,
        }

        self.ui = UIBuilder(self.ctx, self.cb)
        self._build_ui()

        self._check_deps()
        self._refresh_devices()
        self._pump_logs()
        self._monitor_sessions()
        self._bind_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Onboarding primera vez
        if not self.ctx.cfg.get("onboarding_done"):
            self.root.after(800, self._show_onboarding)

    def _bind_shortcuts(self):
        self.root.bind("<Control-q>", lambda _: self._on_close())
        self.root.bind("<Control-r>", lambda _: self._refresh_devices())
        self.root.bind("<Control-i>", lambda _: self._toggle_scene())
        self.root.bind("<Control-h>", lambda _: self._nb.select(5))

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=C["bg"], foreground=C["text"],
                    fieldbackground=C["card"], font=FONT_UI)
        s.configure("TFrame",      background=C["bg"])
        s.configure("TLabel",      background=C["bg"], foreground=C["text"])
        s.configure("TLabelframe", background=C["card"],
                    bordercolor=C["purple_dim"], relief="flat", padding=10)
        s.configure("TLabelframe.Label", background=C["card"],
                    foreground=C["purple"], font=FONT_UI_B)
        s.configure("TNotebook", background=C["card2"], borderwidth=0, tabmargins=0)
        s.configure("TNotebook.Tab", background=C["sep"], foreground=C["muted"],
                    font=FONT_UI_B, padding=(18, 10))
        s.map("TNotebook.Tab",
              background=[("selected", C["card"])],
              foreground=[("selected", C["text"])])
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
                    fieldbackground=C["card2"], rowheight=30, borderwidth=0)
        s.configure("Treeview.Heading", background=C["sep"],
                    foreground=C["text2"], font=FONT_UI_B, relief="flat")
        s.map("Treeview",
              background=[("selected", C["blue"])],
              foreground=[(_("selected"), _("#FFFFFF"))])
        s.configure("TScrollbar", background=C["sep"], troughcolor=C["card"],
                    arrowcolor=C["muted"], borderwidth=0)

        def _btn(name, bg, fg, hover, dis_bg=C["disabled"], dis_fg=C["muted"]):
            s.configure(name, background=bg, foreground=fg, borderwidth=0,
                        focusthickness=2, focuscolor=C["focus"],
                        padding=(12, 6), font=FONT_UI_B, relief="flat")
            s.map(name,
                  background=[("active", hover), ("disabled", dis_bg),
                               ("focus", bg)],
                  foreground=[("disabled", dis_fg)],
                  relief=[(_("focus"), _("solid"))])

        _btn("Primary.TButton",   C["indigo"], "#FFF", C["indigo_hover"])
        _btn("Danger.TButton",    C["red"],    "#FFF", C["red_hover"])
        _btn("Secondary.TButton", C["card2"],  C["text2"], C["card3"])
        _btn("Green.TButton",     C["green"],  "#FFF", C["green_hover"])
        _btn("Warn.TButton",      C["orange"], "#FFF", C["orange_hover"])
        _btn("Ghost.TButton",     C["card"],   C["cyan"], C["card2"])
        _btn("Purple.TButton",    C["purple"], "#FFF", C["purple_hover"])

    def _build_ui(self):
        hdr = tk.Frame(self.root, bg=C["card"], height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Icono + nombre
        brand = tk.Frame(hdr, bg=C["card"])
        brand.pack(side="left", padx=16, pady=10)
        tk.Label(brand, text=_("MASV"), bg=C["card"], fg=C["purple"],
                 font=(FONT_FAMILY, 18, "bold")).pack(side="left")
        tk.Label(brand, text=_("  Memexicanisimos Android Screen Viewer"),
                 bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="left", pady=(2, 0))

        right_hdr = tk.Frame(hdr, bg=C["card"])
        right_hdr.pack(side="right", padx=16)
        self._sess_count_lbl = tk.Label(right_hdr, text="", bg=C["card"],
                                        fg=C["green"], font=FONT_SM)
        self._sess_count_lbl.pack(side="right", padx=(8, 0))
        self._dep_lbl = tk.Label(right_hdr, text="", bg=C["card"],
                                 fg=C["muted"], font=FONT_SM)
        self._dep_lbl.pack(side="right")

        tk.Frame(self.root, bg=C["sep"], height=1).pack(fill="x")

        self._nb = ttk.Notebook(self.root)
        self._nb.pack(fill="both", expand=True, padx=8, pady=(4, 0))

        self._tab_actions  = tk.Frame(self._nb, bg=C["bg"])
        self._tab_controls = tk.Frame(self._nb, bg=C["bg"])
        self._tab_device   = tk.Frame(self._nb, bg=C["bg"])
        self._tab_profile  = tk.Frame(self._nb, bg=C["bg"])
        self._tab_console  = tk.Frame(self._nb, bg=C["bg"])
        self._tab_help     = tk.Frame(self._nb, bg=C["bg"])

        # Pestañas en orden lógico limpio: Acciones(0), Controles(1), Dispositivo(2), Perfiles(3), Consola(4), Ayuda(5)
        self._nb.add(self._tab_actions,  text=_("🚀  Acciones"))
        self._nb.add(self._tab_controls, text=_("🎮  Controles"))
        self._nb.add(self._tab_device,   text=_("📱  Dispositivo"))
        self._nb.add(self._tab_profile,  text=_("⚙️  Perfiles"))
        self._nb.add(self._tab_console,  text=_("🖥  Consola"))
        self._nb.add(self._tab_help,     text=_("❓  Ayuda"))

        self._simple_view = tk.Frame(self.root, bg=C["bg"])

        self.ui.build_tab_actions(self._tab_actions)
        self.ui.build_tab_controls(self._tab_controls)
        self.ui.build_tab_device(self._tab_device)
        self.ui.build_tab_profile(self._tab_profile)
        self.ui.build_tab_console(self._tab_console)
        self.ui.build_tab_help(self._tab_help)
        self.ui.build_simple_view(self._simple_view)

        bar = tk.Frame(self.root, bg=C["card2"], height=34)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self._status_lbl = tk.Label(bar, text=_("Iniciando…"), bg=C["card2"],

        self.is_advanced_view = True
        self.btn_toggle_view = tk.Button(bar, text="Cambiar a Vista Simple", bg=C["sep"], fg=C["text"],
                                     font=FONT_SM, relief="flat", bd=0, padx=12, pady=4,
                                     command=self._toggle_view)
        self.btn_toggle_view.pack(side="right", padx=14)
        self._status_lbl = tk.Label(bar, text="Iniciando…", bg=C["card2"],
                                    fg=C["muted"], font=FONT_SM, anchor="w")
        self._status_lbl.pack(side="left", padx=14, pady=4)

        # Language switcher
        from .i18n import get_language, set_language
        lang_btn = tk.Button(bar, text="🇺🇸" if get_language() == "es" else "🇲🇽",
                             bg=C["card2"], fg=C["text"], bd=0, relief="flat", cursor="hand2", font=FONT_SM)
        lang_btn.pack(side="right", padx=(4, 14), pady=4)

        def _toggle_language():
            new_lang = "en" if get_language() == "es" else "es"
            set_language(new_lang)
            self.ctx.cfg["language"] = new_lang
            save_config(self.ctx.cfg)
            messagebox.showinfo(_("Reinicio requerido"), _("Por favor, reinicia la aplicación para aplicar los cambios de idioma."))

        lang_btn.config(command=_toggle_language)

        tk.Label(bar, text=_("v1.1  |  Ctrl+H → Ayuda  |  Ctrl+Q → Salir"),
                 bg=C["card2"], fg=C["muted"], font=FONT_SM).pack(side="right", padx=4)

        self.ui.refs['profile_listbox'].bind("<<ListboxSelect>>", self._on_profile_listbox_sel)
        self._refresh_profile_listbox()

        self._nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self.ui.refs['profile_listbox'].bind("<<ListboxSelect>>", self._on_profile_listbox_sel)
        self._refresh_profile_listbox()

        self._nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _toggle_view(self):
        if self.is_advanced_view:
            self._nb.pack_forget()
            self._simple_view.pack(fill="both", expand=True, padx=8, pady=(4, 0))
            self.btn_toggle_view.config(text="Cambiar a Vista Avanzada")
            self.is_advanced_view = False
        else:
            self._simple_view.pack_forget()
            self._nb.pack(fill="both", expand=True, padx=8, pady=(4, 0))
            self.btn_toggle_view.config(text="Cambiar a Vista Simple")
            self.is_advanced_view = True

    def _set_status(self, msg: str, color: str = None):
        self._status_lbl.config(text=msg, fg=color or C["muted"])

    # ── Utils & Dependencies ──────────────────────────────────────────
    def _check_deps(self):
        missing = []
        if not self.ctx.adb:
            missing.append("adb")
        else:
            subprocess.Popen([self.ctx.adb, "start-server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.ctx.log("INFO", f"ADB   : {self.ctx.adb}")
        if not self.ctx.scrcpy:
            missing.append("scrcpy")
        else:
            self.ctx.log("INFO", f"scrcpy: {self.ctx.scrcpy}")

        if missing:
            self._dep_lbl.config(text=f"⚠  Falta: {', '.join(missing)}", fg=C["red"])
            self._set_status(f"⚠  Instala las dependencias: {', '.join(missing)}", C["red"])
            self.ui.refs['dep_frame'].pack_forget()
            self.ui.refs['install_frame'].pack(fill="both", expand=True, padx=20, pady=20)
        else:
            self._dep_lbl.config(text=_("✔  ADB + scrcpy OK"), fg=C["green"])
            self._set_status(_("✔  Dependencias OK. Conecta un dispositivo."), C["green"])
            self.ui.refs['install_frame'].pack_forget()
            self.ui.refs['dep_frame'].pack(fill="both", expand=True)
            self.root.after(700, self._check_v4l2)

    def _auto_install_deps(self):
        """Instala automáticamente scrcpy y adb sin requerir comandos manuales en la terminal."""
        import urllib.request, zipfile, shutil
        from .utils import APP_DIR, find_portable_binaries
        target_bin_dir = os.path.join(APP_DIR, "bin")
        os.makedirs(target_bin_dir, exist_ok=True)

        Toast(self.root, _("Iniciando descarga e instalación automática de scrcpy..."), "info", duration=5000)

        def task():
            try:
                if _PLAT == "win32":
                    r = subprocess.run(["winget", "install", "Genymobile.scrcpy", "--silent", "--accept-source-agreements", "--accept-package-agreements"], capture_output=True, text=True)
                    if r.returncode != 0:
                        url = "https://github.com/Genymobile/scrcpy/releases/download/v2.4/scrcpy-win64-v2.4.zip"
                        zip_path = os.path.join(APP_DIR, "scrcpy_temp.zip")
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
                    self.ctx.adb = adb_path
                    self.ctx.scrcpy = scrcpy_path
                    self.root.after(0, self._on_deps_installed_success)
                else:
                    self.root.after(0, lambda: Toast(self.root, _("No se pudo completar la instalación automática."), "error"))
            except Exception as e:
                self.root.after(0, lambda: Toast(self.root, f"Error en instalación: {e}", "error"))

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
        self._set_status(_("🔄  Escaneando dispositivos ADB…"), C["cyan"])
        self.ctx.device_mgr.scan_devices(self._update_devs_ui, self.ctx.log)

    def _update_devs_ui(self, found: list):
        listbox = self.ui.refs['dev_listbox']
        listbox.delete(0, tk.END)
        for serial, model, state in found:
            if state == "ok":
                listbox.insert(tk.END, f"  🟢  {model}  ({serial})")
            elif state == "unauth":
                listbox.insert(tk.END, f"  🟠  {model}  ({serial})")
            else:
                listbox.insert(tk.END, f"  ⚫  {model}  ({serial})")

        simple_combo = self.ui.refs.get('simple_dev_combo')
        if simple_combo:
            simple_combo['values'] = [f"{model} ({serial})" for serial, model, state in found]

        if found:
            listbox.selection_set(0)
            self._on_dev_select()
            self.ui.refs['scan_lbl'].config(text=f"{len(found)} dispositivo(s)", fg=C["green"])
            self._set_status(f"✔  {len(found)} dispositivo(s) detectado(s).", C["green"])
        else:
            self.ctx.active_device_serial = None
            self.ctx.active_device.set("Sin dispositivo")
            self.ui.refs['dev_info_lbl'].config(text=_("Sin dispositivos. Conecta un cable USB o activa ADB WiFi."), fg=C["orange"])
            self.ui.refs['scan_lbl'].config(text=_("Sin dispositivos"), fg=C["orange"])
            self._set_status(_("Sin dispositivos. Conecta un cable USB y activa la Depuración USB."), C["orange"])
            if simple_combo:
                simple_combo.set("Sin dispositivo")
            self.ui.refs['dev_info_lbl'].config(text="Sin dispositivos. Conecta un cable USB o activa ADB WiFi.", fg=C["orange"])
            self.ui.refs['scan_lbl'].config(text="Sin dispositivos", fg=C["orange"])
            self._set_status("Sin dispositivos. Conecta un cable USB y activa la Depuración USB.", C["orange"])

    def _on_dev_select(self, event=None):
        if event and event.widget == self.ui.refs.get('simple_dev_combo'):
            raw = self.ui.refs['simple_dev_combo'].get()
            if not raw or raw == "Sin dispositivo": return
            serial = _extract_serial(raw)
            model = raw.split(" (")[0].strip()
        else:
            listbox = self.ui.refs['dev_listbox']
            sel = listbox.curselection()
            if not sel:
                return
            raw = listbox.get(sel[0])
            serial = _extract_serial(raw)
            model = raw.strip().lstrip("🟢🟠⚫ ").split("  (")[0].strip()

        self.ctx.select_device(serial, f"{model} ({serial})")

        state = next((s for sr, mo, s in self.ctx.device_mgr.devices if sr == serial), "other")
        if state == "unauth":
            self.ui.refs['dev_info_lbl'].config(text=f"🟠  {serial}  —  ¡Acepta el permiso de depuración en la pantalla del teléfono!", fg=C["orange"])
            self._set_status(_("⚠  Dispositivo no autorizado. Acepta el diálogo en el teléfono."), C["orange"])
        elif state == "ok":
            self.ui.refs['dev_info_lbl'].config(text=f"🟢  {model}  ({serial})  —  Conectado y autorizado.", fg=C["green"])
            self._set_status(f"✔  {model}  —  {serial}", C["green"])
            assoc = self.ctx.cfg.get("device_associations", {}).get(serial)
            if assoc and assoc in self.ctx.profile_mgr.get_profiles():
                self.ctx.active_profile.set(assoc)
                self.ui.refs['assoc_lbl'].config(text=f"↳  Perfil '{assoc}' cargado automáticamente para este dispositivo.", fg=C["muted"])
        
        self._on_tab_changed()

    def _connect_wifi(self):
        ip_raw   = self.ui.refs['ip_entry'].get().strip()
        port_raw = self.ui.refs['port_entry'].get().strip() or "5555"
        parsed   = parse_ip_port(f"{ip_raw}:{port_raw}")
        if not parsed:
            messagebox.showerror("IP inválida", f"'{ip_raw}:{port_raw}' no es válida.\nEjemplo: 192.168.1.25:5555")
            return
        ip, port = parsed
        target   = f"{ip}:{port}"
        self.ctx.log("ADB", f"Conectando a {target}…")
        self._set_status(f"Conectando a {target}…", C["cyan"])
        def task():
            try:
                r = subprocess.run([self.ctx.adb, "connect", target], capture_output=True, text=True, timeout=8)
                self.ctx.log("ADB", r.stdout.strip())
                self.root.after(800, self._refresh_devices)
            except Exception as e:
                self.ctx.log("ERROR", f"WiFi: {e}")
        threading.Thread(target=task, daemon=True).start()

    def _enable_tcpip(self):
        serial = self.ctx.active_device_serial
        if not serial or not self.ctx.adb:
            messagebox.showerror(_("Error"), _("Selecciona un dispositivo USB primero."))
            return
        self.ctx.log("ADB", f"[{serial}] TCP/IP 5555…")
        def task():
            try:
                r = subprocess.run([self.ctx.adb, "-s", serial, "tcpip", "5555"],
                                   capture_output=True, text=True, timeout=8)
                self.ctx.log("ADB", r.stdout.strip())
                self.ctx.log(_("OK"), _("Puerto 5555 abierto. Desconecta el cable."))
                self.root.after(0, lambda: messagebox.showinfo(
                    "TCP/IP habilitado",
                    f"Dispositivo {serial} listo en el puerto 5555.\n"
                    f"Desconecta el cable USB y conecta por IP."))
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
        self._set_status(_("Obteniendo IP del dispositivo…"), C["cyan"])
        def task():
            ip = None
            try:
                # Método 1: ip route (funciona en la mayoría de romés)
                r = subprocess.run(
                    [self.ctx.adb, "-s", serial, "shell", "ip route"],
                    capture_output=True, text=True, timeout=8)
                for line in r.stdout.splitlines():
                    m = re.search(r"src (\d+\.\d+\.\d+\.\d+)", line)
                    if m:
                        ip = m.group(1)
                        break
                # Método 2: ifconfig wlan0
                if not ip:
                    r2 = subprocess.run(
                        [self.ctx.adb, "-s", serial, "shell", "ifconfig", "wlan0"],
                        capture_output=True, text=True, timeout=8)
                    m2 = re.search(r"inet addr:(\d+\.\d+\.\d+\.\d+)", r2.stdout)
                    if not m2:
                        m2 = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", r2.stdout)
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
                    self._set_status(f"IP detectada: {ip}", C["green"])
                    Toast(self.root, f"IP del dispositivo: {ip}", "success")
                else:
                    self._set_status(_("No se detectó IP WiFi."), C["orange"])
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
        """Envía un keyevent de control remoto al dispositivo activo vía ADB."""
        serial = self.ctx.active_device_serial
        if not serial or not self.ctx.adb:
            messagebox.showwarning(_("Sin dispositivo"), _("Selecciona un dispositivo activo en la lista primero."))
            return
        def task():
            try:
                if code == "notifications":
                    subprocess.run([self.ctx.adb, "-s", serial, "shell", "cmd", "statusbar", "expand-notifications"], capture_output=True, timeout=5)
                elif code == "paste_text":
                    try:
                        text = self.root.clipboard_get()
                        if text:
                            # Use input text for pasting. Simple quote escaping.
                            escaped_text = text.replace("'", "'\\''")
                            subprocess.run([self.ctx.adb, "-s", serial, "shell", "input", "text", f"'{escaped_text}'"], capture_output=True, timeout=5)
                    except tk.TclError:
                        pass # Clipboard empty
                elif code == "screen_on":
                    subprocess.run([self.ctx.adb, "-s", serial, "shell", "input", "keyevent", "224"], capture_output=True, timeout=5)
                elif code == "screen_off":
                    subprocess.run([self.ctx.adb, "-s", serial, "shell", "input", "keyevent", "223"], capture_output=True, timeout=5)
                else:
                    subprocess.run([self.ctx.adb, "-s", serial, "shell", "input", "keyevent", str(code)], capture_output=True, timeout=5)
            except Exception as e:
                self.ctx.log("ERROR", f"Keyevent {code}: {e}")
        threading.Thread(target=task, daemon=True).start()

    def _install_apk(self):
        """Abre un diálogo para seleccionar un APK e instalarlo vía ADB."""
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
        self.ctx.log("ADB", f"[{serial}] Instalando APK: {apk_name}…")
        self._set_status(f"Instalando {apk_name}…", C["cyan"])
        Toast(self.root, f"Instalando {apk_name}...", "info")
        def task():
            try:
                res = subprocess.run([self.ctx.adb, "-s", serial, "install", "-r", apk_path], capture_output=True, text=True, timeout=120)
                output = (res.stdout or "") + (res.stderr or "")
                if "Success" in output:
                    self.ctx.log("OK", f"[{serial}] Instalación exitosa: {apk_name}")
                    self.root.after(0, lambda: [
                        self._set_status(f"✔ APK instalada: {apk_name}", C["green"]),
                        Toast(self.root, f"✔ APK instalada con éxito: {apk_name}", "success")
                    ])
                else:
                    self.ctx.log("ERROR", f"[{serial}] Error al instalar {apk_name}: {output.strip()}")
                    self.root.after(0, lambda: [
                        self._set_status(f"❌ Error al instalar APK", C["red"]),
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

    def _route_cam(self):
        serial = self.ctx.active_device_serial
        if not serial or not self.ctx.scrcpy:
            messagebox.showerror("Error","Selecciona un dispositivo activo.")
            return
        p = self.ctx.profile_mgr.get_profiles().get(self.ctx.active_profile.get(), {})
        camid = p.get("camera_id","0")
        cmd = [self.ctx.scrcpy,"-s",serial, "--video-source=camera","--camera-id",camid, "--v4l2-sink=/dev/video9","--no-playback"]
        self.ctx.log("INFO",f"[{serial}] Enrutando cámara:\n  {' '.join(cmd)}")
        try:
            kw = {}
            if _PLAT != "win32":
                kw["preexec_fn"] = os.setsid
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, **kw)
            # Create a simple session wrapping logic directly, as this uses standard session management code:
            from .managers import ScrcpySession
            sess = ScrcpySession(serial, "Webcam Loopback", proc)
            self.ctx.session_mgr.sessions[serial + "_cam"] = sess
            self._refresh_table()
            
            # Simple stream reader since it's an ad-hoc process:
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
            self.ctx.log("ERROR",f"Enrutar cámara: {e}")

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

    def _on_profile_listbox_sel(self, _=None):
        listbox = self.ui.refs['profile_listbox']
        sel = listbox.curselection()
        if not sel: return
        raw = listbox.get(sel[0]).strip()
        profiles = self.ctx.profile_mgr.get_profiles()
        if raw not in profiles: return
        p = profiles[raw]
        lines = [
            f"Perfil       : {raw}",
            f"Bitrate      : {p.get('bitrate','?')}",
            f"Resolución   : {p.get('max_size','?')}p",
            f"FPS máx      : {p.get('max_fps','?')}",
            f"Códec        : {p.get('video_codec','?')}",
            f"Audio        : {p.get('audio_source','?')}",
            f"Cámara ID    : {p.get('camera_id','0')}",
            f"Pantalla off : {'Sí' if p.get('turn_screen_off') else 'No'}",
            f"Despierto    : {'Sí' if p.get('stay_awake') else 'No'}",
            f"Keyevent EMUI: {'Sí' if p.get('force_screen_off_keyevent') else 'No'}",
            f"Args extra   : {p.get('extra_args','ninguno')}"
        ]
        if 'profile_chips' in self.ui.refs:
            self.ui.refs['profile_chips'].set_profile(raw, p)
        self.ctx.active_profile.set(raw)
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
            self.ctx.log("OK", f"Perfil '{name}' creado desde el asistente.")
            Toast(self.root, f"Perfil '{name}' creado correctamente.", "success")
        from .ui_widgets import ProfileWizard
        ProfileWizard(self.root, on_save)

    def _start_profile(self):
        """Selecciona el perfil resaltado e inicia la transmisión inmediatamente."""
        listbox = self.ui.refs.get('profile_listbox')
        if not listbox: return
        sel = listbox.curselection()
        if not sel:
            messagebox.showwarning(_("Seleccionar perfil"), _("Selecciona un perfil en la lista primero."))
            return
        name = listbox.get(sel[0]).strip()
        
        if not self.ctx.active_device_serial:
            Toast(self.root, _("Selecciona un dispositivo en la pestaña Dispositivo."), "warning")
            self._nb.select(2)  # Pestaña Dispositivo (índice 2)
            return

        self._on_profile_listbox_sel()
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
            self.ctx.log("INFO", f"Perfil '{name}' eliminado.")

    def _on_active_profile_change(self, _=None):
        self.ctx.save_current_config()
        self._set_status(f"Perfil activo: {self.ctx.active_profile.get()}", C["cyan"])

    # ── Actions Tab ───────────────────────────────────────────────────
    def _toggle_scene(self):
        serial = self.ctx.active_device_serial
        if not serial:
            messagebox.showerror(_("Sin dispositivo"), _("Selecciona un dispositivo en la pestaña Dispositivo."))
            self._nb.select(2) # Fallback to device tab which is index 2 now
            return
        if serial in self.ctx.session_mgr.sessions:
            self._stop_current()
        else:
            profile_name = self.ctx.active_profile.get()
            profile_data = dict(self.ctx.cfg["profiles"].get(profile_name, {}))

            # Incorporar argumentos adicionales si estamos en Vista Simple
            if hasattr(self, 'is_advanced_view') and not self.is_advanced_view:
                extra_var = self.ui.refs.get('simple_extra_cmd_var')
                if extra_var and extra_var.get().strip():
                    existing_args = profile_data.get("extra_args", "")
                    profile_data["extra_args"] = f"{existing_args} {extra_var.get().strip()}".strip()

            self._set_status(f"Iniciando sesión: {profile_name}...", C["green"])
            
            if profile_data.get("force_screen_off_keyevent") or (profile_data.get("audio_source") == "mic" and "--no-video" in profile_data.get("extra_args", "")):
                self.ctx.log("ADB", f"[{serial}] keyevent 26…")
                subprocess.Popen([self.ctx.adb,"-s",serial,"shell","input","keyevent","26"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(0.3)

            def on_started():
                self._refresh_table()
                self._nb.select(1) # Select Actions tab

            self.ctx.session_mgr.start_scene(serial, profile_name, profile_data, on_started)

    def _stop_current(self):
        serial = self.ctx.active_device_serial
        if not serial or serial not in self.ctx.session_mgr.sessions:
            messagebox.showinfo(_("Sin sesión"), _("No hay ninguna sesión activa para el dispositivo seleccionado."))
            return
        self.ctx.session_mgr.stop_session(serial)
        self._refresh_table()
        self._set_status(_("Sesión detenida."), C["muted"])

    def _panic_kill(self):
        if not self.ctx.session_mgr.sessions:
            messagebox.showinfo(_("Sin sesiones"), _("No hay sesiones activas."))
            return
        if messagebox.askyesno(_("Confirmar"), _("¿Cerrar TODAS las sesiones de scrcpy?")):
            self.ctx.session_mgr.stop_all()
            self._refresh_table()
            self.ctx.log(_("WARNING"), _("Pánico: todas las sesiones cerradas."))
            self._set_status(_("Todas las sesiones cerradas."), C["orange"])

    def _restart_adb(self):
        if not self.ctx.adb: return
        self.ctx.log(_("ADB"), _("Reiniciando servidor ADB…"))
        self._set_status(_("Reiniciando ADB…"), C["cyan"])
        def task():
            subprocess.run([self.ctx.adb, "kill-server"], capture_output=True)
            time.sleep(0.5)
            subprocess.run([self.ctx.adb, "start-server"], capture_output=True)
            self.ctx.log(_("OK"), _("Servidor ADB reiniciado."))
            self.root.after(600, self._refresh_devices)
        threading.Thread(target=task, daemon=True).start()

    def _stop_selected(self):
        tree = self.ui.refs['sess_tree']
        sel = tree.selection()
        if not sel:
            messagebox.showwarning(_("Atención"), _("Selecciona una sesión en la tabla."))
            return
        serial = tree.item(sel[0], "values")[0]
        self.ctx.session_mgr.stop_session(serial)
        self._refresh_table()
        self.ctx.log("INFO", f"[{serial}] Sesión detenida.")

    def _on_tab_changed(self, _=None):
        if self.ctx.active_device_serial:
            self.ui.refs['action_device_lbl'].config(text=f"📱  {self.ctx.active_device_serial}", fg=C["text"])
        else:
            self.ui.refs['action_device_lbl'].config(text=_("📱  Sin dispositivo seleccionado"), fg=C["muted"])
        self.ui.refs['action_profile_lbl'].config(text=f"⚙️  {self.ctx.active_profile.get()}", fg=C["cyan"])

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
                self.root.after(0, lambda: self._set_status(
                    f"Sesión finalizada: {sess.profile_name}", C["orange"]))
        if dead or sessions:
            self._refresh_table()
        self.root.after(2000, self._monitor_sessions)

    def _stop_selected(self, _=None):
        """Detiene la sesión seleccionada en la tabla (o invocada por atajo Supr)."""
        tree = self.ui.refs['sess_tree']
        sel  = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], 'values')
        if not vals:
            return
        serial = str(vals[0])
        self.ctx.session_mgr.stop(serial)
        self.ctx.log("INFO", f"[{serial}] Sesión detenida por el usuario.")
        self._refresh_table()
        self._set_status(f"Sesión detenida: {serial}", C["orange"])

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
        menu.add_command(label=f"■  Detener sesión (Supr)",
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
        sess = self.ctx.session_mgr.sessions.get(serial)
        if not sess:
            return
        p = self.ctx.profile_mgr.get_profiles().get(sess.profile_name, {})
        cmd = self.ctx.session_mgr._build_cmd(self.ctx.scrcpy, serial, p)
        self.root.clipboard_clear()
        self.root.clipboard_append(" ".join(cmd))
        Toast(self.root, _("Comando copiado al portapapeles"), "success")

    def _force_kill_sess(self, serial: str):
        sess = self.ctx.session_mgr.sessions.get(serial)
        if sess:
            try: sess.process.kill()
            except Exception: pass
            self.ctx.session_mgr.sessions.pop(serial, None)
            self._refresh_table()
            self._set_status(f"Proceso forzado a cerrar: {serial}", C["red"])
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

        ico_l  = tk.Label(win, text="", bg=C["bg"], font=(FONT_FAMILY, 42))
        ico_l.pack(pady=(28, 6))
        title_l = tk.Label(win, text="", bg=C["bg"], fg=C["purple"], font=(FONT_FAMILY, 15, "bold"))
        title_l.pack()
        body_l  = tk.Label(win, text="", bg=C["bg"], fg=C["text2"], font=FONT_UI,
                           justify="center", wraplength=400)
        body_l.pack(pady=(10, 20), padx=30)

        prog_f = tk.Frame(win, bg=C["bg"])
        prog_f.pack()
        dots = []
        for _ in range(len(steps)):
            d = tk.Label(prog_f, text=_("●"), bg=C["bg"], fg=C["sep"], font=(FONT_FAMILY, 8))
            d.pack(side="left", padx=3)
            dots.append(d)

        nav = tk.Frame(win, bg=C["card2"])
        nav.pack(fill="x", side="bottom", pady=(20, 0))
        skip_btn = tk.Button(nav, text=_("Omitir"), bg=C["card2"], fg=C["muted"],
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

    def _exit(self):
        self.ctx.session_mgr.stop_all()
        try: self.root.destroy()
        except Exception: pass
        sys.exit(0)

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

def main():
    single_inst = SingleInstance()
    if not single_inst.acquire():
        messagebox.showwarning("MASV",
                               "La aplicación ya está en ejecución.\nBusca el icono en la bandeja del sistema.")
        sys.exit(1)

    root = tk.Tk()
    app  = ScrcpyDockApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
