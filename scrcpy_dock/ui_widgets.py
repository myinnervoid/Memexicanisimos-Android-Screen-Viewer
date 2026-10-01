import sys
import tkinter as tk
from .i18n import _
from tkinter import ttk, messagebox
from .utils import C, FONT_FAMILY, FONT_UI, FONT_UI_B, FONT_SM, FONT_LG, FONT_MONO, FONT_CARD

# ─────────────────────────────────────────────────────────────────────────────
# Helpers de layout (usan tokens del sistema Warm Modern)
# ─────────────────────────────────────────────────────────────────────────────

def _row(parent, bg=None, pady=3, padx=4) -> tk.Frame:
    f = tk.Frame(parent, bg=bg or C["card"])
    f.pack(fill="x", padx=padx, pady=pady)
    return f

def _sep(parent, color=None):
    tk.Frame(parent, bg=color or C["sep"], height=1).pack(fill="x", padx=12, pady=4)

def _section(parent, title: str, pady=(5, 5), padx=12) -> tk.Frame:
    """Crea un contenedor moderno con borde sutil de 1px y encabezado integrado sin bordes biselados retro."""
    outer = tk.Frame(parent, bg=C["card_border"], padx=1, pady=1)
    outer.pack(fill="x", padx=padx, pady=pady)
    
    card = tk.Frame(outer, bg=C["card"], padx=12, pady=8)
    card.pack(fill="both", expand=True)

    if title:
        hdr = tk.Frame(card, bg=C["card"])
        hdr.pack(fill="x", pady=(0, 6))
        tk.Label(hdr, text=title, font=FONT_UI_B, bg=C["card"], fg=C["indigo"]).pack(side="left")
    return card

def _recolor(frame: tk.Frame, color: str):
    for child in frame.winfo_children():
        try: child.config(bg=color)
        except Exception: pass
        if isinstance(child, tk.Frame):
            _recolor(child, color)

def bind_mousewheel(widget, canvas):
    """Enlaza el desplazamiento suave con la rueda del ratón de forma recursiva a un canvas."""
    def _on_mousewheel(event):
        try:
            if sys.platform == "darwin":
                canvas.yview_scroll(int(-1 * event.delta), "units")
            elif sys.platform == "win32":
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                if event.num == 4:
                    canvas.yview_scroll(-2, "units")
                elif event.num == 5:
                    canvas.yview_scroll(2, "units")
                elif hasattr(event, 'delta') and event.delta:
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    if sys.platform == "linux":
        widget.bind("<Button-4>", _on_mousewheel, add="+")
        widget.bind("<Button-5>", _on_mousewheel, add="+")
    else:
        widget.bind("<MouseWheel>", _on_mousewheel, add="+")

    for child in widget.winfo_children():
        bind_mousewheel(child, canvas)


# ─────────────────────────────────────────────────────────────────────────────
# Barra de Navegación por Pastillas (Pill Navigation Bar)
# ─────────────────────────────────────────────────────────────────────────────

class PillNavBar(tk.Frame):
    """Barra de navegación horizontal con pastillas estilizadas y transiciones de color modernas."""
    def __init__(self, parent, tabs_data: list, on_select_cb, bg=None):
        super().__init__(parent, bg=bg or C["bg"], pady=4, padx=8)
        self.tabs_data = tabs_data
        self.on_select_cb = on_select_cb
        self.buttons = {}
        self.active_id = None
        self._build_pills()

    def _build_pills(self):
        # Contenedor con borde fino de 1px
        outer = tk.Frame(self, bg=C["card_border"], padx=1, pady=1)
        outer.pack(fill="x")

        container = tk.Frame(outer, bg=C["pill_bg"], padx=3, pady=3)
        container.pack(fill="x")

        for idx, (tab_id, label, shortcut) in enumerate(self.tabs_data):
            btn = tk.Button(
                container, text=label, font=FONT_UI_B,
                bg=C["pill_btn"], fg=C["pill_text"],
                activebackground=C["pill_hover"], activeforeground=C["text"],
                relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
                command=lambda tid=tab_id, i=idx: self.select(tid, i)
            )
            btn.pack(side="left", padx=2, fill="x", expand=True)
            self.buttons[tab_id] = btn

            def _on_enter(e, b=btn, tid=tab_id):
                if self.active_id != tid:
                    b.config(bg=C["pill_hover"], fg=C["text"])
            def _on_leave(e, b=btn, tid=tab_id):
                if self.active_id != tid:
                    b.config(bg=C["pill_btn"], fg=C["pill_text"])
            btn.bind("<Enter>", _on_enter)
            btn.bind("<Leave>", _on_leave)

# ─────────────────────────────────────────────────────────────────────────────
# Barra Lateral de Navegación Estilo Dashboard con Menú Hamburguesa
# ─────────────────────────────────────────────────────────────────────────────

class DashboardSidebar(tk.Frame):
    """Barra lateral de navegación estilo Dashboard con menú hamburguesa colapsable."""
    def __init__(self, parent, nav_items: list, on_select_cb, bg=None):
        super().__init__(parent, bg=bg or C["card"], width=210)
        self.nav_items = nav_items  # list of (id, icon, label, shortcut)
        self.on_select_cb = on_select_cb
        self.is_collapsed = False
        self.buttons = {}
        self.active_id = None
        self.pack_propagate(False)
        self._build_sidebar()

    def _build_sidebar(self):
        # ── Header de Barra Lateral (Logo + Hamburguesa) ───────────
        top_bar = tk.Frame(self, bg=C["card"], height=48)
        top_bar.pack(fill="x", padx=6, pady=(6, 2))
        top_bar.pack_propagate(False)

        self.btn_toggle = tk.Button(
            top_bar, text="☰", font=(FONT_FAMILY, 12, "bold"),
            bg=C["card2"], fg=C["text"], activebackground=C["card3"], activeforeground="#FFF",
            relief="flat", bd=0, width=3, pady=2, cursor="hand2",
            command=self.toggle_collapse
        )
        self.btn_toggle.pack(side="left")
        Tooltip(self.btn_toggle, "Colapsar / Expandir menú lateral (Ctrl+B)")

        self.lbl_title = tk.Label(
            top_bar, text=" MASV Dashboard", font=(FONT_FAMILY, 12, "bold"),
            bg=C["card"], fg=C["indigo"], anchor="w"
        )
        self.lbl_title.pack(side="left", padx=4, fill="x", expand=True)

        tk.Frame(self, bg=C["card_border"], height=1).pack(fill="x", padx=6, pady=4)

        # ── Lista de Ítems de Navegación ───────────────────────────
        self.nav_container = tk.Frame(self, bg=C["card"])
        self.nav_container.pack(fill="both", expand=True, padx=6, pady=4)

        for idx, (item_id, icon, label, shortcut) in enumerate(self.nav_items):
            btn = tk.Button(
                self.nav_container, text=f" {icon}  {label}", font=FONT_UI_B,
                bg=C["pill_btn"], fg=C["pill_text"],
                activebackground=C["pill_hover"], activeforeground=C["text"],
                relief="flat", bd=0, anchor="w", padx=10, pady=7, cursor="hand2",
                command=lambda tid=item_id, i=idx: self.select(tid, i)
            )
            btn.pack(fill="x", pady=2)
            self.buttons[item_id] = (btn, icon, label)

            def _on_enter(e, b=btn, tid=item_id):
                if self.active_id != tid:
                    b.config(bg=C["pill_hover"], fg=C["text"])
            def _on_leave(e, b=btn, tid=item_id):
                if self.active_id != tid:
                    b.config(bg=C["pill_btn"], fg=C["pill_text"])
            btn.bind("<Enter>", _on_enter)
            btn.bind("<Leave>", _on_leave)

            if shortcut:
                Tooltip(btn, f"{label} ({shortcut})")

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.config(width=54)
            self.lbl_title.pack_forget()
            for tid, (btn, icon, label) in self.buttons.items():
                btn.config(text=f" {icon} ", anchor="center", padx=2)
        else:
            self.config(width=210)
            self.lbl_title.pack(side="left", padx=4, fill="x", expand=True)
            for tid, (btn, icon, label) in self.buttons.items():
                btn.config(text=f" {icon}  {label}", anchor="w", padx=10)

    def select(self, item_id, idx=None):
        self.active_id = item_id
        for tid, (btn, icon, label) in self.buttons.items():
            if tid == item_id:
                btn.config(bg=C["pill_active"], fg=C["pill_text_act"])
            else:
                btn.config(bg=C["pill_btn"], fg=C["pill_text"])
        if self.on_select_cb:
            self.on_select_cb(item_id, idx)


