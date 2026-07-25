import tkinter as tk
from tkinter import ttk, messagebox
from .utils import C, FONT_FAMILY, FONT_UI, FONT_UI_B, FONT_SM, FONT_LG, FONT_MONO, FONT_CARD

# ─────────────────────────────────────────────────────────────────────────────
# Helpers de layout (usan tokens del sistema de diseño — sin hex hardcoded)
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
                 fg=C["text2"], font=FONT_SM, padx=9, pady=6,
                 wraplength=280).pack()


# ─────────────────────────────────────────────────────────────────────────────
# Tarjeta de acción (grid de 3 columnas en pestaña Acciones)
# ─────────────────────────────────────────────────────────────────────────────

def _card_button(parent, icon_text: str, title: str, desc: str,
                 command, style_bg: str, style_hover: str,
                 row: int, col: int, shortcut: str = ""):
    """Tarjeta de acción con hover, clic y tooltip con atajo de teclado."""
    outer = tk.Frame(parent, bg=C["card2"], padx=2, pady=2)
    outer.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

    inner = tk.Frame(outer, bg=style_bg, cursor="hand2")
    inner.pack(fill="both", expand=True)

    top_row = tk.Frame(inner, bg=style_bg)
    top_row.pack(pady=(12, 6), padx=8)
    tk.Label(top_row, text=icon_text, font=(FONT_FAMILY, 20, "bold"),
             bg=style_bg, fg="#FFFFFF").pack(side="left", padx=(0, 8))
    tk.Label(top_row, text=title, font=FONT_UI_B,
             bg=style_bg, fg="#FFFFFF").pack(side="left")

    tk.Label(inner, text=desc, font=FONT_SM, wraplength=130,
             bg=style_bg, fg=C["muted"], justify="center"
             ).pack(pady=(0, 14), padx=8)

    def enter(_): inner.config(bg=style_hover); _recolor(inner, style_hover)
    def leave(_): inner.config(bg=style_bg);    _recolor(inner, style_bg)
    def click(_): command()

    for w in [inner] + inner.winfo_children():
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
    """Chip oscuro con texto de comando y botón de copia integrado."""
    chip = tk.Frame(parent, bg=C["card3"], padx=8, pady=4,
                    highlightbackground=C["sep"], highlightthickness=1)
    chip.pack(fill="x", padx=20, pady=3)

    tk.Label(chip, text=cmd, bg=C["card3"], fg=C["cyan"],
             font=FONT_MONO, anchor="w").pack(side="left", fill="x", expand=True)

    def copy():
        if root:
            root.clipboard_clear()
            root.clipboard_append(cmd)
        else:
            chip.clipboard_clear()
            chip.clipboard_append(cmd)
        copy_btn.config(text="✔ Copiado", fg=C["green"])
        chip.after(2000, lambda: copy_btn.config(text="📋 Copiar", fg=C["muted"]))

    copy_btn = tk.Label(chip, text="📋 Copiar", bg=C["card3"], fg=C["muted"],
                        font=FONT_SM, cursor="hand2")
    copy_btn.pack(side="right", padx=4)
    copy_btn.bind("<Button-1>", lambda _: copy())
    return chip


# ─────────────────────────────────────────────────────────────────────────────
# AccordionItem — FAQ expandible con animación suave
# ─────────────────────────────────────────────────────────────────────────────

