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


class UIBuilder:
    """Orquesta la construcción de las siete pestañas.

    `refs` y `_faq_items` se comparten **por identidad** con las pestañas: son la
    salida del proceso de construcción y `ScrcpyDockApp` los consulta después
    (`ui.refs['dev_listbox']`, `ui._faq_items[1].expand()`).
    """

    def __init__(self, app_context, callbacks):
        self.ctx = app_context
        self.cb = callbacks
        self.refs = {}          # Referencias a widgets actualizables
        self._faq_items = []    # Referencia a AccordionItems de la FAQ
        self._tabs = TabContext(app_context, callbacks, self.refs, self._faq_items)

    # ── Vista simple y pestañas ───────────────────────────────────────────
    # Cada método delega en el módulo de su pestaña; la firma es la de siempre.

    def build_simple_view(self, parent):
        return tab_quickcast.build(parent, self._tabs)

    def build_tab_actions(self, parent):
        return tab_actions.build(parent, self._tabs)

    def build_tab_controls(self, parent):
        return tab_controls.build(parent, self._tabs)

    def build_tab_device(self, parent):
        return tab_device.build(parent, self._tabs)

    def build_tab_profile(self, parent):
        return tab_profile.build(parent, self._tabs)

    def build_tab_console(self, parent):
        return tab_console.build(parent, self._tabs)

    def build_tab_help(self, parent):
        return tab_help.build(parent, self._tabs)