# ─────────────────────────────────────────────────────────────────────────────
# Tooltip con soporte para atajo de teclado
# ─────────────────────────────────────────────────────────────────────────────

class Tooltip:
    """Tooltip flotante que muestra texto de ayuda y, opcionalmente, un atajo de teclado."""
    def __init__(self, widget, text: str, shortcut: str = "", delay: int = 650):
        self._w        = widget
        self._text     = text
        self._shortcut = shortcut
        self._delay    = delay
        self._id       = None
        self._win      = None
        widget.bind("<Enter>",       self._schedule)
        widget.bind("<Leave>",       self._cancel)
        widget.bind("<ButtonPress>", self._cancel)

    def _schedule(self, _=None):
        self._cancel()
        self._id = self._w.after(self._delay, self._show)

    def _cancel(self, _=None):
        if self._id:
            self._w.after_cancel(self._id)
            self._id = None
        if self._win:
            self._win.destroy()
            self._win = None

    def _show(self):
        x = self._w.winfo_rootx() + 10
        y = self._w.winfo_rooty() + self._w.winfo_height() + 4
        self._win = tk.Toplevel(self._w)
        self._win.wm_overrideredirect(True)
        self._win.wm_geometry(f"+{x}+{y}")
        self._win.configure(bg=C["card2"])
        body = self._text
        if self._shortcut:
            body += f"\n  ⌨  {self._shortcut}"
        tk.Label(self._win, text=body, justify="left", bg=C["card2"],
                 fg=C["text"], font=FONT_SM, padx=10, pady=7,
                 wraplength=280).pack()


# ─────────────────────────────────────────────────────────────────────────────
# Tarjeta de acción estilizada (Alta legibilidad y contraste WCAG AAA)
# ─────────────────────────────────────────────────────────────────────────────

def _card_button(parent, icon_text: str, title: str, desc: str,
                 command, accent_color: str, hover_color: str,
                 row: int, col: int, shortcut: str = ""):
    """Tarjeta de acción elegante con fondo Slate oscuro, borde de acento y texto de alto contraste."""
    outer = tk.Frame(parent, bg=C["sep"], padx=1, pady=1)
    outer.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

    bg_color = C["card"]
    inner = tk.Frame(outer, bg=bg_color, cursor="hand2")
    inner.pack(fill="both", expand=True)

    # Indicador superior sutil de color de acento
    accent_bar = tk.Frame(inner, bg=accent_color, height=3)
    accent_bar.pack(fill="x", side="top")

    top_row = tk.Frame(inner, bg=bg_color)
    top_row.pack(pady=(12, 4), padx=10)
    tk.Label(top_row, text=icon_text, font=(FONT_FAMILY, 18, "bold"),
             bg=bg_color, fg=accent_color).pack(side="left", padx=(0, 6))
    tk.Label(top_row, text=title, font=FONT_UI_B,
             bg=bg_color, fg=C["text"]).pack(side="left")

    tk.Label(inner, text=desc, font=FONT_SM, wraplength=140,
             bg=bg_color, fg=C["text2"], justify="center"
             ).pack(pady=(0, 12), padx=10)

    def enter(_):
        inner.config(bg=C["card2"])
        _recolor(inner, C["card2"])
        accent_bar.config(bg=hover_color)
    def leave(_):
        inner.config(bg=bg_color)
        _recolor(inner, bg_color)
        accent_bar.config(bg=accent_color)
    def click(_): command()

    for w in [inner] + inner.winfo_children():
        if w is accent_bar: continue
        w.bind("<Enter>", enter)
        w.bind("<Leave>", leave)
        w.bind("<Button-1>", click)
        if isinstance(w, tk.Frame):
            for sub in w.winfo_children():
                sub.bind("<Enter>", enter)
                sub.bind("<Leave>", leave)
                sub.bind("<Button-1>", click)

    if shortcut or desc:
        Tooltip(inner, desc, shortcut=shortcut)

    return inner


# ─────────────────────────────────────────────────────────────────────────────
# Chip de comando copiable (para FAQ y ayuda contextual)
# ─────────────────────────────────────────────────────────────────────────────

def _cmd_chip(parent, cmd: str, root: tk.Tk = None) -> tk.Frame:
    """Chip oscuro con texto de comando copiable de un solo clic."""
    chip = tk.Frame(parent, bg=C["card2"], padx=10, pady=5,
                    highlightbackground=C["sep"], highlightthickness=1)
    chip.pack(fill="x", padx=20, pady=4)

    tk.Label(chip, text=cmd, bg=C["card2"], fg=C["cyan"],
             font=FONT_MONO, anchor="w").pack(side="left", fill="x", expand=True)

    def copy(_=None):
        target = root or chip
        target.clipboard_clear()
        target.clipboard_append(cmd)
        copy_btn.config(text=_("✔ Copiado"), fg=C["green"])
        chip.after(2000, lambda: copy_btn.config(text=_("📋 Copiar"), fg=C["muted"]))

    copy_btn = tk.Label(chip, text=_("📋 Copiar"), bg=C["card2"], fg=C["muted"],
                        font=FONT_SM, cursor="hand2")
    copy_btn.pack(side="right", padx=4)
    copy_btn.bind("<Button-1>", copy)
    return chip


