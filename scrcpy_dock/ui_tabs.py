import tkinter as tk
from .i18n import _
from tkinter import ttk, messagebox
import webbrowser
from .utils import C, FONT_FAMILY, FONT_UI, FONT_UI_B, FONT_SM, FONT_LG, FONT_MONO, FONT_CARD
from .ui_widgets import (
    _row, _sep, _section, Tooltip, _card_button, _cmd_chip,
    AccordionItem, ProfileWizard,
)


class UIBuilder:
    def __init__(self, app_context, callbacks):
        self.ctx = app_context
        self.cb  = callbacks
        self.refs = {}          # Referencias a widgets actualizables
        self._faq_items = []    # Referencia a AccordionItems de la FAQ

    # ─────────────────────────────────────────────────────────────────
    # Vista Simple (Básica)
    # ─────────────────────────────────────────────────────────────────

    def build_simple_view(self, parent):
        p = parent

        # Centrar contenido
        center_frame = tk.Frame(p, bg=C["bg"])
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Título
        tk.Label(center_frame, text="Modo Simple", bg=C["bg"], fg=C["purple"], font=FONT_LG).pack(pady=(0, 20))

        # Dispositivo
        dev_frame = _row(center_frame, bg=C["bg"])
        tk.Label(dev_frame, text="📱 Dispositivo:", bg=C["bg"], fg=C["text"], font=FONT_UI_B, width=15, anchor="w").pack(side="left")
        self.refs['simple_dev_combo'] = ttk.Combobox(dev_frame, textvariable=self.ctx.active_device, state="readonly", width=30)
        self.refs['simple_dev_combo'].pack(side="left", padx=10)
        btn_refresh = ttk.Button(dev_frame, text="🔄", width=3, command=self.cb.get('refresh_devices'), style="Secondary.TButton")
        btn_refresh.pack(side="left")
        Tooltip(btn_refresh, "Refrescar dispositivos conectados")

        self.refs['simple_dev_combo'].bind("<<ComboboxSelected>>", self.cb.get('on_dev_select'))

        # Perfil
        prof_frame = _row(center_frame, bg=C["bg"])
        tk.Label(prof_frame, text="⚙️ Perfil:", bg=C["bg"], fg=C["text"], font=FONT_UI_B, width=15, anchor="w").pack(side="left")
        self.refs['simple_prof_combo'] = ttk.Combobox(prof_frame, textvariable=self.ctx.active_profile, state="readonly", width=30)
        self.refs['simple_prof_combo'].pack(side="left", padx=10)
        btn_new_prof = ttk.Button(prof_frame, text="✨", width=3, command=self.cb.get('open_wizard'), style="Purple.TButton")
        btn_new_prof.pack(side="left")
        Tooltip(btn_new_prof, "Crear un nuevo perfil")

        self.refs['simple_prof_combo'].bind("<<ComboboxSelected>>", self.cb.get('on_active_profile_change'))

        # Comandos extra (Opcional)
        cmd_frame = _row(center_frame, bg=C["bg"])
        tk.Label(cmd_frame, text="🧩 Comandos extra:", bg=C["bg"], fg=C["text"], font=FONT_UI_B, width=15, anchor="w").pack(side="left")

        self.refs['simple_extra_cmd_var'] = tk.StringVar(value="")
        e_extra = ttk.Entry(cmd_frame, textvariable=self.refs['simple_extra_cmd_var'], width=35)
        e_extra.pack(side="left", padx=10)
        Tooltip(e_extra, "Argumentos adicionales para scrcpy (opcional)")

        _sep(center_frame, C["sep"])

        # Acciones principales
        actions_frame = tk.Frame(center_frame, bg=C["bg"])
        actions_frame.pack(pady=20)

        btn_start = ttk.Button(actions_frame, text="▶  Iniciar", command=self.cb.get('toggle_scene'), style="Primary.TButton")
        btn_start.pack(side="left", padx=10)
        Tooltip(btn_start, "Iniciar transmisión")

        btn_stop = ttk.Button(actions_frame, text="■  Detener", command=self.cb.get('stop_current'), style="Danger.TButton")
        btn_stop.pack(side="left", padx=10)
        Tooltip(btn_stop, "Detener transmisión activa")

        btn_adb = ttk.Button(actions_frame, text="↺  Reiniciar ADB", command=self.cb.get('restart_adb'), style="Warn.TButton")
        btn_adb.pack(side="left", padx=10)
        Tooltip(btn_adb, "Reiniciar el servidor ADB")

    # ─────────────────────────────────────────────────────────────────
    # Pestaña 1: Acciones (Hub de Transmisión)
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

        # ── Header de dispositivo + perfil activo ────────────────────
        info = tk.Frame(inner, bg=C["card"], pady=8, padx=12)
        info.pack(fill="x", padx=16, pady=(12, 8))
        
        d_box = tk.Frame(info, bg=C["card"])
        d_box.pack(side="left")
        tk.Label(d_box, text=_("Dispositivo:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
        self.refs['action_device_lbl'] = tk.Label(d_box, textvariable=self.ctx.active_device,
                                                  bg=C["card"], fg=C["text"], font=FONT_UI_B)
        self.refs['action_device_lbl'].pack(side="left")

        p_box = tk.Frame(info, bg=C["card"])
        p_box.pack(side="right")
        tk.Label(p_box, text=_("Perfil:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
        self.refs['action_profile_lbl'] = tk.Label(p_box, textvariable=self.ctx.active_profile,
                                                   bg=C["card"], fg=C["cyan"], font=FONT_UI_B)
        self.refs['action_profile_lbl'].pack(side="left")

        # ── Hero Panel de Control (Acción Principal Destacada) ───────
        hero = tk.Frame(inner, bg=C["card"], padx=20, pady=16, highlightbackground=C["sep"], highlightthickness=1)
        hero.pack(fill="x", padx=16, pady=4)

        hero_left = tk.Frame(hero, bg=C["card"])
        hero_left.pack(side="left", fill="both", expand=True)

        tk.Label(hero_left, text=_("Transmisión de Pantalla"), bg=C["card"], fg=C["text"], font=FONT_CARD).pack(anchor="w")
        tk.Label(hero_left, text=_("Inicia o detiene la sesión de scrcpy para el dispositivo activo."), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(anchor="w", pady=(2, 8))

        btn_bar = tk.Frame(hero_left, bg=C["card"])
        btn_bar.pack(anchor="w")

        btn_start = ttk.Button(btn_bar, text=_("▶  Iniciar Transmisión"),
                               command=self.cb.get('toggle_scene'), style="Primary.TButton")
        btn_start.pack(side="left", padx=(0, 10))
        Tooltip(btn_start, "Lanza scrcpy con el perfil seleccionado.", shortcut="Ctrl+I")

        btn_stop = ttk.Button(btn_bar, text=_("■  Detener"),
                              command=self.cb.get('stop_current'), style="Secondary.TButton")
        btn_stop.pack(side="left", padx=(0, 10))
        Tooltip(btn_stop, "Detiene la transmisión activa del dispositivo.")

        # Herramientas secundarias (Barra compacta)
        tools_sec = tk.Frame(hero, bg=C["card"])
        tools_sec.pack(side="right", anchor="e")

        tk.Label(tools_sec, text=_("Herramientas:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(anchor="e", pady=(0, 4))
        tb = tk.Frame(tools_sec, bg=C["card"])
        tb.pack(anchor="e")

        btn_adb = ttk.Button(tb, text=_("↺ ADB"), command=self.cb.get('restart_adb'), style="Warn.TButton")
        btn_adb.pack(side="left", padx=2)
        Tooltip(btn_adb, "Reinicia el servidor ADB en caso de desconexión.")

        btn_cam = ttk.Button(tb, text=_("📷 Webcam"), command=self.cb.get('route_cam'), style="Purple.TButton")
        btn_cam.pack(side="left", padx=2)
        Tooltip(btn_cam, "Enruta la cámara hacia /dev/video9 (Linux).")

        btn_panic = ttk.Button(tb, text=_("⚠ Todo"), command=self.cb.get('panic_kill'), style="Danger.TButton")
        btn_panic.pack(side="left", padx=2)
        Tooltip(btn_panic, "Cierra todas las sesiones activas de golpe.")

        # ── Tabla de Sesiones Activas ────────────────────────────────
        sf_lbl = tk.Frame(inner, bg=C["bg"])
        sf_lbl.pack(fill="x", padx=16, pady=(16, 4))
        tk.Label(sf_lbl, text=_("  Sesiones activas"), bg=C["bg"],
                 fg=C["purple"], font=FONT_UI_B).pack(side="left")
        tk.Label(sf_lbl, text=_("Supr = detener · Clic derecho = menú contextual"),
                 bg=C["bg"], fg=C["muted"], font=FONT_SM).pack(side="right")

        sf = tk.Frame(inner, bg=C["card2"])
        sf.pack(fill="both", expand=True, padx=16, pady=4)

        cols = ("serial", "profile", "pid", "uptime", "status")
        self.refs['sess_tree'] = ttk.Treeview(sf, columns=cols, show="headings",
                                              height=6, selectmode="browse")
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
        btn_container.pack(fill="x", padx=16, pady=(6, 16))
        ttk.Button(btn_container, text=_("✕  Detener sesión seleccionada"),
                   command=self.cb.get('stop_selected'),
                   style="Danger.TButton").pack(side="right")


    # ─────────────────────────────────────────────────────────────────
    # Pestaña 2: Controles Remotos y APK (PESTAÑA DEDICADA)
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

        # ── 1. Mando de Controles del Hardware & Navegación ──────────
        c_sec = _section(inner, "🎮  Mando de Control Remoto (ADB Keyevents)", pady=(12, 8))

        # ── Indicador compacto de Dispositivo & Perfil activo ─────────────
        info_f = tk.Frame(c_sec, bg=C["card"], padx=12, pady=4)
        info_f.pack(fill="x", padx=12, pady=(2, 8))

        d_box = tk.Frame(info_f, bg=C["card"])
        d_box.pack(side="left")
        tk.Label(d_box, text=_("Dispositivo:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
        self.refs['ctrl_device_lbl'] = tk.Label(d_box, textvariable=self.ctx.active_device,
                                                bg=C["card"], fg=C["green"], font=FONT_UI_B)
        self.refs['ctrl_device_lbl'].pack(side="left")

        p_box = tk.Frame(info_f, bg=C["card"])
        p_box.pack(side="right")
        tk.Label(p_box, text=_("Perfil:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
        self.refs['ctrl_profile_lbl'] = tk.Label(p_box, textvariable=self.ctx.active_profile,
                                                 bg=C["card"], fg=C["cyan"], font=FONT_UI_B)
        self.refs['ctrl_profile_lbl'].pack(side="left")

        tk.Label(c_sec, text=_("Envía señales directas de hardware y navegación al dispositivo activo sin necesidad de tocar la pantalla."),
                 bg=C["card"], fg=C["muted"], font=FONT_SM, wraplength=700, justify="left").pack(anchor="w", padx=12, pady=(4, 10))

        # Remoto - Layout rediseñado tipo control

        remote_frame = tk.Frame(c_sec, bg=C["card"])
        remote_frame.pack(pady=10)

        # Fila 1: Pantalla y Notificaciones
        r1 = tk.Frame(remote_frame, bg=C["card"])
        r1.pack(pady=5)
        for txt, code, tip, style in [
            ("☀️ Encender Pantalla", "screen_on", "Enciende la pantalla del dispositivo", "Green.TButton"),
            ("🌙 Apagar Pantalla", "screen_off", "Apaga la pantalla del dispositivo (equivale a alt+p en scrcpy)", "Danger.TButton"),
            ("🔔 Notificaciones", "notifications", "Desplegar barra de notificaciones", "Secondary.TButton"),
        ]:
            b = ttk.Button(r1, text=txt, command=lambda c=code: self.cb.get('send_keyevent')(c), style=style)
            b.pack(side="left", padx=5)
            Tooltip(b, tip)

        # Fila 2: Volumen y Audio
        r2 = tk.Frame(remote_frame, bg=C["card"])
        r2.pack(pady=5)
        for txt, code, tip, style in [
            ("🔊 Vol +", 24, "Subir volumen", "Primary.TButton"),
            ("🔉 Vol -", 25, "Bajar volumen", "Primary.TButton"),
            ("🔇 Silenciar", 164, "Silenciar todo el audio", "Warn.TButton"),
        ]:
            b = ttk.Button(r2, text=txt, command=lambda c=code: self.cb.get('send_keyevent')(c), style=style)
            b.pack(side="left", padx=5)
            Tooltip(b, tip)

        # Fila 3: Navegación y Utilidad
        r3 = tk.Frame(remote_frame, bg=C["card"])
        r3.pack(pady=5)
        for txt, code, tip, style in [
            ("◀ Atrás", 4, "Retroceder a la pantalla anterior", "Secondary.TButton"),
            ("🏠 Inicio", 3, "Ir a la pantalla principal", "Secondary.TButton"),
            ("📑 Recientes", 187, "Abrir el selector de aplicaciones recientes", "Secondary.TButton"),
            ("📋 Pegar PC", "paste_text", "Pega el texto del portapapeles del PC al dispositivo", "Purple.TButton"),
        ]:
            b = ttk.Button(r3, text=txt, command=lambda c=code: self.cb.get('send_keyevent')(c), style=style)
            b.pack(side="left", padx=5)
            Tooltip(b, tip)

        # ── 2. Gestor de Aplicaciones (Instalar APK) ──────────────────
        apk_sec = _section(inner, "📦  Gestor de Aplicaciones Android (Instalador APK)", pady=(8, 16))

        tk.Label(apk_sec, text=_("Selecciona e instala archivos de aplicación (.apk) directamente desde tu computadora hacia el dispositivo seleccionado."),
                 bg=C["card"], fg=C["muted"], font=FONT_SM, wraplength=700, justify="left").pack(anchor="w", padx=12, pady=(4, 8))

        apk_r = _row(apk_sec, pady=(4, 10))
        btn_apk = ttk.Button(apk_r, text=_("📦  Seleccionar e Instalar APK…"),
                             command=self.cb.get('install_apk'), style="Green.TButton")
        btn_apk.pack(side="left", padx=8)
        Tooltip(btn_apk, "Abre el explorador de archivos para elegir un archivo .apk e instalarlo vía ADB.")

        tk.Label(apk_r, text=_("💡 Tip: Durante una sesión activa de scrcpy, también puedes arrastrar el archivo .apk a la ventana de transmisión."),
                 bg=C["card"], fg=C["cyan"], font=FONT_SM).pack(side="left", padx=12)


    # ─────────────────────────────────────────────────────────────────
    # Pestaña 3: Dispositivo
    # ─────────────────────────────────────────────────────────────────

    def build_tab_device(self, parent):
        p = parent

        # ── Pantalla de dependencias faltantes ──────────────────────
        self.refs['install_frame'] = tk.Frame(p, bg=C["bg"])
        tk.Label(self.refs['install_frame'], text=_("⚠️"), font=(FONT_FAMILY, 48),
                 bg=C["bg"], fg=C["orange"]).pack(pady=(30, 8))
        tk.Label(self.refs['install_frame'], text=_("Faltan dependencias: adb y/o scrcpy"),
                 bg=C["bg"], fg=C["text"], font=FONT_LG).pack()
        tk.Label(self.refs['install_frame'],
                 text=_("MASV puede instalar automáticamente el núcleo sin necesidad de abrir la terminal:"),
                 bg=C["bg"], fg=C["muted"], font=FONT_UI).pack(pady=(8, 6))

        btn_auto = tk.Button(self.refs['install_frame'], text=_("🚀  Instalar núcleo automáticamente (1-Clic)"),
                             bg=C["green"], fg="#FFFFFF", font=(FONT_FAMILY, 11, "bold"),
                             relief="flat", bd=0, padx=20, pady=10, cursor="hand2",
                             command=self.cb.get('auto_install_deps'))
        btn_auto.pack(pady=(4, 12))
        Tooltip(btn_auto, "Descarga e instala scrcpy y adb automáticamente sin abrir consolas.")

        cmd_f = tk.Frame(self.refs['install_frame'], bg=C["card2"], padx=12, pady=6)
        cmd_f.pack()
        tk.Label(cmd_f, text=_("Instalación manual (opcional): sudo apt install adb scrcpy"), bg=C["card2"],
                 fg=C["muted"], font=FONT_SM).pack()

        btns_i = tk.Frame(self.refs['install_frame'], bg=C["bg"])
        btns_i.pack(pady=12)
        tk.Button(btns_i, text=_("📋  Copiar comando"), bg=C["blue"], fg="#FFF",
                  font=FONT_UI_B, relief="flat", bd=0, padx=14, pady=6,
                  command=self.cb.get('copy_install_cmd')).pack(side="left", padx=8)
        tk.Button(btns_i, text=_("🖥  Abrir terminal"), bg=C["sep"], fg=C["text"],
                  font=FONT_UI_B, relief="flat", bd=0, padx=14, pady=6,
                  command=self.cb.get('open_terminal_install')).pack(side="left", padx=8)

        # ── Contenido principal ──────────────────────────────────────
        self.refs['dep_frame'] = tk.Frame(p, bg=C["bg"])

        sf = _section(self.refs['dep_frame'], "🔍  Buscar dispositivos")
        r0 = _row(sf)
        btn_scan = ttk.Button(r0, text=_("🔄  Buscar dispositivos"),
                              command=self.cb.get('refresh_devices'), style="Primary.TButton")
        btn_scan.pack(side="left", padx=(0, 10))
        Tooltip(btn_scan, "Escanea dispositivos USB y WiFi.", shortcut="Ctrl+R")
        self.refs['scan_lbl'] = tk.Label(r0, text="", bg=C["card"], fg=C["muted"], font=FONT_SM)
        self.refs['scan_lbl'].pack(side="left")

        lf = _section(self.refs['dep_frame'], "📋  Dispositivos detectados", pady=(0, 4))
        list_frame = tk.Frame(lf, bg=C["card2"])
        list_frame.pack(fill="both", expand=True)
        self.refs['dev_listbox'] = tk.Listbox(
            list_frame, bg=C["card2"], fg=C["text"],
            selectbackground=C["blue"], selectforeground="#FFF",
            font=(FONT_FAMILY, 11), relief="flat", bd=0,
            highlightthickness=0, activestyle="none", height=5)
        self.refs['dev_listbox'].pack(side="left", fill="both", expand=True)
        dev_sb = ttk.Scrollbar(list_frame, orient="vertical",
                               command=self.refs['dev_listbox'].yview)
        dev_sb.pack(side="right", fill="y")
        self.refs['dev_listbox'].configure(yscrollcommand=dev_sb.set)
        self.refs['dev_listbox'].bind("<<ListboxSelect>>", self.cb.get('on_dev_select'))

        self.refs['dev_info_lbl'] = tk.Label(self.refs['dep_frame'],
                                             text=_("Selecciona un dispositivo de la lista."),
                                             bg=C["bg"], fg=C["muted"], font=FONT_SM)
        self.refs['dev_info_lbl'].pack(padx=14, pady=4, anchor="w")

        self.refs['no_dev_hint'] = tk.Label(
            self.refs['dep_frame'],
            text=_("¿Problemas? Consulta  →  ❓ Ayuda  →  'Cómo habilitar la Depuración USB'"),
            bg=C["bg"], fg=C["cyan"], font=FONT_SM, cursor="hand2")
        self.refs['no_dev_hint'].bind("<Button-1>", lambda _: self.cb.get('go_to_help_usb')())

        # ── WiFi ─────────────────────────────────────────────────────
        wf = _section(self.refs['dep_frame'], "📡  Conexión WiFi (inalámbrica)", pady=(0, 4))
        wr = _row(wf)
        tk.Label(wr, text=_("IP del teléfono:"), bg=C["card"], fg=C["muted"],
                 font=FONT_SM).pack(side="left", padx=(0, 6))
        self.refs['ip_entry'] = ttk.Entry(wr, width=18)
        self.refs['ip_entry'].insert(0, "192.168.1.")
        self.refs['ip_entry'].pack(side="left", padx=4)
        Tooltip(self.refs['ip_entry'], "IP del teléfono (Ajustes → Acerca del teléfono).")
        tk.Label(wr, text=_(":"), bg=C["card"], fg=C["muted"]).pack(side="left")
        self.refs['port_entry'] = ttk.Entry(wr, width=6)
        self.refs['port_entry'].insert(0, "5555")
        self.refs['port_entry'].pack(side="left", padx=4)

        btn_getip = ttk.Button(wr, text=_("📡 Obtener IP"), command=self.cb.get('get_device_ip'), style="Secondary.TButton")
        btn_getip.pack(side="left", padx=8)
        Tooltip(btn_getip, "Consulta automáticamente la IP WiFi del dispositivo seleccionado vía ADB.")

        btns_w = _row(wf)
        ttk.Button(btns_w, text=_("Conectar"), command=self.cb.get('connect_wifi'),
                   style="Primary.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(btns_w, text=_("Habilitar TCP/IP (USB→WiFi)"),
                   command=self.cb.get('enable_tcpip'),
                   style="Secondary.TButton").pack(side="left")

        # ── v4l2loopback ─────────────────────────────────────────────
        vf = _section(self.refs['dep_frame'], "📷  Webcam Virtual (v4l2loopback)")
        self.refs['v4l2_lbl'] = tk.Label(vf, text=_("Verificando módulo…"),
                                         bg=C["card"], fg=C["orange"], font=FONT_SM)
        self.refs['v4l2_lbl'].pack(anchor="w", padx=4, pady=2)
        vr = _row(vf)
        self.refs['load_v4l2_btn'] = ttk.Button(vr, text=_("Cargar módulo"),
                                                command=self.cb.get('setup_v4l2'),
                                                style="Secondary.TButton")
        self.refs['load_v4l2_btn'].pack(side="left", padx=(0, 8))
        self.refs['route_cam_btn'] = ttk.Button(vr, text=_("Enrutar cámara → /dev/video9"),
                                               command=self.cb.get('route_cam'),
                                               state="disabled", style="Green.TButton")
        self.refs['route_cam_btn'].pack(side="left", padx=(0, 8))
        ttk.Button(vr, text=_("Ver Guía en Ayuda 🔗"), command=lambda: self.cb.get('go_to_help_v4l2')(),
                   style="Ghost.TButton").pack(side="left")

        if not self.ctx.adb or not self.ctx.scrcpy:
            self.refs['install_frame'].pack(fill="both", expand=True, padx=20, pady=20)
        else:
            self.refs['dep_frame'].pack(fill="both", expand=True)

    # ─────────────────────────────────────────────────────────────────
    # Pestaña 4: Perfiles
    # ─────────────────────────────────────────────────────────────────

    def build_tab_profile(self, parent):
        p = parent
        sf = _section(p, "📁  Perfiles guardados")
        self.refs['profile_listbox'] = tk.Listbox(
            sf, bg=C["card2"], fg=C["text"],
            selectbackground=C["purple_dim"], selectforeground="#FFF",
            font=(FONT_FAMILY, 11), relief="flat", bd=0,
            highlightthickness=0, activestyle="none", height=6)
        self.refs['profile_listbox'].pack(fill="both", expand=True)
        self.refs['profile_listbox'].bind("<<ListboxSelect>>",
                                         self.cb.get('on_profile_listbox_sel'))

        self.refs['profile_empty_lbl'] = tk.Label(
            sf,
            text=_("Aún no hay perfiles.\nCrea uno con el botón  ✨ Nuevo perfil  para comenzar."),
            bg=C["card2"], fg=C["muted"], font=FONT_SM, justify="center", pady=12)

        pa = _row(sf)
        btn_new = ttk.Button(pa, text=_("✨  Nuevo perfil (asistente)"),
                             command=self.cb.get('open_wizard'), style="Purple.TButton")
        btn_new.pack(side="left", padx=(0, 8))
        Tooltip(btn_new, "Crea un perfil con el asistente paso a paso.")
        btn_del = ttk.Button(pa, text=_("🗑  Eliminar"),
                             command=self.cb.get('delete_profile'), style="Danger.TButton")
        btn_del.pack(side="left")
        Tooltip(btn_del, "Elimina el perfil seleccionado.")

        df = _section(p, "🔍  Detalle del perfil seleccionado")
        from .ui_widgets import ProfileChipsView
        self.refs['profile_chips'] = ProfileChipsView(df)
        self.refs['profile_chips'].pack(fill="both", expand=True, pady=4)

        af = _section(p, "🎯  Perfil activo para la próxima sesión")
        ar = _row(af)
        tk.Label(ar, text=_("Perfil:"), bg=C["card"], fg=C["muted"],
                 font=FONT_SM).pack(side="left", padx=(0, 6))
        self.refs['active_profile_combo'] = ttk.Combobox(
            ar, textvariable=self.ctx.active_profile, state="readonly", width=24)
        self.refs['active_profile_combo'].pack(side="left")
        self.refs['active_profile_combo'].bind("<<ComboboxSelected>>",
                                              self.cb.get('on_active_profile_change'))

        btn_start_prof = ttk.Button(ar, text=_("▶  Iniciar transmisión con este perfil"),
                                    command=self.cb.get('start_profile'), style="Primary.TButton")
        btn_start_prof.pack(side="right", padx=(8, 0))
        Tooltip(btn_start_prof, "Activa este perfil y lanza la sesión inmediatamente con el dispositivo seleccionado.")

        self.refs['assoc_lbl'] = tk.Label(p, text="", bg=C["bg"],
                                         fg=C["muted"], font=FONT_SM)
        self.refs['assoc_lbl'].pack(padx=14, anchor="w", pady=2)

    # ─────────────────────────────────────────────────────────────────
    # Pestaña 5: Consola
    # ─────────────────────────────────────────────────────────────────

    def build_tab_console(self, parent):
        p = parent
        tb = tk.Frame(p, bg=C["card2"], pady=4, padx=8)
        tb.pack(fill="x", side="top")
        tk.Label(tb, text=_("Filtrar:"), bg=C["card2"], fg=C["muted"],
                 font=FONT_SM).pack(side="left", padx=(4, 6))

        for name, filter_key in [(_("Todos"), _("ALL")), (_("Errores"), _("ERROR")),
                                  (_("ADB"), _("ADB")), (_("Scrcpy"), _("INFO"))]:
            btn = tk.Button(tb, text=name, bg=C["card"], fg=C["text"],
                            font=FONT_SM, relief="flat", bd=0, padx=10, pady=3,
                            command=lambda k=filter_key: self.cb.get('filter_log')(k))
            btn.pack(side="left", padx=2)

        tk.Button(tb, text=_("📋  Copiar todo"), bg=C["sep"], fg=C["text"],
                  font=FONT_SM, relief="flat", bd=0, padx=10, pady=3,
                  command=self.cb.get('copy_log')).pack(side="right", padx=4)

        self.refs['log_txt'] = tk.Text(p, bg="#0B0F19", fg=C["text"], wrap="word",
                                       font=FONT_MONO, state="disabled",
                                       relief="flat", bd=0)
        log_sb = ttk.Scrollbar(p, orient="vertical",
                               command=self.refs['log_txt'].yview)
        self.refs['log_txt'].configure(yscrollcommand=log_sb.set)
        self.refs['log_txt'].pack(side="left", fill="both", expand=True)
        log_sb.pack(side="right", fill="y")

        for tag, color in [("ERROR", C["red"]), ("WARNING", C["orange"]),
                           ("INFO", C["cyan"]), (_("ADB"), _("#A0D8EF")), ("OK", C["green"])]:
            self.refs['log_txt'].tag_config(tag, foreground=color)

        cb = tk.Frame(p, bg=C["card2"])
        cb.pack(fill="x", side="bottom")
        tk.Button(cb, text=_("🗑  Limpiar consola"), bg=C["sep"], fg=C["text"],
                  font=FONT_SM, relief="flat", bd=0, padx=12, pady=6,
                  command=self.cb.get('clear_log')).pack(side="left", padx=8, pady=4)
        tk.Button(cb, text=_("📄  Abrir archivo de log"), bg=C["bg"], fg=C["muted"],
                  font=FONT_SM, relief="flat", bd=0, padx=12, pady=6,
                  command=self.cb.get('open_log')).pack(side="right", padx=8, pady=4)

    # ─────────────────────────────────────────────────────────────────
    # Pestaña 6: Ayuda — FAQ Interactiva Completa
    # ─────────────────────────────────────────────────────────────────

    def build_tab_help(self, parent):
        p = parent
        for w in p.winfo_children():
            w.destroy()

        hdr = tk.Frame(p, bg=C["card"], pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text=_("❓  Preguntas Frecuentes y Documentación"),
                 bg=C["card"], fg=C["purple"], font=FONT_LG).pack(side="left", padx=16)
        tk.Label(hdr, text=_("Ctrl+H"),
                 bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="right", padx=16)

        tk.Frame(p, bg=C["sep"], height=1).pack(fill="x")

        canvas = tk.Canvas(p, bg=C["bg"], highlightthickness=0)
        vsb    = ttk.Scrollbar(p, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        sf = tk.Frame(canvas, bg=C["bg"])
        _win = canvas.create_window((0, 0), window=sf, anchor="nw")

        def _resize(e): canvas.itemconfig(_win, width=e.width)
        def _frame(e):  canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<Configure>", _resize)
        sf.bind("<Configure>", _frame)

        self._faq_items = []
        root_ref = self.ctx.root

        def _add(title, build_fn):
            item = AccordionItem(sf, title, build_fn)
            item.pack(fill="x", padx=12, pady=(0, 2))
            self._faq_items.append(item)

        # ── 0. Inicio rápido ─────────────────────────────────────────
        def _faq_quickstart(f):
            steps = [
                "1. Conecta tu teléfono con un cable USB de datos.",
                "2. Activa la Depuración USB en tu Android (ver sección 2 abajo).",
                "3. En la pantalla del teléfono acepta el mensaje 'Permitir depuración USB'.",
                "4. Ve a la pestaña  📱 Dispositivo  y pulsa  🔄 Buscar dispositivos.",
                "5. Selecciona tu teléfono de la lista.",
                "6. Ve a la pestaña  🚀 Acciones  y pulsa  ▶ Iniciar Transmisión.",
            ]
            for s in steps:
                tk.Label(f, text=s, bg=C["bg"], fg=C["text2"], font=FONT_UI,
                         anchor="w", justify="left", wraplength=680).pack(fill="x", padx=20, pady=2)

        _add("🚀  Inicio rápido — primeros pasos", _faq_quickstart)

        # ── 1. Depuración USB ─────────────────────────────────────────
        def _faq_usb_debug(f):
            tk.Label(f, text=_("Paso 1 — Activa las Opciones de desarrollador:"),
                     bg=C["bg"], fg=C["text2"], font=FONT_UI_B, anchor="w").pack(fill="x", padx=20, pady=(4, 2))
            for line in [
                "   a. Abre Ajustes en tu teléfono.",
                "   b. Ve a 'Acerca del teléfono' → 'Información de software'.",
                "   c. Toca 7 veces seguidas sobre 'Número de compilación'.",
                "   d. Aparecerá el mensaje: ¡Ahora eres desarrollador!",
            ]:
                tk.Label(f, text=line, bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w").pack(fill="x", padx=20, pady=1)

            tk.Label(f, text=_("Paso 2 — Activa la Depuración USB:"),
                     bg=C["bg"], fg=C["text2"], font=FONT_UI_B, anchor="w").pack(fill="x", padx=20, pady=(8, 2))
            for line in [
                "   a. Regresa a Ajustes → Sistema → Opciones para desarrolladores.",
                "   b. Activa el interruptor 'Depuración USB'.",
                "   c. Conecta el cable USB a tu PC y acepta el cuadro emergente RSA.",
            ]:
                tk.Label(f, text=line, bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w").pack(fill="x", padx=20, pady=1)

        _add("🔌  Cómo habilitar la Depuración USB en Android", _faq_usb_debug)

        # ── 2. Dispositivo no detectado ───────────────────────────────
        def _faq_not_found(f):
            tk.Label(f, text=_("Si tu dispositivo no aparece o dice 'unauthorized':"), bg=C["bg"], fg=C["text2"], font=FONT_UI_B).pack(anchor="w", padx=20, pady=4)
            _cmd_chip(f, "adb kill-server", root_ref)
            _cmd_chip(f, "adb start-server", root_ref)
            _cmd_chip(f, "adb devices", root_ref)

        _add("⚠️  El dispositivo no aparece o dice 'no autorizado'", _faq_not_found)

        # ── 3. Dependencias ───────────────────────────────────────────
        def _faq_deps(f):
            for os_name, cmds in [
                ("🐧 Linux (Debian / Ubuntu):", ["sudo apt update", "sudo apt install adb scrcpy"]),
                ("🪟 Windows (winget):", ["winget install Genymobile.scrcpy"]),
                ("🍎 macOS (Homebrew):", ["brew install scrcpy android-platform-tools"]),
            ]:
                tk.Label(f, text=os_name, bg=C["bg"], fg=C["text2"], font=FONT_UI_B).pack(anchor="w", padx=20, pady=(6, 2))
                for c in cmds: _cmd_chip(f, c, root_ref)

        _add("📦  Dependencias necesarias (adb y scrcpy)", _faq_deps)

        # ── 4. WiFi ───────────────────────────────────────────────────
        def _faq_wifi(f):
            steps = [
                "1. Conecta el teléfono por USB una vez.",
                "2. Ve a 📱 Dispositivo → Habilitar TCP/IP (USB→WiFi).",
                "3. Desconecta el cable USB.",
                "4. Usa el botón '📡 Obtener IP' y pulsa Conectar.",
            ]
            for s in steps:
                tk.Label(f, text=s, bg=C["bg"], fg=C["text2"], font=FONT_UI).pack(anchor="w", padx=20, pady=2)
            _cmd_chip(f, "adb tcpip 5555", root_ref)
            _cmd_chip(f, "adb connect 192.168.1.X:5555", root_ref)

        _add("📡  Conexión por WiFi (ADB inalámbrico)", _faq_wifi)

        # ── 5. SECCIÓN DEDICADA: WEBCAM VIRTUAL (V4L2LOOPBACK) ────────
        def _faq_v4l2(f):
            tk.Label(f, text=_("¿Qué es y para qué sirve?"), bg=C["bg"], fg=C["cyan"], font=FONT_UI_B).pack(anchor="w", padx=20, pady=(4, 2))
            tk.Label(f, text=_("La función Webcam Virtual te permite transmitir la cámara de tu teléfono Android como una cámara de vídeo nativa (/dev/video9) en Linux. Esto permite usar tu celular como cámara de alta definición en OBS Studio, Discord, Zoom o Google Meet sin lags ni marcas de agua."),
                     bg=C["bg"], fg=C["text2"], font=FONT_UI, wraplength=680, justify="left").pack(anchor="w", padx=20, pady=(0, 8))

            tk.Label(f, text=_("Requisitos:"), bg=C["bg"], fg=C["text2"], font=FONT_UI_B).pack(anchor="w", padx=20, pady=(4, 2))
            tk.Label(f, text=_("• Sistema operativo Linux.\n• Paquete v4l2loopback-dkms instalado."), bg=C["bg"], fg=C["muted"], font=FONT_SM).pack(anchor="w", padx=20, pady=(0, 6))

            tk.Label(f, text=_("Comandos de instalación y configuración (haz clic en 📋 Copiar):"), bg=C["bg"], fg=C["text2"], font=FONT_UI_B).pack(anchor="w", padx=20, pady=(6, 2))

            tk.Label(f, text=_("1. Instalar el módulo en el sistema:"), bg=C["bg"], fg=C["muted"], font=FONT_SM).pack(anchor="w", padx=20)
            _cmd_chip(f, "sudo apt install v4l2loopback-dkms v4l2loopback-utils", root_ref)

            tk.Label(f, text=_("2. Cargar el módulo manualmente:"), bg=C["bg"], fg=C["muted"], font=FONT_SM).pack(anchor="w", padx=20, pady=(4, 0))
            _cmd_chip(f, "sudo modprobe v4l2loopback devices=1 video_nr=9 card_label='MASV Webcam' exclusive_caps=1", root_ref)

            tk.Label(f, text=_("3. Configurar carga automática en cada arranque:"), bg=C["bg"], fg=C["muted"], font=FONT_SM).pack(anchor="w", padx=20, pady=(4, 0))
            _cmd_chip(f, "echo 'v4l2loopback' | sudo tee -a /etc/modules", root_ref)
            _cmd_chip(f, "echo 'options v4l2loopback devices=1 video_nr=9 card_label=\"MASV Webcam\" exclusive_caps=1' | sudo tee /etc/modprobe.d/masv.conf", root_ref)

            tk.Label(f, text=_("4. Comando scrcpy equivalente en terminal:"), bg=C["bg"], fg=C["muted"], font=FONT_SM).pack(anchor="w", padx=20, pady=(4, 0))
            _cmd_chip(f, "scrcpy --video-source=camera --v4l2-sink=/dev/video9 --no-playback", root_ref)

        _add("📷  Cámara Virtual v4l2loopback (Linux)", _faq_v4l2)

        # ── 6. Perfiles ───────────────────────────────────────────────
        def _faq_profiles(f):
            for param, desc in [
                (_("Bitrate"), _("Velocidad de datos. 4M = liviano, 16M = alta calidad para juegos.")),
                (_("Resolución"), _("Altura máxima en px (720p, 1080p, 1920p). 0 = resolución nativa.")),
                (_("Códec"), _("H.264 (alta compatibilidad), H.265 (mejor compresión), AV1 (moderno).")),
            ]:
                row = tk.Frame(f, bg=C["card"], padx=10, pady=4)
                row.pack(fill="x", padx=20, pady=2)
                tk.Label(row, text=param, bg=C["card"], fg=C["cyan"], font=FONT_UI_B, width=12, anchor="w").pack(side="left")
                tk.Label(row, text=desc, bg=C["card"], fg=C["text2"], font=FONT_SM).pack(side="left")

        _add("⚙️  Perfiles y configuraciones — qué significan", _faq_profiles)

        # ── 7. Atajos Nativo Scrcpy ───────────────────────────────────
        def _faq_scrcpy_keys(f):
            for combo, desc in [
                (_("Alt + Up / MOD + u"), _("🔊 Subir volumen")),
                (_("Alt + Down / MOD + d"), _("🔉 Bajar volumen")),
                (_("MOD + p"), _("⚡ Encendido / Apagar pantalla")),
                (_("MOD + h"), _("🏠 Ir a Inicio (Home)")),
                (_("MOD + b / Backspace"), _("◀ Volver Atrás (Back)")),
                (_("MOD + s"), _("📑 Ver aplicaciones recientes")),
                (_("MOD + f"), _("🖥️ Pantalla completa")),
                (_("MOD + m"), _("🔇 Silenciar / Activar audio")),
                (_("MOD + n"), _("🔔 Desplegar notificaciones")),
                (_("MOD + v"), _("📋 Pegar portapapeles del PC")),
                (_("Arrastrar .apk"), _("📦 Instalar archivo APK en el teléfono")),
            ]:
                row = tk.Frame(f, bg=C["card"], padx=10, pady=3)
                row.pack(fill="x", padx=20, pady=1)
                tk.Label(row, text=combo, bg=C["card"], fg=C["cyan"], font=FONT_MONO, width=22, anchor="w").pack(side="left")
                tk.Label(row, text=desc, bg=C["card"], fg=C["text2"], font=FONT_SM).pack(side="left")

        _add("⌨️  Atajos nativos de scrcpy (control por teclado)", _faq_scrcpy_keys)

        # ── 8. NUEVO FAQ: Controles Remotos (Mando) ───────────────────
        def _faq_controls(f):
            tk.Label(f, text=_("¿Cómo funcionan los controles remotos?"), bg=C["bg"], fg=C["cyan"], font=FONT_UI_B).pack(anchor="w", padx=20, pady=(4, 2))
            tk.Label(f, text=_("Desde la pestaña 🎮 Controles puedes enviar señales directas de hardware y comandos de navegación a tu dispositivo Android sin necesidad de tocar la pantalla física."),
                     bg=C["bg"], fg=C["text2"], font=FONT_UI, wraplength=680, justify="left").pack(anchor="w", padx=20, pady=(0, 6))

            tk.Label(f, text=_("Agrupación de botones disponibles:"), bg=C["bg"], fg=C["text2"], font=FONT_UI_B).pack(anchor="w", padx=20, pady=(4, 2))
            groups = [
                (_("🔊 Audio"), _("Vol+ (subir volumen), Vol- (bajar volumen), Silenciar (mute instantáneo).")),
                (_("⚡ Pantalla"), _("Encender/Apagar (señal Power) y Notificaciones (desplegar barra de estado).")),
                (_("🧭 Navegación"), _("Inicio (pantalla principal), Volver (Atrás), Recientes (selector de apps).")),
            ]
            for title, desc in groups:
                r = tk.Frame(f, bg=C["card"], padx=10, pady=4)
                r.pack(fill="x", padx=20, pady=2)
                tk.Label(r, text=title, bg=C["card"], fg=C["purple"], font=FONT_UI_B, width=14, anchor="w").pack(side="left")
                tk.Label(r, text=desc, bg=C["card"], fg=C["text2"], font=FONT_SM, wraplength=520, justify="left").pack(side="left")

            tk.Label(f, text=_("⚠️ Requisito: Debes tener un dispositivo activo seleccionado en la pestaña 📱 Dispositivo para enviar los comandos."),
                     bg=C["bg"], fg=C["orange"], font=FONT_SM, wraplength=680, justify="left").pack(anchor="w", padx=20, pady=(6, 4))

        _add("🎮  Controles Remotos (Mando)", _faq_controls)

        # ── 9. NUEVO FAQ: Instalación de APKs ─────────────────────────
        def _faq_apks(f):
            tk.Label(f, text=_("Existen dos métodos sencillos para instalar aplicaciones (.apk) en tu teléfono:"),
                     bg=C["bg"], fg=C["text2"], font=FONT_UI, wraplength=680, justify="left").pack(anchor="w", padx=20, pady=(4, 6))

            methods = [
                (_("a) Botón de instalación en la app:"), _("Ve a la pestaña 🎮 Controles y pulsa '📦 Seleccionar e Instalar APK…'. Abre el explorador de archivos, elige el archivo .apk y MASV lo instalará vía ADB.")),
                (_("b) Arrastrar y soltar en scrcpy:"), _("Durante una transmisión activa, arrastra el archivo .apk desde tu explorador de archivos directamente sobre la ventana de vídeo de scrcpy.")),
            ]
            for title, desc in methods:
                r = tk.Frame(f, bg=C["card"], padx=12, pady=6)
                r.pack(fill="x", padx=20, pady=3)
                tk.Label(r, text=title, bg=C["card"], fg=C["green"], font=FONT_UI_B).pack(anchor="w")
                tk.Label(r, text=desc, bg=C["card"], fg=C["text2"], font=FONT_SM, wraplength=640, justify="left").pack(anchor="w", pady=(2, 0))

            tk.Label(f, text=_("Comando equivalente manual en terminal:"), bg=C["bg"], fg=C["muted"], font=FONT_SM).pack(anchor="w", padx=20, pady=(6, 0))
            _cmd_chip(f, "adb install -r nombre.apk", root_ref)

        _add("📦  Instalación de APKs", _faq_apks)

        # ── 10. NUEVO FAQ: Atajos de la aplicación MASV ───────────────
        def _faq_masv_keys(f):
            tk.Label(f, text=_("Atajos globales y combinaciones de teclado dentro de MASV:"),
                     bg=C["bg"], fg=C["muted"], font=FONT_SM, anchor="w").pack(fill="x", padx=20, pady=(2, 6))

            masv_shortcuts = [
                (_("Ctrl + I"), _("🚀 Iniciar / Detener transmisión activa")),
                (_("Ctrl + R"), _("🔄 Buscar y refrescar dispositivos conectados")),
                (_("Ctrl + H"), _("❓ Abrir pestaña de Ayuda y FAQ")),
                (_("Ctrl + Q"), _("❌ Salir de la aplicación")),
                (_("Supr (Delete)"), _("✕ Detener la sesión seleccionada en la tabla")),
                (_("Clic derecho (tabla)"), _("📋 Menú contextual: copiar serial, copiar comando, forzar cierre")),
            ]
            for combo, desc in masv_shortcuts:
                row = tk.Frame(f, bg=C["card"], padx=10, pady=3)
                row.pack(fill="x", padx=20, pady=1)
                tk.Label(row, text=combo, bg=C["card"], fg=C["cyan"], font=FONT_MONO, width=22, anchor="w").pack(side="left")
                tk.Label(row, text=desc, bg=C["card"], fg=C["text2"], font=FONT_SM).pack(side="left")

        _add("⌨️  Atajos de la aplicación MASV", _faq_masv_keys)

        # ── 11. Problemas Comunes ──────────────────────────────────────
        def _faq_troubleshoot(f):
            for prob, desc in [
                (_("Error: device offline"), _("Desconecta y vuelve a conectar el cable USB o ejecuta 'adb reconnect'.")),
                (_("Error: more than one device"), _("Selecciona el dispositivo deseado en la pestaña 📱 Dispositivo.")),
                (_("La sesión no se detiene"), _("Usa el botón '⚠ Todo' en Acciones o clic derecho → Forzar cierre.")),
            ]:
                row = tk.Frame(f, bg=C["card"], padx=12, pady=6)
                row.pack(fill="x", padx=20, pady=2)
                tk.Label(row, text=f"🛠 {prob}", bg=C["card"], fg=C["red"], font=FONT_UI_B).pack(anchor="w")
                tk.Label(row, text=desc, bg=C["card"], fg=C["text2"], font=FONT_SM).pack(anchor="w")

        _add("🛠️  Problemas comunes y soluciones", _faq_troubleshoot)

        # Footer
        ft = tk.Frame(sf, bg=C["bg"])
        ft.pack(fill="x", padx=12, pady=(12, 16))
        tk.Label(ft, text=_("MASV — Memexicanisimos Android Screen Viewer"), bg=C["bg"], fg=C["muted"], font=FONT_SM).pack(side="left")
        link = tk.Label(ft, text=_("🔗 GitHub"), bg=C["bg"], fg=C["blue"], font=FONT_SM, cursor="hand2")
        link.pack(side="right")
        link.bind("<Button-1>", lambda _: webbrowser.open("https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer"))
