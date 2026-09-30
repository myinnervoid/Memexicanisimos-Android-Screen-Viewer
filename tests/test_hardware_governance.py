import unittest
import queue
from unittest.mock import patch, MagicMock
from scrcpy_dock.managers import SessionManager, DeviceManager, ScrcpySession

class DummyDeviceManager:
    def __init__(self, props_map):
        self.props_map = props_map
    def get_device_props(self, serial):
        return self.props_map.get(serial, {})

class TestHardwareGovernance(unittest.TestCase):
    def setUp(self):
        self.log_q = queue.Queue()

    @patch("subprocess.Popen")
    @patch("scrcpy_dock.managers.find_portable_binaries", return_value=("/usr/bin/adb", "/usr/bin/scrcpy"))
    def test_android_10_forces_no_audio(self, mock_bin, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_proc.stdout = iter([])
        mock_proc.wait.return_value = 0
        mock_popen.return_value = mock_proc

        dev_mgr = DummyDeviceManager({
            "HUAWEI_Y9_SERIAL": {
                "model": "Huawei Y9 Prime",
                "android_version": 10,
                "manufacturer": "HUAWEI",
                "platform": "kirin710"
            }
        })

        sm = SessionManager(self.log_q, device_mgr=dev_mgr)
        res = sm.start_scene("HUAWEI_Y9_SERIAL", "Curso Foto", {"audio_source": "playback", "bitrate": "16M"})
        
        self.assertTrue(res.success)
        # Verificar argumentos enviados a scrcpy
        cmd = mock_popen.call_args[0][0]
        
        # 1. Debe incluir --no-audio para Android 10
        self.assertIn("--no-audio", cmd)
        self.assertNotIn("playback", cmd)
        
        # 2. Debe limitar bitrate en Huawei Kirin a 8M
        idx_br = cmd.index("--video-bit-rate")
        self.assertEqual(cmd[idx_br + 1], "8M")
        
        # 3. Debe incluir puerto dinámico
        self.assertIn("--port", cmd)
        idx_port = cmd.index("--port")
        self.assertEqual(cmd[idx_port + 1], "27183")

        # 4. Título de ventana con modelo
        idx_title = cmd.index("--window-title")
        self.assertIn("Huawei Y9 Prime", cmd[idx_title + 1])

    @patch("subprocess.Popen")
    @patch("scrcpy_dock.managers.find_portable_binaries", return_value=("/usr/bin/adb", "/usr/bin/scrcpy"))
    def test_multi_device_dynamic_ports(self, mock_bin, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 5555
        mock_proc.stdout = iter([])
        mock_proc.wait.return_value = 0
        mock_popen.return_value = mock_proc

        dev_mgr = DummyDeviceManager({
            "DEV1": {"model": "Phone 1", "android_version": 12},
            "DEV2": {"model": "Phone 2", "android_version": 13}
        })

        sm = SessionManager(self.log_q, device_mgr=dev_mgr)
        
        # Simular sesión 1 activa en puerto 27183
        sm.sessions["DEV1"] = ScrcpySession("DEV1", "P1", mock_proc, assigned_port=27183)
        
        # Iniciar sesión 2
        res2 = sm.start_scene("DEV2", "P2", {})
        self.assertTrue(res2.success)
        
        cmd2 = mock_popen.call_args[0][0]
        idx_port = cmd2.index("--port")
        # Debe asignar 27184 para no colisionar con 27183
        self.assertEqual(cmd2[idx_port + 1], "27184")

if __name__ == "__main__":
    unittest.main()