# ─────────────────────────────────────────────────────────────────────────────
# AccordionItem — FAQ expandible con animación suave
# ─────────────────────────────────────────────────────────────────────────────

class AccordionItem(tk.Frame):
    """
    Elemento de FAQ acordeón con apertura/cierre fluido y scroll sincronizado.
    """
    def __init__(self, parent, title: str, build_fn, canvas_ref=None, **kw):
        super().__init__(parent, bg=C["card"], **kw)
        self._title      = title
        self._expanded   = False
        self._canvas_ref = canvas_ref

        # ── Header ────────────────────────────────────────────────────
        self._hdr = tk.Frame(self, bg=C["card2"], cursor="hand2")
        self._hdr.pack(fill="x")

        self._arrow = tk.Label(self._hdr, text="▶", bg=C["card2"],
                               fg=C["purple"], font=FONT_UI_B, width=2)
        self._arrow.pack(side="left", padx=(12, 4), pady=10)

        tk.Label(self._hdr, text=title, bg=C["card2"], fg=C["text"],
                 font=FONT_UI_B, anchor="w").pack(side="left", fill="x",
                                                   expand=True, pady=10)

        tk.Frame(self, bg=C["sep"], height=1).pack(fill="x")

        # ── Contenido ─────────────────────────────────────────────────
        self._content_outer = tk.Frame(self, bg=C["bg"])
        self._content_inner = tk.Frame(self._content_outer, bg=C["bg"])
        self._content_inner.pack(fill="both", padx=10, pady=(8, 12))

        # Construir widgets del contenido
        if callable(build_fn):
            build_fn(self._content_inner)
        elif isinstance(build_fn, str):
            tk.Label(self._content_inner, text=build_fn, bg=C["bg"], fg=C["text2"],
                     font=FONT_SM, justify="left", wraplength=700).pack(anchor="w", padx=4, pady=4)

        # Bindings de toggle sin duplicar referencias a self._arrow
        target_widgets = {self._hdr} | set(self._hdr.winfo_children())
        for w in target_widgets:
            w.bind("<Button-1>", self._toggle)
            w.bind("<Return>",   self._toggle)

        # Hover del header
        def enter(_):
            self._hdr.config(bg=C["card3"])
            for c in self._hdr.winfo_children():
                if hasattr(c, 'config'): c.config(bg=C["card3"])
        def leave(_):
            self._hdr.config(bg=C["card2"])
            for c in self._hdr.winfo_children():
                if hasattr(c, 'config'): c.config(bg=C["card2"])

        self._hdr.bind("<Enter>", enter)
        self._hdr.bind("<Leave>", leave)

        if self._canvas_ref:
            bind_mousewheel(self, self._canvas_ref)

        tk.Frame(self, bg=C["sep"], height=1).pack(fill="x")

    def _toggle(self, event=None):
        if self._expanded:
            self._content_outer.pack_forget()
            self._arrow.config(text="▶")
            self._expanded = False
        else:
            self._content_outer.pack(fill="x")
            self._arrow.config(text="▼")
            self._expanded = True
        self.update_idletasks()
        if self._canvas_ref:
            try:
                self._canvas_ref.configure(scrollregion=self._canvas_ref.bbox("all"))
                bind_mousewheel(self._content_outer, self._canvas_ref)
            except Exception:
                pass

    def expand(self):
        if not self._expanded:
            self._toggle()

    def collapse(self):
        if self._expanded:
            self._toggle()


# ─────────────────────────────────────────────────────────────────────────────
# Toast — Notificación emergente no bloqueante
# ─────────────────────────────────────────────────────────────────────────────

class Toast:
    """Notificación emergente ligera en la esquina inferior derecha de la ventana."""
    def __init__(self, root: tk.Tk, message: str, level: str = "info", duration: int = 3500):
        self.root = root
        colors = {
            "info":    (C["card2"],     C["cyan"]),
            "success": (C["green_dim"], C["green"]),
            "warning": (C["card2"],     C["orange"]),
            "error":   (C["red_dim"],   C["red"]),
        }
        bg_col, fg_col = colors.get(level, (C["card2"], C["text"]))

        try:
            rx = root.winfo_rootx() + root.winfo_width() - 320
            ry = root.winfo_rooty() + root.winfo_height() - 70
        except Exception:
            rx, ry = 100, 100

        self.win = tk.Toplevel(root)
        self.win.wm_overrideredirect(True)
        self.win.wm_geometry(f"300x48+{rx}+{ry}")
        self.win.configure(bg=bg_col)

        f = tk.Frame(self.win, bg=bg_col, padx=12, pady=10)
        f.pack(fill="both", expand=True)

        icons = {"success": "✔", "warning": "⚠️", "error": "❌", "info": "ℹ"}
        ico   = icons.get(level, "ℹ")
        tk.Label(f, text=f"{ico}  {message}", bg=bg_col, fg=fg_col,
                 font=FONT_UI_B, anchor="w", wraplength=270).pack(side="left")

        self.win.after(duration, self._destroy)

    def _destroy(self):
        try: self.win.destroy()
        except Exception: pass


# ─────────────────────────────────────────────────────────────────────────────
# ProfileChipsView — Vista de chips del perfil seleccionado
# ─────────────────────────────────────────────────────────────────────────────