class AccordionItem(tk.Frame):
    """
    Elemento de FAQ acordeón con apertura/cierre animado.
    El contenido se pasa como una función build_fn(content_frame) que
    rellena el frame interior con los widgets deseados.
    """
    _ANIM_STEPS = 8
    _ANIM_MS    = 12   # ms entre steps — fluido sin ser lento

    def __init__(self, parent, title: str, build_fn, **kw):
        super().__init__(parent, bg=C["card"], **kw)
        self._title    = title
        self._expanded = False
        self._anim_id  = None

        # ── Header ────────────────────────────────────────────────────
        self._hdr = tk.Frame(self, bg=C["card2"], cursor="hand2")
        self._hdr.pack(fill="x")

        self._arrow = tk.Label(self._hdr, text="▶", bg=C["card2"],
                               fg=C["purple"], font=FONT_UI_B, width=2)
        self._arrow.pack(side="left", padx=(10, 4), pady=10)

        tk.Label(self._hdr, text=title, bg=C["card2"], fg=C["text"],
                 font=FONT_UI_B, anchor="w").pack(side="left", fill="x",
                                                   expand=True, pady=10)

        # Separador inferior del header
        tk.Frame(self, bg=C["sep"], height=1).pack(fill="x")

        # ── Contenido (oculto por defecto) ────────────────────────────
        self._content_outer = tk.Frame(self, bg=C["bg"])
        self._content_inner = tk.Frame(self._content_outer, bg=C["bg"])
        self._content_inner.pack(fill="both", padx=10, pady=(6, 10))

        # Construir widgets del contenido
        build_fn(self._content_inner)

        # Bindings de toggle
        for w in [self._hdr, self._arrow] + self._hdr.winfo_children():
            w.bind("<Button-1>", self._toggle)
            w.bind("<Return>",   self._toggle)

        # Hover del header
        self._hdr.bind("<Enter>", lambda _: self._hdr.config(bg=C["card3"]) or
                        [c.config(bg=C["card3"]) for c in self._hdr.winfo_children()
                         if hasattr(c, 'config')])
        self._hdr.bind("<Leave>", lambda _: self._hdr.config(bg=C["card2"]) or
                        [c.config(bg=C["card2"]) for c in self._hdr.winfo_children()
                         if hasattr(c, 'config')])

        # Separador al final del ítem
        tk.Frame(self, bg=C["sep"], height=1).pack(fill="x")

    def _toggle(self, _=None):
        if self._anim_id:
            self.after_cancel(self._anim_id)
            self._anim_id = None

        if self._expanded:
            self._content_outer.pack_forget()
            self._arrow.config(text="▶")
            self._expanded = False
        else:
            self._content_outer.pack(fill="x")
            self._arrow.config(text="▼")
            self._expanded = True

    def expand(self):
        """Expande este ítem programáticamente."""
        if not self._expanded:
            self._toggle()

    def collapse(self):
        """Colapsa este ítem programáticamente."""
        if self._expanded:
            self._toggle()


# ─────────────────────────────────────────────────────────────────────────────
# Toast — Notificación flotante no bloqueante
# ─────────────────────────────────────────────────────────────────────────────

