"""Acciones: transmisión y tabla de sesiones activas."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ...i18n import _
from ...utils import C, FONT_UI_B, FONT_SM, FONT_CARD
from ...ui_widgets import Tooltip

from .common import clear, scrollable


def build(parent, tab) -> None:
    p = parent
    clear(parent)
    inner, canvas = scrollable(p)

    # ── Header de dispositivo + perfil activo ────────────────────
    info = tk.Frame(inner, bg=C["card"], pady=8, padx=14,
                    highlightbackground=C["card_border"], highlightthickness=1)
    info.pack(fill="x", padx=14, pady=(10, 6))
    
    d_box = tk.Frame(info, bg=C["card"])
    d_box.pack(side="left")
    tk.Label(d_box, text=_("Dispositivo:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
    tab.refs['action_device_lbl'] = tk.Label(d_box, textvariable=tab.ctx.active_device,
                                              bg=C["card"], fg=C["text"], font=FONT_UI_B)
    tab.refs['action_device_lbl'].pack(side="left")
    tab.refs['action_trust_lbl'] = tk.Label(d_box, text="", bg=C["card"], fg=C["green"], font=FONT_SM)
    tab.refs['action_trust_lbl'].pack(side="left", padx=(6, 0))

    p_box = tk.Frame(info, bg=C["card"])
    p_box.pack(side="right")
    tk.Label(p_box, text=_("Perfil:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
    tab.refs['action_profile_lbl'] = tk.Label(p_box, textvariable=tab.ctx.active_profile,
                                               bg=C["card"], fg=C["cyan"], font=FONT_UI_B)
    tab.refs['action_profile_lbl'].pack(side="left")

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
                          command=tab.cb.get('toggle_scene'))
    btn_start.pack(side="left", padx=(0, 8))
    Tooltip(btn_start, "Lanza scrcpy con el perfil seleccionado (Ctrl+I)")

    btn_stop = tk.Button(btn_bar, text=_("■  Detener"), bg=C["card2"], fg=C["text"],
                         font=FONT_UI_B, relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
                         command=tab.cb.get('stop_current'))
    btn_stop.pack(side="left", padx=(0, 8))
    Tooltip(btn_stop, "Detiene la transmisión activa del dispositivo.")

    # Herramientas secundarias
    tools_sec = tk.Frame(hero, bg=C["card"])
    tools_sec.pack(side="right", anchor="e")

    tk.Label(tools_sec, text=_("Herramientas:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(anchor="e", pady=(0, 2))
    tb = tk.Frame(tools_sec, bg=C["card"])
    tb.pack(anchor="e")

    btn_adb = tk.Button(tb, text=_("↺ ADB"), bg=C["card2"], fg=C["text2"], font=FONT_SM,
                        relief="flat", bd=0, padx=8, pady=4, cursor="hand2", command=tab.cb.get('restart_adb'))
    btn_adb.pack(side="left", padx=2)
    Tooltip(btn_adb, "Reinicia el servidor ADB en caso de desconexión.")

    btn_cam = tk.Button(tb, text=_("📷 Webcam"), bg=C["card2"], fg=C["indigo"], font=FONT_SM,
                        relief="flat", bd=0, padx=8, pady=4, cursor="hand2", command=tab.cb.get('route_cam'))
    btn_cam.pack(side="left", padx=2)
    Tooltip(btn_cam, "Enruta la cámara hacia /dev/video9 (Linux).")

    btn_panic = tk.Button(tb, text=_("⚠ Todo"), bg=C["red_dim"], fg=C["red"], font=FONT_SM,
                          relief="flat", bd=0, padx=8, pady=4, cursor="hand2", command=tab.cb.get('panic_kill'))
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
    tab.refs['sess_tree'] = ttk.Treeview(sf, columns=cols, show="headings",
                                          height=5, selectmode="browse")
    for col_id, heading, width, stretch in [
        ("serial",  "Dispositivo",  200, True),
        ("profile", "Perfil",       140, True),
        ("pid",     "PID",           80, False),
        ("uptime",  "Tiempo",        90, False),
        ("status",  "Estado",       130, True),
    ]:
        tab.refs['sess_tree'].heading(col_id, text=heading)
        tab.refs['sess_tree'].column(col_id, width=width,
                                     anchor="center", stretch=stretch)

    tab.refs['sess_tree'].tag_configure("RUN", foreground=C["green"])
    tab.refs['sess_tree'].tag_configure("STP", foreground=C["red"])
    sess_sb = ttk.Scrollbar(sf, orient="vertical",
                            command=tab.refs['sess_tree'].yview)
    tab.refs['sess_tree'].configure(yscrollcommand=sess_sb.set)
    tab.refs['sess_tree'].pack(side="left", fill="both", expand=True)
    sess_sb.pack(side="right", fill="y")

    tab.refs['sess_tree'].bind("<Delete>",  tab.cb.get('stop_selected'))
    tab.refs['sess_tree'].bind("<Button-3>", tab.cb.get('sess_context_menu'))

    btn_container = tk.Frame(inner, bg=C["bg"])
    btn_container.pack(fill="x", padx=14, pady=(4, 14))
    tk.Button(btn_container, text=_("✕  Detener sesión seleccionada"), bg=C["red_dim"], fg=C["red"],
              font=FONT_SM, relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
              command=tab.cb.get('stop_selected')).pack(side="right")
