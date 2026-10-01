import ipaddress
import logging
import os
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from .contracts import OperationResult
from .errors import ErrorCode
from .services.security_service import SecurityService

log = logging.getLogger(__name__)


class SecurityManager:
    """Gestiona la bóveda de dispositivos confiables, validación de red,

    emparejamiento seguro (Android 11+) y blindaje de puertos TCP/IP.

    Es la **fachada** que consume la UI. La criptografía de la bóveda NO se
    implementa aquí: delega en `SecurityService` (única fuente de verdad), y
    persiste el vault cifrado en `vault.enc` cuando se le pasa `vault_dir`.
    """

    def __init__(self, cfg: dict, vault_dir: Optional[str] = None):
        self.cfg = cfg
        self._vault_dir = vault_dir
        self._vault_path = os.path.join(vault_dir, SecurityService.VAULT_FILENAME) if vault_dir else None
        self._crypto: Optional[SecurityService] = None
        self._vault_broken = False
        self._vault_encrypted = False
        self._ensure_security_config()

        # Autoridad en memoria de la bóveda (permite retirar el texto plano
        # sin que `setdefault` la recree vacía).
        current = self.cfg["security"].get("trusted_devices")
        self._trusted: Dict[str, dict] = dict(current) if isinstance(current, dict) else {}

        if self._vault_path:
            self._init_vault()

    def _ensure_security_config(self):
        if "security" not in self.cfg or not isinstance(self.cfg["security"], dict):
            self.cfg["security"] = {}
        sec = self.cfg["security"]
        sec.setdefault("safe_mode_enabled", True)
        sec.setdefault("auto_lockdown_on_exit", True)
        sec.setdefault("trusted_devices", {})
        sec.setdefault("blocked_ips", [])
        sec.setdefault("vault_encrypted", False)

    # ── Bóveda cifrada (SecurityService es la única implementación criptográfica) ──

    def _crypto_or_none(self) -> Optional[SecurityService]:
        """Instancia SecurityService o None si el cifrado no está disponible."""
        if self._vault_broken or not self._vault_dir:
            return None
        if self._crypto is None:
            try:
                self._crypto = SecurityService(
                    salt_path=Path(self._vault_dir) / ".vault_salt",
                )
            except Exception as exc:  # pragma: no cover - depende del SO
                log.warning("vault: cifrado no disponible (%s)", exc)
                self._vault_broken = True
                return None
        return self._crypto

    def _vault_payload(self) -> dict:
        return {"schema_version": 1, "trusted_devices": dict(self._trusted)}

    def _init_vault(self) -> None:
        """Carga la bóveda cifrada o migra el texto plano existente."""
        svc = self._crypto_or_none()
        if svc is None:
            return
        path = Path(self._vault_path)
        if path.exists():
            res = svc.load_vault(path)
            trusted = res.data.get("trusted_devices") if (res.success and isinstance(res.data, dict)) else None
            if isinstance(trusted, dict):
                self._trusted = trusted
                self._vault_encrypted = True
                return
            log.warning("vault: no se pudo descifrar (%s); se conserva la config en claro", res.message)
            return
        if self.cfg["security"].get("vault_encrypted"):
            log.warning("vault: se esperaba un vault cifrado en %s y no existe", path)
        if self._trusted:
            self._persist_vault()

    def _persist_vault(self) -> bool:
        """Cifra la bóveda y, SOLO si se puede releer idéntica, retira el texto plano."""
        svc = self._crypto_or_none()
        if svc is None or not self._vault_path:
            return False
        try:
            Path(self._vault_dir).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log.warning("vault: %s", exc)
            return False

        backup = self._backup_plaintext_config()
        res = svc.save_vault(Path(self._vault_path), self._vault_payload())
        if not res.success:
            log.warning("vault: no se pudo escribir (%s)", res.message)
            return False

        # Verificación de ida y vuelta ANTES de retirar la copia en claro.
        check = svc.load_vault(Path(self._vault_path))
        if not check.success or not isinstance(check.data, dict) or \
                check.data.get("trusted_devices") != self._trusted:
            log.warning("vault: verificación fallida; se conserva la copia en claro")
            return False

        self._vault_encrypted = True
        self.cfg["security"]["trusted_devices"] = {}
        self.cfg["security"]["vault_encrypted"] = True
        if backup:
            log.info("vault: copia de seguridad previa en %s", backup)
        return True

    def _backup_plaintext_config(self) -> Optional[str]:
        """Copia única de config.json antes de retirar la bóveda en claro.

        Se deriva del directorio de la bóveda (en la app coincide con CONFIG_DIR),
        evitando acoplarse a `utils.CONFIG_FILE`.
        """
        try:
            import shutil
            src = Path(self._vault_dir) / "config.json"
            if not src.exists():
                return None
            bak = src.with_suffix(".json.pre-vault.bak")
            if bak.exists():
                return None
            shutil.copy2(src, bak)
            return str(bak)
        except Exception:
            return None

    def _sync_vault(self, save_cb=None) -> None:
        """Persiste la bóveda: cifrada si está disponible; si no, en config.json."""
        if self._vault_path and self._persist_vault():
            pass
        else:
            self.cfg["security"]["trusted_devices"] = dict(self._trusted)
        if save_cb:
            save_cb(self.cfg)

    @property
    def is_vault_encrypted(self) -> bool:
        return self._vault_encrypted

    @property
    def is_safe_mode_enabled(self) -> bool:
        return self.cfg.get("security", {}).get("safe_mode_enabled", True)

    def set_safe_mode(self, enabled: bool, save_cb=None):
        self._ensure_security_config()
        self.cfg["security"]["safe_mode_enabled"] = bool(enabled)
        if save_cb:
            save_cb(self.cfg)

    @property
    def is_auto_lockdown_enabled(self) -> bool:
        return self.cfg.get("security", {}).get("auto_lockdown_on_exit", True)

    def set_auto_lockdown(self, enabled: bool, save_cb=None):
        self._ensure_security_config()
        self.cfg["security"]["auto_lockdown_on_exit"] = bool(enabled)
        if save_cb:
            save_cb(self.cfg)

    # ── Validación de Red & IPs ─────────────────────────────────────────────

    @staticmethod
    def is_private_ip(ip_str: str) -> bool:
        """Verifica que la IP pertenezca estrictamente a rangos privados locales (RFC 1918 / Loopback / Link-Local)."""
        clean = ip_str.strip()
        if not clean:
            return False
        try:
            ip = ipaddress.ip_address(clean)
            return ip.is_private or ip.is_loopback or ip.is_link_local
        except ValueError:
            return False

    @staticmethod
    def parse_pair_ip_port_code(raw_ip_port: str, raw_code: str) -> Optional[Tuple[str, str, str]]:
        """Valida y estructura los datos para 'adb pair': IP, puerto (1-65535) y código numérico de 6 dígitos."""
        raw_ip_port = (raw_ip_port or "").strip()
        raw_code = (raw_code or "").strip()

        if not raw_ip_port or not raw_code:
            return None

        # El código de emparejamiento de Android es típicamente de 6 dígitos numéricos
        if not (raw_code.isdigit() and len(raw_code) == 6):
            return None

        if ":" not in raw_ip_port:
            return None

        parts = raw_ip_port.split(":", 1)
        ip_str = parts[0].strip()
        port_str = parts[1].strip()

        if not port_str.isdigit() or not (1 <= int(port_str) <= 65535):
            return None

        try:
            ip_obj = ipaddress.ip_address(ip_str)
            return str(ip_obj), port_str, raw_code
        except ValueError:
            return None

    @staticmethod
    def sanitize_text_input(text: str) -> str:
        """Sanitiza el texto del portapapeles para evitar inyecciones o caracteres de control en 'adb shell input text'."""
        if not text:
            return ""
        # Eliminar caracteres nulos y caracteres de control no imprimibles
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        # Reemplazar saltos de línea y tabuladores por espacios seguros
        sanitized = sanitized.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        # Escapar comillas para adb shell input text
        # El comando 'input text' de android interpreta espacios como caracteres especiales si no se manejan bien
        return sanitized

    # ── Bóveda de Dispositivos Confiables (Trusted Devices Vault) ───────────

    def get_trusted_devices(self) -> Dict[str, dict]:
        return self._trusted

    def is_trusted_device(self, serial: str) -> bool:
        """Determina si un serial específico está registrado y verificado en la bóveda de confianza."""
        if not serial:
            return False
        dev = self._trusted.get(serial)
        if dev and isinstance(dev, dict):
            return dev.get("is_trusted", False)
        return False

    def trust_device(self, serial: str, model: str = "Android", alias: str = "",
                     save_cb=None) -> OperationResult[dict]:
        """Registra o actualiza un dispositivo como Confiable en la bóveda."""
        if not serial:
            return OperationResult.fail(ErrorCode.INVALID_INPUT, "serial vacío")
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = dict(self._trusted.get(serial, {}))
        entry["serial"] = serial
        entry["model"] = model or entry.get("model", "Android")
        entry["alias"] = alias.strip() or entry.get("alias") or model or "Dispositivo Confiable"
        entry["is_trusted"] = True
        entry["trusted_since"] = entry.get("trusted_since", now)
        entry["last_seen"] = now

        self._trusted[serial] = entry
        self._sync_vault(save_cb)
        return OperationResult.ok(entry, f"{serial} en la bóveda")

    def untrust_device(self, serial: str, save_cb=None) -> OperationResult[None]:
        """Elimina la condición de confianza de un dispositivo (conserva el alias)."""
        if serial not in self._trusted:
            return OperationResult.ok(None, f"{serial} no estaba en la bóveda (no-op)")
        self._trusted[serial]["is_trusted"] = False
        self._sync_vault(save_cb)
        return OperationResult.ok(None, f"{serial} revocado")

    def remove_device_from_vault(self, serial: str, save_cb=None) -> OperationResult[None]:
        """Elimina completamente un dispositivo de la bóveda. Idempotente."""
        if serial in self._trusted:
            del self._trusted[serial]
            self._sync_vault(save_cb)
            return OperationResult.ok(None, f"{serial} eliminado de la bóveda")
        return OperationResult.ok(None, f"{serial} no estaba en la bóveda (no-op)")

    def get_device_alias(self, serial: str, default_model: str = "Android") -> str:
        """Obtiene el alias amigable del dispositivo si existe, o el modelo."""
        dev = self._trusted.get(serial)
        if dev and dev.get("alias"):
            return dev["alias"]
        return default_model

    # ── Operaciones de Red y Blindaje (Lockdown) ────────────────────────────

    @staticmethod
    def pair_device(adb_path: str, ip: str, port: str, code: str, timeout: int = 15) -> OperationResult[str]:
        """Ejecuta 'adb pair IP:PORT CODE' con Android 11+."""
        if not adb_path:
            return OperationResult.fail(ErrorCode.ADB_NOT_FOUND, "Binario adb no encontrado")
        target = f"{ip}:{port}"
        cmd = [adb_path, "pair", target, code]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            out = (res.stdout or "") + (res.stderr or "")
            if res.returncode == 0 and ("Successfully paired" in out or "paired to" in out):
                return OperationResult.ok(data=out.strip(), message=out.strip())
            return OperationResult.fail(
                ErrorCode.PAIRING_FAILED,
                out.strip() or f"Error de emparejamiento (código {res.returncode})"
            )
        except subprocess.TimeoutExpired:
            return OperationResult.fail(
                ErrorCode.PAIRING_TIMEOUT,
                "Tiempo de espera agotado al intentar emparejar."
            )
        except Exception as e:
            return OperationResult.fail(ErrorCode.UNKNOWN_ERROR, str(e))

    @staticmethod
    def lockdown_device_tcpip(adb_path: str, serial: str, timeout: int = 8) -> OperationResult[str]:
        """Cierra el puerto TCP/IP (5555) en el teléfono ejecutando 'adb usb' para devolverlo a modo USB seguro."""
        if not adb_path or not serial:
            return OperationResult.fail(ErrorCode.INVALID_INPUT, "Parámetros inválidos")
        try:
            res = subprocess.run([adb_path, "-s", serial, "usb"], capture_output=True, text=True, timeout=timeout)
            out = (res.stdout or "") + (res.stderr or "")
            if res.returncode == 0 or "restarting in USB mode" in out.lower():
                return OperationResult.ok(
                    data=serial,
                    message="Puerto TCP/IP cerrado. Dispositivo restaurado a modo USB seguro."
                )
            return OperationResult.fail(
                ErrorCode.LOCKDOWN_FAILED,
                out.strip() or "No se pudo cambiar a modo USB"
            )
        except Exception as e:
            return OperationResult.fail(ErrorCode.UNKNOWN_ERROR, str(e))

    @staticmethod
    def validate_extra_arguments(extra_args: str) -> OperationResult[List[str]]:
        """Valida y sanitiza argumentos adicionales para scrcpy."""
        if not extra_args or not extra_args.strip():
            return OperationResult.ok(data=[])

        # Comprobar si hay operadores peligrosos de shell
        dangerous_patterns = [r';', r'&&', r'\|\|', r'\|', r'`', r'\$\(', r'>', r'<']
        for pat in dangerous_patterns:
            if re.search(pat, extra_args):
                return OperationResult.fail(
                    ErrorCode.UNSAFE_ARGUMENT_DETECTED,
                    f"Comando contiene caracteres de shell no permitidos ('{pat}')"
                )

        try:
            tokens = shlex.split(extra_args)
            return OperationResult.ok(data=tokens, message="Argumentos válidos")
        except ValueError as ve:
            return OperationResult.fail(
                ErrorCode.INVALID_INPUT,
                f"Error al analizar argumentos ({ve}). Revisa las comillas."
            )

    @staticmethod
    def lockdown_all_devices(adb_path: str, active_serials: List[str]) -> int:
        """Ejecuta 'adb usb' en todos los dispositivos conectados para revocar puertos inalámbricos abiertos."""
        if not adb_path:
            return 0
        success_count = 0
        for serial in active_serials:
            res = SecurityManager.lockdown_device_tcpip(adb_path, serial)
            if res.success:
                success_count += 1
        return success_count

    @staticmethod
    def kill_adb_server(adb_path: str) -> bool:
        """Termina el servidor ADB local para limpiar conexiones residuales."""
        if not adb_path:
            return False
        try:
            subprocess.run([adb_path, "kill-server"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False
