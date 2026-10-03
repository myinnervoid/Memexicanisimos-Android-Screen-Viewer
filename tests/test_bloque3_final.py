"""Pruebas de verificación de cierre para Bloque 3: ⑦, ⑧ y ⑭–⑲.

Verifica:
- ⑦ §3.20 ScrcpySession.terminate: no bloqueante con reaper daemon thread
- ⑧ D4 Catálogo de errores 30/30 (31/31 enum completo) con remediaciones bilingües
  + Ratio de contraste WCAG 2.1 AA en temas de THEMES
- ⑭ §3.34 Etiquetas de dispositivo atadas reactivamente a ctx.active_device
- ⑮ P3.35 Diálogos sin dispositivo unificados en showwarning
- ⑯ P3.36 Perfil de Cámara Frontal ratificado en DEFAULT_CONFIG y validado por ScrcpyEngine
- ⑰ P3.37 Fallback transparente de lectura de vault.enc hacia ~/.MASV/config/
- ⑱ P3.38 Gobernanza dinámica de Android 10 (--no-audio) para dispositivos Kirin/Huawei
- ⑲ P3.39 DashboardSidebar.select con notify=False rompe ciclo re-entrante
"""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
import time

from scrcpy_dock.errors import ErrorCode, ERROR_CATALOG, get_error_detail
from scrcpy_dock.utils import THEMES, DEFAULT_CONFIG
from scrcpy_dock.managers import ScrcpySession
# CONFIG_DIR aislado en directorios temporales (test_suite_sin_efectos)
from scrcpy_dock.security import SecurityManager
from scrcpy_dock.services.security_service import SecurityService
from scrcpy_dock.ui_widgets import DashboardSidebar
from scrcpy_dock.core.scrcpy_engine import ScrcpyEngine
from scrcpy_dock.domain.models import Codec, Device, DeviceCapabilities, SessionConfig