class ProfileChipsView(tk.Frame):
    """Panel de chips visuales para los metadatos de un perfil."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=C["card2"], **kwargs)

    def set_profile(self, name: str, p: dict):
        for w in self.winfo_children():
            w.destroy()

        if not p:
            tk.Label(self, text=_("Selecciona un perfil para ver sus detalles."),
                     bg=C["card2"], fg=C["muted"], font=FONT_SM).pack(padx=16, pady=20)
            return

        hdr = tk.Frame(self, bg=C["card2"])
        hdr.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(hdr, text=f"⚙️  {name}", bg=C["card2"],
                 fg=C["purple"], font=FONT_CARD).pack(side="left")

        grid_frame = tk.Frame(self, bg=C["card2"])
        grid_frame.pack(fill="both", expand=True, padx=8, pady=4)

        chips_data = [
            (_("📺 Resolución"), f"{p.get('max_size','Nativa')}p", C["blue"]),
            (_("⚡ FPS máx"), f"{p.get('max_fps','60')} FPS", C["cyan"]),
            (_("📊 Bitrate"), f"{p.get('bitrate','8M')}", C["purple"]),
            (_("🎥 Códec"), f"{p.get('video_codec','H.264').upper()}", C["green"]),
            (_("🔊 Audio"), f"{p.get('audio_source','playback')}", C["orange"]),
            ("🌙 Pantalla Off","Sí" if p.get('turn_screen_off') else "No",
             C["red"] if p.get('turn_screen_off') else C["muted"]),
            ("☀️ Despierto",   "Sí" if p.get('stay_awake') else "No",
             C["green"] if p.get('stay_awake') else C["muted"]),
        ]
        if p.get("no_video") or "--no-video" in p.get("extra_args",""):
            chips_data.append(("🎙️ Solo Audio", "Sí", C["orange"]))
        if p.get("force_screen_off_keyevent"):
            chips_data.append(("🔑 EMUI Keyevent", "Sí", C["orange"]))
        if p.get("extra_args"):
            chips_data.append(("🧩 Extra Args", p.get("extra_args"), C["text2"]))

        r, c = 0, 0
        for label, val, color in chips_data:
            chip = tk.Frame(grid_frame, bg=C["card"], padx=10, pady=6,
                            highlightbackground=C["sep"], highlightthickness=1)
            chip.grid(row=r, column=c, padx=5, pady=5, sticky="ew")
            tk.Label(chip, text=label, bg=C["card"], fg=C["muted"], font=FONT_SM).pack(anchor="w")
            tk.Label(chip, text=val,   bg=C["card"], fg=color,      font=FONT_UI_B).pack(anchor="w")
            c += 1
            if c > 2:
                c = 0; r += 1

        for col_idx in range(3):
            grid_frame.columnconfigure(col_idx, weight=1)


# ─────────────────────────────────────────────────────────────────────────────
# ProfileWizard — Asistente paso a paso de creación de perfiles (7 Pasos)
# ─────────────────────────────────────────────────────────────────────────────

class ProfileWizard(tk.Toplevel):
    STEPS = [
        ("📝", "Nombre del perfil",   "Elige un nombre descriptivo para identificar este perfil fácilmente."),
        (_("🎯"), "¿Qué quieres hacer?", _("Selecciona un caso de uso predefinido o personaliza cada ajuste.")),
        ("🖼️", "Calidad de imagen",   "Define la resolución, fotogramas por segundo, bitrate y códec de vídeo."),
        ("🔊", "Fuente de audio",     "Configura la captura de sonido del sistema, micrófono o modo solo audio."),
        (_("🔋"), "Opciones de batería", _("Controla el apagado de pantalla y suspensión durante la transmisión.")),
        ("🧩", "Ajustes avanzados",   "ID de cámara trasera y argumentos adicionales para el comando scrcpy."),
        ("✅", "Resumen",             "Revisa toda la configuración antes de guardar el perfil."),
    ]

    PRESETS = {
        "🎮 Jugar en pantalla grande": {
            "bitrate": "16M", "max_size": "1920", "max_fps": "60",
            "audio_source": "playback", "video_codec": "h264",
            "turn_screen_off": False, "stay_awake": True,
            "force_screen_off_keyevent": False, "no_video": False, "extra_args": "",
        },
        "📡 Stream con OBS (solo audio mic)": {
            "bitrate": "4M", "max_size": "1080", "max_fps": "30",
            "audio_source": "mic", "video_codec": "h264",
            "turn_screen_off": True, "stay_awake": True,
            "force_screen_off_keyevent": True, "no_video": True, "extra_args": "--no-video",
        },
        "📷 Usar cámara trasera como webcam": {
            "bitrate": "12M", "max_size": "1920", "max_fps": "30",
            "audio_source": "mic", "video_codec": "h264",
            "turn_screen_off": False, "stay_awake": True,
            "force_screen_off_keyevent": False, "no_video": False,
            "extra_args": "--video-source=camera --camera-id 0",
        },
        "⚡ Espejo ligero (bajo consumo)": {
            "bitrate": "4M", "max_size": "720", "max_fps": "30",
            "audio_source": "playback", "video_codec": "h264",
            "turn_screen_off": False, "stay_awake": True,
            "force_screen_off_keyevent": False, "no_video": False, "extra_args": "",
        },
        "⌨️ Modo OTG (Teclado y Ratón USB)": {
            "bitrate": "4M", "max_size": "720", "max_fps": "30",
            "audio_source": "none", "video_codec": "h264",
            "turn_screen_off": False, "stay_awake": True,
            "force_screen_off_keyevent": False, "no_video": False,
            "extra_args": "--otg",
        },
    }

    def __init__(self, parent, on_save_callback):
        super().__init__(parent)
        self.title("Asistente de nuevo perfil — MASV")
        self.geometry("600x560")
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self.grab_set()

        self._cb   = on_save_callback
        self._step = 0
        self._data = {
            "name": "", "bitrate": "8M", "max_size": "1080", "max_fps": "60",
            "audio_source": "playback", "video_codec": "h264", "camera_id": "0",
            "turn_screen_off": True, "stay_awake": True,
            "force_screen_off_keyevent": False, "no_video": False, "extra_args": "",
        }
        self._build()
        self._show_step(0)

    def _build(self):
        top = tk.Frame(self, bg=C["card"], height=64)
        top.pack(fill="x")
        top.pack_propagate(False)
        self._ico_lbl  = tk.Label(top, text="", bg=C["card"], font=(FONT_FAMILY, 22))
        self._ico_lbl.pack(side="left", padx=16, pady=10)
        right_top = tk.Frame(top, bg=C["card"])
        right_top.pack(side="left", fill="both", expand=True)
        self._step_lbl = tk.Label(right_top, text="", bg=C["card"], fg=C["purple"], font=FONT_LG, anchor="w")
        self._step_lbl.pack(anchor="w", padx=4, pady=(8, 0))
        self._desc_lbl = tk.Label(right_top, text="", bg=C["card"], fg=C["muted"],
                                   font=FONT_SM, anchor="w", wraplength=380, justify="left")
        self._desc_lbl.pack(anchor="w", padx=4)

        self._prog_frame = tk.Frame(top, bg=C["card"])
        self._prog_frame.pack(side="right", padx=14)
        self._prog_dots = []
        for i in range(len(self.STEPS)):
            d = tk.Label(self._prog_frame, text=_("●"), bg=C["card"], fg=C["sep"],
                         font=(FONT_FAMILY, 7))
            d.grid(row=0, column=i, padx=2)
            self._prog_dots.append(d)

        self._content = tk.Frame(self, bg=C["bg"])
        self._content.pack(fill="both", expand=True, padx=20, pady=10)

        nav = tk.Frame(self, bg=C["card2"])
        nav.pack(fill="x", side="bottom")
        self._back_btn   = tk.Button(nav, text=_("◀  Atrás"), bg=C["sep"], fg=C["text"],
                                     font=FONT_UI_B, relief="flat", bd=0, padx=16, pady=8, command=self._prev)
        self._back_btn.pack(side="left", padx=10, pady=8)
        self._next_btn   = tk.Button(nav, text=_("Siguiente  ▶"), bg=C["blue"], fg="#FFFFFF",
                                     font=FONT_UI_B, relief="flat", bd=0, padx=16, pady=8, command=self._next)
        self._next_btn.pack(side="right", padx=10, pady=8)
        self._cancel_btn = tk.Button(nav, text=_("Cancelar"), bg=C["bg"], fg=C["muted"],
                                     font=FONT_SM, relief="flat", bd=0, padx=10, pady=8, command=self.destroy)
        self._cancel_btn.pack(side="right", padx=4, pady=8)

    def _show_step(self, step: int):
        self._step = step
        ico, title, desc = self.STEPS[step]
        self._ico_lbl.config(text=ico)
        self._step_lbl.config(text=f"Paso {step + 1} de {len(self.STEPS)}  —  {title}")
        self._desc_lbl.config(text=desc)
        for i, d in enumerate(self._prog_dots):
            d.config(fg=C["blue"] if i <= step else C["sep"])
        self._back_btn.config(state="normal" if step > 0 else "disabled")
        last = (step == len(self.STEPS) - 1)
        self._next_btn.config(text=_("💾  Guardar perfil") if last else "Siguiente  ▶",
                              bg=C["green"] if last else C["blue"])
        for w in self._content.winfo_children():
            w.destroy()
        getattr(self, f"_step_{step}")()

    def _next(self):
        if not self._collect_step(self._step): return
        if self._step < len(self.STEPS) - 1:
            self._show_step(self._step + 1)
        else:
            self._finish()

    def _prev(self):
        if self._step > 0:
            self._show_step(self._step - 1)

    def _collect_step(self, step: int) -> bool:
        if step == 0:
            name = self._name_var.get().strip()
            if not name:
                messagebox.showerror(_("Error"), _("El nombre no puede estar vacío."), parent=self)
                return False
            self._data["name"] = name
        elif step == 1:
            sel = self._preset_var.get()
            if sel in self.PRESETS:
                self._data.update(self.PRESETS[sel])
        elif step == 2:
            self._data["bitrate"]     = self._br_var.get()
            self._data["max_size"]    = self._sz_var.get()
            self._data["max_fps"]     = self._fps_var.get()
            self._data["video_codec"] = self._codec_var.get()
        elif step == 3:
            self._data["audio_source"] = self._audio_var.get()
            self._data["no_video"]     = self._novideo_var.get()
            if self._usemic_var.get():
                self._data["audio_source"] = "mic"
        elif step == 4:
            self._data["turn_screen_off"]          = self._scroff_var.get()
            self._data["stay_awake"]               = self._awake_var.get()
            self._data["force_screen_off_keyevent"] = self._kev_var.get()
        elif step == 5:
            self._data["video_source"]  = self._vsource_var.get()
            self._data["camera_facing"] = self._camfacing_var.get()
            self._data["audio_codec"]   = self._acodec_var.get()
            self._data["camera_id"]     = self._camid_var.get()
            self._data["extra_args"]    = self._extra_var.get().strip()
        return True

    def _finish(self):
        self._collect_step(self._step)
        if self._data.get("no_video"):
            args = self._data.get("extra_args", "").strip()
            if "--no-video" not in args:
                self._data["extra_args"] = (args + " --no-video").strip()
        self.destroy()
        self._cb(self._data)

    def _step_0(self):
        tk.Label(self._content, text=_("Nombre del perfil:"), bg=C["bg"],
                 fg=C["text2"], font=FONT_UI_B).pack(anchor="w", pady=(20, 6))
        self._name_var = tk.StringVar(value=self._data.get("name", ""))
        e = ttk.Entry(self._content, textvariable=self._name_var,
                      font=(FONT_FAMILY, 13), width=32)
        e.pack(anchor="w"); e.focus_set()
        tk.Label(self._content, text=_("Ejemplo: 'Juego Vivo', 'Stream Huawei mic', 'Cámara OBS'"),
                 bg=C["bg"], fg=C["muted"], font=FONT_SM).pack(anchor="w", pady=(6, 0))

    def _step_1(self):
        tk.Label(self._content, text=_("Elige un caso de uso (preselecciona todo):"),
                 bg=C["bg"], fg=C["text2"], font=FONT_UI_B).pack(anchor="w", pady=(8, 10))
        self._preset_var = tk.StringVar(value="(Personalizado)")
        for opt in list(self.PRESETS.keys()) + ["(Personalizado)"]:
            tk.Radiobutton(self._content, text=opt, variable=self._preset_var, value=opt,
                           bg=C["bg"], fg=C["text"], selectcolor=C["card2"],
                           activebackground=C["bg"], font=FONT_UI, anchor="w"
                           ).pack(fill="x", padx=4, pady=3)

    def _step_2(self):
        def pair(lbl, var, values, tip=""):
            r = tk.Frame(self._content, bg=C["bg"])
            r.pack(fill="x", pady=5)
            tk.Label(r, text=lbl, bg=C["bg"], fg=C["text2"],
                     font=FONT_UI, width=18, anchor="e").pack(side="left", padx=(0,8))
            cb = ttk.Combobox(r, textvariable=var, values=values, width=12, state="readonly")
            cb.pack(side="left")
            if tip: Tooltip(cb, tip)

        self._br_var    = tk.StringVar(value=self._data["bitrate"])
        self._sz_var    = tk.StringVar(value=self._data["max_size"])
        self._fps_var   = tk.StringVar(value=self._data["max_fps"])
        self._codec_var = tk.StringVar(value=self._data["video_codec"])
        pair("Bitrate (calidad):", self._br_var, ["2M","4M","8M","12M","16M","24M","32M"])
        pair("Resolución máx:",    self._sz_var, ["720","1080","1440","1920","0"])
        pair("FPS máximos:",       self._fps_var, ["24","30","60","90","120"])
        pair("Códec de vídeo:",    self._codec_var, ["h264","h265","av1","vp8","vp9"])

    def _step_3(self):
        curr_audio = self._data.get("audio_source", "playback")
        if curr_audio == "system":
            curr_audio = "playback"
        self._audio_var   = tk.StringVar(value=curr_audio)
        self._novideo_var = tk.BooleanVar(value=self._data.get("no_video", False))
        self._usemic_var  = tk.BooleanVar(value=(curr_audio == "mic"))

        tk.Label(self._content, text=_("Selecciona la fuente de audio:"),
                 bg=C["bg"], fg=C["text2"], font=FONT_UI_B).pack(anchor="w", pady=(4, 6))

        for emoji_lbl, val, tip in [
            (_("🔈 playback (sistema)"), "playback", _("Audio del sistema interno del teléfono.")),
            (_("🎤 mic (micrófono)"),     "mic",      _("Micrófono físico del teléfono.")),
            (_("🔇 none (sin audio)"),    "none",     _("Solo transmisión de vídeo, sin captura de audio.")),
        ]:
            f = tk.Frame(self._content, bg=C["card"], pady=5, padx=10)
            f.pack(fill="x", pady=3)
            tk.Radiobutton(f, text=f"  {emoji_lbl}", variable=self._audio_var, value=val,
                           bg=C["card"], fg=C["text"], selectcolor=C["blue"],
                           activebackground=C["card"], font=FONT_UI_B, anchor="w").pack(side="left")
            tk.Label(f, text=tip, bg=C["card"], fg=C["muted"],
                     font=FONT_SM, justify="left", wraplength=320).pack(side="left", padx=10)

        _sep(self._content, C["sep"])

        f_extra = tk.Frame(self._content, bg=C["card"], pady=6, padx=10)
        f_extra.pack(fill="x", pady=4)
        tk.Checkbutton(f_extra, text=_(" 🚫 Solo audio (sin video --no-video)"), variable=self._novideo_var,
                       bg=C["card"], fg=C["text"], selectcolor=C["card2"],
                       activebackground=C["card"], font=FONT_UI_B).pack(anchor="w")
        Tooltip(f_extra, "Transmite únicamente el sonido del teléfono sin abrir la ventana de vídeo.")

        f_mic = tk.Frame(self._content, bg=C["card"], pady=6, padx=10)
        f_mic.pack(fill="x", pady=2)
        def _on_mic_toggle():
            if self._usemic_var.get():
                self._audio_var.set("mic")
        tk.Checkbutton(f_mic, text=_(" 🎤 Usar micrófono como entrada de audio principal"), variable=self._usemic_var,
                       command=_on_mic_toggle, bg=C["card"], fg=C["text"], selectcolor=C["card2"],
                       activebackground=C["card"], font=FONT_UI_B).pack(anchor="w")

    def _step_4(self):
        self._scroff_var = tk.BooleanVar(value=self._data["turn_screen_off"])
        self._awake_var  = tk.BooleanVar(value=self._data["stay_awake"])
        self._kev_var    = tk.BooleanVar(value=self._data["force_screen_off_keyevent"])
        for var, label, tip in [
            (self._scroff_var, "🌙 Apagar pantalla del teléfono",      "Ahorra batería durante la sesión."),
            (self._awake_var,  "☀️ Mantener el teléfono despierto",    "Evita la suspensión mientras scrcpy está activo."),
            (self._kev_var,    "🔑 Forzar apagado de pantalla (EMUI)", "Envía keyevent 26 antes de iniciar. Necesario en Huawei EMUI."),
        ]:
            f = tk.Frame(self._content, bg=C["card"], pady=8, padx=12)
            f.pack(fill="x", pady=5)
            tk.Checkbutton(f, text=f"  {label}", variable=var, bg=C["card"], fg=C["text"],
                           selectcolor=C["card2"], activebackground=C["card"],
                           font=FONT_UI, anchor="w").pack(side="left")
            Tooltip(f, tip)
            tk.Label(f, text=tip, bg=C["card"], fg=C["muted"],
                     font=FONT_SM, wraplength=280).pack(side="left", padx=10)

    def _step_5(self):
        def pair(lbl, var, values, tip=""):
            r = tk.Frame(self._content, bg=C["bg"])
            r.pack(fill="x", pady=4)
            tk.Label(r, text=lbl, bg=C["bg"], fg=C["text2"],
                     font=FONT_UI, width=22, anchor="e").pack(side="left", padx=(0,8))
            cb = ttk.Combobox(r, textvariable=var, values=values, width=14, state="readonly")
            cb.pack(side="left")
            if tip: Tooltip(cb, tip)

        self._vsource_var = tk.StringVar(value=self._data.get("video_source", "display"))
        self._camfacing_var = tk.StringVar(value=self._data.get("camera_facing", "back"))
        self._camid_var = tk.StringVar(value=self._data.get("camera_id", "0"))
        self._acodec_var = tk.StringVar(value=self._data.get("audio_codec", "opus"))

        pair("Fuente de vídeo:", self._vsource_var, ["display", "camera"], "Pantalla del teléfono o transmisión directa de cámara.")
        pair("Orientación cámara:", self._camfacing_var, ["back", "front"], "Cámara trasera o frontal (Android 12+).")
        pair("Códec de audio:", self._acodec_var, ["opus", "aac", "flac", "raw"], "Formato de compresión de audio.")

        tk.Label(self._content, text=_("Argumentos adicionales de scrcpy (extra_args):"),
                 bg=C["bg"], fg=C["text2"], font=FONT_UI_B).pack(anchor="w", pady=(10, 4))
        self._extra_var = tk.StringVar(value=self._data.get("extra_args", ""))
        e_extra = ttk.Entry(self._content, textvariable=self._extra_var, width=42, font=FONT_MONO)
        e_extra.pack(anchor="w", padx=4)
        tk.Label(self._content, text=_("Ejemplos: '--no-control', '--max-fps 30', '--v4l2-buffer 50'"),
                 bg=C["bg"], fg=C["muted"], font=FONT_SM).pack(anchor="w", padx=4, pady=(4, 0))

    def _step_6(self):
        self._collect_step(5)
        d = self._data
        lines = [
            f"  Nombre           : {d['name']}",
            f"  Bitrate          : {d['bitrate']}",
            f"  Resolución       : {d['max_size']}p",
            f"  FPS máx          : {d['max_fps']}",
            f"  Códec            : {d['video_codec']}",
            f"  Audio            : {d['audio_source']}",
            f"  Solo Audio       : {'Sí' if d.get('no_video') else 'No'}",
            f"  Pantalla apagada : {'Sí' if d['turn_screen_off'] else 'No'}",
            f"  Despierto        : {'Sí' if d['stay_awake'] else 'No'}",
            f"  Cámara ID        : {d.get('camera_id','0')}",
            f"  Keyevent EMUI    : {'Sí' if d['force_screen_off_keyevent'] else 'No'}",
        ]
        if d.get("extra_args"):
            lines.append(f"  Args extra       : {d['extra_args']}")
        tk.Label(self._content, text=_("Perfil listo para guardar:"), bg=C["bg"],
                 fg=C["text2"], font=FONT_UI_B).pack(anchor="w", pady=(6, 4))
        box = tk.Text(self._content, bg=C["card2"], fg=C["text"], font=FONT_MONO,
                      height=11, relief="flat", bd=0, state="normal", wrap="word")
        box.insert("1.0", "\n".join(lines))
        box.config(state="disabled")
        box.pack(fill="both", expand=True, pady=4)
        tk.Label(self._content, text=_("✔  Pulsa 'Guardar perfil' para finalizar."),
                 bg=C["bg"], fg=C["green"], font=FONT_UI_B).pack(pady=(4, 0))


# ─────────────────────────────────────────────────────────────────────────────
# Diálogos Modales de Seguridad y Bóveda de Confianza (Trusted Vault)
# ─────────────────────────────────────────────────────────────────────────────

class DeviceTrustModal:
    """Ventana modal para inspeccionar, asignar alias y confiar/desconfiar de un dispositivo."""
    def __init__(self, parent, serial: str, model: str, security_mgr, save_cb=None, on_close_cb=None):
        self.parent = parent
        self.serial = serial
        self.model = model or "Android"
        self.sec = security_mgr
        self.save_cb = save_cb
        self.on_close_cb = on_close_cb

        self.win = tk.Toplevel(parent)
        self.win.title(_("Bóveda de Seguridad — Dispositivo"))
        self.win.geometry("520x420")
        self.win.resizable(False, False)
        self.win.configure(bg=C["bg"])
        self.win.transient(parent)
        self.win.grab_set()

        # Centrar
        self.win.update_idletasks()
        w = 520; h = 420
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

        self._build_ui()

    def _build_ui(self):
        is_trusted = self.sec.is_trusted_device(self.serial)
        current_alias = self.sec.get_device_alias(self.serial, self.model)

        # Header
        hdr = tk.Frame(self.win, bg=C["card2"], pady=14, padx=16)
        hdr.pack(fill="x")
        icon_str = "🛡️" if is_trusted else "⚠️"
        title_str = _("Dispositivo Confiable") if is_trusted else _("Dispositivo No Verificado")
        color = C["green"] if is_trusted else C["orange"]

        tk.Label(hdr, text=icon_str, font=(FONT_FAMILY, 24), bg=C["card2"], fg=color).pack(side="left", padx=(0, 10))
        tk.Label(hdr, text=title_str, font=FONT_LG, bg=C["card2"], fg=C["text"]).pack(side="left")

        # Contenido
        body = tk.Frame(self.win, bg=C["bg"], padx=20, pady=14)
        body.pack(fill="both", expand=True)

        # Tarjeta de Datos
        info_f = tk.Frame(body, bg=C["card"], padx=14, pady=10)
        info_f.pack(fill="x", pady=(0, 12))

        def _row_info(lbl, val):
            r = tk.Frame(info_f, bg=C["card"])
            r.pack(fill="x", pady=2)
            tk.Label(r, text=lbl, bg=C["card"], fg=C["muted"], font=FONT_SM, width=18, anchor="w").pack(side="left")
            tk.Label(r, text=val, bg=C["card"], fg=C["text"], font=FONT_UI_B, anchor="w").pack(side="left")

        _row_info(_("Modelo:"), self.model)
        _row_info(_("Identificador / Serial:"), self.serial)
        conn_type = _("Inalámbrico (Wi-Fi TCP/IP)") if (":" in self.serial) else _("Físico Seguro (Cable USB)")
        _row_info(_("Tipo de Conexión:"), conn_type)

        # Entrada de Alias
        alias_sec = _section(body, _("Alias personalizado"))
        tk.Label(alias_sec, text=_("Asigna un nombre fácil de reconocer (ej. 'Mi Teléfono Personal'):"),
                 bg=C["card"], fg=C["muted"], font=FONT_SM).pack(anchor="w", padx=8, pady=(4, 2))
        self.alias_var = tk.StringVar(value=current_alias)
        e_alias = ttk.Entry(alias_sec, textvariable=self.alias_var, width=38)
        e_alias.pack(fill="x", padx=8, pady=(2, 8))

        # Botones de Acción
        btn_bar = tk.Frame(body, bg=C["bg"])
        btn_bar.pack(fill="x", pady=(14, 0))

        if is_trusted:
            btn_trust = ttk.Button(btn_bar, text=_("❌ Quitar de Confiables"),
                                   command=self._untrust, style="Danger.TButton")
            btn_trust.pack(side="left")
            Tooltip(btn_trust, "Marca este dispositivo como desconocido para evitar conexiones involuntarias.")
        else:
            btn_trust = ttk.Button(btn_bar, text=_("🛡️ Confiar en este Dispositivo"),
                                   command=self._trust, style="Green.TButton")
            btn_trust.pack(side="left")
            Tooltip(btn_trust, "Añade este dispositivo a tu bóveda de confianza para operar de forma segura.")

        btn_save = ttk.Button(btn_bar, text=_("Guardar Cambios"),
                              command=self._save_alias, style="Primary.TButton")
        btn_save.pack(side="right", padx=(8, 0))

        btn_cancel = ttk.Button(btn_bar, text=_("Cerrar"),
                                command=self._close, style="Secondary.TButton")
        btn_cancel.pack(side="right")

    def _trust(self):
        self.sec.trust_device(self.serial, self.model, self.alias_var.get(), self.save_cb)
        self._close()

    def _untrust(self):
        self.sec.untrust_device(self.serial, self.save_cb)
        self._close()

    def _save_alias(self):
        if self.sec.is_trusted_device(self.serial):
            self.sec.trust_device(self.serial, self.model, self.alias_var.get(), self.save_cb)
        self._close()

    def _close(self):
        self.win.destroy()
        if self.on_close_cb:
            self.on_close_cb()


class TrustPromptModal:
    """Modal amigable cuando un dispositivo no verificado intenta conectarse en Modo Seguro."""
    def __init__(self, parent, serial: str, model: str, alias: str, security_mgr, cfg=None):
        self.result = "cancel"
        self.serial = serial
        self.model = model or "Android"
        self.alias = alias or model or serial
        self.sec = security_mgr
        self.cfg = cfg

        self.win = tk.Toplevel(parent)
        self.win.title(_("Dispositivo No Verificado — Bóveda de Seguridad"))
        self.win.geometry("540x360")
        self.win.resizable(False, False)
        self.win.configure(bg=C["bg"])
        self.win.transient(parent)
        self.win.grab_set()

        # Centrar ventana
        self.win.update_idletasks()
        w, h = 540, 360
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

        self._build_ui()
        parent.wait_window(self.win)

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.win, bg=C["card2"], pady=12, padx=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🛡️", font=(FONT_FAMILY, 24), bg=C["card2"], fg=C["orange"]).pack(side="left", padx=(0, 10))
        tk.Label(hdr, text=_("Dispositivo No Verificado en Bóveda"), font=FONT_LG, bg=C["card2"], fg=C["text"]).pack(side="left")

        body = tk.Frame(self.win, bg=C["bg"], padx=18, pady=12)
        body.pack(fill="both", expand=True)

        msg = (
            f"{_('El dispositivo')} '{self.alias}' ({self.serial}) {_('no está registrado en tu Bóveda de Confianza.')}\n\n"
            f"{_('El Modo Seguro protege tus transmisiones evitando conexiones involuntarias o no autorizadas.')}\n\n"
            f"{_('¿Deseas agregar este dispositivo a la Bóveda de Confianza para no volver a ver este aviso?')}"
        )
        tk.Label(body, text=msg, bg=C["bg"], fg=C["text2"], font=FONT_UI, wraplength=490, justify="left").pack(anchor="w", pady=(0, 12))

        btn_bar = tk.Frame(body, bg=C["bg"])
        btn_bar.pack(fill="x", side="bottom", pady=(8, 0))

        btn_trust = tk.Button(
            btn_bar, text=_("🛡️ Confiar y Recordar"), bg=C["green_dim"], fg=C["green"],
            font=FONT_UI_B, relief="flat", bd=0, padx=14, pady=8, cursor="hand2",
            command=self._on_trust
        )
        btn_trust.pack(side="left", padx=(0, 6))
        Tooltip(btn_trust, _("Agrega el teléfono a la Bóveda permanentemente. No volverás a ver este aviso."))

        btn_once = tk.Button(
            btn_bar, text=_("▶ Iniciar solo esta vez"), bg=C["card3"], fg=C["text"],
            font=FONT_SM, relief="flat", bd=0, padx=10, pady=8, cursor="hand2",
            command=self._on_once
        )
        btn_once.pack(side="left")

        btn_cancel = tk.Button(
            btn_bar, text=_("✕ Cancelar"), bg=C["card2"], fg=C["muted"],
            font=FONT_SM, relief="flat", bd=0, padx=10, pady=8, cursor="hand2",
            command=self._on_cancel
        )
        btn_cancel.pack(side="right")

    def _on_trust(self):
        from .utils import save_config
        self.sec.trust_device(self.serial, self.model, self.alias)
        if self.cfg:
            save_config(self.cfg)
        self.result = "trust"
        self.win.destroy()

    def _on_once(self):
        self.result = "once"
        self.win.destroy()

    def _on_cancel(self):
        self.result = "cancel"
        self.win.destroy()


class SafeActionConfirmModal:
    """Diálogo modal de confirmación previa a operaciones críticas (Instalar APK, Enviar Texto, etc.)."""
    def __init__(self, parent, title: str, message: str, device_name: str, on_confirm_cb):
        self.result = False
        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.geometry("480x280")
        self.win.resizable(False, False)
        self.win.configure(bg=C["bg"])
        self.win.transient(parent)
        self.win.grab_set()

        # Centrar
        self.win.update_idletasks()
        w = 480; h = 280
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

        # Header
        hdr = tk.Frame(self.win, bg=C["card2"], pady=10, padx=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🛡️", font=(FONT_FAMILY, 20), bg=C["card2"], fg=C["orange"]).pack(side="left", padx=(0, 8))
        tk.Label(hdr, text=title, font=FONT_LG, bg=C["card2"], fg=C["text"]).pack(side="left")

        # Contenido
        body = tk.Frame(self.win, bg=C["bg"], padx=18, pady=12)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=message, bg=C["bg"], fg=C["text"], font=FONT_UI,
                 wraplength=440, justify="left").pack(anchor="w", pady=(0, 10))

        # Tarjeta de destino
        dev_card = tk.Frame(body, bg=C["card"], padx=12, pady=8)
        dev_card.pack(fill="x", pady=4)
        tk.Label(dev_card, text=_("Dispositivo Destino:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(anchor="w")
        tk.Label(dev_card, text=f"📱  {device_name}", bg=C["card"], fg=C["indigo"], font=FONT_UI_B).pack(anchor="w", pady=(2, 0))

        # Botones
        btns = tk.Frame(body, bg=C["bg"])
        btns.pack(fill="x", side="bottom", pady=(10, 0))

        def _confirm():
            self.result = True
            self.win.destroy()
            if on_confirm_cb:
                on_confirm_cb()

        def _cancel():
            self.result = False
            self.win.destroy()

        btn_ok = ttk.Button(btns, text=_("Confirmar y Proceder"), command=_confirm, style="Primary.TButton")
        btn_ok.pack(side="right", padx=(8, 0))

        btn_no = ttk.Button(btns, text=_("Cancelar"), command=_cancel, style="Secondary.TButton")
        btn_no.pack(side="right")


class TrustVaultDialog:
    """Ventana para gestionar todos los dispositivos guardados en la Bóveda de Confianza."""
    def __init__(self, parent, security_mgr, save_cb=None, on_change_cb=None):
        self.parent = parent
        self.sec = security_mgr
        self.save_cb = save_cb
        self.on_change_cb = on_change_cb

        self.win = tk.Toplevel(parent)
        self.win.title(_("Bóveda de Dispositivos Confiables — MASV"))
        self.win.geometry("620x460")
        self.win.minsize(500, 380)
        self.win.configure(bg=C["bg"])
        self.win.transient(parent)
        self.win.grab_set()

        # Centrar
        self.win.update_idletasks()
        w = 620; h = 460
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self.win, bg=C["card2"], pady=12, padx=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🛡️", font=(FONT_FAMILY, 20), bg=C["card2"], fg=C["purple"]).pack(side="left", padx=(0, 8))
        tk.Label(hdr, text=_("Bóveda de Dispositivos Confiables"), font=FONT_LG, bg=C["card2"], fg=C["text"]).pack(side="left")

        body = tk.Frame(self.win, bg=C["bg"], padx=16, pady=12)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=_("Los dispositivos en esta lista están autorizados para streaming, control y transferencia."),
                 bg=C["bg"], fg=C["muted"], font=FONT_SM).pack(anchor="w", pady=(0, 8))

        # Lista / Treeview
        tree_f = tk.Frame(body, bg=C["card2"])
        tree_f.pack(fill="both", expand=True)

        cols = ("alias", "model", "serial", "status")
        self.tree = ttk.Treeview(tree_f, columns=cols, show="headings", height=8, selectmode="browse")
        self.tree.heading("alias", text=_("Alias"))
        self.tree.heading("model", text=_("Modelo"))
        self.tree.heading("serial", text=_("Serial / IP"))
        self.tree.heading("status", text=_("Estado"))

        self.tree.column("alias", width=180, stretch=True)
        self.tree.column("model", width=120, stretch=True)
        self.tree.column("serial", width=160, stretch=True)
        self.tree.column("status", width=90, anchor="center")

        sb = ttk.Scrollbar(tree_f, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._populate()

        # Botones
        btns = tk.Frame(body, bg=C["bg"])
        btns.pack(fill="x", pady=(12, 0))

        btn_del = ttk.Button(btns, text=_("🗑️ Eliminar de la Bóveda"),
                             command=self._delete_selected, style="Danger.TButton")
        btn_del.pack(side="left")

        btn_close = ttk.Button(btns, text=_("Cerrar"),
                               command=self.win.destroy, style="Secondary.TButton")
        btn_close.pack(side="right")

    def _populate(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        vault = self.sec.get_trusted_devices()
        for serial, d in vault.items():
            alias = d.get("alias", d.get("model", "Android"))
            model = d.get("model", "Android")
            status = _("Confiable") if d.get("is_trusted", True) else _("Revocado")
            self.tree.insert("", "end", iid=serial, values=(alias, model, serial, status))

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        serial = sel[0]
        self.sec.remove_device_from_vault(serial, self.save_cb)
        self._populate()
        if self.on_change_cb:
            self.on_change_cb()

