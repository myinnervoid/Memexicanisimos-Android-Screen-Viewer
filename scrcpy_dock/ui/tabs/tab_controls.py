"""Controles: mando remoto por keyevents e instalador APK."""
from __future__ import annotations

import tkinter as tk

from ...i18n import _
from ...utils import C, FONT_UI_B, FONT_SM
from ...ui_widgets import _section, Tooltip

from .common import clear, scrollable


def build(parent, tab) -> None:
    p = parent
    clear(parent)
    inner, canvas = scrollable(p)

    # ── 1. Mando de Controles del Hardware & Navegación ──────────
    c_sec = _section(inner, "🎮  Mando de Control Remoto (ADB Keyevents)", pady=(10, 8), padx=14)

    info_f = tk.Frame(c_sec, bg=C["card"], padx=8, pady=2)
    info_f.pack(fill="x", pady=(0, 6))

    d_box = tk.Frame(info_f, bg=C["card"])
    d_box.pack(side="left")
    tk.Label(d_box, text=_("Dispositivo:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
    tab.refs['ctrl_device_lbl'] = tk.Label(d_box, textvariable=tab.ctx.active_device,
                                            bg=C["card"], fg=C["green"], font=FONT_UI_B)
    tab.refs['ctrl_device_lbl'].pack(side="left")
    tab.refs['ctrl_trust_lbl'] = tk.Label(d_box, text="", bg=C["card"], fg=C["green"], font=FONT_SM)
    tab.refs['ctrl_trust_lbl'].pack(side="left", padx=(6, 0))

    p_box = tk.Frame(info_f, bg=C["card"])
    p_box.pack(side="right")
    tk.Label(p_box, text=_("Perfil:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 4))
    tab.refs['ctrl_profile_lbl'] = tk.Label(p_box, textvariable=tab.ctx.active_profile,
                                             bg=C["card"], fg=C["cyan"], font=FONT_UI_B)
    tab.refs['ctrl_profile_lbl'].pack(side="left")

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
                      cursor="hand2", command=lambda c=code: tab.cb.get('send_keyevent')(c))
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
                      cursor="hand2", command=lambda c=code: tab.cb.get('send_keyevent')(c))
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
                      cursor="hand2", command=lambda c=code: tab.cb.get('send_keyevent')(c))
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
                        command=tab.cb.get('install_apk'))
    btn_apk.pack(side="left", padx=4)
    Tooltip(btn_apk, "Abre el explorador de archivos para elegir un .apk e instalarlo vía ADB.")

    # Tip en su propia fila para evitar truncamiento
    tip_r = tk.Frame(apk_sec, bg=C["card"])
    tip_r.pack(fill="x", pady=(6, 4))
    tk.Label(tip_r, text=_("💡 Tip: Durante una sesión activa, también puedes arrastrar archivos .apk directo a la ventana de transmisión."),
             bg=C["card"], fg=C["cyan"], font=FONT_SM, wraplength=650, justify="left").pack(anchor="w", padx=4)