class Toast:
    """Notificación emergente ligera en la esquina inferior derecha de la ventana."""
    def __init__(self, root: tk.Tk, message: str, level: str = "info", duration: int = 3500):
        self.root = root
        colors = {
            "info":    (C["card2"],     C["cyan"]),
            "success": (C["green_dim"], C["green"]),
            "warning": (C["card2"],     C["orange"]),
            "error":   (C["card2"],     C["red"]),
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
# ProfileWizard — Asistente paso a paso de creación de perfiles
# ─────────────────────────────────────────────────────────────────────────────

class ProfileWizard(tk.Toplevel):
    STEPS = [
        ("📝", "Nombre del perfil",   "Elige un nombre descriptivo para identificar este perfil fácilmente."),
        ("🎯", "¿Qué quieres hacer?", "Selecciona el caso de uso principal. Esto preseleccionará los ajustes óptimos."),
        ("🖼️", "Calidad de imagen",   "Define la resolución y la velocidad de bits del vídeo.\nMayor calidad = más consumo de CPU y batería."),
        ("🔊", "Fuente de audio",     "Elige qué audio se captura desde el teléfono."),
        ("🔋", "Opciones de batería", "Controla el comportamiento de la pantalla del teléfono durante la sesión."),
        ("✅", "Resumen",             "Revisa la configuración y guarda el perfil."),
    ]

    PRESETS = {
        "🎮 Jugar en pantalla grande": {
            "bitrate": "16M", "max_size": "1920", "max_fps": "60",
            "audio_source": "playback", "video_codec": "h264",
            "turn_screen_off": False, "stay_awake": True,
            "force_screen_off_keyevent": False, "extra_args": "",
        },
        "📡 Stream con OBS (solo audio mic)": {
            "bitrate": "4M", "max_size": "1080", "max_fps": "30",
            "audio_source": "mic", "video_codec": "h264",
            "turn_screen_off": True, "stay_awake": True,
            "force_screen_off_keyevent": True, "extra_args": "--no-video",
        },
        "📷 Usar cámara trasera como webcam": {
            "bitrate": "12M", "max_size": "1920", "max_fps": "30",
            "audio_source": "mic", "video_codec": "h264",
            "turn_screen_off": False, "stay_awake": True,
            "force_screen_off_keyevent": False,
            "extra_args": "--video-source=camera --camera-id 0",
        },
        "⚡ Espejo ligero (bajo consumo)": {
            "bitrate": "4M", "max_size": "720", "max_fps": "30",
            "audio_source": "playback", "video_codec": "h264",
            "turn_screen_off": False, "stay_awake": True,
            "force_screen_off_keyevent": False, "extra_args": "",
        },
    }

    def __init__(self, parent, on_save_callback):
        super().__init__(parent)
        self.title("Asistente de nuevo perfil — MASV")
        self.geometry("580x540")
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self.grab_set()

        self._cb   = on_save_callback
        self._step = 0
        self._data = {
            "name": "", "bitrate": "8M", "max_size": "1080", "max_fps": "60",
            "audio_source": "playback", "video_codec": "h264", "camera_id": "0",
            "turn_screen_off": True, "stay_awake": True,
            "force_screen_off_keyevent": False, "extra_args": "",
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
                                   font=FONT_SM, anchor="w", wraplength=370, justify="left")
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
        elif step == 4:
            self._data["turn_screen_off"]          = self._scroff_var.get()
            self._data["stay_awake"]               = self._awake_var.get()
            self._data["force_screen_off_keyevent"] = self._kev_var.get()
        return True

    def _finish(self):
        self._collect_step(self._step)
        self._cb(self._data)
        self.destroy()

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
        self._audio_var = tk.StringVar(value=self._data["audio_source"])
        for emoji_lbl, val, tip in [
            ("🔈 playback", "playback", "Audio del sistema del teléfono."),
            ("🎤 Micrófono","mic",      "Micrófono físico. Ideal para Huawei con --no-video."),
            ("🔇 Sin audio","no-audio", "Solo vídeo, sin captura de audio."),
        ]:
            f = tk.Frame(self._content, bg=C["card"], pady=8, padx=12)
            f.pack(fill="x", pady=5)
            tk.Radiobutton(f, text=f"  {emoji_lbl}", variable=self._audio_var, value=val,
                           bg=C["card"], fg=C["text"], selectcolor=C["blue"],
                           activebackground=C["card"], font=FONT_UI_B, anchor="w").pack(side="left")
            tk.Label(f, text=tip, bg=C["card"], fg=C["muted"],
                     font=FONT_SM, justify="left", wraplength=280).pack(side="left", padx=12)

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
        self._collect_step(4)
        d = self._data
        lines = [
            f"  Nombre    : {d['name']}",
            f"  Bitrate   : {d['bitrate']}",
            f"  Resolución: {d['max_size']}p",
            f"  FPS máx   : {d['max_fps']}",
            f"  Códec     : {d['video_codec']}",
            f"  Audio     : {d['audio_source']}",
            f"  Pantalla apagada : {'Sí' if d['turn_screen_off'] else 'No'}",
            f"  Despierto        : {'Sí' if d['stay_awake'] else 'No'}",
            f"  Keyevent EMUI    : {'Sí' if d['force_screen_off_keyevent'] else 'No'}",
        ]
        if d.get("extra_args"):
            lines.append(f"  Args extra: {d['extra_args']}")
        tk.Label(self._content, text="Perfil listo para guardar:", bg=C["bg"],
                 fg=C["text2"], font=FONT_UI_B).pack(anchor="w", pady=(8,4))
        box = tk.Text(self._content, bg=C["card2"], fg=C["text"], font=FONT_MONO,
                      height=10, relief="flat", bd=0, state="normal", wrap="word")
        box.insert("1.0", "\n".join(lines))
        box.config(state="disabled")
        box.pack(fill="both", expand=True, pady=4)
        tk.Label(self._content, text="✔  Pulsa 'Guardar perfil' para finalizar.",
                 bg=C["bg"], fg=C["green"], font=FONT_UI_B).pack(pady=(6,0))
