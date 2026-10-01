import unittest
from scrcpy_dock.contracts import OperationResult, DeviceEntry, ProfileConfig
from scrcpy_dock.errors import ErrorCode, get_error_detail

class TestOperationResult(unittest.TestCase):
    def test_ok_result(self):
        res = OperationResult.ok(data={"key": "val"}, message="Success message")
        self.assertTrue(res.success)
        self.assertTrue(bool(res))
        self.assertEqual(res.data, {"key": "val"})
        self.assertEqual(res.error_code, ErrorCode.NONE)
        self.assertEqual(res.message, "Success message")

    def test_fail_result(self):
        res = OperationResult.fail(ErrorCode.DEVICE_NOT_FOUND, "Dispositivo no encontrado", data=None)
        self.assertFalse(res.success)
        self.assertFalse(bool(res))
        self.assertIsNone(res.data)
        self.assertEqual(res.error_code, ErrorCode.DEVICE_NOT_FOUND)
        self.assertEqual(res.message, "Dispositivo no encontrado")

    def test_tuple_unpacking_compatibility(self):
        # Asegurar compatibilidad hacia atrás con el patrón ok, msg = func()
        res_ok = OperationResult.ok(data="192.168.1.5", message="Conectado")
        ok, msg = res_ok
        self.assertTrue(ok)
        self.assertEqual(msg, "Conectado")

        res_fail = OperationResult.fail(ErrorCode.PAIRING_FAILED, "Código incorrecto")
        ok, msg = res_fail
        self.assertFalse(ok)
        self.assertEqual(msg, "Código incorrecto")

    def test_to_dict_serialization(self):
        res = OperationResult.fail(ErrorCode.PAIRING_TIMEOUT, "Tiempo agotado", data="192.168.1.100:5555")
        d = res.to_dict()
        self.assertEqual(d["success"], False)
        self.assertEqual(d["error_code"], "ERR_PAIRING_TIMEOUT")
        self.assertEqual(d["message"], "Tiempo agotado")
        self.assertEqual(d["data"], "192.168.1.100:5555")


class TestDomainDataclasses(unittest.TestCase):
    def test_device_entry(self):
        dev = DeviceEntry(serial="DEV_999", model="Pixel 7 Pro", state="device", alias="Mi Pixel")
        self.assertEqual(dev.serial, "DEV_999")
        self.assertEqual(dev.display_name, "Mi Pixel (DEV_999)")
        self.assertTrue(dev.is_authorized)

    def test_device_entry_unauthorized(self):
        dev = DeviceEntry(serial="DEV_000", model="Android", state="unauthorized")
        self.assertFalse(dev.is_authorized)
        self.assertEqual(dev.display_name, "Android (DEV_000)")

    def test_profile_config(self):
        prof = ProfileConfig(name="Custom Gaming", bitrate="16M", max_fps="120", video_codec="h265")
        self.assertEqual(prof.name, "Custom Gaming")
        self.assertEqual(prof.bitrate, "16M")
        self.assertEqual(prof.max_fps, "120")
        self.assertEqual(prof.video_codec, "h265")


class TestErrors(unittest.TestCase):
    def test_error_catalog_lookup(self):
        detail = get_error_detail(ErrorCode.ADB_NOT_FOUND)
        self.assertEqual(detail.code, ErrorCode.ADB_NOT_FOUND)
        self.assertIn("adb", detail.title_es.lower())
        self.assertTrue(len(detail.remediation_es) > 0)
        self.assertTrue(len(detail.remediation_en) > 0)

    def test_unknown_error_fallback(self):
        detail = get_error_detail(ErrorCode.UNKNOWN_ERROR)
        self.assertEqual(detail.code, ErrorCode.UNKNOWN_ERROR)
        self.assertTrue(len(detail.description_es) > 0)

if __name__ == "__main__":
    unittest.main()
