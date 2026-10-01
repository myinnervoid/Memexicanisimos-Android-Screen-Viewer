"""Piezas que comparten las pestañas: el contrato de construcción y el lienzo.

Antes todo esto vivía dentro de `UIBuilder`, copiado en cada pestaña. Aquí hay
una sola versión de cada cosa.
"""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Any

from ...ui_widgets import bind_mousewheel
from ...utils import C


@dataclass
class TabContext:
    """Lo que una pestaña necesita para construirse, como contrato explícito.

    `refs` y `faq_items` se comparten **por identidad** con la fachada: las
    pestañas escriben en estas estructuras y `ScrcpyDockApp` las consulta en
    caliente (`ui.refs['dev_listbox']`, `ui._faq_items[1].expand()`).
    """

    ctx: Any          # AppContext: estado y servicios de la aplicación
    cb: dict          # callbacks de la app, indexados por nombre
    refs: dict        # salida: widgets que la app refresca después
    faq_items: list   # salida: acordeones de la FAQ (solo los usa la pestaña Ayuda)


def clear(parent) -> None:
    """Vacía el contenedor antes de reconstruir la pestaña.

    Sin esto, `main.py:_change_theme` (que vuelve a llamar a los siete
    constructores sobre los mismos frames) apila un árbol de widgets completo
    encima del anterior: P3.25.
    """
    for w in parent.winfo_children():
        w.destroy()


def scrollable(parent) -> tuple[tk.Frame, tk.Canvas]:
    """Crea el marco interior desplazable estándar y devuelve `(inner, canvas)`.

    El bloque estaba copiado en cinco pestañas, con las mismas trece líneas.
    """
    canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
    vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    inner = tk.Frame(canvas, bg=C["bg"])
    cwin = canvas.create_window((0, 0), window=inner, anchor="nw")

    canvas.bind("<Configure>", lambda e: canvas.itemconfig(cwin, width=e.width))
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    bind_mousewheel(inner, canvas)
    return inner, canvas
