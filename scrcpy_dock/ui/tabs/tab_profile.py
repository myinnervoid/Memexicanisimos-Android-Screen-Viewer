"""Perfiles: listado, detalle y perfil activo."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ...i18n import _
from ...utils import C, FONT_FAMILY, FONT_SM
from ...ui_widgets import _row, _section, Tooltip, ProfileChipsView

from .common import clear, scrollable


def build(parent, tab) -> None:
    p = parent
    clear(parent)
    inner, canvas = scrollable(p)

    sf = _section(inner, "📁  Perfiles Guardados", pady=(8, 6), padx=14)
    
    list_f = tk.Frame(sf, bg=C["card2"], highlightbackground=C["card_border"], highlightthickness=1)
    list_f.pack(fill="both", expand=True, pady=4)

    tab.refs['profile_listbox'] = tk.Listbox(
        list_f, bg=C["card2"], fg=C["text"],
        selectbackground=C["card3"], selectforeground="#FFF",
        font=(FONT_FAMILY, 10), relief="flat", bd=0,
        highlightthickness=0, activestyle="none", height=5)
    tab.refs['profile_listbox'].pack(fill="both", expand=True)
    tab.refs['profile_listbox'].bind("<<ListboxSelect>>", tab.cb.get('on_profile_listbox_sel'))

    pa = _row(sf, pady=2)
    btn_new = tk.Button(pa, text=_("✨  Nuevo perfil (asistente)"), bg=C["blue"], fg="#FFFFFF",
                        font=FONT_SM, relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
                        command=tab.cb.get('open_wizard'))
    btn_new.pack(side="left", padx=(0, 6))
    Tooltip(btn_new, "Crea un perfil con el asistente paso a paso.")

    btn_del = tk.Button(pa, text=_("🗑  Eliminar"), bg=C["red_dim"], fg=C["red"],
                        font=FONT_SM, relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                        command=tab.cb.get('delete_profile'))
    btn_del.pack(side="left")
    Tooltip(btn_del, "Elimina el perfil seleccionado.")

    df = _section(inner, "🔍  Detalle del Perfil Seleccionado", pady=(4, 6), padx=14)
    tab.refs['profile_chips'] = ProfileChipsView(df)
    tab.refs['profile_chips'].pack(fill="both", expand=True, pady=2)

    af = _section(inner, "🎯  Perfil Activo para la Próxima Sesión", pady=(4, 12), padx=14)
    ar = _row(af, pady=2)
    tk.Label(ar, text=_("Perfil:"), bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(0, 6))
    tab.refs['active_profile_combo'] = ttk.Combobox(
        ar, textvariable=tab.ctx.active_profile, state="readonly", width=24)
    tab.refs['active_profile_combo'].pack(side="left")
    tab.refs['active_profile_combo'].bind("<<ComboboxSelected>>", tab.cb.get('on_active_profile_change'))

    btn_start_prof = tk.Button(ar, text=_("▶  Lanzar con este perfil"), bg=C["blue"], fg="#FFFFFF",
                               font=FONT_SM, relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
                               command=tab.cb.get('start_profile'))
    btn_start_prof.pack(side="right")
    Tooltip(btn_start_prof, "Lanza scrcpy inmediatamente con el perfil y dispositivo activo.")
