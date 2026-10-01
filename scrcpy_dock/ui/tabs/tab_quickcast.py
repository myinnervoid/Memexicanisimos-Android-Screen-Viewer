"""Vista rápida (Quick Cast): dashboard compacto."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ...i18n import _
from ...utils import C, FONT_FAMILY, FONT_UI, FONT_UI_B, FONT_SM
from ...ui_widgets import _section, Tooltip

from .common import clear, scrollable


def build(parent, tab) -> None:
    p = parent
    clear(parent)

    inner, canvas = scrollable(p)

    container = tk.Frame(inner, bg=C["bg"], padx=12, pady=10)
    container.pack(fill="both", expand=True)

    # ── 1. Tarjeta: Dispositivo Activo ───────────────────────────
    dev_card = _section(container, _("📱  Dispositivo Android Activo"), pady=(0, 8), padx=0)
    
    dev_row = tk.Frame(dev_card, bg=C["card"])
    dev_row.pack(fill="x", pady=4)

    tk.Label(dev_row, text=_("Dispositivo:"), bg=C["card"], fg=C["muted"], font=FONT_UI_B, width=10, anchor="w").pack(side="left")
    
    btn_refresh = tk.Button(dev_row, text=_("🔄 Buscar"), bg=C["card2"], fg=C["text"],
                            font=FONT_SM, relief="flat", bd=0, padx=8, pady=3, cursor="hand2",
                            command=tab.cb.get('refresh_devices'))
    btn_refresh.pack(side="right", padx=(4, 0))
    Tooltip(btn_refresh, _("Buscar dispositivos conectados (USB o Wi-Fi)"))

    tab.refs['simple_dev_combo'] = ttk.Combobox(dev_row, textvariable=tab.ctx.active_device, state="readonly", font=FONT_UI)
    tab.refs['simple_dev_combo'].pack(side="left", fill="x", expand=True, padx=(0, 4))
    tab.refs['simple_dev_combo'].bind("<<ComboboxSelected>>", tab.cb.get('on_dev_select'))

    tab.refs['simple_trust_lbl'] = tk.Label(dev_row, text="", bg=C["card"], fg=C["green"], font=FONT_SM)
    tab.refs['simple_trust_lbl'].pack(side="right", padx=4)

    # ── 2. Tarjeta: Perfil Rápido de Transmisión ─────────────────
    prof_card = _section(container, _("🎮  Perfil de Transmisión"), pady=(0, 8), padx=0)

    # Botones rápidos de 1-clic para perfiles estándar
    presets_row = tk.Frame(prof_card, bg=C["card"])
    presets_row.pack(fill="x", pady=(2, 6))

    def _select_preset(name):
        profiles = tab.ctx.profile_mgr.get_profiles()
        if name in profiles:
            tab.ctx.active_profile.set(name)
            tab.ctx.save_current_config()
            if tab.cb.get('on_active_profile_change'):
                tab.cb.get('on_active_profile_change')()

    for icon, title, prof_name in [
        ("🎮", _("Juego"), "Juego Rápido"),
        ("🎙️", _("Stream"), "Stream OBS"),
        ("📷", _("Webcam"), "Webcam HD"),
        ("⌨️", _("OTG"), "Modo OTG (Teclado y Ratón USB)"),
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
                             command=tab.cb.get('open_wizard'))
    btn_new_prof.pack(side="right", padx=(4, 0))
    Tooltip(btn_new_prof, _("Crear un nuevo perfil personalizado con el asistente."))

    tab.refs['simple_prof_combo'] = ttk.Combobox(prof_row, textvariable=tab.ctx.active_profile, state="readonly", font=FONT_UI)
    tab.refs['simple_prof_combo'].pack(side="left", fill="x", expand=True, padx=(0, 4))
    tab.refs['simple_prof_combo'].bind("<<ComboboxSelected>>", tab.cb.get('on_active_profile_change'))

    # Argumentos adicionales opcionales
    cmd_frame = tk.Frame(prof_card, bg=C["card"])
    cmd_frame.pack(fill="x", pady=(4, 2))
    tk.Label(cmd_frame, text=_("Args extra:"), bg=C["card"], fg=C["muted"], font=FONT_SM, width=10, anchor="w").pack(side="left")
    tab.refs['simple_extra_cmd_var'] = tk.StringVar(value="")
    e_extra = ttk.Entry(cmd_frame, textvariable=tab.refs['simple_extra_cmd_var'])
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
                          relief="flat", bd=0, padx=20, pady=10, cursor="hand2",
                          command=tab.cb.get('toggle_scene'))
    btn_start.pack(side="left", fill="x", expand=True, padx=(0, 8))
    Tooltip(btn_start, _("Lanzar transmisión con scrcpy (Ctrl+I)"))

    btn_otg = tk.Button(hero_btn_row, text=_("⌨️  Modo OTG"),
                        bg=C["card3"], fg=C["cyan"], font=(FONT_FAMILY, 10, "bold"),
                        relief="flat", bd=0, padx=12, pady=10, cursor="hand2",
                        command=tab.cb.get('start_otg_mode'))
    btn_otg.pack(side="left", padx=(0, 8))
    Tooltip(btn_otg, _("Controlar teléfono con teclado y ratón sin abrir ventana de video (cero consumo CPU)."))

    btn_stop = tk.Button(hero_btn_row, text=_("■  Detener"),
                         bg=C["red"], fg="#FFFFFF", font=(FONT_FAMILY, 11, "bold"),
                         relief="flat", bd=0, padx=16, pady=10, cursor="hand2",
                         command=tab.cb.get('stop_current'))
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
                      command=lambda c=code: tab.cb.get('send_keyevent')(c))
        b.pack(side="left", padx=3, fill="x", expand=True)
        Tooltip(b, tip)
