"""SecurityService · Validación de red, cifrado de vault y whitelist.

Contrato v1 congelado — ver ADR-020, ADR-031.
NO cambiar firmas sin reabrir el ADR correspondiente.

Estado del esqueleto:
  ✅ __init__ + helpers internos           → implementados
  ✅ is_private_ip                          → TODO-S1 implementado
  🟡 validate_wifi_endpoint                 → TODO-S2
  🟡 encrypt_vault / decrypt_vault          → TODO-S3
  🟡 is_whitelisted_device                  → TODO-S4
"""
from __future__ import annotations

import ipaddress
import json
import logging
import os
import secrets
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.errors import ErrorCode


log = logging.getLogger(__name__)


# Constantes de cifrado (ADR-020)
_PBKDF2_DEFAULT_ITERATIONS = 200_000
_SALT_SIZE_BYTES = 32
_VAULT_VERSION = 1


@dataclass(frozen=True)
class TrustedDevice:
    serial: str
    label: str
    added_at: float


class SecurityService:
    """Servicio de seguridad transversal.

    Responsabilidades:
      - Validación de IPs privadas (RFC 1918 / 4193 + loopback + link-local)
      - Normalización de endpoints WiFi (host:puerto)
      - Cifrado/descifrado de vault.enc con Fernet + PBKDF2(machine-id, salt)
      - Consulta de dispositivos en whitelist

    NO responsabilidades:
      - Enviar paquetes de red
      - Gestionar claves del SO (keyring, KWallet, SecretService)
      - Tocar la UI
    """

    def __init__(
        self,
        machine_id_path: Path = Path("/etc/machine-id"),
        salt_path: Path | None = None,
        pbkdf2_iterations: int = _PBKDF2_DEFAULT_ITERATIONS,
    ) -> None:
        self._machine_id_path = Path(machine_id_path)
        self._salt_path = Path(salt_path) if salt_path else None
        self._pbkdf2_iterations = pbkdf2_iterations
        self._cached_key: bytes | None = None

    # ────────────────────────────────────────────────────────────────────
    # Helpers internos (implementados)
    # ────────────────────────────────────────────────────────────────────

    def _read_machine_id(self) -> bytes:
        """Lee /etc/machine-id o el path inyectado. Sin cache (test-friendly)."""
        try:
            return self._machine_id_path.read_bytes().strip()
        except (FileNotFoundError, PermissionError) as e:
            raise RuntimeError(f"machine-id inaccesible: {e}") from e

    def _ensure_salt(self, salt_path: Path) -> bytes:
        """Lee el salt existente o crea uno nuevo con permisos 0o600."""
        if salt_path.exists():
            data = salt_path.read_bytes()
            if len(data) == _SALT_SIZE_BYTES:
                return data
            log.warning("salt con tamaño inválido, regenerando")

        salt = secrets.token_bytes(_SALT_SIZE_BYTES)
        salt_path.parent.mkdir(parents=True, exist_ok=True)
        # Escritura atómica con permisos restringidos
        tmp = salt_path.with_suffix(".tmp")
        tmp.write_bytes(salt)
        os.chmod(tmp, 0o600)
        os.replace(tmp, salt_path)
        return salt

    def _derive_fernet_key(self) -> bytes:
        """Deriva la clave Fernet de machine-id + salt vía PBKDF2-SHA256."""
        if self._cached_key is not None:
            return self._cached_key

        if self._salt_path is None:
            home = Path(os.environ.get("HOME", str(Path.home())))
            self._salt_path = home / ".MASV" / ".salt"

        machine_id = self._read_machine_id()
        salt = self._ensure_salt(self._salt_path)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self._pbkdf2_iterations,
        )
        raw = kdf.derive(machine_id)
        self._cached_key = urlsafe_b64encode(raw)
        return self._cached_key

    # ────────────────────────────────────────────────────────────────────
    # API pública · contratos congelados
    # ────────────────────────────────────────────────────────────────────

    # ─── TODO-S1 · is_private_ip ─────────────────────────────────────
    def is_private_ip(self, host: str) -> bool:
        """True si `host` es una IP privada/loopback/link-local.

        Contrato:
          - Acepta IPv4 e IPv6.
          - Acepta formato con brackets IPv6: "[::1]".
          - Rechaza: públicas, 0.0.0.0, 255.255.255.255, hostnames,
            cadenas vacías, espacios en blanco.
          - NUNCA lanza excepción: entrada inválida → False.
        """
        if not host or not host.strip():
            return False
        candidate = host.strip()
        # Quitar brackets IPv6
        if candidate.startswith("[") and candidate.endswith("]"):
            candidate = candidate[1:-1]
        try:
            ip = ipaddress.ip_address(candidate)
        except ValueError:
            return False
        # Rechazar 0.0.0.0/:: y broadcast
        if ip.is_unspecified or (ip.version == 4 and str(ip) == "255.255.255.255"):
            return False
        return ip.is_private or ip.is_loopback or ip.is_link_local

    # ─── TODO-S2 · validate_wifi_endpoint ────────────────────────────
    def validate_wifi_endpoint(
        self, host: str, port: int,
    ) -> OperationResult[str]:
        """Valida y normaliza "host:puerto" para conexión WiFi ADB.

        Contrato:
          - host debe pasar is_private_ip().
          - port debe estar en [1, 65535].
          - Devuelve "host:port" normalizado.
          - Host público → fail(INVALID_IP_RANGE).
          - Puerto fuera de rango → fail(INVALID_INPUT).
        """
        if not isinstance(port, int) or not (1 <= port <= 65535):
            return OperationResult.fail(
                ErrorCode.INVALID_INPUT,
                f"Puerto inválido: {port}. Debe estar en rango [1, 65535].",
            )

        if not self.is_private_ip(host):
            return OperationResult.fail(
                ErrorCode.INVALID_IP_RANGE,
                f"Host no es una IP privada válida: {host}",
            )

        return OperationResult.ok(f"{host.strip()}:{port}")

    # ─── TODO-S3 · encrypt/decrypt_vault ─────────────────────────────
    def encrypt_vault(self, data: dict[str, Any]) -> OperationResult[bytes]:
        """Serializa data a JSON y lo cifra con Fernet.

        Contrato:
          - data debe ser JSON-serializable.
          - data no serializable → fail(INVALID_INPUT).
          - Devuelve bytes cifrados (token Fernet).
          - Determinista solo en longitud (Fernet usa IV aleatorio).
        """
        try:
            raw_json = json.dumps(data).encode("utf-8")
        except (TypeError, ValueError) as e:
            return OperationResult.fail(
                ErrorCode.INVALID_INPUT,
                f"Datos no serializables a JSON: {e}",
            )

        try:
            key = self._derive_fernet_key()
            fernet = Fernet(key)
            encrypted = fernet.encrypt(raw_json)
            return OperationResult.ok(encrypted)
        except Exception as e:
            return OperationResult.fail(
                ErrorCode.UNKNOWN_ERROR,
                f"Error al cifrar vault: {e}",
            )

    def decrypt_vault(self, blob: bytes) -> OperationResult[dict[str, Any]]:
        """Descifra y deserializa el blob del vault.

        Contrato:
          - Token inválido (corrupción o clave distinta) → fail(CONFIG_CORRUPT).
          - JSON inválido tras descifrar → fail(CONFIG_CORRUPT).
          - Éxito → OperationResult.ok(dict).
        """
        try:
            key = self._derive_fernet_key()
            fernet = Fernet(key)
            decrypted_bytes = fernet.decrypt(blob)
        except (InvalidToken, Exception):
            return OperationResult.fail(
                ErrorCode.CONFIG_CORRUPT,
                "Token de vault corrupto o clave de cifrado inválida.",
            )

        try:
            parsed = json.loads(decrypted_bytes.decode("utf-8"))
            if not isinstance(parsed, dict):
                return OperationResult.fail(
                    ErrorCode.CONFIG_CORRUPT,
                    "Contenido del vault descifrado no es un diccionario.",
                )
            return OperationResult.ok(parsed)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return OperationResult.fail(
                ErrorCode.CONFIG_CORRUPT,
                f"JSON corrupto en vault descifrado: {e}",
            )

    # ─── TODO-S4 · is_whitelisted_device ─────────────────────────────
    def is_whitelisted_device(
        self, serial: str, vault: dict[str, Any],
    ) -> bool:
        """True si `serial` está en vault['trusted_devices'].

        Contrato:
          - vault malformado → False (no lanza).
          - vault vacío o sin clave 'trusted_devices' → False.
          - Comparación case-sensitive sobre 'serial'.
        """
        if not isinstance(vault, dict):
            return False
        devices = vault.get("trusted_devices")
        if not isinstance(devices, list):
            return False
        for entry in devices:
            if isinstance(entry, dict) and entry.get("serial") == serial:
                return True
        return False
