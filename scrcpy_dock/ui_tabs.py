import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from .utils import C, FONT_FAMILY, FONT_UI, FONT_UI_B, FONT_SM, FONT_LG, FONT_MONO
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
    # Pestaña: Dispositivo
    # ─────────────────────────────────────────────────────────────────

    def build_tab_device(self, parent):
        p = parent

        # ── Pantalla de dependencias faltantes ──────────────────────
        self.refs['install_frame'] = tk.Frame(p, bg=C["bg"])
        tk.Label(self.refs['install_frame'], text="⚠️", font=(FONT_FAMILY, 48),
                 bg=C["bg"], fg=C["orange"]).pack(pady=(30, 8))
        tk.Label(self.refs['install_frame'], text="Faltan dependencias: adb y/o scrcpy",
                 bg=C["bg"], fg=C["text"], font=FONT_LG).pack()
        tk.Label(self.refs['install_frame'],
                 text="Para instalarlas en Debian/Ubuntu ejecuta en la terminal:",
                 bg=C["bg"], fg=C["muted"], font=FONT_UI).pack(pady=(8, 4))
        cmd_f = tk.Frame(self.refs['install_frame'], bg=C["card2"], padx=12, pady=8)
        cmd_f.pack()
        tk.Label(cmd_f, text="sudo apt install adb scrcpy", bg=C["card2"],
                 fg=C["cyan"], font=FONT_MONO).pack()
        btns_i = tk.Frame(self.refs['install_frame'], bg=C["bg"])
        btns_i.pack(pady=16)
        tk.Button(btns_i, text="📋  Copiar comando", bg=C["blue"], fg="#FFF",
                  font=FONT_UI_B, relief="flat", bd=0, padx=14, pady=8,
                  command=self.cb.get('copy_install_cmd')).pack(side="left", padx=8)
        tk.Button(btns_i, text="🖥  Abrir terminal e instalar", bg=C["sep"], fg=C["text"],
                  font=FONT_UI_B, relief="flat", bd=0, padx=14, pady=8,
                  command=self.cb.get('open_terminal_install')).pack(side="left", padx=8)
        tk.Label(self.refs['install_frame'],
                 text="Después de instalar, reinicia MASV.",
                 bg=C["bg"], fg=C["muted"], font=FONT_SM).pack()

        # ── Contenido principal ──────────────────────────────────────
        self.refs['dep_frame'] = tk.Frame(p, bg=C["bg"])

        sf = _section(self.refs['dep_frame'], "🔍  Buscar dispositivos")
        r0 = _row(sf)
        btn_scan = tk.Button(r0, text="🔄  Buscar dispositivos", bg=C["blue"], fg="#FFF",
                             font=FONT_UI_B, relief="flat", bd=0, padx=12, pady=7,
                             command=self.cb.get('refresh_devices'))
        btn_scan.pack(side="left", padx=(0, 10))
        Tooltip(btn_scan, "Escanea dispositivos USB y WiFi\nAsegúrate de tener Depuración USB activada.",
                shortcut="Ctrl+R")
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

        # Mensaje de estado del dispositivo seleccionado
        self.refs['dev_info_lbl'] = tk.Label(self.refs['dep_frame'],
                                             text="Selecciona un dispositivo de la lista.",
                                             bg=C["bg"], fg=C["muted"], font=FONT_SM)
        self.refs['dev_info_lbl'].pack(padx=14, pady=4, anchor="w")

        # Enlace a FAQ si no hay dispositivos (visible cuando no hay ninguno)
        self.refs['no_dev_hint'] = tk.Label(
            self.refs['dep_frame'],
            text="¿Problemas? Consulta  →  ❓ Ayuda  →  'Cómo habilitar la Depuración USB'",
            bg=C["bg"], fg=C["blue"], font=FONT_SM, cursor="hand2")
        self.refs['no_dev_hint'].bind("<Button-1>", lambda _: self.cb.get('go_to_help_usb')())

        # ── WiFi ─────────────────────────────────────────────────────
        wf = _section(self.refs['dep_frame'], "📡  Conexión WiFi (inalámbrica)", pady=(0, 4))
        wr = _row(wf)
        tk.Label(wr, text="IP del teléfono:", bg=C["card"], fg=C["muted"],
                 font=FONT_SM).pack(side="left", padx=(0, 6))
        self.refs['ip_entry'] = ttk.Entry(wr, width=18)
        self.refs['ip_entry'].insert(0, "192.168.1.")
        self.refs['ip_entry'].pack(side="left", padx=4)
        Tooltip(self.refs['ip_entry'],
                "IP del teléfono:\nAjustes → Acerca del teléfono → Estado → Dirección IP")
        tk.Label(wr, text=":", bg=C["card"], fg=C["muted"]).pack(side="left")
        self.refs['port_entry'] = ttk.Entry(wr, width=6)
        self.refs['port_entry'].insert(0, "5555")
        self.refs['port_entry'].pack(side="left", padx=4)

        # Botón "Obtener IP"
        btn_getip = tk.Button(wr, text="📡 Obtener IP", bg=C["sep"], fg=C["text"],
                              font=FONT_SM, relief="flat", bd=0, padx=8, pady=4,
                              command=self.cb.get('get_device_ip'))
        btn_getip.pack(side="left", padx=8)
        Tooltip(btn_getip, "Consulta automáticamente la IP WiFi del dispositivo seleccionado via ADB.")

        btns_w = _row(wf)
        ttk.Button(btns_w, text="Conectar", command=self.cb.get('connect_wifi'),
                   style="Primary.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(btns_w, text="Habilitar TCP/IP (USB→WiFi)",
                   command=self.cb.get('enable_tcpip'),
                   style="Secondary.TButton").pack(side="left")

        # ── v4l2loopback ─────────────────────────────────────────────
        vf = _section(self.refs['dep_frame'], "📷  Webcam Virtual (v4l2loopback)")
        self.refs['v4l2_lbl'] = tk.Label(vf, text="Verificando módulo…",
                                         bg=C["card"], fg=C["orange"], font=FONT_SM)
        self.refs['v4l2_lbl'].pack(anchor="w", padx=4, pady=2)
        vr = _row(vf)
        self.refs['load_v4l2_btn'] = ttk.Button(vr, text="Cargar módulo",
                                                command=self.cb.get('setup_v4l2'),
                                                style="Secondary.TButton")
        self.refs['load_v4l2_btn'].pack(side="left", padx=(0, 8))
        self.refs['route_cam_btn'] = ttk.Button(vr, text="Enrutar cámara → /dev/video9",
                                               command=self.cb.get('route_cam'),
                                               state="disabled", style="Green.TButton")
        self.refs['route_cam_btn'].pack(side="left", padx=(0, 8))
        ttk.Button(vr, text="Instrucciones", command=self.cb.get('v4l2_help'),
                   style="Ghost.TButton").pack(side="left")

        if not self.ctx.adb or not self.ctx.scrcpy:
            self.refs['install_frame'].pack(fill="both", expand=True, padx=20, pady=20)
        else:
            self.refs['dep_frame'].pack(fill="both", expand=True)

    # ─────────────────────────────────────────────────────────────────
    # Pestaña: Perfiles
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

        # Empty state: se muestra si no hay perfiles
        self.refs['profile_empty_lbl'] = tk.Label(
            sf,
            text="Aún no hay perfiles.\nCrea uno con el botón  ✨ Nuevo perfil  para comenzar.",
            bg=C["card2"], fg=C["muted"], font=FONT_SM, justify="center", pady=12)

        pa = _row(sf)
        btn_new = ttk.Button(pa, text="✨  Nuevo perfil (asistente)",
                             command=self.cb.get('open_wizard'), style="Purple.TButton")
        btn_new.pack(side="left", padx=(0, 8))
        Tooltip(btn_new, "Crea un perfil con el asistente paso a paso.")
        btn_del = ttk.Button(pa, text="🗑  Eliminar",
                             command=self.cb.get('delete_profile'), style="Danger.TButton")
        btn_del.pack(side="left")
        Tooltip(btn_del, "Elimina el perfil seleccionado de la lista.")

        df = _section(p, "🔍  Detalle del perfil seleccionado")
        from .ui_widgets import ProfileChipsView
        self.refs['profile_chips'] = ProfileChipsView(df)
        self.refs['profile_chips'].pack(fill="both", expand=True, pady=4)

        af = _section(p, "🎯  Perfil activo para la próxima sesión")
        ar = _row(af)
        tk.Label(ar, text="Perfil:", bg=C["card"], fg=C["muted"],
                 font=FONT_SM).pack(side="left", padx=(0, 6))
        self.refs['active_profile_combo'] = ttk.Combobox(
            ar, textvariable=self.ctx.active_profile, state="readonly", width=28)
        self.refs['active_profile_combo'].pack(side="left")
        self.refs['active_profile_combo'].bind("<<ComboboxSelected>>",
                                              self.cb.get('on_active_profile_change'))

        self.refs['assoc_lbl'] = tk.Label(p, text="", bg=C["bg"],
                                         fg=C["muted"], font=FONT_SM)
        self.refs['assoc_lbl'].pack(padx=14, anchor="w", pady=2)

    # ─────────────────────────────────────────────────────────────────
    # Pestaña: Acciones
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
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1,  "units"))

        # Barra de dispositivo + perfil activo
        info = tk.Frame(inner, bg=C["card"], pady=6)
        info.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(info, text="Dispositivo:", bg=C["card"], fg=C["muted"],
                 font=FONT_SM).pack(side="left", padx=(10, 2))
        self.refs['action_device_lbl'] = tk.Label(info, textvariable=self.ctx.active_device,
                                                  bg=C["card"], fg=C["muted"], font=FONT_UI_B)
        self.refs['action_device_lbl'].pack(side="left", padx=(0, 14))
        tk.Label(info, text="Perfil:", bg=C["card"], fg=C["muted"],
                 font=FONT_SM).pack(side="left", padx=(0, 2))
        self.refs['action_profile_lbl'] = tk.Label(info, textvariable=self.ctx.active_profile,
                                                   bg=C["card"], fg=C["cyan"], font=FONT_UI_B)
        self.refs['action_profile_lbl'].pack(side="left")

        # Grid de tarjetas
        grid = tk.Frame(inner, bg=C["bg"])
        grid.pack(fill="x", padx=16, pady=12)
        for c in range(3):
            grid.columnconfigure(c, weight=1)
        grid.rowconfigure(0, minsize=110)
        grid.rowconfigure(1, minsize=110)

        _card_button(grid, "▶", "Iniciar",
                     "Lanza scrcpy con el perfil\ny dispositivo seleccionados",
                     self.cb.get('toggle_scene'), C["blue"], C["blue_hover"],
                     row=0, col=0, shortcut="Ctrl+I")
        _card_button(grid, "■", "Detener",
                     "Detiene la sesión activa\ndel dispositivo seleccionado",
                     self.cb.get('stop_current'), C["sep"], C["card3"],
                     row=0, col=1)
        _card_button(grid, "⚠", "Todo",
                     "Cierra TODAS las sesiones\nscrcpy de golpe",
                     self.cb.get('panic_kill'), C["red"], C["red_hover"],
                     row=0, col=2)
        _card_button(grid, "↺", "ADB",
                     "Reiniciar servidor ADB",
                     self.cb.get('restart_adb'), C["orange"], C["orange_hover"],
                     row=1, col=0)
        _card_button(grid, "◉", "Cam",
                     "Enrutar cámara → /dev/video9",
                     self.cb.get('route_cam'), C["purple_dim"], C["purple_hover"],
                     row=1, col=1)
        _card_button(grid, "~", "WiFi",
                     "Ir a sección de conexión WiFi",
                     self.cb.get('go_to_wifi'), C["sep"], C["card3"],
                     row=1, col=2)

        # Tabla de sesiones
        sf_lbl = tk.Frame(inner, bg=C["card"])
        sf_lbl.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(sf_lbl, text="  Sesiones activas", bg=C["card"],
                 fg=C["purple"], font=FONT_UI_B).pack(side="left", padx=4, pady=4)
        tk.Label(sf_lbl, text="Supr = detener · Clic derecho = opciones",
                 bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="right", padx=8, pady=4)

        sf = tk.Frame(inner, bg=C["card2"])
        sf.pack(fill="both", expand=True, padx=16, pady=(0, 4))

        cols = ("serial", "profile", "pid", "uptime", "status")
        self.refs['sess_tree'] = ttk.Treeview(sf, columns=cols, show="headings",
                                              height=5, selectmode="browse")
        for col_id, heading, width, stretch in [
            ("serial",  "Dispositivo",  200, True),
            ("profile", "Perfil",       140, True),
            ("pid",     "PID",           70, False),
            ("uptime",  "Tiempo",        80, False),
            ("status",  "Estado",       120, True),
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

        # Atajos de teclado en la tabla
        self.refs['sess_tree'].bind("<Delete>",  self.cb.get('stop_selected'))
        self.refs['sess_tree'].bind("<Button-3>", self.cb.get('sess_context_menu'))

        btn_container = tk.Frame(inner, bg=C["bg"])
        btn_container.pack(fill="x", padx=16, pady=(4, 6))
        ttk.Button(btn_container, text="✕  Detener sesión seleccionada",
                   command=self.cb.get('stop_selected'),
                   style="Danger.TButton").pack(side="right")

        # ── Controles rápidos del dispositivo (remoto / ADB) ────────
        ctrl_sec = _section(inner, "🎮  Controles rápidos del dispositivo (remoto / ADB)", pady=(6, 12))

        ctrl_r1 = _row(ctrl_sec, pady=4)
        ctrl_btns = [
            ("🔊 Vol +",    lambda: self.cb.get('send_keyevent')(24),  "Subir volumen"),
            ("🔉 Vol -",    lambda: self.cb.get('send_keyevent')(25),  "Bajar volumen"),
            ("🔇 Mute",     lambda: self.cb.get('send_keyevent')(164), "Silenciar audio"),
            ("⚡ Encender", lambda: self.cb.get('send_keyevent')(26),  "Encender/Apagar pantalla (Power)"),
            ("🏠 Inicio",   lambda: self.cb.get('send_keyevent')(3),   "Ir a la pantalla de Inicio (Home)"),
            ("◀ Atrás",    lambda: self.cb.get('send_keyevent')(4),   "Volver atrás (Back)"),
            ("📑 Recientes",lambda: self.cb.get('send_keyevent')(187), "Ver aplicaciones recientes"),
            ("🔔 Notif",    lambda: self.cb.get('send_keyevent')("notifications"), "Desplegar panel de notificaciones"),
        ]
        for txt, cmd, tip in ctrl_btns:
            btn = tk.Button(ctrl_r1, text=txt, bg=C["card2"], fg=C["text2"],
                            font=FONT_SM, relief="flat", bd=0, padx=6, pady=5,
                            activebackground=C["card3"], activeforeground=C["text"],
                            command=cmd)
            btn.pack(side="left", padx=2, expand=True, fill="x")
            Tooltip(btn, tip)

        ctrl_r2 = _row(ctrl_sec, pady=(2, 6))
        btn_apk = ttk.Button(ctrl_r2, text="📦  Instalar APK en dispositivo…",
                             command=self.cb.get('install_apk'),
                             style="Secondary.TButton")
        btn_apk.pack(side="left", padx=4)
        Tooltip(btn_apk, "Selecciona un archivo .apk del equipo para instalarlo automáticamente vía ADB.")

    # ─────────────────────────────────────────────────────────────────
    # Pestaña: Consola
    # ─────────────────────────────────────────────────────────────────

    def build_tab_console(self, parent):
        p = parent
        tb = tk.Frame(p, bg=C["card2"], pady=4, padx=8)
        tb.pack(fill="x", side="top")
        tk.Label(tb, text="Filtrar:", bg=C["card2"], fg=C["muted"],
                 font=FONT_SM).pack(side="left", padx=(4, 6))

        for name, filter_key in [("Todos", "ALL"), ("Errores", "ERROR"),
                                  ("ADB", "ADB"), ("Scrcpy", "INFO")]:
            btn = tk.Button(tb, text=name, bg=C["card"], fg=C["text"],
                            font=FONT_SM, relief="flat", bd=0, padx=10, pady=3,
                            command=lambda k=filter_key: self.cb.get('filter_log')(k))
            btn.pack(side="left", padx=2)

        tk.Button(tb, text="📋  Copiar todo", bg=C["sep"], fg=C["text"],
                  font=FONT_SM, relief="flat", bd=0, padx=10, pady=3,
                  command=self.cb.get('copy_log')).pack(side="right", padx=4)

        self.refs['log_txt'] = tk.Text(p, bg="#0A0A0A", fg=C["text"], wrap="word",
                                       font=FONT_MONO, state="disabled",
                                       relief="flat", bd=0)
        log_sb = ttk.Scrollbar(p, orient="vertical",
                               command=self.refs['log_txt'].yview)
        self.refs['log_txt'].configure(yscrollcommand=log_sb.set)
        self.refs['log_txt'].pack(side="left", fill="both", expand=True)
        log_sb.pack(side="right", fill="y")

        for tag, color in [("ERROR", C["red"]), ("WARNING", C["orange"]),
                           ("INFO", C["cyan"]), ("ADB", "#A0D8EF"), ("OK", C["green"])]:
            self.refs['log_txt'].tag_config(tag, foreground=color)

        cb = tk.Frame(p, bg=C["card2"])
        cb.pack(fill="x", side="bottom")
        tk.Button(cb, text="🗑  Limpiar consola", bg=C["sep"], fg=C["text"],
                  font=FONT_SM, relief="flat", bd=0, padx=12, pady=6,
                  command=self.cb.get('clear_log')).pack(side="left", padx=8, pady=4)
        tk.Button(cb, text="📄  Abrir archivo de log", bg=C["bg"], fg=C["muted"],
                  font=FONT_SM, relief="flat", bd=0, padx=12, pady=6,
                  command=self.cb.get('open_log')).pack(side="right", padx=8, pady=4)

    # ─────────────────────────────────────────────────────────────────
    # Pestaña: Ayuda — FAQ Interactiva con Acordeón
    # ─────────────────────────────────────────────────────────────────

    def build_tab_help(self, parent):
        p = parent
        for w in p.winfo_children():
            w.destroy()

        # ── Header de la pestaña ─────────────────────────────────────
        hdr = tk.Frame(p, bg=C["card"], pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="❓  Preguntas Frecuentes",
                 bg=C["card"], fg=C["purple"], font=FONT_LG).pack(side="left", padx=16)
        tk.Label(hdr, text="Ctrl+H",
                 bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="right", padx=16)

        tk.Frame(p, bg=C["sep"], height=1).pack(fill="x")

        # ── Canvas con scroll ─────────────────────────────────────────
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
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1,  "units"))

        self._faq_items = []
        root_ref = self.ctx.root  # para _cmd_chip clipboard

        def _add(title, build_fn):
            item = AccordionItem(sf, title, build_fn)
            item.pack(fill="x", padx=12, pady=(0, 2))
            self._faq_items.append(item)

        # ── 1. Inicio rápido ─────────────────────────────────────────
        def _faq_quickstart(f):
            steps = [
                "1. Conecta el teléfono con un cable USB (de datos, no solo carga).",
                "2. Activa la Depuración USB en el teléfono (ver FAQ 2).",
                "3. En la pantalla del teléfono aparecerá un cuadro de diálogo:\n   → Toca 'Permitir' y marca '✔ Siempre permitir desde este equipo'.",
                "4. Ve a la pestaña  📱 Dispositivo  y pulsa  🔄 Buscar dispositivos.",
                "5. Selecciona tu dispositivo de la lista.",
                "6. Ve a la pestaña  ⚙️ Perfiles  y elige o crea un perfil.",
                "7. Ve a  🚀 Acciones  →  ▶ Iniciar.",
            ]
            for s in steps:
                tk.Label(f, text=s, bg=C["bg"], fg=C["text2"], font=FONT_UI,
                         anchor="w", justify="left", wraplength=680).pack(
                    fill="x", padx=20, pady=2)
            tk.Label(f, text="⌨  Atajo rápido: Ctrl+I para iniciar/detener",
                     bg=C["bg"], fg=C["cyan"], font=FONT_SM, anchor="w").pack(
                fill="x", padx=20, pady=(6, 4))

        _add("🚀  Inicio rápido — primeros pasos", _faq_quickstart)

        # ── 2. Cómo habilitar la Depuración USB ──────────────────────
        def _faq_usb_debug(f):
            tk.Label(f, text="La Depuración USB es necesaria para que ADB pueda comunicarse con tu teléfono.",
                     bg=C["bg"], fg=C["muted"], font=FONT_SM, anchor="w",
                     wraplength=680, justify="left").pack(fill="x", padx=20, pady=(2, 6))

            tk.Label(f, text="Paso 1 — Activa las Opciones de desarrollador:",
                     bg=C["bg"], fg=C["text2"], font=FONT_UI_B, anchor="w").pack(
                fill="x", padx=20, pady=(4, 2))
            for line in [
                "   a. Abre  Ajustes  en tu teléfono.",
                "   b. Ve a  Acerca del teléfono  (o  Información del software).",
                "   c. Toca 7 veces sobre  Número de compilación.",
                "   d. Verás el mensaje: «¡Ahora eres desarrollador!»",
            ]:
                tk.Label(f, text=line, bg=C["bg"], fg=C["text2"], font=FONT_UI,
                         anchor="w", wraplength=680).pack(fill="x", padx=20, pady=1)

            tk.Label(f, text="Paso 2 — Activa la Depuración USB:",
                     bg=C["bg"], fg=C["text2"], font=FONT_UI_B, anchor="w").pack(
                fill="x", padx=20, pady=(8, 2))
            for line in [
                "   a. Vuelve a  Ajustes  →  Opciones de desarrollador.",
                "   b. Activa el interruptor  Depuración USB.",
                "   c. Conecta el cable USB a tu PC.",
                "   d. En la pantalla del teléfono acepta el diálogo RSA.",
            ]:
                tk.Label(f, text=line, bg=C["bg"], fg=C["text2"], font=FONT_UI,
                         anchor="w", wraplength=680).pack(fill="x", padx=20, pady=1)

            tk.Label(f, text="💡  Consejo: En Huawei/EMUI, busca las Opciones de desarrollador en Ajustes → Sistema.",
                     bg=C["bg"], fg=C["orange"], font=FONT_SM, anchor="w",
                     wraplength=680).pack(fill="x", padx=20, pady=(8, 4))

        _add("🔌  Cómo habilitar la Depuración USB", _faq_usb_debug)

        # ── 3. Dispositivo no aparece o "no autorizado" ───────────────
        def _faq_not_found(f):
            causes = [
                ("🔌  Cable USB de solo carga", "Usa un cable que soporte datos. Prueba otro cable."),
                ("🚫  Diálogo RSA no aceptado", "En la pantalla del teléfono acepta 'Permitir depuración USB'."),
                ("🔄  Servidor ADB colgado",    "Reinicia el servidor desde Acciones → ↺ ADB, o usa los comandos de abajo."),
                ("📵  Modo de conexión USB incorrecto", "El teléfono puede estar en modo 'Solo carga'. Cambia a 'Transferencia de archivos' (MTP)."),
            ]
            for title, desc in causes:
                row = tk.Frame(f, bg=C["card"], padx=12, pady=8)
                row.pack(fill="x", padx=20, pady=3)
                tk.Label(row, text=title, bg=C["card"], fg=C["text2"],
                         font=FONT_UI_B, anchor="w").pack(anchor="w")
                tk.Label(row, text=desc, bg=C["card"], fg=C["muted"],
                         font=FONT_SM, anchor="w", wraplength=640, justify="left").pack(anchor="w")

            tk.Label(f, text="Comandos de diagnóstico (ejecutar en terminal):",
                     bg=C["bg"], fg=C["text2"], font=FONT_UI_B, anchor="w").pack(
                fill="x", padx=20, pady=(10, 2))
            for cmd in ["adb kill-server", "adb start-server", "adb devices"]:
                _cmd_chip(f, cmd, root_ref)

        _add("⚠️  El dispositivo no aparece o aparece 'no autorizado'", _faq_not_found)

        # ── 4. Dependencias: adb y scrcpy ─────────────────────────────
        def _faq_deps(f):
            tk.Label(f, text="MASV necesita que adb y scrcpy estén instalados en tu sistema (o en la carpeta bin/).",
                     bg=C["bg"], fg=C["muted"], font=FONT_SM, anchor="w",
                     wraplength=680).pack(fill="x", padx=20, pady=(2, 8))

            for os_name, cmds, link in [
                ("🐧  Linux (Debian/Ubuntu/Mint)",
                 ["sudo apt update", "sudo apt install adb scrcpy"],
                 "https://github.com/Genymobile/scrcpy"),
                ("🪟  Windows",
                 ["winget install Genymobile.scrcpy",
                  "# O descarga el .zip desde github.com/Genymobile/scrcpy"],
                 "https://github.com/Genymobile/scrcpy/blob/master/doc/windows.md"),
                ("🍎  macOS",
                 ["brew install scrcpy android-platform-tools"],
                 "https://github.com/Genymobile/scrcpy/blob/master/doc/macos.md"),
            ]:
                lbl = tk.Label(f, text=os_name, bg=C["bg"], fg=C["text2"],
                               font=FONT_UI_B, anchor="w")
                lbl.pack(fill="x", padx=20, pady=(8, 2))
                for cmd in cmds:
                    _cmd_chip(f, cmd, root_ref)
                link_lbl = tk.Label(f, text=f"  🔗  Documentación oficial: {link}",
                                    bg=C["bg"], fg=C["blue"], font=FONT_SM,
                                    cursor="hand2", anchor="w")
                link_lbl.pack(fill="x", padx=20, pady=2)
                link_lbl.bind("<Button-1>", lambda e, u=link: webbrowser.open(u))

        _add("📦  Dependencias necesarias (adb y scrcpy)", _faq_deps)

        # ── 5. Conexión por WiFi ───────────────────────────────────────
        def _faq_wifi(f):
            tk.Label(f, text="Requisito previo: el primer emparejamiento siempre debe hacerse con cable USB.",
                     bg=C["bg"], fg=C["orange"], font=FONT_SM, anchor="w",
                     wraplength=680).pack(fill="x", padx=20, pady=(2, 8))

            steps = [
                "1. Conecta el teléfono por USB y asegúrate de que aparece en la lista de dispositivos.",
                "2. Ve a  📱 Dispositivo  →  sección WiFi  →  pulsa  'Habilitar TCP/IP (USB→WiFi)'.",
                "3. El puerto 5555 queda abierto. Desconecta el cable USB.",
                "4. Introduce la IP del teléfono en el campo correspondiente (usa 'Obtener IP' para detectarla).",
                "5. Pulsa  Conectar. El dispositivo aparecerá en la lista con su IP como serial.",
            ]
            for s in steps:
                tk.Label(f, text=s, bg=C["bg"], fg=C["text2"], font=FONT_UI,
                         anchor="w", justify="left", wraplength=680).pack(
                    fill="x", padx=20, pady=2)

            tk.Label(f, text="Comandos manuales equivalentes:",
                     bg=C["bg"], fg=C["text2"], font=FONT_UI_B, anchor="w").pack(
                fill="x", padx=20, pady=(10, 2))
            for cmd in ["adb tcpip 5555", "adb connect 192.168.1.X:5555"]:
                _cmd_chip(f, cmd, root_ref)

            tk.Label(f, text="🛡  Solución de problemas: asegúrate de que PC y teléfono están en la misma red WiFi y que el firewall no bloquea el puerto 5555.",
                     bg=C["bg"], fg=C["muted"], font=FONT_SM, anchor="w",
                     wraplength=680, justify="left").pack(fill="x", padx=20, pady=(8, 4))

        _add("📡  Conectarse por WiFi (ADB inalámbrico)", _faq_wifi)

        # ── 6. Cámara como Webcam v4l2loopback ───────────────────────
        def _faq_v4l2(f):
            tk.Label(f, text="⚠  Esta función solo está disponible en Linux.",
                     bg=C["bg"], fg=C["orange"], font=FONT_UI_B, anchor="w").pack(
                fill="x", padx=20, pady=(2, 8))

            tk.Label(f, text="1. Instala el módulo v4l2loopback:",
                     bg=C["bg"], fg=C["text2"], font=FONT_UI_B, anchor="w").pack(
                fill="x", padx=20, pady=(4, 2))
            _cmd_chip(f, "sudo apt install v4l2loopback-dkms v4l2loopback-utils", root_ref)

            tk.Label(f, text="2. Carga el módulo (o usa el botón en la app):",
                     bg=C["bg"], fg=C["text2"], font=FONT_UI_B, anchor="w").pack(
                fill="x", padx=20, pady=(8, 2))
            _cmd_chip(f, "sudo modprobe v4l2loopback devices=1 video_nr=9 card_label='MASV Webcam' exclusive_caps=1", root_ref)

            tk.Label(f, text="3. En MASV: 📱 Dispositivo → Cargar módulo → Enrutar cámara.",
                     bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w",
                     wraplength=680).pack(fill="x", padx=20, pady=4)

            tk.Label(f, text="4. En OBS Studio: + Fuente → Dispositivo de captura de vídeo (V4L2) → selecciona 'MASV Webcam'.",
                     bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w",
                     wraplength=680).pack(fill="x", padx=20, pady=4)

            tk.Label(f, text="Para cargar el módulo automáticamente al arrancar el sistema:",
                     bg=C["bg"], fg=C["muted"], font=FONT_SM, anchor="w").pack(
                fill="x", padx=20, pady=(8, 2))
            _cmd_chip(f, "echo 'v4l2loopback' | sudo tee -a /etc/modules", root_ref)
            _cmd_chip(f, "echo 'options v4l2loopback devices=1 video_nr=9 card_label=\"MASV Webcam\" exclusive_caps=1' | sudo tee /etc/modprobe.d/masv.conf", root_ref)

        _add("📷  Usar la cámara como Webcam (v4l2loopback)", _faq_v4l2)

        # ── 7. Perfiles y configuraciones ─────────────────────────────
        def _faq_profiles(f):
            params = [
                ("Bitrate",     "Calidad del vídeo. 4M = streaming eficiente · 16M = gaming · 24M+ = máxima calidad."),
                ("Resolución",  "Altura máxima del vídeo en píxeles. 0 = resolución nativa del teléfono."),
                ("FPS máx",     "Fotogramas por segundo. 30 FPS para streaming, 60 FPS para gaming fluido."),
                ("Códec",       "h264 = compatible con todo · h265/av1 = más compresión, requiere hardware reciente."),
                ("Audio",       "playback = audio del sistema · mic = micrófono del teléfono · no-audio = sin audio."),
            ]
            for param, desc in params:
                row = tk.Frame(f, bg=C["card"], padx=12, pady=6)
                row.pack(fill="x", padx=20, pady=2)
                tk.Label(row, text=param, bg=C["card"], fg=C["cyan"],
                         font=FONT_UI_B, width=14, anchor="w").pack(side="left")
                tk.Label(row, text=desc, bg=C["card"], fg=C["text2"],
                         font=FONT_SM, anchor="w", justify="left", wraplength=540).pack(
                    side="left", fill="x", expand=True)

            tk.Label(f, text="💡  Un perfil puede asociarse automáticamente a un dispositivo:\nal seleccionar el dispositivo por primera vez y guardar, MASV recuerda qué perfil usas con él.",
                     bg=C["bg"], fg=C["muted"], font=FONT_SM, anchor="w",
                     wraplength=680, justify="left").pack(fill="x", padx=20, pady=(10, 4))

        _add("⚙️  Perfiles y configuraciones — qué significan", _faq_profiles)

        # ── 8. Atajos nativos de scrcpy ─────────────────────────────
        def _faq_scrcpy_keys(f):
            tk.Label(f, text="Cuando la ventana de scrcpy está enfocada, puedes controlar el teléfono con estos atajos:",
                     bg=C["bg"], fg=C["muted"], font=FONT_SM, anchor="w",
                     wraplength=680).pack(fill="x", padx=20, pady=(2, 6))

            keys = [
                ("Alt + Up  /  MOD + u", "🔊 Subir volumen del teléfono"),
                ("Alt + Down /  MOD + d", "🔉 Bajar volumen del teléfono"),
                ("MOD + p",              "⚡ Botón de encendido / apagar pantalla"),
                ("MOD + h",              "🏠 Ir a la pantalla de inicio (Home)"),
                ("MOD + b  /  Backspace", "◀ Botón Atrás (Back)"),
                ("MOD + s",              "📑 Abrir aplicaciones recientes"),
                ("MOD + f",              "🖥️ Activar / Desactivar pantalla completa"),
                ("MOD + m",              "🔇 Silenciar / Desactivar silencio"),
                ("MOD + Shift + o",      "☀️ Encender pantalla físicamente"),
                ("MOD + n",              "🔔 Desplegar panel de notificaciones"),
                ("MOD + v",              "📋 Pegar portapapeles del PC al teléfono"),
                ("Arrastrar .apk",       "📦 Instalar archivo APK arrastrando a la ventana"),
            ]
            for combo, desc in keys:
                row = tk.Frame(f, bg=C["card"], padx=12, pady=4)
                row.pack(fill="x", padx=20, pady=2)
                tk.Label(row, text=combo, bg=C["card"], fg=C["cyan"],
                         font=FONT_MONO, width=22, anchor="w").pack(side="left")
                tk.Label(row, text=desc, bg=C["card"], fg=C["text2"],
                         font=FONT_SM, anchor="w", justify="left").pack(side="left", fill="x", expand=True)

        _add("⌨️  Atajos nativos de scrcpy (control por teclado)", _faq_scrcpy_keys)

        # ── 9. Problemas comunes y soluciones ─────────────────────────
        def _faq_troubleshoot(f):
            problems = [
                ("Error: 'device offline'",
                 "El dispositivo se desconectó. Prueba:",
                 ["adb reconnect", "adb disconnect && adb connect <IP>:5555"]),
                ("Error: 'more than one device/emulator'",
                 "Hay más de un dispositivo. Selecciona el correcto en la lista de MASV antes de iniciar.",
                 []),
                ("La sesión no se detiene",
                 "Usa la opción 'Cerrar todo' (tarjeta ⚠ Todo) o clic derecho en la tabla → Forzar cierre.",
                 []),
                ("Sudo solicitado al cargar v4l2loopback",
                 "Es normal. MASV usa pkexec (GUI). Puedes cargarlo manualmente en terminal con:",
                 ["sudo modprobe v4l2loopback devices=1 video_nr=9 exclusive_caps=1"]),
                ("scrcpy: error 'Video encoding failed'",
                 "Prueba a reducir el bitrate o cambiar el códec (usa h264 como fallback).",
                 []),
            ]
            for prob, desc, cmds in problems:
                row = tk.Frame(f, bg=C["card"], padx=14, pady=8)
                row.pack(fill="x", padx=20, pady=3)
                tk.Label(row, text=f"🛠  {prob}", bg=C["card"], fg=C["red"],
                         font=FONT_UI_B, anchor="w").pack(anchor="w")
                tk.Label(row, text=desc, bg=C["card"], fg=C["text2"],
                         font=FONT_UI, anchor="w", wraplength=640, justify="left").pack(anchor="w")
                for cmd in cmds:
                    _cmd_chip(row, cmd, root_ref)

        _add("🛠️  Problemas comunes y soluciones", _faq_troubleshoot)

        # ── Footer ────────────────────────────────────────────────────
        ft = tk.Frame(sf, bg=C["bg"])
        ft.pack(fill="x", padx=12, pady=(12, 16))
        tk.Label(ft, text="MASV — Memexicanisimos Android Screen Viewer",
                 bg=C["bg"], fg=C["muted"], font=FONT_SM).pack(side="left")
        link = tk.Label(ft, text="🔗  GitHub",
                        bg=C["bg"], fg=C["blue"], font=FONT_SM, cursor="hand2")
        link.pack(side="right")
        link.bind("<Button-1>", lambda _: webbrowser.open(
            "https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer"))
