"""Dispositivo: detección, bóveda, Wi-Fi, blindaje y webcam virtual."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ...i18n import _
from ...utils import C, FONT_FAMILY, FONT_UI_B, FONT_SM
from ...ui_widgets import _row, _section, Tooltip

from .common import clear, scrollable


def build(parent, tab) -> None:
    p = parent
    clear(parent)

    inner, canvas = scrollable(p)

    # ── Pantalla de dependencias faltantes ──────────────────────
    tab.refs['install_frame'] = tk.Frame(inner, bg=C["bg"])
    
    # ── Contenido principal ──────────────────────────────────────
    tab.refs['dep_frame'] = tk.Frame(inner, bg=C["bg"])
    tab.refs['dep_frame'].pack(fill="both", expand=True)

    # 1. Dispositivos Detectados & Bóveda
    sf = _section(tab.refs['dep_frame'], "🔍  Dispositivos Detectados & Bóveda de Confianza", pady=(8, 6), padx=14)
    r0 = _row(sf, pady=2)
    btn_scan = tk.Button(r0, text=_("🔄  Buscar dispositivos"), bg=C["blue"], fg="#FFFFFF",
                         font=FONT_SM, relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
                         command=tab.cb.get('refresh_devices'))
    btn_scan.pack(side="left", padx=(0, 8))
    Tooltip(btn_scan, "Escanea dispositivos USB y WiFi (Ctrl+R)")

    tab.refs['scan_lbl'] = tk.Label(r0, text="", bg=C["card"], fg=C["muted"], font=FONT_SM)
    tab.refs['scan_lbl'].pack(side="left")

    btn_vault = tk.Button(r0, text=_("🛡️ Bóveda de Confiables"), bg=C["card2"], fg=C["indigo"],
                          font=FONT_SM, relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                          command=tab.cb.get('open_trust_vault'))
    btn_vault.pack(side="right")
    Tooltip(btn_vault, "Administra los dispositivos autorizados en la bóveda de seguridad.")

    list_frame = tk.Frame(sf, bg=C["card2"], highlightbackground=C["card_border"], highlightthickness=1)
    list_frame.pack(fill="both", expand=True, pady=4)
    tab.refs['dev_listbox'] = tk.Listbox(
        list_frame, bg=C["card2"], fg=C["text"],
        selectbackground=C["card3"], selectforeground="#FFF",
        font=(FONT_FAMILY, 10), relief="flat", bd=0,
        highlightthickness=0, activestyle="none", height=4)
    tab.refs['dev_listbox'].pack(side="left", fill="both", expand=True)
    dev_sb = ttk.Scrollbar(list_frame, orient="vertical",
                            command=tab.refs['dev_listbox'].yview)
    dev_sb.pack(side="right", fill="y")
    tab.refs['dev_listbox'].configure(yscrollcommand=dev_sb.set)
    tab.refs['dev_listbox'].bind("<<ListboxSelect>>", tab.cb.get('on_dev_select'))

    info_act_row = _row(sf, pady=2)
    tab.refs['dev_info_lbl'] = tk.Label(info_act_row,
                                         text=_("Selecciona un dispositivo de la lista."),
                                         bg=C["card"], fg=C["muted"], font=FONT_SM)
    tab.refs['dev_info_lbl'].pack(side="left")

    tab.refs['dev_trust_btn'] = tk.Button(info_act_row, text=_("🛡️ Confiar / Alias"),
                                           bg=C["card2"], fg=C["text"], font=FONT_SM,
                                           relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
                                           command=tab.cb.get('open_device_trust_modal'))
    tab.refs['dev_trust_btn'].pack(side="right")
    Tooltip(tab.refs['dev_trust_btn'], "Configura el estado de confianza y alias en la bóveda.")

    # 2. Conexión Wi-Fi & Seguridad Inalámbrica
    wf = _section(tab.refs['dep_frame'], "📡  Conexión Inalámbrica Wi-Fi & Blindaje", pady=(4, 6), padx=14)
    
    # Modo A: Emparejamiento Seguro (Android 11+)
    pair_box = tk.Frame(wf, bg=C["card2"], padx=10, pady=8, highlightbackground=C["card_border"], highlightthickness=1)
    pair_box.pack(fill="x", pady=(2, 6))

    tk.Label(pair_box, text=_("🔒 Emparejamiento Seguro (Android 11+)"), bg=C["card2"], fg=C["green"], font=FONT_UI_B).pack(anchor="w")
    tk.Label(pair_box, text=_("Empareja de forma segura mediante código de 6 dígitos usando TLS."), bg=C["card2"], fg=C["muted"], font=FONT_SM).pack(anchor="w", pady=(0, 4))

    pr1 = tk.Frame(pair_box, bg=C["card2"])
    pr1.pack(fill="x", pady=2)

    tk.Label(pr1, text=_("IP:Puerto:"), bg=C["card2"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
    tab.refs['pair_ip_entry'] = ttk.Entry(pr1, width=18)
    tab.refs['pair_ip_entry'].insert(0, "192.168.1.")
    tab.refs['pair_ip_entry'].pack(side="left", padx=4)
    Tooltip(tab.refs['pair_ip_entry'], "IP y puerto que muestra el diálogo 'Vincular con código'.")

    tk.Label(pr1, text=_("Código:"), bg=C["card2"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(6, 4))
    tab.refs['pair_code_entry'] = ttk.Entry(pr1, width=8)
    tab.refs['pair_code_entry'].pack(side="left", padx=4)
    Tooltip(tab.refs['pair_code_entry'], "Código de vinculación de 6 dígitos.")

    btn_pair = tk.Button(pr1, text=_("🔒 Emparejar (`adb pair`)"), bg=C["green_dim"], fg=C["green"],
                         font=FONT_SM, relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
                         command=tab.cb.get('pair_wifi'))
    btn_pair.pack(side="left", padx=6)

    # Modo B: Conexión Directa TCP/IP & Blindaje
    tcp_box = tk.Frame(wf, bg=C["card2"], padx=10, pady=8, highlightbackground=C["card_border"], highlightthickness=1)
    tcp_box.pack(fill="x", pady=(2, 4))

    tk.Label(tcp_box, text=_("📶 Conexión Directa TCP/IP & Blindaje"), bg=C["card2"], fg=C["indigo"], font=FONT_UI_B).pack(anchor="w")

    wr = tk.Frame(tcp_box, bg=C["card2"])
    wr.pack(fill="x", pady=(4, 4))

    tk.Label(wr, text=_("IP:"), bg=C["card2"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
    tab.refs['ip_entry'] = ttk.Entry(wr, width=16)
    tab.refs['ip_entry'].insert(0, "192.168.1.")
    tab.refs['ip_entry'].pack(side="left", padx=4)

    tk.Label(wr, text=_(":"), bg=C["card2"], fg=C["muted"]).pack(side="left")
    tab.refs['port_entry'] = ttk.Entry(wr, width=6)
    tab.refs['port_entry'].insert(0, "5555")
    tab.refs['port_entry'].pack(side="left", padx=4)

    btn_getip = tk.Button(wr, text=_("📡 Obtener IP"), bg=C["card3"], fg=C["text2"],
                          font=FONT_SM, relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
                          command=tab.cb.get('get_device_ip'))
    btn_getip.pack(side="left", padx=6)

    btns_w = tk.Frame(tcp_box, bg=C["card2"])
    btns_w.pack(fill="x", pady=(4, 2))

    tk.Button(btns_w, text=_("Conectar"), bg=C["blue"], fg="#FFFFFF", font=FONT_SM,
              relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
              command=tab.cb.get('connect_wifi')).pack(side="left", padx=(0, 6))

    tk.Button(btns_w, text=_("Habilitar TCP/IP (USB→WiFi)"), bg=C["card3"], fg=C["text2"], font=FONT_SM,
              relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=tab.cb.get('enable_tcpip')).pack(side="left", padx=(0, 6))
    
    btn_lockdown = tk.Button(btns_w, text=_("🛡️ Blindar TCP/IP"), bg=C["red_dim"], fg=C["red"], font=FONT_SM,
                             relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                             command=tab.cb.get('lockdown_tcpip'))
    btn_lockdown.pack(side="right")
    Tooltip(btn_lockdown, "Revoca el puerto 5555 en el teléfono y lo devuelve a modo USB seguro.")

    # Reverse Tethering (Compartir Internet de PC a Android por USB)
    tether_r = tk.Frame(tcp_box, bg=C["card2"])
    tether_r.pack(fill="x", pady=(6, 2))
    btn_tether = tk.Button(tether_r, text=_("🌐 Compartir Internet (USB / Reverse Tethering)"), bg=C["card3"], fg=C["cyan"],
                           font=FONT_SM, relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                           command=tab.cb.get('toggle_tethering'))
    btn_tether.pack(side="left")
    Tooltip(btn_tether, _("Comparte la conexión de internet de tu PC al teléfono mediante el cable USB (gnirehtet)."))

    # 3. v4l2loopback
    vf = _section(tab.refs['dep_frame'], "📷  Webcam Virtual (v4l2loopback)", pady=(4, 12), padx=14)
    tab.refs['v4l2_lbl'] = tk.Label(vf, text=_("Verificando módulo…"), bg=C["card"], fg=C["orange"], font=FONT_SM)
    tab.refs['v4l2_lbl'].pack(anchor="w", padx=4, pady=2)
    vr = _row(vf, pady=2)
    tab.refs['load_v4l2_btn'] = tk.Button(vr, text=_("Cargar módulo"), bg=C["card2"], fg=C["text"],
                                           font=FONT_SM, relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                                           command=tab.cb.get('setup_v4l2'))
    tab.refs['load_v4l2_btn'].pack(side="left", padx=(0, 6))

    tab.refs['route_cam_btn'] = tk.Button(vr, text=_("Enrutar cámara → /dev/video9"), bg=C["green_dim"], fg=C["green"],
                                           font=FONT_SM, relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                                           command=tab.cb.get('route_cam'))
    tab.refs['route_cam_btn'].pack(side="left", padx=(0, 6))
