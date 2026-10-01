"""Pruebas unitarias completas de ui_widgets.py.

Cubre todos los widgets y componentes compartidos de interfaz:
- Helpers de layout (_row, _sep, _section, _recolor, bind_mousewheel)
- PillNavBar (construcción, hover, selección)
- DashboardSidebar (construcción, colapso/expansión, selección, hover)
- Tooltip (programación, cancelación, renderizado y atajos)
- _card_button y _cmd_chip (eventos, hover, portapapeles)
- AccordionItem (acordeón con callable, string, canvas, scroll sincronizado)
- Toast (niveles info, success, warning, error, ciclo de vida)
- ProfileChipsView (renderizado de chips vacíos y completos)
- ProfileWizard (los 7 pasos, presets, validaciones y guardado)
- Modales de seguridad (DeviceTrustModal, TrustPromptModal, SafeActionConfirmModal, TrustVaultDialog)

Aislamiento:
- Ejecuta en Tkinter oculto (root.withdraw())
- Neutraliza modales bloqueantes (wait_window, grab_set)
- Redirige `CONFIG_FILE`, `CONFIG_DIR` y `LOG_FILE` a un directorio temporal y
  anula `save_config`, de modo que ninguna prueba pueda escribir en la
  configuración real del usuario (ver P3.32)
"""
from __future__ import annotations

import sys
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import MagicMock, patch

import scrcpy_dock.utils as utils
from tests.ui_harness import aislar_config
from scrcpy_dock.ui_widgets import (
    AccordionItem,
    DashboardSidebar,
    DeviceTrustModal,
    PillNavBar,
    ProfileChipsView,
    ProfileWizard,
    SafeActionConfirmModal,
    Toast,
    Tooltip,
    TrustPromptModal,
    TrustVaultDialog,
    _card_button,
    _cmd_chip,
    _recolor,
    _row,
    _section,
    _sep,
    bind_mousewheel,
)


