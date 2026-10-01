import sys
import tkinter as tk
from .i18n import _
from tkinter import ttk, messagebox
import webbrowser
from .utils import C, FONT_FAMILY, FONT_UI, FONT_UI_B, FONT_SM, FONT_LG, FONT_MONO, FONT_CARD, FONT_XL
from .ui_widgets import (
    _row, _sep, _section, Tooltip, _card_button, _cmd_chip,
    AccordionItem, ProfileWizard, bind_mousewheel
)


class UIBuilder:
    def __init__(self, app_context, callbacks):
        self.ctx = app_context
        self.cb  = callbacks
        self.refs = {}          # Referencias a widgets actualizables
        self._faq_items = []    # Referencia a AccordionItems de la FAQ

    # ─────────────────────────────────────────────────────────────────
    # Vista Simple / Básica (Quick-Cast Dashboard Moderno)
    # ─────────────────────────────────────────────────────────────────

    def build_simple_view(self, parent):
        p = parent
        for w in p.winfo_children():
            w.destroy()

        canvas = tk.Canvas(p, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(p, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=C["bg"])
        _cwin = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _resize(e): canvas.itemconfig(_cwin, width=e.width)
        def _scroll(e): canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<Configure>", _resize)
        inner.bind("<Configure>", _scroll)
        bind_mousewheel(inner, canvas)

        container = tk.Frame(inner, bg=C["bg"], padx=12, pady=10)
        container.pack(fill="both", expand=True)

        # ── 1. Tarjeta: Dispositivo Activo ───────────────────────────
        dev_card = _section(container, _("📱  Dispositivo Android Activo"), pady=(0, 8), padx=0)
        
        dev_row = tk.Frame(dev_card, bg=C["card"])
        dev_row.pack(fill="x", pady=4)

        tk.Label(dev_row, text=_("Dispositivo:"), bg=C["card"], fg=C["muted"], font=FONT_UI_B, width=10, anchor="w").pack(side="left")
        
        btn_refresh = tk.Button(dev_row, text=_("🔄 Buscar"), bg=C["card2"], fg=C["text"],
                                font=FONT_SM, relief="flat", bd=0, padx=8, pady=3, cursor="hand2",
                                command=self.cb.get('refresh_devices'))
        btn_refresh.pack(side="right", padx=(4, 0))
        Tooltip(btn_refresh, _("Buscar dispositivos conectados (USB o Wi-Fi)"))

        self.refs['simple_dev_combo'] = ttk.Combobox(dev_row, textvariable=self.ctx.active_device, state="readonly", font=FONT_UI)
        self.refs['simple_dev_combo'].pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.refs['simple_dev_combo'].bind("<<ComboboxSelected>>", self.cb.get('on_dev_select'))

        self.refs['simple_trust_lbl'] = tk.Label(dev_row, text="", bg=C["card"], fg=C["green"], font=FONT_SM)
        self.refs['simple_trust_lbl'].pack(side="right", padx=4)

        # ── 2. Tarjeta: Perfil Rápido de Transmisión ─────────────────
        prof_card = _section(container, _("🎮  Perfil de Transmisión"), pady=(0, 8), padx=0)

        # Botones rápidos de 1-clic para perfiles estándar
        presets_row = tk.Frame(prof_card, bg=C["card"])
        presets_row.pack(fill="x", pady=(2, 6))

        def _select_preset(name):
            profiles = self.ctx.profile_mgr.get_profiles()
            if name in profiles:
                self.ctx.active_profile.set(name)
                self.ctx.save_current_config()
                if self.cb.get('on_active_profile_change'):
                    self.cb.get('on_active_profile_change')()

        for icon, title, prof_name in [
            ("🎮", _("Juego"), "Juego Rápido"),
            ("🎙️", _("Stream"), "Stream OBS"),
            ("📷", _("Webcam"), "Webcam HD")
        ]:
            pb = tk.Button(presets_row, text=f"{icon} {title}", bg=C["card2"], fg=C["text"],
                           font=FONT_SM, relief="flat", bd=0, padx=8, pady=5, cursor="hand2",
                           command=lambda p=prof_name: _select_preset(p))
            pb.pack(side="left", padx=2, fill="x", expand=True)

        prof_row = tk.Frame(prof_card, bg=C["card"])
        prof_row.pack(fill="x", pady=4)

        tk.Label(prof_row, text=_("Perfil:"), bg=C["card"], fg=C["muted"], font=FONT_SM, width=10, anchor="w").pack(side="left")

        btn_new_prof = tk.Button(prof_row, text=_("✨ Nuevo"), bg=C["card2"], fg=C["indigo"],
                                 font=FONT_SM, relief="flat", bd=0, padx=8, pady=3, cursor="hand2",
                                 command=self.cb.get('open_wizard'))
        btn_new_prof.pack(side="right", padx=(4, 0))
        Tooltip(btn_new_prof, _("Crear un nuevo perfil personalizado con el asistente."))

        self.refs['simple_prof_combo'] = ttk.Combobox(prof_row, textvariable=self.ctx.active_profile, state="readonly", font=FONT_UI)
        self.refs['simple_prof_combo'].pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.refs['simple_prof_combo'].bind("<<ComboboxSelected>>", self.cb.get('on_active_profile_change'))

        # Argumentos adicionales opcionales
        cmd_frame = tk.Frame(prof_card, bg=C["card"])
        cmd_frame.pack(fill="x", pady=(4, 2))
        tk.Label(cmd_frame, text=_("Args extra:"), bg=C["card"], fg=C["muted"], font=FONT_SM, width=10, anchor="w").pack(side="left")
        self.refs['simple_extra_cmd_var'] = tk.StringVar(value="")
        e_extra = ttk.Entry(cmd_frame, textvariable=self.refs['simple_extra_cmd_var'])
        e_extra.pack(side="left", fill="x", expand=True)
        Tooltip(e_extra, _("Argumentos adicionales para scrcpy (ej: --always-on-top --fullscreen)"))

        # ── 3. Tarjeta Hero: Control de Transmisión Principal ────────
        hero_card = tk.Frame(container, bg=C["card2"], padx=18, pady=14,
                             highlightbackground=C["card_border"], highlightthickness=1)
        hero_card.pack(fill="x", pady=(0, 10))

        hero_btn_row = tk.Frame(hero_card, bg=C["card2"])
        hero_btn_row.pack(fill="x", pady=4)

        btn_start = tk.Button(hero_btn_row, text=_("▶  INICIAR TRANSMISIÓN"),
                              bg=C["blue"], fg="#FFFFFF", font=(FONT_FAMILY, 12, "bold"),
                              relief="flat", bd=0, padx=24, pady=10, cursor="hand2",
                              command=self.cb.get('toggle_scene'))
        btn_start.pack(side="left", fill="x", expand=True, padx=(0, 10))
        Tooltip(btn_start, _("Lanzar transmisión con scrcpy (Ctrl+I)"))

        btn_stop = tk.Button(hero_btn_row, text=_("■  Detener"),
                             bg=C["red"], fg="#FFFFFF", font=(FONT_FAMILY, 11, "bold"),
                             relief="flat", bd=0, padx=18, pady=10, cursor="hand2",
                             command=self.cb.get('stop_current'))
        btn_stop.pack(side="right")
        Tooltip(btn_stop, _("Detener la transmisión activa del dispositivo seleccionado."))

        # ── 4. Mini-Dock de Utilidad y Mando Rápido ──────────────────
        dock_card = _section(container, _("⚡  Controles Rápidos del Teléfono"), pady=(0, 6), padx=0)
        dock_row = tk.Frame(dock_card, bg=C["card"])
        dock_row.pack(fill="x", pady=4)

        for icon, txt, code, tip in [
            ("☀️", _("Pantalla On"), "screen_on", _("Encender pantalla")),
            ("🌙", _("Pantalla Off"), "screen_off", _("Apagar pantalla")),
            ("🔊", _("Vol +"), 24, _("Subir volumen")),
            ("🔉", _("Vol -"), 25, _("Bajar volumen")),
            ("📋", _("Pegar PC"), "paste_text", _("Pegar portapapeles del PC"))
        ]:
            b = tk.Button(dock_row, text=f"{icon} {txt}", bg=C["card2"], fg=C["text2"],
                          font=FONT_SM, relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
                          command=lambda c=code: self.cb.get('send_keyevent')(c))
            b.pack(side="left", padx=3, fill="x", expand=True)
            Tooltip(b, tip)

    # ─────────────────────────────────────────────────────────────────
    # Pestaña 1: Acciones (Hub de Transmisión Avanzado)
    # ─────────────────────────────────────────────────────────────────

    def build_tab_actions(self, parent):
        p = parent
        canvas = tk.Canvas(p, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(p, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=C["bg"])
        _cwin = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _resize(e): canvas.itemconfig(_cwin, width=e.width)
        def _scroll(e): canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<Configure>", _resize)
        inner.bind("<Configure>", _scroll)
        bind_mousewheel(inner, canvas)

        # ── Header de dispositivo + perfil activo ────────────────────
        info = tk.Frame(inner, bg=C["card"], pady=8, padx=14,
                        highlightbackground=C["card_border"], highlightthickness=1)
        info.pack(fill="x", padx=14, pady=(10, 6))
        
        d_box = tk.Frame(info, bg=C["card"])
        d_box.pack(side="left")
        tk.Label(d_box, text=_("Dispositivo:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
        self.refs['action_device_lbl'] = tk.Label(d_box, textvariable=self.ctx.active_device,
                                                  bg=C["card"], fg=C["text"], font=FONT_UI_B)
        self.refs['action_device_lbl'].pack(side="left")
        self.refs['action_trust_lbl'] = tk.Label(d_box, text="", bg=C["card"], fg=C["green"], font=FONT_SM)
        self.refs['action_trust_lbl'].pack(side="left", padx=(6, 0))

        p_box = tk.Frame(info, bg=C["card"])
        p_box.pack(side="right")
        tk.Label(p_box, text=_("Perfil:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
        self.refs['action_profile_lbl'] = tk.Label(p_box, textvariable=self.ctx.active_profile,
                                                   bg=C["card"], fg=C["cyan"], font=FONT_UI_B)
        self.refs['action_profile_lbl'].pack(side="left")

        # ── Hero Panel de Control ───────────────────────────────────
        hero = tk.Frame(inner, bg=C["card"], padx=16, pady=12,
                        highlightbackground=C["card_border"], highlightthickness=1)
        hero.pack(fill="x", padx=14, pady=4)

        hero_left = tk.Frame(hero, bg=C["card"])
        hero_left.pack(side="left", fill="both", expand=True)

        tk.Label(hero_left, text=_("Transmisión de Pantalla"), bg=C["card"], fg=C["text"], font=FONT_CARD).pack(anchor="w")
        tk.Label(hero_left, text=_("Inicia o detiene la sesión de scrcpy para el dispositivo activo."), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(anchor="w", pady=(2, 6))

        btn_bar = tk.Frame(hero_left, bg=C["card"])
        btn_bar.pack(anchor="w")

        btn_start = tk.Button(btn_bar, text=_("▶  Iniciar Transmisión"), bg=C["blue"], fg="#FFFFFF",
                              font=FONT_UI_B, relief="flat", bd=0, padx=16, pady=6, cursor="hand2",
                              command=self.cb.get('toggle_scene'))
        btn_start.pack(side="left", padx=(0, 8))
        Tooltip(btn_start, "Lanza scrcpy con el perfil seleccionado (Ctrl+I)")

        btn_stop = tk.Button(btn_bar, text=_("■  Detener"), bg=C["card2"], fg=C["text"],
                             font=FONT_UI_B, relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
                             command=self.cb.get('stop_current'))
        btn_stop.pack(side="left", padx=(0, 8))
        Tooltip(btn_stop, "Detiene la transmisión activa del dispositivo.")

        # Herramientas secundarias
        tools_sec = tk.Frame(hero, bg=C["card"])
        tools_sec.pack(side="right", anchor="e")

        tk.Label(tools_sec, text=_("Herramientas:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(anchor="e", pady=(0, 2))
        tb = tk.Frame(tools_sec, bg=C["card"])
        tb.pack(anchor="e")

        btn_adb = tk.Button(tb, text=_("↺ ADB"), bg=C["card2"], fg=C["text2"], font=FONT_SM,
                            relief="flat", bd=0, padx=8, pady=4, cursor="hand2", command=self.cb.get('restart_adb'))
        btn_adb.pack(side="left", padx=2)
        Tooltip(btn_adb, "Reinicia el servidor ADB en caso de desconexión.")

        btn_cam = tk.Button(tb, text=_("📷 Webcam"), bg=C["card2"], fg=C["indigo"], font=FONT_SM,
                            relief="flat", bd=0, padx=8, pady=4, cursor="hand2", command=self.cb.get('route_cam'))
        btn_cam.pack(side="left", padx=2)
        Tooltip(btn_cam, "Enruta la cámara hacia /dev/video9 (Linux).")

        btn_panic = tk.Button(tb, text=_("⚠ Todo"), bg=C["red_dim"], fg=C["red"], font=FONT_SM,
                              relief="flat", bd=0, padx=8, pady=4, cursor="hand2", command=self.cb.get('panic_kill'))
        btn_panic.pack(side="left", padx=2)
        Tooltip(btn_panic, "Cierra todas las sesiones activas de golpe.")

        # ── Tabla de Sesiones Activas ────────────────────────────────
        sf_lbl = tk.Frame(inner, bg=C["bg"])
        sf_lbl.pack(fill="x", padx=14, pady=(12, 4))
        tk.Label(sf_lbl, text=_("  Sesiones activas"), bg=C["bg"],
                 fg=C["indigo"], font=FONT_UI_B).pack(side="left")
        tk.Label(sf_lbl, text=_("Supr = detener · Clic derecho = menú contextual"),
                 bg=C["bg"], fg=C["muted"], font=FONT_SM).pack(side="right")

        sf = tk.Frame(inner, bg=C["card2"], highlightbackground=C["card_border"], highlightthickness=1)
        sf.pack(fill="both", expand=True, padx=14, pady=4)

        cols = ("serial", "profile", "pid", "uptime", "status")
        self.refs['sess_tree'] = ttk.Treeview(sf, columns=cols, show="headings",
                                              height=5, selectmode="browse")
        for col_id, heading, width, stretch in [
            ("serial",  "Dispositivo",  200, True),
            ("profile", "Perfil",       140, True),
            ("pid",     "PID",           80, False),
            ("uptime",  "Tiempo",        90, False),
            ("status",  "Estado",       130, True),
        ]:
            self.refs['sess_tree'].heading(col_id, text=heading)
            self.refs['sess_tree'].column(col_id, width=width,
                                         anchor="center", stretch=stretch)

        self.refs['sess_tree'].tag_configure("RUN", foreground=C["green"])
        self.refs['sess_tree'].tag_configure("STP", foreground=C["red"])
        sess_sb = ttk.Scrollbar(sf, orient="vertical",
                                command=self.refs['sess_tree'].yview)
        self.refs['sess_tree'].configure(yscrollcommand=sess_sb.set)
        self.refs['sess_tree'].pack(side="left", fill="both", expand=True)
        sess_sb.pack(side="right", fill="y")

        self.refs['sess_tree'].bind("<Delete>",  self.cb.get('stop_selected'))
        self.refs['sess_tree'].bind("<Button-3>", self.cb.get('sess_context_menu'))

        btn_container = tk.Frame(inner, bg=C["bg"])
        btn_container.pack(fill="x", padx=14, pady=(4, 14))
        tk.Button(btn_container, text=_("✕  Detener sesión seleccionada"), bg=C["red_dim"], fg=C["red"],
                  font=FONT_SM, relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
                  command=self.cb.get('stop_selected')).pack(side="right")

    # ─────────────────────────────────────────────────────────────────
    # Pestaña 2: Controles Remotos y APK
    # ─────────────────────────────────────────────────────────────────

    def build_tab_controls(self, parent):
        p = parent
        canvas = tk.Canvas(p, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(p, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=C["bg"])
        _cwin = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _resize(e): canvas.itemconfig(_cwin, width=e.width)
        def _scroll(e): canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<Configure>", _resize)
        inner.bind("<Configure>", _scroll)
        bind_mousewheel(inner, canvas)

        # ── 1. Mando de Controles del Hardware & Navegación ──────────
        c_sec = _section(inner, "🎮  Mando de Control Remoto (ADB Keyevents)", pady=(10, 8), padx=14)

        info_f = tk.Frame(c_sec, bg=C["card"], padx=8, pady=2)
        info_f.pack(fill="x", pady=(0, 6))

        d_box = tk.Frame(info_f, bg=C["card"])
        d_box.pack(side="left")
        tk.Label(d_box, text=_("Dispositivo:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
        self.refs['ctrl_device_lbl'] = tk.Label(d_box, textvariable=self.ctx.active_device,
                                                bg=C["card"], fg=C["green"], font=FONT_UI_B)
        self.refs['ctrl_device_lbl'].pack(side="left")
        self.refs['ctrl_trust_lbl'] = tk.Label(d_box, text="", bg=C["card"], fg=C["green"], font=FONT_SM)
        self.refs['ctrl_trust_lbl'].pack(side="left", padx=(6, 0))

        p_box = tk.Frame(info_f, bg=C["card"])
        p_box.pack(side="right")
        tk.Label(p_box, text=_("Perfil:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
        self.refs['ctrl_profile_lbl'] = tk.Label(p_box, textvariable=self.ctx.active_profile,
                                                 bg=C["card"], fg=C["cyan"], font=FONT_UI_B)
        self.refs['ctrl_profile_lbl'].pack(side="left")

        # Layout tipo Mando Multimedia Ergonómico
        remote_frame = tk.Frame(c_sec, bg=C["card"])
        remote_frame.pack(pady=4)

        # Fila 1: Pantalla y Notificaciones
        r1 = tk.Frame(remote_frame, bg=C["card"])
        r1.pack(pady=3)
        for txt, code, tip, color, fg in [
            ("☀️ Encender Pantalla", "screen_on", "Enciende la pantalla del dispositivo", C["green_dim"], C["green"]),
            ("🌙 Apagar Pantalla", "screen_off", "Apaga la pantalla del dispositivo", C["red_dim"], C["red"]),
            ("🔔 Notificaciones", "notifications", "Desplegar barra de notificaciones", C["card2"], C["text"]),
        ]:
            b = tk.Button(r1, text=txt, bg=color, fg=fg, font=FONT_SM, relief="flat", bd=0, padx=12, pady=5,
                          cursor="hand2", command=lambda c=code: self.cb.get('send_keyevent')(c))
            b.pack(side="left", padx=4)
            Tooltip(b, tip)

        # Fila 2: Volumen y Audio
        r2 = tk.Frame(remote_frame, bg=C["card"])
        r2.pack(pady=3)
        for txt, code, tip in [
            ("🔊 Vol +", 24, "Subir volumen"),
            ("🔉 Vol -", 25, "Bajar volumen"),
            ("🔇 Silenciar", 164, "Silenciar todo el audio"),
        ]:
            b = tk.Button(r2, text=txt, bg=C["card2"], fg=C["text2"], font=FONT_SM, relief="flat", bd=0, padx=14, pady=5,
                          cursor="hand2", command=lambda c=code: self.cb.get('send_keyevent')(c))
            b.pack(side="left", padx=4)
            Tooltip(b, tip)

        # Fila 3: Navegación y Utilidad
        r3 = tk.Frame(remote_frame, bg=C["card"])
        r3.pack(pady=3)
        for txt, code, tip, color in [
            ("◀ Atrás", 4, "Retroceder a la pantalla anterior", C["card2"]),
            ("🏠 Inicio", 3, "Ir a la pantalla principal", C["card2"]),
            ("📑 Recientes", 187, "Abrir selector de apps recientes", C["card2"]),
            ("📋 Pegar PC", "paste_text", "Pega el texto del portapapeles al dispositivo", C["card3"]),
        ]:
            b = tk.Button(r3, text=txt, bg=color, fg=C["text"], font=FONT_SM, relief="flat", bd=0, padx=12, pady=5,
                          cursor="hand2", command=lambda c=code: self.cb.get('send_keyevent')(c))
            b.pack(side="left", padx=4)
            Tooltip(b, tip)

        # ── 2. Gestor de Aplicaciones (Instalar APK) ──────────────────
        apk_sec = _section(inner, "📦  Gestor de Aplicaciones Android (Instalador APK)", pady=(6, 14), padx=14)

        tk.Label(apk_sec, text=_("Selecciona e instala archivos (.apk) directamente desde tu computadora hacia el dispositivo."),
                 bg=C["card"], fg=C["muted"], font=FONT_SM, wraplength=650, justify="left").pack(anchor="w", padx=4, pady=(2, 6))

        apk_r = tk.Frame(apk_sec, bg=C["card"])
        apk_r.pack(fill="x", pady=2)

        btn_apk = tk.Button(apk_r, text=_("📦  Seleccionar e Instalar APK…"), bg=C["card2"], fg=C["green"],
                            font=FONT_UI_B, relief="flat", bd=0, padx=16, pady=6, cursor="hand2",
                            command=self.cb.get('install_apk'))
        btn_apk.pack(side="left", padx=4)
        Tooltip(btn_apk, "Abre el explorador de archivos para elegir un .apk e instalarlo vía ADB.")

        # Tip en su propia fila para evitar truncamiento
        tip_r = tk.Frame(apk_sec, bg=C["card"])
        tip_r.pack(fill="x", pady=(6, 4))
        tk.Label(tip_r, text=_("💡 Tip: Durante una sesión activa, también puedes arrastrar archivos .apk directo a la ventana de transmisión."),
                 bg=C["card"], fg=C["cyan"], font=FONT_SM, wraplength=650, justify="left").pack(anchor="w", padx=4)

    # ─────────────────────────────────────────────────────────────────
    # Pestaña 3: Dispositivo (Gestión & Wi-Fi Modular)
    # ─────────────────────────────────────────────────────────────────

    def build_tab_device(self, parent):
        p = parent
        for w in p.winfo_children():
            w.destroy()

        canvas = tk.Canvas(p, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(p, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=C["bg"])
        _cwin = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _resize(e): canvas.itemconfig(_cwin, width=e.width)
        def _scroll(e): canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<Configure>", _resize)
        inner.bind("<Configure>", _scroll)
        bind_mousewheel(inner, canvas)

        # ── Pantalla de dependencias faltantes ──────────────────────
        self.refs['install_frame'] = tk.Frame(inner, bg=C["bg"])
        
        # ── Contenido principal ──────────────────────────────────────
        self.refs['dep_frame'] = tk.Frame(inner, bg=C["bg"])
        self.refs['dep_frame'].pack(fill="both", expand=True)

        # 1. Dispositivos Detectados & Bóveda
        sf = _section(self.refs['dep_frame'], "🔍  Dispositivos Detectados & Bóveda de Confianza", pady=(8, 6), padx=14)
        r0 = _row(sf, pady=2)
        btn_scan = tk.Button(r0, text=_("🔄  Buscar dispositivos"), bg=C["blue"], fg="#FFFFFF",
                             font=FONT_SM, relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
                             command=self.cb.get('refresh_devices'))
        btn_scan.pack(side="left", padx=(0, 8))
        Tooltip(btn_scan, "Escanea dispositivos USB y WiFi (Ctrl+R)")

        self.refs['scan_lbl'] = tk.Label(r0, text="", bg=C["card"], fg=C["muted"], font=FONT_SM)
        self.refs['scan_lbl'].pack(side="left")

        btn_vault = tk.Button(r0, text=_("🛡️ Bóveda de Confiables"), bg=C["card2"], fg=C["indigo"],
                              font=FONT_SM, relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                              command=self.cb.get('open_trust_vault'))
        btn_vault.pack(side="right")
        Tooltip(btn_vault, "Administra los dispositivos autorizados en la bóveda de seguridad.")

        list_frame = tk.Frame(sf, bg=C["card2"], highlightbackground=C["card_border"], highlightthickness=1)
        list_frame.pack(fill="both", expand=True, pady=4)
        self.refs['dev_listbox'] = tk.Listbox(
            list_frame, bg=C["card2"], fg=C["text"],
            selectbackground=C["card3"], selectforeground="#FFF",
            font=(FONT_FAMILY, 10), relief="flat", bd=0,
            highlightthickness=0, activestyle="none", height=4)
        self.refs['dev_listbox'].pack(side="left", fill="both", expand=True)
        dev_sb = ttk.Scrollbar(list_frame, orient="vertical",
                                command=self.refs['dev_listbox'].yview)
        dev_sb.pack(side="right", fill="y")
        self.refs['dev_listbox'].configure(yscrollcommand=dev_sb.set)
        self.refs['dev_listbox'].bind("<<ListboxSelect>>", self.cb.get('on_dev_select'))

        info_act_row = _row(sf, pady=2)
        self.refs['dev_info_lbl'] = tk.Label(info_act_row,
                                             text=_("Selecciona un dispositivo de la lista."),
                                             bg=C["card"], fg=C["muted"], font=FONT_SM)
        self.refs['dev_info_lbl'].pack(side="left")

        self.refs['dev_trust_btn'] = tk.Button(info_act_row, text=_("🛡️ Confiar / Alias"),
                                               bg=C["card2"], fg=C["text"], font=FONT_SM,
                                               relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
                                               command=self.cb.get('open_device_trust_modal'))
        self.refs['dev_trust_btn'].pack(side="right")
        Tooltip(self.refs['dev_trust_btn'], "Configura el estado de confianza y alias en la bóveda.")

        # 2. Conexión Wi-Fi & Seguridad Inalámbrica
        wf = _section(self.refs['dep_frame'], "📡  Conexión Inalámbrica Wi-Fi & Blindaje", pady=(4, 6), padx=14)
        
        # Modo A: Emparejamiento Seguro (Android 11+)
        pair_box = tk.Frame(wf, bg=C["card2"], padx=10, pady=8, highlightbackground=C["card_border"], highlightthickness=1)
        pair_box.pack(fill="x", pady=(2, 6))

        tk.Label(pair_box, text=_("🔒 Emparejamiento Seguro (Android 11+)"), bg=C["card2"], fg=C["green"], font=FONT_UI_B).pack(anchor="w")
        tk.Label(pair_box, text=_("Empareja de forma segura mediante código de 6 dígitos usando TLS."), bg=C["card2"], fg=C["muted"], font=FONT_SM).pack(anchor="w", pady=(0, 4))

        pr1 = tk.Frame(pair_box, bg=C["card2"])
        pr1.pack(fill="x", pady=2)

        tk.Label(pr1, text=_("IP:Puerto:"), bg=C["card2"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
        self.refs['pair_ip_entry'] = ttk.Entry(pr1, width=18)
        self.refs['pair_ip_entry'].insert(0, "192.168.1.")
        self.refs['pair_ip_entry'].pack(side="left", padx=4)
        Tooltip(self.refs['pair_ip_entry'], "IP y puerto que muestra el diálogo 'Vincular con código'.")

        tk.Label(pr1, text=_("Código:"), bg=C["card2"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(6, 4))
        self.refs['pair_code_entry'] = ttk.Entry(pr1, width=8)
        self.refs['pair_code_entry'].pack(side="left", padx=4)
        Tooltip(self.refs['pair_code_entry'], "Código de vinculación de 6 dígitos.")

        btn_pair = tk.Button(pr1, text=_("🔒 Emparejar (`adb pair`)"), bg=C["green_dim"], fg=C["green"],
                             font=FONT_SM, relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
                             command=self.cb.get('pair_wifi'))
        btn_pair.pack(side="left", padx=6)

        # Modo B: Conexión Directa TCP/IP & Blindaje
        tcp_box = tk.Frame(wf, bg=C["card2"], padx=10, pady=8, highlightbackground=C["card_border"], highlightthickness=1)
        tcp_box.pack(fill="x", pady=(2, 4))

        tk.Label(tcp_box, text=_("📶 Conexión Directa TCP/IP & Blindaje"), bg=C["card2"], fg=C["indigo"], font=FONT_UI_B).pack(anchor="w")

        wr = tk.Frame(tcp_box, bg=C["card2"])
        wr.pack(fill="x", pady=(4, 4))

        tk.Label(wr, text=_("IP:"), bg=C["card2"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
        self.refs['ip_entry'] = ttk.Entry(wr, width=16)
        self.refs['ip_entry'].insert(0, "192.168.1.")
        self.refs['ip_entry'].pack(side="left", padx=4)

        tk.Label(wr, text=_(":"), bg=C["card2"], fg=C["muted"]).pack(side="left")
        self.refs['port_entry'] = ttk.Entry(wr, width=6)
        self.refs['port_entry'].insert(0, "5555")
        self.refs['port_entry'].pack(side="left", padx=4)

        btn_getip = tk.Button(wr, text=_("📡 Obtener IP"), bg=C["card3"], fg=C["text2"],
                              font=FONT_SM, relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
                              command=self.cb.get('get_device_ip'))
        btn_getip.pack(side="left", padx=6)

        btns_w = tk.Frame(tcp_box, bg=C["card2"])
        btns_w.pack(fill="x", pady=(4, 2))

        tk.Button(btns_w, text=_("Conectar"), bg=C["blue"], fg="#FFFFFF", font=FONT_SM,
                  relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
                  command=self.cb.get('connect_wifi')).pack(side="left", padx=(0, 6))

        tk.Button(btns_w, text=_("Habilitar TCP/IP (USB→WiFi)"), bg=C["card3"], fg=C["text2"], font=FONT_SM,
                  relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                  command=self.cb.get('enable_tcpip')).pack(side="left", padx=(0, 6))
        
        btn_lockdown = tk.Button(btns_w, text=_("🛡️ Blindar TCP/IP"), bg=C["red_dim"], fg=C["red"], font=FONT_SM,
                                 relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                                 command=self.cb.get('lockdown_tcpip'))
        btn_lockdown.pack(side="right")
        Tooltip(btn_lockdown, "Revoca el puerto 5555 en el teléfono y lo devuelve a modo USB seguro.")

        # 3. v4l2loopback
        vf = _section(self.refs['dep_frame'], "📷  Webcam Virtual (v4l2loopback)", pady=(4, 12), padx=14)
        self.refs['v4l2_lbl'] = tk.Label(vf, text=_("Verificando módulo…"), bg=C["card"], fg=C["orange"], font=FONT_SM)
        self.refs['v4l2_lbl'].pack(anchor="w", padx=4, pady=2)
        vr = _row(vf, pady=2)
        self.refs['load_v4l2_btn'] = tk.Button(vr, text=_("Cargar módulo"), bg=C["card2"], fg=C["text"],
                                               font=FONT_SM, relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                                               command=self.cb.get('setup_v4l2'))
        self.refs['load_v4l2_btn'].pack(side="left", padx=(0, 6))

        self.refs['route_cam_btn'] = tk.Button(vr, text=_("Enrutar cámara → /dev/video9"), bg=C["green_dim"], fg=C["green"],
                                               font=FONT_SM, relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                                               command=self.cb.get('route_cam'))
        self.refs['route_cam_btn'].pack(side="left", padx=(0, 6))

    # ─────────────────────────────────────────────────────────────────
    # Pestaña 4: Perfiles
    # ─────────────────────────────────────────────────────────────────

    def build_tab_profile(self, parent):
        p = parent
        canvas = tk.Canvas(p, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(p, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=C["bg"])
        _cwin = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _resize(e): canvas.itemconfig(_cwin, width=e.width)
        def _scroll(e): canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<Configure>", _resize)
        inner.bind("<Configure>", _scroll)
        bind_mousewheel(inner, canvas)

        sf = _section(inner, "📁  Perfiles Guardados", pady=(8, 6), padx=14)
        
        list_f = tk.Frame(sf, bg=C["card2"], highlightbackground=C["card_border"], highlightthickness=1)
        list_f.pack(fill="both", expand=True, pady=4)

        self.refs['profile_listbox'] = tk.Listbox(
            list_f, bg=C["card2"], fg=C["text"],
            selectbackground=C["card3"], selectforeground="#FFF",
            font=(FONT_FAMILY, 10), relief="flat", bd=0,
            highlightthickness=0, activestyle="none", height=5)
        self.refs['profile_listbox'].pack(fill="both", expand=True)
        self.refs['profile_listbox'].bind("<<ListboxSelect>>", self.cb.get('on_profile_listbox_sel'))

        pa = _row(sf, pady=2)
        btn_new = tk.Button(pa, text=_("✨  Nuevo perfil (asistente)"), bg=C["blue"], fg="#FFFFFF",
                            font=FONT_SM, relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
                            command=self.cb.get('open_wizard'))
        btn_new.pack(side="left", padx=(0, 6))
        Tooltip(btn_new, "Crea un perfil con el asistente paso a paso.")

        btn_del = tk.Button(pa, text=_("🗑  Eliminar"), bg=C["red_dim"], fg=C["red"],
                            font=FONT_SM, relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                            command=self.cb.get('delete_profile'))
        btn_del.pack(side="left")
        Tooltip(btn_del, "Elimina el perfil seleccionado.")

        df = _section(inner, "🔍  Detalle del Perfil Seleccionado", pady=(4, 6), padx=14)
        from .ui_widgets import ProfileChipsView
        self.refs['profile_chips'] = ProfileChipsView(df)
        self.refs['profile_chips'].pack(fill="both", expand=True, pady=2)

        af = _section(inner, "🎯  Perfil Activo para la Próxima Sesión", pady=(4, 12), padx=14)
        ar = _row(af, pady=2)
        tk.Label(ar, text=_("Perfil:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 6))
        self.refs['active_profile_combo'] = ttk.Combobox(
            ar, textvariable=self.ctx.active_profile, state="readonly", width=24)
        self.refs['active_profile_combo'].pack(side="left")
        self.refs['active_profile_combo'].bind("<<ComboboxSelected>>", self.cb.get('on_active_profile_change'))

        btn_start_prof = tk.Button(ar, text=_("▶  Lanzar con este perfil"), bg=C["blue"], fg="#FFFFFF",
                                   font=FONT_SM, relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
                                   command=self.cb.get('start_profile'))
        btn_start_prof.pack(side="right")
        Tooltip(btn_start_prof, "Lanza scrcpy inmediatamente con el perfil y dispositivo activo.")

    # ─────────────────────────────────────────────────────────────────
    # Pestaña 5: Consola de Diagnóstico
    # ─────────────────────────────────────────────────────────────────

    def build_tab_console(self, parent):
        p = parent
        for w in p.winfo_children():
            w.destroy()

        tb = tk.Frame(p, bg=C["card2"], pady=4, padx=8)
        tb.pack(fill="x", side="top")
        tk.Label(tb, text=_("Filtrar:"), bg=C["card2"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(4, 6))

        for name, filter_key in [(_("Todos"), _("ALL")), (_("Errores"), _("ERROR")),
                                  (_("ADB"), _("ADB")), (_("Scrcpy"), _("INFO"))]:
            btn = tk.Button(tb, text=name, bg=C["card"], fg=C["text"],
                            font=FONT_SM, relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
                            command=lambda k=filter_key: self.cb.get('filter_log')(k))
            btn.pack(side="left", padx=2)

        tk.Button(tb, text=_("📋  Copiar todo"), bg=C["card3"], fg=C["text"],
                  font=FONT_SM, relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
                  command=self.cb.get('copy_log')).pack(side="right", padx=4)

        self.refs['log_txt'] = tk.Text(p, bg="#0E0D0B", fg=C["text"], wrap="word",
                                       font=FONT_MONO, state="disabled", relief="flat", bd=0)
        log_sb = ttk.Scrollbar(p, orient="vertical", command=self.refs['log_txt'].yview)
        self.refs['log_txt'].configure(yscrollcommand=log_sb.set)
        self.refs['log_txt'].pack(side="left", fill="both", expand=True)
        log_sb.pack(side="right", fill="y")

        for tag, color in [("ERROR", C["red"]), ("WARNING", C["orange"]),
                           ("INFO", C["cyan"]), (_("ADB"), "#A0D8EF"), ("OK", C["green"])]:
            self.refs['log_txt'].tag_config(tag, foreground=color)

        cb = tk.Frame(p, bg=C["card2"])
        cb.pack(fill="x", side="bottom")
        tk.Button(cb, text=_("🗑  Limpiar consola"), bg=C["card3"], fg=C["text"],
                  font=FONT_SM, relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
                  command=self.cb.get('clear_log')).pack(side="left", padx=8, pady=4)
        tk.Button(cb, text=_("📄  Abrir archivo de log"), bg=C["card"], fg=C["muted"],
                  font=FONT_SM, relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
                  command=self.cb.get('open_log')).pack(side="right", padx=8, pady=4)

    # ─────────────────────────────────────────────────────────────────
    # Pestaña 6: Ayuda — FAQ & Documentación
    # ─────────────────────────────────────────────────────────────────

    def build_tab_help(self, parent):
        p = parent
        for w in p.winfo_children():
            w.destroy()

        self._faq_items = []
        root_ref = self.ctx.root

        hdr = tk.Frame(p, bg=C["card"], pady=10, padx=16,
                       highlightbackground=C["card_border"], highlightthickness=1)
        hdr.pack(fill="x", padx=12, pady=(8, 4))
        
        tk.Label(hdr, text=_("❓  Centro de Ayuda, Documentación y FAQ"),
                 bg=C["card"], fg=C["indigo"], font=FONT_LG).pack(side="left")
        tk.Label(hdr, text=_("Atajo rápido: Ctrl+H"),
                 bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="right")

        canvas = tk.Canvas(p, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(p, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=C["bg"])
        _cwin = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _resize(e): canvas.itemconfig(_cwin, width=e.width)
        def _scroll(e): canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<Configure>", _resize)
        inner.bind("<Configure>", _scroll)
        bind_mousewheel(inner, canvas)

        def _add(title, build_fn):
            item = AccordionItem(inner, title, build_fn)
            item.pack(fill="x", padx=12, pady=3)
            self._faq_items.append(item)

        # ── 1. Inicio rápido ─────────────────────────────────────────
        def _faq_quickstart(f):
            steps = [
                "1. Conecta tu teléfono Android a tu computadora con un cable USB de datos de buena calidad.",
                "2. Activa la Depuración USB en tu Android (ver sección 2 abajo).",
                "3. En la pantalla del teléfono, acepta la ventana emergente '¿Permitir depuración USB?'.",
                "4. Ve a la sección 📱 Dispositivos y pulsa  🔄 Buscar dispositivos.",
                "5. Selecciona tu teléfono de la lista detectada.",
                "6. Ve a 🚀 Quick Cast (o Acciones) y pulsa  ▶ INICIAR TRANSMISIÓN."
            ]
            for s in steps:
                tk.Label(f, text=s, bg=C["bg"], fg=C["text2"], font=FONT_UI,
                         anchor="w", justify="left", wraplength=680).pack(fill="x", padx=16, pady=2)

        _add("🚀  1. Inicio rápido — Primeros pasos con MASV", _faq_quickstart)

        # ── 2. Depuración USB ─────────────────────────────────────────
        def _faq_usb_debug(f):
            tk.Label(f, text=_("Paso 1 — Activa las Opciones de desarrollador:"),
                     bg=C["bg"], fg=C["indigo"], font=FONT_UI_B, anchor="w").pack(fill="x", padx=16, pady=(4, 2))
            for line in [
                "   a. Abre Ajustes en tu teléfono.",
                "   b. Ve a 'Acerca del teléfono' → 'Información de software'.",
                "   c. Toca 7 veces seguidas sobre 'Número de compilación' (Build number).",
                "   d. Aparecerá el mensaje: ¡Ahora eres desarrollador!"
            ]:
                tk.Label(f, text=line, bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w").pack(fill="x", padx=16, pady=1)

            tk.Label(f, text=_("Paso 2 — Activa la Depuración USB:"),
                     bg=C["bg"], fg=C["indigo"], font=FONT_UI_B, anchor="w").pack(fill="x", padx=16, pady=(8, 2))
            for line in [
                "   a. Regresa a Ajustes → Sistema → Opciones para desarrolladores.",
                "   b. Activa el interruptor 'Depuración USB'.",
                "   c. Conecta el cable USB a tu PC y marca 'Permitir siempre desde esta computadora'."
            ]:
                tk.Label(f, text=line, bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w").pack(fill="x", padx=16, pady=1)

        _add("🔌  2. Cómo habilitar la Depuración USB en Android", _faq_usb_debug)

        # ── 3. Dispositivo no detectado ───────────────────────────────
        def _faq_not_found(f):
            tk.Label(f, text=_("Si tu dispositivo no aparece o indica 'unauthorized':"),
                     bg=C["bg"], fg=C["text2"], font=FONT_UI_B).pack(anchor="w", padx=16, pady=4)
            _cmd_chip(f, "adb kill-server", root_ref)
            _cmd_chip(f, "adb start-server", root_ref)
            _cmd_chip(f, "adb devices", root_ref)
            tk.Label(f, text=_("• En Linux: Si no tienes permisos de acceso USB, añade tu usuario al grupo 'plugdev' o instala udev rules."),
                     bg=C["bg"], fg=C["muted"], font=FONT_SM, wraplength=680, justify="left").pack(anchor="w", padx=16, pady=4)

        _add("⚠️  3. El dispositivo no aparece o dice 'no autorizado'", _faq_not_found)

        # ── 4. Dependencias ───────────────────────────────────────────
        def _faq_deps(f):
            for os_name, cmds in [
                ("🐧 Linux (Debian / Ubuntu / Mint):", ["sudo apt update", "sudo apt install adb scrcpy"]),
                ("🐧 Linux (Arch / Manjaro):", ["sudo pacman -S scrcpy android-tools"]),
                ("🪟 Windows (winget):", ["winget install Genymobile.scrcpy"]),
                ("🍎 macOS (Homebrew):", ["brew install scrcpy android-platform-tools"]),
            ]:
                tk.Label(f, text=os_name, bg=C["bg"], fg=C["indigo"], font=FONT_UI_B).pack(anchor="w", padx=16, pady=(6, 2))
                for c in cmds: _cmd_chip(f, c, root_ref)

        _add("📦  4. Dependencias necesarias (Instalación de adb y scrcpy)", _faq_deps)

        # ── 5. WiFi TCP/IP ────────────────────────────────────────────
        def _faq_wifi(f):
            steps = [
                "1. Conecta el teléfono por USB una primera vez para autorizar.",
                "2. Asegúrate de que el teléfono y la PC estén conectados a la MISMA red Wi-Fi local.",
                "3. En la sección 📱 Dispositivos → pulsa 'Habilitar TCP/IP (USB→WiFi)'.",
                "4. Pulsa '📡 Obtener IP' y a continuación pulsa 'Conectar'.",
                "5. ¡Ya puedes desconectar el cable USB y transmitir de forma inalámbrica!"
            ]
            for s in steps:
                tk.Label(f, text=s, bg=C["bg"], fg=C["text2"], font=FONT_UI,
                         anchor="w", justify="left", wraplength=680).pack(fill="x", padx=16, pady=2)

        _add("📡  5. Conexión inalámbrica por Wi-Fi TCP/IP (sin cables)", _faq_wifi)

        # ── 6. Emparejamiento Seguro Android 11+ ──────────────────────
        def _faq_pair(f):
            steps = [
                "En Android 11 y versiones superiores no necesitas conectar ningún cable para iniciar Wi-Fi:",
                "1. En el teléfono: Ajustes → Opciones de desarrollador → 'Depuración inalámbrica' (activar).",
                "2. Toca sobre 'Vincular dispositivo con código de vinculación'.",
                "3. El teléfono mostrará una IP con un puerto efímero (ej. 192.168.1.50:38291) y un código PIN de 6 dígitos.",
                "4. En MASV, ingresa esa IP:Puerto y el código de 6 dígitos en la sección 'Emparejamiento Seguro'.",
                "5. Pulsa '🔒 Emparejar (`adb pair`)' y la conexión quedará autenticada con cifrado TLS."
            ]
            for s in steps:
                tk.Label(f, text=s, bg=C["bg"], fg=C["text2"], font=FONT_UI,
                         anchor="w", justify="left", wraplength=680).pack(fill="x", padx=16, pady=2)

        _add("🔒  6. Emparejamiento Seguro en Android 11+ (adb pair)", _faq_pair)

        # ── 7. Webcam en OBS ──────────────────────────────────────────
        def _faq_obs(f):
            steps = [
                "1. En MASV, selecciona el perfil preestablecido 'Webcam HD' o 'Cámara Trasera'.",
                "2. En Linux: pulsa 'Cargar módulo' en la sección Webcam Virtual para activar v4l2loopback.",
                "3. Pulsa 'Enrutar cámara → /dev/video9'.",
                "4. Abre OBS Studio → Fuentes → Añadir '+' → 'Dispositivo de captura de video (V4L2)'.",
                "5. Selecciona el dispositivo '/dev/video9' y disfruta de tu cámara de celular en 1080p con cero latencia."
            ]
            for s in steps:
                tk.Label(f, text=s, bg=C["bg"], fg=C["text2"], font=FONT_UI,
                         anchor="w", justify="left", wraplength=680).pack(fill="x", padx=16, pady=2)

        _add("📷  7. Cómo usar la cámara como Webcam en OBS Studio", _faq_obs)

        # ── 8. Pantalla apagada ───────────────────────────────────────
        def _faq_screen_off(f):
            steps = [
                "• scrcpy permite transmitir la pantalla manteniendo el display físico del teléfono totalmente apagado:",
                "  - Ahorra hasta un 80% de batería en sesiones largas de streaming.",
                "  - Evita que el dispositivo se caliente.",
                "• Puedes activar esta opción creando o editando un perfil en ⚙️ Perfiles marcando 'Apagar pantalla del dispositivo (--turn-screen-off)'.",
                "• Para teléfonos Huawei / Honor / EMUI donde scrcpy no apaga la pantalla directamente, activa la casilla de compatibilidad EMUI (Keyevent 26)."
            ]
            for s in steps:
                tk.Label(f, text=s, bg=C["bg"], fg=C["text2"], font=FONT_UI,
                         anchor="w", justify="left", wraplength=680).pack(fill="x", padx=16, pady=2)

        _add("⚡  8. Pantalla apagada mientras transmites (Ahorro de batería)", _faq_screen_off)

        # ── 9. Atajos de teclado ──────────────────────────────────────
        def _faq_shortcuts(f):
            tk.Label(f, text=_("Atajos en la ventana de scrcpy:"), bg=C["bg"], fg=C["indigo"], font=FONT_UI_B).pack(anchor="w", padx=16, pady=(4, 2))
            shortcuts_scrcpy = [
                ("Alt + f", "Pantalla completa"),
                ("Alt + g", "Ajustar ventana al tamaño original (1:1)"),
                ("Alt + h", "Botón Inicio (Home)"),
                ("Alt + b", "Botón Atrás (Back)"),
                ("Alt + s", "Selector de aplicaciones recientes"),
                ("Alt + p", "Encender / Apagar pantalla del dispositivo"),
                ("Alt + r", "Rotar orientación de pantalla"),
                ("Alt + ↑ / ↓", "Subir / Bajar volumen"),
            ]
            for sc, desc in shortcuts_scrcpy:
                row = tk.Frame(f, bg=C["bg"])
                row.pack(fill="x", padx=16, pady=1)
                tk.Label(row, text=f"• {sc}:", bg=C["bg"], fg=C["text"], font=FONT_UI_B, width=14, anchor="w").pack(side="left")
                tk.Label(row, text=desc, bg=C["bg"], fg=C["text2"], font=FONT_UI).pack(side="left")

            tk.Label(f, text=_("Atajos en MASV:"), bg=C["bg"], fg=C["indigo"], font=FONT_UI_B).pack(anchor="w", padx=16, pady=(8, 2))
            shortcuts_masv = [
                ("Ctrl + I", "Iniciar o alternar transmisión de pantalla"),
                ("Ctrl + R", "Refrescar y escanear dispositivos"),
                ("Ctrl + H", "Abrir este Centro de Ayuda"),
                ("Ctrl + B", "Colapsar / Expandir barra lateral (Dashboard)"),
                ("Ctrl + Q", "Salir con blindaje automático"),
            ]
            for sc, desc in shortcuts_masv:
                row = tk.Frame(f, bg=C["bg"])
                row.pack(fill="x", padx=16, pady=1)
                tk.Label(row, text=f"• {sc}:", bg=C["bg"], fg=C["text"], font=FONT_UI_B, width=14, anchor="w").pack(side="left")
                tk.Label(row, text=desc, bg=C["bg"], fg=C["text2"], font=FONT_UI).pack(side="left")

        _add("⌨  9. Atajos de teclado en MASV y scrcpy", _faq_shortcuts)

        # ── 10. Solución de problemas ─────────────────────────────────
        def _faq_troubleshooting(f):
            tips = [
                ("Pantalla en negro o scrcpy se cierra de inmediato:",
                 "Prueba cambiar el códec de video en ⚙️ Perfiles a H.264 o baja la resolución a 1080p o 720p."),
                ("Audio no se escucha en PC:",
                 "La transmisión nativa de audio de scrcpy requiere Android 11 o superior. En Android 10 o inferior selecciona 'mic' como fuente de audio."),
                ("Lag o retraso en Wi-Fi:",
                 "Conecta tu PC por cable Ethernet al router y usa la banda Wi-Fi de 5 GHz en el teléfono con bitrate a 8M."),
                ("El puerto 5555 sigue abierto en el teléfono:",
                 "Pulsa el botón '🛡️ Blindar TCP/IP' o '🔒 Blindar Red' en MASV para ejecutar `adb usb` y cerrar el puerto inmediatamente.")
            ]
            for title, desc in tips:
                tk.Label(f, text=f"• {title}", bg=C["bg"], fg=C["orange"], font=FONT_UI_B, anchor="w").pack(fill="x", padx=16, pady=(4, 1))
                tk.Label(f, text=f"  {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=(0, 4))

        _add("🛠  10. Solución de problemas comunes y optimización", _faq_troubleshooting)

        # ── 11. Dispositivo en estado Offline ─────────────────────────
        def _faq_offline(f):
            tips = [
                _("El teléfono perdió comunicación con el socket ADB debido a desconexión o suspensión de energía USB."),
                _("Solución: reconecta el cable, asegúrate de que el puerto USB no suspenda la energía y haz clic en 'Reiniciar ADB' en MASV.")
            ]
            for desc in tips:
                tk.Label(f, text=f"• {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=2)

        _add(_("🔴 Dispositivo en estado Offline"), _faq_offline)

        # ── 12. Huawei Y9 y Android 10 ───────────────────────────────
        def _faq_huawei(f):
            tips = [
                _("Android 10 no soporta captura nativa de audio interno en scrcpy (requiere Android 11+), por lo que MASV fuerza automáticamente --no-audio."),
                _("Recomendación: para el chipset Kirin 710, usa el códec H.264 a 8Mbps para obtener mejor rendimiento.")
            ]
            for desc in tips:
                tk.Label(f, text=f"• {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=2)

        _add(_("📱 Huawei Y9 y Android 10 (Restricciones y Optimización)"), _faq_huawei)

        # ── 13. Bóveda y Modo Seguro ─────────────────────────────────
        def _faq_vault(f):
            tips = [
                _("Registrar dispositivos confiables previene conexiones no autorizadas o accidentales en redes públicas Wi-Fi."),
                _("Usa el blindaje de red (Modo Seguro) para revocar el puerto 5555 (adb usb), cerrando así el acceso remoto al teléfono.")
            ]
            for desc in tips:
                tk.Label(f, text=f"• {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=2)

        _add(_("🛡️ Bóveda de Dispositivos Confiables y Modo Seguro"), _faq_vault)

        # ── 14. Modo Estudio Fotográfico ─────────────────────────────
        def _faq_studio(f):
            tips = [
                _("Puedes usar el feed limpio de la cámara trasera de tu Android en OBS Studio."),
                _("Con la opción Webcam Virtual en Linux, MASV monta la cámara nativamente usando el módulo v4l2loopback para cero latencia.")
            ]
            for desc in tips:
                tk.Label(f, text=f"• {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=2)

        _add(_("📷 Modo Estudio Fotográfico & Clean Camera Feed"), _faq_studio)

        # ── 15. Cierre Limpio vs Bandeja ─────────────────────────────
        def _faq_exit(f):
            tips = [
                _("El botón Salir (o Ctrl+Q) termina por completo la aplicación y el rastreador de dispositivos (Device Tracker)."),
                _("Esto libera de forma limpia los puertos de red y bloqueos, algo útil si otras herramientas necesitan acceder a ADB.")
            ]
            for desc in tips:
                tk.Label(f, text=f"• {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=2)

        _add(_("🚪 Cierre Limpio vs. Minimizar a la Bandeja"), _faq_exit)