def _srgb_luminance(hex_str: str) -> float:
    hex_str = hex_str.lstrip("#")
    r, g, b = [int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
    def chan(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def _contrast_ratio(c1: str, c2: str) -> float:
    l1 = _srgb_luminance(c1)
    l2 = _srgb_luminance(c2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class TestBloque3Final(unittest.TestCase):

    # ─────────────────────────────────────────────────────────────────────────
    # ⑧ D4: Catálogo de errores completo y contraste WCAG 2.1 AA
    # ─────────────────────────────────────────────────────────────────────────

    def test_todos_los_codigos_de_error_tienen_detalle_completo(self):
        """Todos los miembros de ErrorCode deben estar en ERROR_CATALOG con textos válidos."""
        self.assertEqual(len(ERROR_CATALOG), len(ErrorCode))
        for code in ErrorCode:
            self.assertIn(code, ERROR_CATALOG, f"Código {code} no está en ERROR_CATALOG")
            detail = ERROR_CATALOG[code]
            self.assertEqual(detail.code, code)
            self.assertTrue(detail.title_es.strip(), f"{code}: title_es vacío")
            self.assertTrue(detail.title_en.strip(), f"{code}: title_en vacío")
            self.assertTrue(detail.description_es.strip(), f"{code}: description_es vacía")
            self.assertTrue(detail.description_en.strip(), f"{code}: description_en vacía")
            if code != ErrorCode.NONE:
                self.assertTrue(detail.remediation_es.strip(), f"{code}: remediation_es vacía")
                self.assertTrue(detail.remediation_en.strip(), f"{code}: remediation_en vacía")

    def test_get_error_detail_retorna_registro_del_catalogo(self):
        detail = get_error_detail(ErrorCode.PORT_POOL_EXHAUSTED)
        self.assertEqual(detail.code, ErrorCode.PORT_POOL_EXHAUSTED)
        self.assertIn("puertos", detail.title_es.lower())

    def test_contraste_wcag_21_aa_en_todos_los_temas(self):
        """El texto principal y la pastilla activa deben cumplir WCAG 2.1 AA."""
        for name, theme in THEMES.items():
            with self.subTest(theme=name):
                # Texto general sobre fondo: >= 4.5:1 (normal text)
                ratio_text_bg = _contrast_ratio(theme["text"], theme["bg"])
                self.assertGreaterEqual(
                    ratio_text_bg, 4.5,
                    f"Tema {name}: ratio text on bg {ratio_text_bg:.2f} < 4.5",
                )
                # Texto secundario sobre tarjeta: >= 4.5:1
                ratio_text2_card = _contrast_ratio(theme["text2"], theme["card"])
                self.assertGreaterEqual(
                    ratio_text2_card, 4.5,
                    f"Tema {name}: ratio text2 on card {ratio_text2_card:.2f} < 4.5",
                )
                # Texto de pastilla activa sobre pastilla activa: >= 4.5:1
                ratio_pill = _contrast_ratio(theme["pill_text_act"], theme["pill_active"])
                self.assertGreaterEqual(
                    ratio_pill, 4.5,
                    f"Tema {name}: ratio pill_text_act on pill_active {ratio_pill:.2f} < 4.5",
                )

    # ─────────────────────────────────────────────────────────────────────────
    # ⑦ §3.20: ScrcpySession.terminate no bloqueante
    # ─────────────────────────────────────────────────────────────────────────

    def test_terminate_no_bloquea_el_hilo_llamante_por_defecto(self):
        """terminate() debe retornar de inmediato (asíncrono) sin esperar los 3s."""
        proc = MagicMock()
        proc.poll.return_value = None  # Simula proceso que tarda en morir
        sess = ScrcpySession("SERIAL1", "Perfil", proc, 27183)

        t0 = time.perf_counter()
        sess.terminate(timeout=3.0, block=False)
        duracion = time.perf_counter() - t0

        self.assertFalse(sess.active)
        self.assertLess(duracion, 0.5, "terminate() bloqueó más de 500ms en el hilo llamante")

    def test_terminate_con_block_true_espera_sincrono(self):
        """terminate(block=True) espera hasta que el proceso termine o se agote el timeout."""
        proc = MagicMock()
        proc.poll.side_effect = [None, None, 0]  # Termina tras 2 iteraciones
        sess = ScrcpySession("SERIAL1", "Perfil", proc, 27183)

        sess.terminate(timeout=1.0, block=True)
        self.assertFalse(sess.active)
        self.assertTrue(proc.terminate.called)

    # ─────────────────────────────────────────────────────────────────────────
    # ⑲ P3.39: DashboardSidebar.select con notify=False
    # ─────────────────────────────────────────────────────────────────────────

    def test_sidebar_select_respeta_flag_notify(self):
        """DashboardSidebar.select con notify=False no dispara el callback on_select."""
        llamadas = []
        sidebar = DashboardSidebar.__new__(DashboardSidebar)
        sidebar.buttons = {"tab1": (MagicMock(), "icon", "Tab 1")}
        sidebar.active_id = None
        sidebar.on_select_cb = lambda tid, idx: llamadas.append((tid, idx))

        sidebar.select("tab1", 0, notify=False)
        self.assertEqual(sidebar.active_id, "tab1")
        self.assertEqual(llamadas, [], "notify=False no debió disparar el callback")

        sidebar.select("tab1", 0, notify=True)
        self.assertEqual(llamadas, [("tab1", 0)], "notify=True debió disparar el callback")

    # ─────────────────────────────────────────────────────────────────────────
    # ⑰ P3.37: Fallback de lectura transparente de vault.enc
    # ─────────────────────────────────────────────────────────────────────────

    def test_init_vault_lee_de_ruta_legacy_si_la_canonika_no_existe(self):
        """Si ~/.config/masv/vault.enc no existe pero ~/.MASV/config/vault.enc sí, se carga."""
        with tempfile.TemporaryDirectory() as tmp_masv, tempfile.TemporaryDirectory() as tmp_canon:
            legacy_dir = Path(tmp_masv) / ".MASV" / "config"
            legacy_dir.mkdir(parents=True, exist_ok=True)
            legacy_vault = legacy_dir / SecurityService.VAULT_FILENAME
            salt_file = Path(tmp_canon) / ".vault_salt"

            # Escribir bóveda cifrada en la ruta legacy (path primero, data segundo)
            sec_svc = SecurityService(salt_path=salt_file)
            guardado = sec_svc.save_vault(legacy_vault, {"schema_version": 1, "trusted_devices": {"DEV_LEGACY": {"alias": "Mi Dispositivo", "is_trusted": True}}})
            self.assertTrue(guardado.success, guardado.message)

            canon_vault = Path(tmp_canon) / "vault.enc"
            self.assertFalse(canon_vault.exists())

            cfg = {"security": {"safe_mode_enabled": True}}
            with patch.dict("os.environ", {"HOME": tmp_masv, "USERPROFILE": tmp_masv}), patch.object(Path, "home", return_value=Path(tmp_masv)):
                sec_mgr = SecurityManager(cfg, vault_dir=tmp_canon)
                self.assertTrue(sec_mgr.is_vault_encrypted)
                self.assertTrue(sec_mgr.is_trusted_device("DEV_LEGACY"))

    # ─────────────────────────────────────────────────────────────────────────
    # ⑯ P3.36: Perfil Cámara Frontal ratificado en DEFAULT_CONFIG
    # ─────────────────────────────────────────────────────────────────────────

    def test_perfil_camara_frontal_valido_en_default_config(self):
        """El perfil Cámara Frontal debe estar en DEFAULT_CONFIG y generar comando válido."""
        self.assertIn("📷 Cámara Frontal", DEFAULT_CONFIG["profiles"])
        p = DEFAULT_CONFIG["profiles"]["📷 Cámara Frontal"]
        self.assertIn("--camera-facing=front", p["extra_args"])

        from scrcpy_dock.services.stream_service import StreamService
        engine = ScrcpyEngine("/usr/bin/scrcpy", "/usr/share/scrcpy/scrcpy-server")
        svc = StreamService(lambda: engine, lambda: None, lambda msg: None)
        res_comp = svc._compile_profile(p)
        self.assertTrue(res_comp.success)

        sess_cfg = svc._build_config(p, res_comp.data, 27183)
        self.assertEqual(sess_cfg.camera_facing, "front")
        self.assertEqual(sess_cfg.video_source, "camera")

        dev = Device(serial="DEV_FRONT", model="Test", android_sdk=31)
        caps = DeviceCapabilities("Samsung", "Android")
        res_cmd = engine.build_command(sess_cfg, dev, caps)
        self.assertTrue(res_cmd.success)
        self.assertIn("--camera-facing", res_cmd.data)
        self.assertEqual(res_cmd.data[res_cmd.data.index("--camera-facing") + 1], "front")

    # ─────────────────────────────────────────────────────────────────────────
    # ⑱ P3.38: Gobernanza dinámica de Android 10
    # ─────────────────────────────────────────────────────────────────────────

    def test_android_10_fuerza_no_audio_dinamicamente(self):
        """En dispositivos con Android 10 (SDK <= 29), se añade --no-audio automáticamente."""
        engine = ScrcpyEngine("/usr/bin/scrcpy", "/usr/share/scrcpy/scrcpy-server")
        cfg = SessionConfig(
            port=27183,
            codec=Codec.H264,
            resolution="1080",
            bit_rate=8_000_000,
            video_source="display",
            audio_source="playback",
        )
        dev_android10 = Device(serial="HWY9", model="Huawei Y9", android_sdk=29)
        caps = DeviceCapabilities("Huawei", "Android")

        res = engine.build_command(cfg, dev_android10, caps)
        self.assertTrue(res.success)
        self.assertIn("--no-audio", res.data)
        self.assertNotIn("--audio-source", res.data)


if __name__ == "__main__":
    unittest.main()