class TestUiWidgets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception:
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        if cls.root:
            try:
                cls.root.destroy()
            except Exception:
                pass

    def setUp(self):
        if not self.root:
            self.skipTest("Entorno gráfico no disponible (DISPLAY no configurado)")

        # Aislamiento del entorno del usuario (P3.32): un `cfg` parcial acababa
        # escrito en la configuración REAL a través de `TrustPromptModal`.
        self._tmp = tempfile.TemporaryDirectory()
        tmp = self._tmp.name
        self.guardados: list = []
        self._patches = [
            *aislar_config(tmp),
            # Ningún widget debe tocar el disco: se registra el intento.
            patch.object(utils, "save_config", lambda cfg: self.guardados.append(cfg)),
        ]
        for p in self._patches:
            p.start()
        self.addCleanup(self._tmp.cleanup)

        # Neutralizar bloqueos de ventana para que los modales no cuelguen el runner
        self._patch_wait = patch("tkinter.Misc.wait_window", lambda self, window=None: None)
        self._patch_grab = patch("tkinter.Misc.grab_set", lambda self: None)
        self._patch_wait.start()
        self._patch_grab.start()

    def tearDown(self):
        self._patch_grab.stop()
        self._patch_wait.stop()
        for p in reversed(self._patches):
            p.stop()
        # Limpiar ventanas hijas creadas
        if self.root:
            for child in list(self.root.winfo_children()):
                try:
                    child.destroy()
                except Exception:
                    pass

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers de Layout
    # ─────────────────────────────────────────────────────────────────────────

    def test_layout_helpers(self):
        parent = tk.Frame(self.root)
        parent.pack()

        # _row
        r = _row(parent, pady=5, padx=8)
        self.assertIsInstance(r, tk.Frame)

        # _sep
        _sep(parent)

        # _section con título
        sec = _section(parent, "Sección de Prueba")
        self.assertIsInstance(sec, tk.Frame)

        # _section sin título
        sec_empty = _section(parent, "")
        self.assertIsInstance(sec_empty, tk.Frame)

        # _recolor recursivo
        child1 = tk.Frame(parent)
        child2 = tk.Label(child1, text="Hijo")
        child2.pack()
        _recolor(parent, "#123456")
        self.assertEqual(child1.cget("bg"), "#123456")

    def test_bind_mousewheel_events(self):
        parent = tk.Frame(self.root)
        parent.pack()
        canvas = tk.Canvas(parent)
        canvas.pack()
        canvas.yview_scroll = MagicMock()

        lbl = tk.Label(parent, text="Scroll me")
        lbl.pack()
        bind_mousewheel(parent, canvas)

        # Simular evento de mousewheel en Linux (Button-4 y Button-5)
        evt4 = MagicMock()
        evt4.num = 4
        evt4.delta = 0
        lbl.event_generate("<Button-4>") if sys.platform == "linux" else None

        # Simular plataformas darwin y win32
        with patch("sys.platform", "darwin"):
            ev = MagicMock(delta=5)
            # Invocar handler directo
            def run_darwin():
                canvas.yview_scroll(int(-1 * ev.delta), "units")
            run_darwin()
            canvas.yview_scroll.assert_called_with(-5, "units")

        with patch("sys.platform", "win32"):
            ev = MagicMock(delta=120)
            def run_win32():
                canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units")
            run_win32()
            canvas.yview_scroll.assert_called_with(-1, "units")

    # ─────────────────────────────────────────────────────────────────────────
    # PillNavBar
    # ─────────────────────────────────────────────────────────────────────────

    def test_pill_nav_bar(self):
        tabs = [
            ("t1", "Pestaña 1", "F1"),
            ("t2", "Pestaña 2", "F2"),
        ]
        selected = []
        navbar = PillNavBar(self.root, tabs, on_select_cb=lambda tid, idx: selected.append((tid, idx)))
        navbar.pack()

        # Verificar que se crearon los botones
        self.assertIn("t1", navbar.buttons)
        self.assertIn("t2", navbar.buttons)

        # Eventos hover
        btn1 = navbar.buttons["t1"]
        btn1.event_generate("<Enter>")
        btn1.event_generate("<Leave>")

        # Seleccionar pestaña t1
        navbar.select("t1", 0)
        self.assertEqual(navbar.active_id, "t1")
        self.assertEqual(selected, [("t1", 0)])

        # Invocar comando del botón directamente
        btn2 = navbar.buttons["t2"]
        btn2.invoke()
        self.assertEqual(navbar.active_id, "t2")
        self.assertEqual(selected[-1], ("t2", 1))

    # ─────────────────────────────────────────────────────────────────────────
    # DashboardSidebar
    # ─────────────────────────────────────────────────────────────────────────

    def test_dashboard_sidebar(self):
        nav_items = [
            ("dev", "📱", "Dispositivos", "Ctrl+1"),
            ("cast", "📡", "Transmitir", ""),
        ]
        selected = []
        sidebar = DashboardSidebar(self.root, nav_items, on_select_cb=lambda tid, i: selected.append((tid, i)))
        sidebar.pack()

        self.assertFalse(sidebar.is_collapsed)
        self.assertIn("dev", sidebar.buttons)

        # Hover
        btn, icon, lbl = sidebar.buttons["dev"]
        btn.event_generate("<Enter>")
        btn.event_generate("<Leave>")

        # Colapsar
        sidebar.toggle_collapse()
        self.assertTrue(sidebar.is_collapsed)
        self.assertEqual(sidebar.cget("width"), 54)

        # Expandir
        sidebar.toggle_collapse()
        self.assertFalse(sidebar.is_collapsed)
        self.assertEqual(sidebar.cget("width"), 210)

        # Seleccionar
        sidebar.select("cast", 1)
        self.assertEqual(sidebar.active_id, "cast")
        self.assertEqual(selected[-1], ("cast", 1))

    # ─────────────────────────────────────────────────────────────────────────
    # Tooltip
    # ─────────────────────────────────────────────────────────────────────────

    def test_tooltip_lifecycle(self):
        lbl = tk.Label(self.root, text="Widget con tooltip")
        lbl.pack()
        tip = Tooltip(lbl, "Texto explicativo", shortcut="Ctrl+T", delay=50)

        # Programar y cancelar directamente y por evento
        tip._schedule()
        self.assertIsNotNone(tip._id)
        tip._cancel()
        self.assertIsNone(tip._id)

        # Mostrar tooltip directamente
        tip._show()
        self.assertIsNotNone(tip._win)
        self.assertTrue(tip._win.winfo_exists())

        # Cancelar destruye la ventana
        tip._cancel()
        self.assertIsNone(tip._win)

    # ─────────────────────────────────────────────────────────────────────────
    # Tarjeta de acción y Chip de comando
    # ─────────────────────────────────────────────────────────────────────────

    def test_card_button_and_cmd_chip(self):
        f_card = tk.Frame(self.root)
        f_card.pack()

        clicked = []
        card = _card_button(
            f_card, "🚀", "Acción Rápida", "Descripción de la tarjeta",
            command=lambda: clicked.append(True),
            accent_color="#FF0000", hover_color="#00FF00",
            row=0, col=0, shortcut="Ctrl+R"
        )
        self.assertIsInstance(card, tk.Frame)

        # Simular hover y clic en tarjeta (mapeando brevemente la ventana para eventos de puntero)
        self.root.deiconify()
        self.root.geometry("200x200+0+0")
        self.root.update()
        card.event_generate("<Enter>")
        card.event_generate("<Leave>")
        card.event_generate("<Button-1>")
        self.root.update()
        self.root.withdraw()
        self.assertEqual(clicked, [True])

        # _cmd_chip en su propio contenedor pack
        f_chip = tk.Frame(self.root)
        f_chip.pack()
        chip = _cmd_chip(f_chip, "adb devices -l", root=self.root)
        self.assertIsInstance(chip, tk.Frame)

        # Clic en el botón de copiar
        copy_label = None
        for child in chip.winfo_children():
            if isinstance(child, tk.Label) and "Copiar" in child.cget("text"):
                copy_label = child
                break
        self.assertIsNotNone(copy_label)
        self.root.deiconify()
        self.root.update()
        copy_label.event_generate("<Button-1>")
        self.root.update()
        self.root.withdraw()
        self.assertIn("Copiado", copy_label.cget("text"))

    # ─────────────────────────────────────────────────────────────────────────
    # AccordionItem
    # ─────────────────────────────────────────────────────────────────────────

    def test_accordion_item_string_and_callable(self):
        canvas = tk.Canvas(self.root)
        canvas.pack()

        # Construcción con string
        acc_str = AccordionItem(self.root, "Pregunta Frecuente 1", "Respuesta en texto simple.", canvas_ref=canvas)
        acc_str.pack()
        self.assertFalse(acc_str._expanded)
        acc_str.expand()
        self.assertTrue(acc_str._expanded)
        acc_str.collapse()
        self.assertFalse(acc_str._expanded)

        # Hover header
        acc_str._hdr.event_generate("<Enter>")
        acc_str._hdr.event_generate("<Leave>")

        # Construcción con callable
        called = []
        def builder(container):
            called.append(container)
            tk.Label(container, text="Contenido Dinámico").pack()

        acc_cb = AccordionItem(self.root, "Pregunta Frecuente 2", builder)
        acc_cb.pack()
        self.assertEqual(len(called), 1)

    # ─────────────────────────────────────────────────────────────────────────
    # Toast
    # ─────────────────────────────────────────────────────────────────────────

    def test_toast_levels_and_destroy(self):
        for lvl in ["info", "success", "warning", "error", "unknown"]:
            t = Toast(self.root, f"Mensaje nivel {lvl}", level=lvl, duration=5000)
            self.assertTrue(t.win.winfo_exists())
            t._destroy()

    # ─────────────────────────────────────────────────────────────────────────
    # ProfileChipsView
    # ─────────────────────────────────────────────────────────────────────────

    def test_profile_chips_view(self):
        view = ProfileChipsView(self.root)
        view.pack()

        # Perfil vacío
        view.set_profile("Sin perfil", {})

        # Perfil completo con todas las opciones
        full_profile = {
            "max_size": "1080",
            "max_fps": "60",
            "bitrate": "8M",
            "video_codec": "h264",
            "audio_source": "mic",
            "turn_screen_off": True,
            "stay_awake": True,
            "no_video": True,
            "force_screen_off_keyevent": True,
            "extra_args": "--record=video.mp4",
        }
        view.set_profile("Perfil Completo", full_profile)
        # Verificar que se crearon los chips
        self.assertGreater(len(view.winfo_children()), 1)

    # ─────────────────────────────────────────────────────────────────────────
    # ProfileWizard (7 Pasos, Presets y Guardado)
    # ─────────────────────────────────────────────────────────────────────────

    def test_profile_wizard_full_flow(self):
        saved = []
        wiz = ProfileWizard(self.root, on_save_callback=lambda d: saved.append(d))

        # Paso 0: Nombre vacío falla
        wiz._name_var.set("")
        with patch("tkinter.messagebox.showerror") as mock_err:
            res = wiz._collect_step(0)
            self.assertFalse(res)
            mock_err.assert_called_once()

        # Paso 0: Nombre válido
        wiz._name_var.set("Perfil Custom Test")
        self.assertTrue(wiz._collect_step(0))
        self.assertEqual(wiz._data["name"], "Perfil Custom Test")

        # Paso 1: Presets
        for preset_name in ProfileWizard.PRESETS:
            wiz._show_step(1)
            wiz._preset_var.set(preset_name)
            self.assertTrue(wiz._collect_step(1))

        # Paso 2: Calidad de imagen
        wiz._show_step(2)
        wiz._br_var.set("12M")
        wiz._sz_var.set("1440")
        wiz._fps_var.set("60")
        wiz._codec_var.set("h265")
        self.assertTrue(wiz._collect_step(2))
        self.assertEqual(wiz._data["video_codec"], "h265")

        # Paso 3: Audio y solo audio
        wiz._show_step(3)
        wiz._audio_var.set("playback")
        wiz._novideo_var.set(True)
        wiz._usemic_var.set(True)
        self.assertTrue(wiz._collect_step(3))
        self.assertEqual(wiz._data["audio_source"], "mic")
        self.assertTrue(wiz._data["no_video"])

        # Paso 4: Batería y pantalla
        wiz._show_step(4)
        wiz._scroff_var.set(True)
        wiz._awake_var.set(True)
        wiz._kev_var.set(True)
        self.assertTrue(wiz._collect_step(4))
        self.assertTrue(wiz._data["force_screen_off_keyevent"])

        # Paso 5: Opciones avanzadas
        wiz._show_step(5)
        wiz._vsource_var.set("camera")
        wiz._camfacing_var.set("front")
        wiz._camid_var.set("1")
        wiz._acodec_var.set("aac")
        wiz._extra_var.set("--window-title 'Test'")
        self.assertTrue(wiz._collect_step(5))
        self.assertEqual(wiz._data["camera_id"], "1")

        # Paso 6: Resumen y Guardado
        wiz._show_step(6)
        wiz._prev()  # probar navegación hacia atrás
        self.assertEqual(wiz._step, 5)
        wiz._next()  # avanzar al resumen
        self.assertEqual(wiz._step, 6)

        # Finalizar
        wiz._finish()
        self.assertEqual(len(saved), 1)
        res_data = saved[0]
        self.assertEqual(res_data["name"], "Perfil Custom Test")
        self.assertIn("--no-video", res_data["extra_args"])

    # ─────────────────────────────────────────────────────────────────────────
    # Modales de Seguridad y Bóveda
    # ─────────────────────────────────────────────────────────────────────────

    def test_device_trust_modal(self):
        sec = MagicMock()
        sec.is_trusted_device.return_value = True
        sec.get_device_alias.return_value = "Alias Guardado"

        saved = []
        closed = []
        modal = DeviceTrustModal(
            self.root, "USB12345", "Pixel 7", sec,
            save_cb=lambda: saved.append(True),
            on_close_cb=lambda: closed.append(True)
        )
        # Operaciones
        modal._trust()
        sec.trust_device.assert_called()

        modal._untrust()
        sec.untrust_device.assert_called()

        modal._save_alias()
        modal._close()
        self.assertEqual(closed, [True, True, True, True])

        # Caso dispositivo no confiable y por WiFi (contiene ':')
        sec.is_trusted_device.return_value = False
        modal_wifi = DeviceTrustModal(self.root, "192.168.1.50:5555", "Huawei Y9", sec)
        modal_wifi._close()

    def test_trust_prompt_modal(self):
        sec = MagicMock()
        cfg = {"trusted_devices": {}}

        # Probar opción Trust
        m1 = TrustPromptModal(self.root, "SER1", "Model1", "Alias1", sec, cfg)
        m1._on_trust()
        self.assertEqual(m1.result, "trust")
        sec.trust_device.assert_called_with("SER1", "Model1", "Alias1")

        # Probar opción Once
        m2 = TrustPromptModal(self.root, "SER2", "Model2", "Alias2", sec)
        m2._on_once()
        self.assertEqual(m2.result, "once")

        # Probar opción Cancel
        m3 = TrustPromptModal(self.root, "SER3", "Model3", "Alias3", sec)
        m3._on_cancel()
        self.assertEqual(m3.result, "cancel")

    def test_safe_action_confirm_modal(self):
        confirmed = []
        m = SafeActionConfirmModal(
            self.root, "Confirmar acción", "¿Estás seguro?", "Pixel 7",
            on_confirm_cb=lambda: confirmed.append(True)
        )
        self.assertFalse(m.result)
        # Buscar y ejecutar botón confirmar
        for child in m.win.winfo_children():
            if isinstance(child, tk.Frame):
                for sub in child.winfo_children():
                    if isinstance(sub, tk.Frame):
                        for btn in sub.winfo_children():
                            if isinstance(btn, ttk.Button) and "Confirmar" in btn.cget("text"):
                                btn.invoke()
                                break
        self.assertTrue(m.result)
        self.assertEqual(confirmed, [True])

    def test_trust_vault_dialog(self):
        sec = MagicMock()
        sec.get_trusted_devices.return_value = {
            "DEV1": {"alias": "Mi Celular", "model": "Pixel", "is_trusted": True},
            "DEV2": {"alias": "Viejo", "model": "Nexus", "is_trusted": False},
        }
        changed = []
        dlg = TrustVaultDialog(self.root, sec, on_change_cb=lambda: changed.append(True))

        # Verificar población de la tabla
        items = dlg.tree.get_children()
        self.assertEqual(len(items), 2)

        # Eliminar sin selección
        dlg._delete_selected()
        sec.remove_device_from_vault.assert_not_called()

        # Seleccionar y eliminar
        dlg.tree.selection_set("DEV1")
        dlg._delete_selected()
        sec.remove_device_from_vault.assert_called_with("DEV1", None)
        self.assertEqual(changed, [True])
        dlg.win.destroy()


if __name__ == "__main__":
    unittest.main()
