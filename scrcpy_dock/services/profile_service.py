"""ProfileService · Persistencia y migración de perfiles.

Contrato v1 congelado — ver ADR-005.
NO cambiar firmas sin reabrir el ADR correspondiente.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.errors import ErrorCode
from scrcpy_dock.domain.models import Codec


log = logging.getLogger(__name__)


_CURRENT_SCHEMA_VERSION = 2
_DEFAULT_CONFIG_FILENAME = "config.json"

# Límites de validación (coerción silenciosa)
_BITRATE_MIN = 100_000
_BITRATE_MAX = 50_000_000
_BITRATE_DEFAULT = 8_000_000
_RESOLUTION_MAX_LEN = 20
_RESOLUTION_DEFAULT = "1080"
_MAX_FPS_MIN = 1.0
_MAX_FPS_MAX = 240.0

_VALID_VIDEO_SOURCES = ("display", "camera")
_VALID_AUDIO_SOURCES = ("playback", "mic")
_VALID_CODECS = tuple(c.value for c in Codec)


@dataclass(frozen=True)
class Profile:
    """Perfil de sesión · serializable a JSON."""
    name: str
    codec: Codec = Codec.H264
    bit_rate: int = _BITRATE_DEFAULT
    resolution: str = _RESOLUTION_DEFAULT
    video_source: str = "display"
    max_fps: Optional[float] = None
    audio_source: str = "playback"
    turn_screen_off: bool = True
    stay_awake: bool = True
    schema_version: int = _CURRENT_SCHEMA_VERSION


class ProfileService:
    """Serialización, sanitización y migración de perfiles.

    Responsabilidades:
      - Leer/escribir config.json con escritura atómica.
      - Sanitizar dicts (strip unknown, coerce invalid values).
      - Migrar v1 → v2 transparentemente al cargar.

    NO responsabilidades:
      - Validar contra hardware (eso es SessionManager).
      - Gestionar rutas de perfil en la UI.
    """

    def __init__(
        self,
        config_dir: Path,
        filename: str = _DEFAULT_CONFIG_FILENAME,
    ) -> None:
        self._config_dir = Path(config_dir)
        self._filename = filename
        self._config_path = self._config_dir / filename

    # ────────────────────────────────────────────────────────────────────
    # Helpers internos
    # ────────────────────────────────────────────────────────────────────

    def _read_file(self) -> OperationResult[dict[str, Any]]:
        """Lee config.json. Ausente → dict vacío (no error)."""
        if not self._config_path.exists():
            return OperationResult.ok({"profiles": {}})
        try:
            raw = self._config_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            log.error("config.json corrupto: %s", e)
            return OperationResult.fail(
                ErrorCode.CONFIG_CORRUPT, f"JSON inválido: {e}",
            )
        if not isinstance(data, dict):
            return OperationResult.fail(
                ErrorCode.CONFIG_CORRUPT, "raíz no es dict",
            )
        data.setdefault("profiles", {})
        return OperationResult.ok(data)

    def _write_file_atomic(
        self, data: dict[str, Any],
    ) -> OperationResult[None]:
        """Escritura atómica: escribe a .tmp y os.replace."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self._config_path.with_suffix(
            self._config_path.suffix + ".tmp",
        )
        try:
            tmp_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            os.replace(tmp_path, self._config_path)
        except (OSError, TypeError) as e:
            log.error("no se pudo escribir config.json: %s", e)
            # Limpieza best-effort
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            return OperationResult.fail(
                ErrorCode.CONFIG_CORRUPT, f"write falló: {e}",
            )
        return OperationResult.ok(None, "config.json guardado")

    # ────────────────────────────────────────────────────────────────────
    # API pública · contratos congelados
    # ────────────────────────────────────────────────────────────────────

    # ─── TODO-P1 · sanitize_profile_dict ─────────────────────────────
    @staticmethod
    def sanitize_profile_dict(raw: dict[str, Any]) -> dict[str, Any]:
        """Devuelve un dict con solo campos conocidos y valores válidos.

        Contrato:
          - Campos desconocidos → ignorados silenciosamente.
          - codec: str en {h264,h265,av1}. Inválido → "h264".
          - bit_rate: int en [100k, 50M]. Inválido → 8_000_000.
          - resolution: str no vacío, ≤20 chars. Inválido → "1080".
          - video_source: "display"|"camera". Inválido → "display".
          - max_fps: float|None, rango [1, 240]. Inválido → None.
          - audio_source: "playback"|"mic". Inválido → "playback".
          - turn_screen_off / stay_awake: bool. Inválido → True.
          - schema_version: int ≥ 1. Inválido → 1.
          - NO incluye 'name' (eso lo maneja el dict padre).

        Cada campo se delega en un validador puro (un campo, una regla). Así el
        orden de las claves es explícito y auditable, y añadir un campo nuevo no
        obliga a releer la sanitización entera.
        """
        if not isinstance(raw, dict):
            raw = {}

        return {
            "codec": ProfileService._sanitize_codec(raw.get("codec")),
            "bit_rate": ProfileService._sanitize_bitrate(raw.get("bit_rate")),
            "resolution": ProfileService._sanitize_resolution(raw.get("resolution")),
            "video_source": ProfileService._sanitize_video_source(
                raw.get("video_source"), raw.get("extra_args"),
            ),
            "max_fps": ProfileService._sanitize_fps(raw.get("max_fps")),
            "audio_source": ProfileService._sanitize_audio_source(raw.get("audio_source")),
            "turn_screen_off": ProfileService._sanitize_flag(raw.get("turn_screen_off")),
            "stay_awake": ProfileService._sanitize_flag(raw.get("stay_awake")),
            "schema_version": ProfileService._sanitize_schema_version(raw.get("schema_version")),
        }

    # ─── Validadores atómicos (uno por campo · CC ≤ 3) ────────────────

    @staticmethod
    def _sanitize_codec(value: Any) -> str:
        if isinstance(value, Codec):
            return value.value
        if isinstance(value, str) and value.lower() in _VALID_CODECS:
            return value.lower()
        return "h264"

    @staticmethod
    def _sanitize_bitrate(value: Any) -> int:
        """`bool` es subclase de `int`: se descarta antes de convertir."""
        if isinstance(value, bool):
            return _BITRATE_DEFAULT
        try:
            bit_rate = int(value)
        except (TypeError, ValueError):
            return _BITRATE_DEFAULT
        return bit_rate if _BITRATE_MIN <= bit_rate <= _BITRATE_MAX else _BITRATE_DEFAULT

    @staticmethod
    def _sanitize_resolution(value: Any) -> str:
        if isinstance(value, str):
            clean = value.strip()
            if clean and len(clean) <= _RESOLUTION_MAX_LEN:
                return clean
            return _RESOLUTION_DEFAULT
        # `bool` también es `int`; sin esta guarda `True` se colaría como "True".
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            text = str(value)
            if len(text) <= _RESOLUTION_MAX_LEN:
                return text
        return _RESOLUTION_DEFAULT

    @staticmethod
    def _sanitize_video_source(value: Any, extra_args: Any) -> str:
        if isinstance(value, str) and value.lower() in _VALID_VIDEO_SOURCES:
            return value.lower()
        if "--video-source=camera" in str(extra_args or ""):
            return "camera"
        return "display"

    @staticmethod
    def _sanitize_fps(value: Any) -> Optional[float]:
        if value is None or isinstance(value, bool):
            return None
        try:
            fps = float(value)
        except (TypeError, ValueError):
            return None
        return fps if _MAX_FPS_MIN <= fps <= _MAX_FPS_MAX else None

    @staticmethod
    def _sanitize_audio_source(value: Any) -> str:
        if isinstance(value, str) and value.lower() in _VALID_AUDIO_SOURCES:
            return value.lower()
        return "playback"

    @staticmethod
    def _sanitize_flag(value: Any) -> bool:
        """`turn_screen_off` / `stay_awake`: ausente o None → True (default)."""
        return True if value is None else bool(value)

    @staticmethod
    def _sanitize_schema_version(value: Any) -> int:
        if isinstance(value, bool):
            return 1
        try:
            version = int(value)
        except (TypeError, ValueError):
            return 1
        return version if version >= 1 else 1

    # ─── TODO-P2 · migrate_v1_to_v2 ─────────────────────────────────
    @staticmethod
    def migrate_v1_to_v2(raw: dict[str, Any]) -> dict[str, Any]:
        """Migra un perfil v1 al schema actual v2.

        Contrato:
          - Preserva TODOS los campos v1 presentes con valores válidos.
          - Añade schema_version=2.
          - Añade campos nuevos con defaults: max_fps=None,
            audio_source="playback", turn_screen_off=True,
            stay_awake=True.
          - NO elimina claves desconocidas (eso lo hace sanitize).
          - Idempotente: aplicar dos veces da el mismo resultado.
        """
        out = dict(raw)
        out.setdefault("max_fps", None)
        out.setdefault("audio_source", "playback")
        out.setdefault("turn_screen_off", True)
        out.setdefault("stay_awake", True)
        out["schema_version"] = _CURRENT_SCHEMA_VERSION
        return out

    # ─── TODO-P3 · load / save ──────────────────────────────────────
    def load_profile(self, name: str) -> OperationResult[Profile]:
        """Carga un perfil, migrando v1 → v2 si es necesario.

        Contrato:
          - Perfil ausente → PROFILE_NOT_FOUND.
          - config.json corrupto → CONFIG_CORRUPT.
          - Perfil v1 → migrado silenciosamente y devuelto como v2.
          - 'name' del Profile = name solicitado (no el del JSON).
        """
        read_res = self._read_file()
        if not read_res.success:
            return OperationResult.fail(read_res.error or ErrorCode.CONFIG_CORRUPT, read_res.message)

        profiles = read_res.data.get("profiles", {})
        if name not in profiles:
            return OperationResult.fail(ErrorCode.PROFILE_NOT_FOUND, f"Perfil '{name}' no encontrado.")

        raw = profiles[name]
        if not isinstance(raw, dict):
            return OperationResult.fail(ErrorCode.CONFIG_CORRUPT, f"Perfil '{name}' malformado.")

        if raw.get("schema_version", 1) < _CURRENT_SCHEMA_VERSION:
            raw = self.migrate_v1_to_v2(raw)

        clean = self.sanitize_profile_dict(raw)
        clean["codec"] = Codec(clean["codec"])

        return OperationResult.ok(Profile(name=name, **clean))

    def save_profile(self, profile: Profile) -> OperationResult[None]:
        """Guarda o sobreescribe un perfil. Escritura atómica.

        Contrato:
          - Preserva otros perfiles del archivo.
          - Crea config_dir y config.json si no existen.
          - Sobreescribe sin prompt si el perfil ya existe.
          - Falla con CONFIG_CORRUPT si el archivo está corrupto (no lo
            sobreescribe silenciosamente).
        """
        read_res = self._read_file()
        if not read_res.success:
            return OperationResult.fail(read_res.error or ErrorCode.CONFIG_CORRUPT, read_res.message)

        data = read_res.data
        prof_dict = asdict(profile)
        prof_dict.pop("name", None)
        if isinstance(prof_dict.get("codec"), Codec):
            prof_dict["codec"] = prof_dict["codec"].value

        clean = self.sanitize_profile_dict(prof_dict)
        data.setdefault("profiles", {})
        data["profiles"][profile.name] = clean

        return self._write_file_atomic(data)

    # ─── TODO-P4 · list / delete ────────────────────────────────────
    def list_profiles(self) -> OperationResult[list[str]]:
        """Lista nombres de perfiles ordenados alfabéticamente.

        Contrato:
          - config.json ausente → [] con success=True.
          - config.json corrupto → CONFIG_CORRUPT.
          - Orden: sorted() ascendente.
        """
        read_res = self._read_file()
        if not read_res.success:
            return OperationResult.fail(read_res.error or ErrorCode.CONFIG_CORRUPT, read_res.message)

        profiles = read_res.data.get("profiles", {})
        return OperationResult.ok(sorted(profiles.keys()))

    def delete_profile(self, name: str) -> OperationResult[None]:
        """Elimina un perfil. Idempotente.

        Contrato:
          - Nombre desconocido → success=True (no-op).
          - Tras delete, el nombre no aparece en list_profiles.
        """
        read_res = self._read_file()
        if not read_res.success:
            return OperationResult.fail(read_res.error or ErrorCode.CONFIG_CORRUPT, read_res.message)

        data = read_res.data
        profiles = data.get("profiles", {})
        if name in profiles:
            del profiles[name]
            return self._write_file_atomic(data)

        return OperationResult.ok(None, "perfil no existía (no-op)")
