"""Fachada de construcción de la interfaz (`ScrcpyDockApp.ui`).

Este módulo conserva la API que ya consumía `main.py` —`UIBuilder(ctx, callbacks)`,
`ui.refs`, `ui._faq_items` y los siete métodos `build_*`— pero **ya no construye
widgets**: cada pestaña vive en `scrcpy_dock/ui/tabs/` y aquí sólo se orquesta.

Antes de C2 este archivo tenía 1.034 líneas con siete constructores de 38 a 344
líneas; ahora cada pestaña es un módulo de responsabilidad única y este archivo
sólo declara el contrato (ver `ANALISIS.md` §11.8).
"""
from __future__ import annotations

from .ui.tabs import (
    tab_actions,
    tab_console,
    tab_controls,
    tab_device,
    tab_help,
    tab_profile,
    tab_quickcast,
)
from .ui.tabs.common import TabContext


import tkinter as tk
from typing import Any, Callable, Dict, List, Optional
from .context import AppContext

class UIBuilder:
    """Orquesta la construcción de las siete pestañas.

    `refs` y `_faq_items` se comparten **por identidad** con las pestañas: son la
    salida del proceso de construcción y `ScrcpyDockApp` los consulta después
    (`ui.refs['dev_listbox']`, `ui._faq_items[1].expand()`).

    Attributes:
        ctx (AppContext): Contexto global de la aplicación.
        cb (Dict[str, Callable]): Diccionario de callbacks de la interfaz.
        refs (Dict[str, Any]): Referencias a widgets actualizables.
        _faq_items (List[Any]): Referencia a AccordionItems de la FAQ.
        _tabs (TabContext): Contexto inyectado en cada pestaña durante su construcción.
    """

    def __init__(self, app_context: AppContext, callbacks: Dict[str, Callable]) -> None:
        """Inicializa la fachada de construcción.

        Args:
            app_context: Contexto global de la aplicación con estado y dependencias.
            callbacks: Diccionario de funciones expuestas por `ScrcpyDockApp` para responder a eventos UI.
        """
        self.ctx: AppContext = app_context
        self.cb: Dict[str, Callable] = callbacks
        self.refs: Dict[str, Any] = {}          # Referencias a widgets actualizables
        self._faq_items: List[Any] = []         # Referencia a AccordionItems de la FAQ
        self._tabs: TabContext = TabContext(app_context, callbacks, self.refs, self._faq_items)

    # ── Vista simple y pestañas ───────────────────────────────────────────
    # Cada método delega en el módulo de su pestaña; la firma es la de siempre.

    def build_simple_view(self, parent: tk.Widget) -> None:
        """Construye la vista de Quickcast.

        Args:
            parent: El widget contenedor donde se inyectará la vista.
        """
        return tab_quickcast.build(parent, self._tabs)

    def build_tab_actions(self, parent: tk.Widget) -> None:
        """Construye la pestaña de Acciones.

        Args:
            parent: El widget contenedor donde se inyectará la vista.
        """
        return tab_actions.build(parent, self._tabs)

    def build_tab_controls(self, parent: tk.Widget) -> None:
        """Construye la pestaña de Controles.

        Args:
            parent: El widget contenedor donde se inyectará la vista.
        """
        return tab_controls.build(parent, self._tabs)

    def build_tab_device(self, parent: tk.Widget) -> None:
        """Construye la pestaña de Dispositivos.

        Args:
            parent: El widget contenedor donde se inyectará la vista.
        """
        return tab_device.build(parent, self._tabs)

    def build_tab_profile(self, parent: tk.Widget) -> None:
        """Construye la pestaña de Perfiles.

        Args:
            parent: El widget contenedor donde se inyectará la vista.
        """
        return tab_profile.build(parent, self._tabs)

    def build_tab_console(self, parent: tk.Widget) -> None:
        """Construye la pestaña de Consola.

        Args:
            parent: El widget contenedor donde se inyectará la vista.
        """
        return tab_console.build(parent, self._tabs)

    def build_tab_help(self, parent: tk.Widget) -> None:
        """Construye la pestaña de Ayuda.

        Args:
            parent: El widget contenedor donde se inyectará la vista.
        """
        return tab_help.build(parent, self._tabs)
