"""Contratos congelados de SecurityService. NO modificar sin reabrir ADR-020."""
from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path

from scrcpy_dock.services.security_service import SecurityService
from scrcpy_dock.contracts import ErrorCode


def _make_service(tmp: Path, machine_id: str = "abc123def456") -> SecurityService:
    """Helper: service con machine-id y salt en tmp, PBKDF2 rápido."""
    mid = tmp / "machine-id"
    mid.write_text(machine_id)
    return SecurityService(
        machine_id_path=mid,
        salt_path=tmp / ".salt",
        pbkdf2_iterations=1_000,   # test-speed
    )


# ─── is_private_ip · TODO-S1 ────────────────────────────────────────

class IsPrivateIPContract(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.svc = _make_service(self.tmp)

    # IPv4 privadas (RFC 1918)
    def test_rfc1918_class_a(self):
        self.assertTrue(self.svc.is_private_ip("10.0.0.1"))
        self.assertTrue(self.svc.is_private_ip("10.255.255.254"))

    def test_rfc1918_class_b(self):
        self.assertTrue(self.svc.is_private_ip("172.16.0.1"))
        self.assertTrue(self.svc.is_private_ip("172.31.255.254"))

    def test_rfc1918_class_c(self):
        self.assertTrue(self.svc.is_private_ip("192.168.0.1"))
        self.assertTrue(self.svc.is_private_ip("192.168.1.42"))

    # Loopback y link-local
    def test_loopback_ipv4(self):
        self.assertTrue(self.svc.is_private_ip("127.0.0.1"))

    def test_link_local_ipv4(self):
        self.assertTrue(self.svc.is_private_ip("169.254.1.1"))

    # IPv6
    def test_loopback_ipv6(self):
        self.assertTrue(self.svc.is_private_ip("::1"))

    def test_link_local_ipv6(self):
        self.assertTrue(self.svc.is_private_ip("fe80::1"))

    def test_ula_ipv6(self):
        self.assertTrue(self.svc.is_private_ip("fd00::1"))

    def test_ipv6_with_brackets(self):
        self.assertTrue(self.svc.is_private_ip("[::1]"))
        self.assertTrue(self.svc.is_private_ip("[fe80::1]"))

    # Públicas
    def test_public_ipv4_rejected(self):
        self.assertFalse(self.svc.is_private_ip("8.8.8.8"))
        self.assertFalse(self.svc.is_private_ip("1.1.1.1"))
        self.assertFalse(self.svc.is_private_ip("172.32.0.1"))  # fuera de rango

    def test_public_ipv6_rejected(self):
        self.assertFalse(self.svc.is_private_ip("2001:4860:4860::8888"))

    # Casos especiales / inválidos
    def test_unspecified_rejected(self):
        self.assertFalse(self.svc.is_private_ip("0.0.0.0"))

    def test_broadcast_rejected(self):
        self.assertFalse(self.svc.is_private_ip("255.255.255.255"))

    def test_hostname_rejected(self):
        self.assertFalse(self.svc.is_private_ip("localhost"))
        self.assertFalse(self.svc.is_private_ip("example.com"))

    def test_empty_or_whitespace_rejected(self):
        self.assertFalse(self.svc.is_private_ip(""))
        self.assertFalse(self.svc.is_private_ip("   "))

    def test_garbage_never_raises(self):
        for garbage in ["not an ip", "1.2.3", "999.999.999.999",
                        ":::", "abc::def::ghi", "192.168.1.1:5555"]:
            self.assertFalse(self.svc.is_private_ip(garbage))


# ─── validate_wifi_endpoint · TODO-S2 ───────────────────────────────

class ValidateWifiEndpointContract(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.svc = _make_service(self.tmp)

    def test_valid_private_ip_normalizes(self):
        r = self.svc.validate_wifi_endpoint("192.168.1.42", 5555)
        self.assertTrue(r.success)
        self.assertEqual(r.data, "192.168.1.42:5555")

    def test_public_ip_rejected_with_invalid_ip_range(self):
        r = self.svc.validate_wifi_endpoint("8.8.8.8", 5555)
        self.assertFalse(r.success)
        self.assertEqual(r.error, ErrorCode.INVALID_IP_RANGE)

    def test_port_zero_rejected(self):
        r = self.svc.validate_wifi_endpoint("192.168.1.42", 0)
        self.assertFalse(r.success)
        self.assertEqual(r.error, ErrorCode.INVALID_INPUT)

    def test_port_above_65535_rejected(self):
        r = self.svc.validate_wifi_endpoint("192.168.1.42", 70000)
        self.assertFalse(r.success)
        self.assertEqual(r.error, ErrorCode.INVALID_INPUT)

    def test_port_1_and_65535_accepted(self):
        self.assertTrue(self.svc.validate_wifi_endpoint("10.0.0.1", 1).success)
        self.assertTrue(self.svc.validate_wifi_endpoint("10.0.0.1", 65535).success)

    def test_hostname_rejected(self):
        r = self.svc.validate_wifi_endpoint("localhost", 5555)
        self.assertFalse(r.success)
        self.assertEqual(r.error, ErrorCode.INVALID_IP_RANGE)


# ─── encrypt/decrypt_vault · TODO-S3 ────────────────────────────────

class VaultEncryptionContract(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.svc = _make_service(self.tmp)
        self.sample = {
            "version": 1,
            "trusted_devices": [
                {"serial": "ABC", "label": "Huawei Y9", "added_at": 1726281000.0},
            ],
        }

    def test_roundtrip_preserves_data(self):
        enc = self.svc.encrypt_vault(self.sample)
        self.assertTrue(enc.success)
        dec = self.svc.decrypt_vault(enc.data)
        self.assertTrue(dec.success)
        self.assertEqual(dec.data, self.sample)

    def test_encrypt_output_is_bytes(self):
        enc = self.svc.encrypt_vault(self.sample)
        self.assertIsInstance(enc.data, bytes)

    def test_ciphertext_does_not_contain_plaintext(self):
        enc = self.svc.encrypt_vault(self.sample)
        self.assertNotIn(b"ABC", enc.data)
        self.assertNotIn(b"Huawei", enc.data)

    def test_two_encryptions_differ_iv_randomized(self):
        enc1 = self.svc.encrypt_vault(self.sample)
        enc2 = self.svc.encrypt_vault(self.sample)
        self.assertNotEqual(enc1.data, enc2.data)

    def test_decrypt_with_wrong_key_fails(self):
        enc = self.svc.encrypt_vault(self.sample)

        other_tmp = Path(tempfile.mkdtemp())
        other = _make_service(other_tmp, machine_id="different-machine-id")
        dec = other.decrypt_vault(enc.data)
        self.assertFalse(dec.success)
        self.assertEqual(dec.error, ErrorCode.CONFIG_CORRUPT)

    def test_decrypt_corrupt_blob_fails(self):
        dec = self.svc.decrypt_vault(b"not-a-fernet-token")
        self.assertFalse(dec.success)
        self.assertEqual(dec.error, ErrorCode.CONFIG_CORRUPT)

    def test_encrypt_non_serializable_fails(self):
        class NotSerializable:
            pass
        enc = self.svc.encrypt_vault({"obj": NotSerializable()})
        self.assertFalse(enc.success)
        self.assertEqual(enc.error, ErrorCode.INVALID_INPUT)

    def test_decrypt_valid_token_with_bad_json_fails(self):
        from cryptography.fernet import Fernet
        key = self.svc._derive_fernet_key()
        f = Fernet(key)
        blob = f.encrypt(b"not json at all {[")
        dec = self.svc.decrypt_vault(blob)
        self.assertFalse(dec.success)
        self.assertEqual(dec.error, ErrorCode.CONFIG_CORRUPT)

    def test_salt_file_created_with_restricted_permissions(self):
        self.svc.encrypt_vault(self.sample)
        salt = self.tmp / ".salt"
        self.assertTrue(salt.exists())
        if sys.platform != "win32":
            mode = salt.stat().st_mode & 0o777
            self.assertEqual(mode, 0o600)

    def test_salt_is_reused_across_calls(self):
        enc1 = self.svc.encrypt_vault(self.sample)
        salt_bytes_before = (self.tmp / ".salt").read_bytes()

        # Nuevo service con mismo salt
        mid = self.tmp / "machine-id"
        svc2 = SecurityService(
            machine_id_path=mid,
            salt_path=self.tmp / ".salt",
            pbkdf2_iterations=1_000,
        )
        dec = svc2.decrypt_vault(enc1.data)
        self.assertTrue(dec.success)
        self.assertEqual((self.tmp / ".salt").read_bytes(), salt_bytes_before)


# ─── is_whitelisted_device · TODO-S4 ────────────────────────────────

class IsWhitelistedDeviceContract(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.svc = _make_service(self.tmp)
        self.vault = {
            "version": 1,
            "trusted_devices": [
                {"serial": "ABC123", "label": "Y9", "added_at": 1.0},
                {"serial": "DEF456", "label": "S24", "added_at": 2.0},
            ],
        }

    def test_known_serial_returns_true(self):
        self.assertTrue(self.svc.is_whitelisted_device("ABC123", self.vault))
        self.assertTrue(self.svc.is_whitelisted_device("DEF456", self.vault))

    def test_unknown_serial_returns_false(self):
        self.assertFalse(self.svc.is_whitelisted_device("XYZ", self.vault))

    def test_empty_vault_returns_false(self):
        self.assertFalse(self.svc.is_whitelisted_device("ABC123", {}))

    def test_vault_without_trusted_devices_returns_false(self):
        self.assertFalse(
            self.svc.is_whitelisted_device("ABC123", {"version": 1}),
        )

    def test_malformed_entries_are_skipped(self):
        bad = {"trusted_devices": [None, "not-a-dict", {"foo": "bar"}]}
        self.assertFalse(self.svc.is_whitelisted_device("ABC123", bad))

    def test_case_sensitive_serial(self):
        self.assertFalse(self.svc.is_whitelisted_device("abc123", self.vault))

    def test_never_raises_on_garbage(self):
        for garbage in [None, [], "string", 42]:
            self.assertFalse(self.svc.is_whitelisted_device("ABC", garbage))


if __name__ == "__main__":
    unittest.main()
