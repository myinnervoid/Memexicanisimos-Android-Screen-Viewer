import tkinter as tk
from tkinter import ttk, messagebox
from .utils import C, FONT_FAMILY, FONT_UI, FONT_UI_B, FONT_SM, FONT_LG, FONT_MONO, FONT_CARD

# ─────────────────────────────────────────────────────────────────────────────
# Helpers de layout (usan tokens del sistema Slate Dark)
# ─────────────────────────────────────────────────────────────────────────────

def _row(parent, bg=None, pady=3, padx=4) -> tk.Frame:
    f = tk.Frame(parent, bg=bg or C["card"])
    f.pack(fill="x", padx=padx, pady=pady)
    return f

def _sep(parent, color=None):
    tk.Frame(parent, bg=color or C["sep"], height=1).pack(fill="x", padx=12, pady=4)

def _section(parent, title: str, pady=(6, 4)) -> ttk.LabelFrame:
    f = ttk.LabelFrame(parent, text=f"  {title}  ")
    f.pack(fill="x", padx=14, pady=pady)
    return f

def _recolor(frame: tk.Frame, color: str):
    for child in frame.winfo_children():
        try: child.config(bg=color)
        except Exception: pass
        if isinstance(child, tk.Frame):
            _recolor(child, color)


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
        copy_btn.config(text="✔ Copiado", fg=C["green"])
        chip.after(2000, lambda: copy_btn.config(text="📋 Copiar", fg=C["muted"]))

    copy_btn = tk.Label(chip, text="📋 Copiar", bg=C["card2"], fg=C["muted"],
                        font=FONT_SM, cursor="hand2")
    copy_btn.pack(side="right", padx=4)
    copy_btn.bind("<Button-1>", copy)
    return chip


# ─────────────────────────────────────────────────────────────────────────────
# AccordionItem — FAQ expandible con animación suave
# ─────────────────────────────────────────────────────────────────────────────

