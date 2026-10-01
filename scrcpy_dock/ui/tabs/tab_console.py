"""Consola: visor de logs con filtros."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ...i18n import _
from ...utils import C, FONT_SM, FONT_MONO

from .common import clear


def build(parent, tab) -> None:
    p = parent
    clear(parent)

    tb = tk.Frame(p, bg=C["card2"], pady=4, padx=8)
    tb.pack(fill="x", side="top")
    tk.Label(tb, text=_("Filtrar:"), bg=C["card2"], fg=C["muted"], font=FONT_SM).pack(side="left", padx=(4, 6))

    for name, filter_key in [(_("Todos"), _("ALL")), (_("Errores"), _("ERROR")),
                              (_("ADB"), _("ADB")), (_("Scrcpy"), _("INFO"))]:
        btn = tk.Button(tb, text=name, bg=C["card"], fg=C["text"],
                        font=FONT_SM, relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
                        command=lambda k=filter_key: tab.cb.get('filter_log')(k))
        btn.pack(side="left", padx=2)

    tk.Button(tb, text=_("📋  Copiar todo"), bg=C["card3"], fg=C["text"],
              font=FONT_SM, relief="flat", bd=0, padx=10, pady=3, cursor="hand2",
              command=tab.cb.get('copy_log')).pack(side="right", padx=4)

    tab.refs['log_txt'] = tk.Text(p, bg="#0E0D0B", fg=C["text"], wrap="word",
                                   font=FONT_MONO, state="disabled", relief="flat", bd=0)
    log_sb = ttk.Scrollbar(p, orient="vertical", command=tab.refs['log_txt'].yview)
    tab.refs['log_txt'].configure(yscrollcommand=log_sb.set)
    tab.refs['log_txt'].pack(side="left", fill="both", expand=True)
    log_sb.pack(side="right", fill="y")

    for tag, color in [("ERROR", C["red"]), ("WARNING", C["orange"]),
                       ("INFO", C["cyan"]), (_("ADB"), "#A0D8EF"), ("OK", C["green"])]:
        tab.refs['log_txt'].tag_config(tag, foreground=color)

    cb = tk.Frame(p, bg=C["card2"])
    cb.pack(fill="x", side="bottom")
    tk.Button(cb, text=_("🗑  Limpiar consola"), bg=C["card3"], fg=C["text"],
              font=FONT_SM, relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
              command=tab.cb.get('clear_log')).pack(side="left", padx=8, pady=4)
    tk.Button(cb, text=_("📄  Abrir archivo de log"), bg=C["card"], fg=C["muted"],
              font=FONT_SM, relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
              command=tab.cb.get('open_log')).pack(side="right", padx=8, pady=4)