class AccordionItem(tk.Frame):
    """
    Elemento de FAQ acordeón con apertura/cierre fluido.
    """
    def __init__(self, parent, title: str, build_fn, **kw):
        super().__init__(parent, bg=C["card"], **kw)
        self._title    = title
        self._expanded = False

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
        build_fn(self._content_inner)

        # Bindings de toggle
        for w in [self._hdr, self._arrow] + self._hdr.winfo_children():
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

        tk.Frame(self, bg=C["sep"], height=1).pack(fill="x")

    def _toggle(self, _=None):
        if self._expanded:
            self._content_outer.pack_forget()
            self._arrow.config(text="▶")
            self._expanded = False
        else:
            self._content_outer.pack(fill="x")
            self._arrow.config(text="▼")
            self._expanded = True

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
            tk.Label(self, text="Selecciona un perfil para ver sus detalles.",
                     bg=C["card2"], fg=C["muted"], font=FONT_SM).pack(padx=16, pady=20)
            return

        hdr = tk.Frame(self, bg=C["card2"])
        hdr.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(hdr, text=f"⚙️  {name}", bg=C["card2"],
                 fg=C["purple"], font=FONT_CARD).pack(side="left")

        grid_frame = tk.Frame(self, bg=C["card2"])
        grid_frame.pack(fill="both", expand=True, padx=8, pady=4)

        chips_data = [
            ("📺 Resolución",  f"{p.get('max_size','Nativa')}p",  C["blue"]),
            ("⚡ FPS máx",     f"{p.get('max_fps','60')} FPS",    C["cyan"]),
            ("📊 Bitrate",     f"{p.get('bitrate','8M')}",        C["purple"]),
            ("🎥 Códec",       f"{p.get('video_codec','H.264').upper()}", C["green"]),
            ("🔊 Audio",       f"{p.get('audio_source','playback')}",     C["orange"]),
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
        ("🎯", "¿Qué quieres hacer?", "Selecciona un caso de uso predefinido o personaliza cada ajuste."),
        ("🖼️", "Calidad de imagen",   "Define la resolución, fotogramas por segundo, bitrate y códec de vídeo."),
        ("🔊", "Fuente de audio",     "Configura la captura de sonido del sistema, micrófono o modo solo audio."),
        ("🔋", "Opciones de batería", "Controla el apagado de pantalla y suspensión durante la transmisión."),
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
            d = tk.Label(self._prog_frame, text="●", bg=C["card"], fg=C["sep"],
                         font=(FONT_FAMILY, 7))
            d.grid(row=0, column=i, padx=2)
            self._prog_dots.append(d)

        self._content = tk.Frame(self, bg=C["bg"])
        self._content.pack(fill="both", expand=True, padx=20, pady=10)

        nav = tk.Frame(self, bg=C["card2"])
        nav.pack(fill="x", side="bottom")
        self._back_btn   = tk.Button(nav, text="◀  Atrás", bg=C["sep"], fg=C["text"],
                                     font=FONT_UI_B, relief="flat", bd=0, padx=16, pady=8, command=self._prev)
        self._back_btn.pack(side="left", padx=10, pady=8)
        self._next_btn   = tk.Button(nav, text="Siguiente  ▶", bg=C["blue"], fg="#FFFFFF",
                                     font=FONT_UI_B, relief="flat", bd=0, padx=16, pady=8, command=self._next)
        self._next_btn.pack(side="right", padx=10, pady=8)
        self._cancel_btn = tk.Button(nav, text="Cancelar", bg=C["bg"], fg=C["muted"],
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
        self._next_btn.config(text="💾  Guardar perfil" if last else "Siguiente  ▶",
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
                messagebox.showerror("Error", "El nombre no puede estar vacío.", parent=self)
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
            self._data["camera_id"]  = self._camid_var.get()
            self._data["extra_args"] = self._extra_var.get().strip()
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
        tk.Label(self._content, text="Nombre del perfil:", bg=C["bg"],
                 fg=C["text2"], font=FONT_UI_B).pack(anchor="w", pady=(20, 6))
        self._name_var = tk.StringVar(value=self._data.get("name", ""))
        e = ttk.Entry(self._content, textvariable=self._name_var,
                      font=(FONT_FAMILY, 13), width=32)
        e.pack(anchor="w"); e.focus_set()
        tk.Label(self._content, text="Ejemplo: 'Juego Vivo', 'Stream Huawei mic', 'Cámara OBS'",
                 bg=C["bg"], fg=C["muted"], font=FONT_SM).pack(anchor="w", pady=(6, 0))

    def _step_1(self):
        tk.Label(self._content, text="Elige un caso de uso (preselecciona todo):",
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
        pair("Códec de vídeo:",    self._codec_var, ["h264","h265","av1"])

    def _step_3(self):
        self._audio_var   = tk.StringVar(value=self._data.get("audio_source", "playback"))
        self._novideo_var = tk.BooleanVar(value=self._data.get("no_video", False))
        self._usemic_var  = tk.BooleanVar(value=(self._data.get("audio_source") == "mic"))

        tk.Label(self._content, text="Selecciona la fuente de audio:",
                 bg=C["bg"], fg=C["text2"], font=FONT_UI_B).pack(anchor="w", pady=(4, 6))

        for emoji_lbl, val, tip in [
            ("🔈 playback (sistema)", "playback", "Audio del sistema interno del teléfono."),
            ("🎤 mic (micrófono)",     "mic",      "Micrófono físico del teléfono."),
            ("📻 system (sonido)",     "system",   "Audio directo del sistema Android."),
            ("🔇 none (sin audio)",    "none",     "Solo transmisión de vídeo, sin captura de audio."),
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
        tk.Checkbutton(f_extra, text=" 🚫 Solo audio (sin video --no-video)", variable=self._novideo_var,
                       bg=C["card"], fg=C["text"], selectcolor=C["card2"],
                       activebackground=C["card"], font=FONT_UI_B).pack(anchor="w")
        Tooltip(f_extra, "Transmite únicamente el sonido del teléfono sin abrir la ventana de vídeo.")

        f_mic = tk.Frame(self._content, bg=C["card"], pady=6, padx=10)
        f_mic.pack(fill="x", pady=2)
        def _on_mic_toggle():
            if self._usemic_var.get():
                self._audio_var.set("mic")
        tk.Checkbutton(f_mic, text=" 🎤 Usar micrófono como entrada de audio principal", variable=self._usemic_var,
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
        tk.Label(self._content, text="ID de Cámara trasera (para webcam):",
                 bg=C["bg"], fg=C["text2"], font=FONT_UI_B).pack(anchor="w", pady=(8, 4))
        self._camid_var = tk.StringVar(value=self._data.get("camera_id", "0"))
        cb_cam = ttk.Combobox(self._content, textvariable=self._camid_var, values=["0", "1", "2"], width=8, state="readonly")
        cb_cam.pack(anchor="w", padx=4, pady=(0, 10))

        tk.Label(self._content, text="Argumentos adicionales de scrcpy (extra_args):",
                 bg=C["bg"], fg=C["text2"], font=FONT_UI_B).pack(anchor="w", pady=(8, 4))
        self._extra_var = tk.StringVar(value=self._data.get("extra_args", ""))
        e_extra = ttk.Entry(self._content, textvariable=self._extra_var, width=42, font=FONT_MONO)
        e_extra.pack(anchor="w", padx=4)
        tk.Label(self._content, text="Ejemplos: '--no-control', '--max-fps 30', '--no-audio'",
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
        tk.Label(self._content, text="Perfil listo para guardar:", bg=C["bg"],
                 fg=C["text2"], font=FONT_UI_B).pack(anchor="w", pady=(6, 4))
        box = tk.Text(self._content, bg=C["card2"], fg=C["text"], font=FONT_MONO,
                      height=11, relief="flat", bd=0, state="normal", wrap="word")
        box.insert("1.0", "\n".join(lines))
        box.config(state="disabled")
        box.pack(fill="both", expand=True, pady=4)
        tk.Label(self._content, text="✔  Pulsa 'Guardar perfil' para finalizar.",
                 bg=C["bg"], fg=C["green"], font=FONT_UI_B).pack(pady=(4, 0))
