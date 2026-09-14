"""Contratos congelados de ProfileService. NO modificar sin reabrir ADR-005."""
from __future__ import annotations
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scrcpy_dock.services.profile_service import (
    Profile, ProfileService, _CURRENT_SCHEMA_VERSION,
)
from scrcpy_dock.contracts import ErrorCode
from scrcpy_dock.domain.models import Codec


def _make_service(tmp: Path) -> ProfileService:
    return ProfileService(config_dir=tmp)


# ─── sanitize_profile_dict · TODO-P1 ───────────────────────────────

class SanitizeProfileDictContract(unittest.TestCase):

    def test_keeps_all_valid_fields(self):
        raw = {
            "codec": "h265",
            "bit_rate": 4_000_000,
            "resolution": "720",
            "video_source": "camera",
            "max_fps": 30.0,
            "audio_source": "mic",
            "turn_screen_off": False,
            "stay_awake": False,
            "schema_version": 2,
        }
        out = ProfileService.sanitize_profile_dict(raw)
        self.assertEqual(out["codec"], "h265")
        self.assertEqual(out["bit_rate"], 4_000_000)
        self.assertEqual(out["resolution"], "720")
        self.assertEqual(out["video_source"], "camera")
        self.assertEqual(out["max_fps"], 30.0)
        self.assertEqual(out["audio_source"], "mic")
        self.assertFalse(out["turn_screen_off"])
        self.assertFalse(out["stay_awake"])

    def test_strips_unknown_keys(self):
        raw = {"codec": "h264", "evil": "injection", "port": 9999}
        out = ProfileService.sanitize_profile_dict(raw)
        self.assertNotIn("evil", out)
        self.assertNotIn("port", out)
        self.assertNotIn("name", out)

    def test_invalid_codec_falls_back_to_h264(self):
        out = ProfileService.sanitize_profile_dict({"codec": "vp9"})
        self.assertEqual(out["codec"], "h264")

    def test_bit_rate_below_min_clamped(self):
        out = ProfileService.sanitize_profile_dict({"bit_rate": 100})
        self.assertEqual(out["bit_rate"], 8_000_000)

    def test_bit_rate_above_max_clamped(self):
        out = ProfileService.sanitize_profile_dict({"bit_rate": 999_999_999})
        self.assertEqual(out["bit_rate"], 8_000_000)

    def test_bit_rate_non_int_falls_back(self):
        out = ProfileService.sanitize_profile_dict({"bit_rate": "not-a-number"})
        self.assertEqual(out["bit_rate"], 8_000_000)

    def test_resolution_too_long_rejected(self):
        out = ProfileService.sanitize_profile_dict({"resolution": "x" * 50})
        self.assertEqual(out["resolution"], "1080")

    def test_invalid_video_source_falls_back(self):
        out = ProfileService.sanitize_profile_dict({"video_source": "webcam"})
        self.assertEqual(out["video_source"], "display")

    def test_max_fps_out_of_range_rejected(self):
        self.assertIsNone(
            ProfileService.sanitize_profile_dict({"max_fps": 500})["max_fps"],
        )
        self.assertIsNone(
            ProfileService.sanitize_profile_dict({"max_fps": 0})["max_fps"],
        )

    def test_max_fps_none_preserved(self):
        out = ProfileService.sanitize_profile_dict({"max_fps": None})
        self.assertIsNone(out["max_fps"])

    def test_invalid_audio_source_falls_back(self):
        out = ProfileService.sanitize_profile_dict({"audio_source": "system"})
        self.assertEqual(out["audio_source"], "playback")

    def test_bool_fields_coerced(self):
        out = ProfileService.sanitize_profile_dict({
            "turn_screen_off": "yes", "stay_awake": 1,
        })
        self.assertIs(out["turn_screen_off"], True)
        self.assertIs(out["stay_awake"], True)

    def test_empty_input_returns_defaults(self):
        out = ProfileService.sanitize_profile_dict({})
        self.assertEqual(out["codec"], "h264")
        self.assertEqual(out["bit_rate"], 8_000_000)
        self.assertEqual(out["resolution"], "1080")


# ─── migrate_v1_to_v2 · TODO-P2 ────────────────────────────────────

class MigrateV1ToV2Contract(unittest.TestCase):

    def test_adds_schema_version(self):
        v1 = {"codec": "h264", "bit_rate": 4_000_000}
        v2 = ProfileService.migrate_v1_to_v2(v1)
        self.assertEqual(v2["schema_version"], 2)

    def test_preserves_v1_fields(self):
        v1 = {
            "codec": "h264", "bit_rate": 4_000_000,
            "resolution": "720", "video_source": "display",
        }
        v2 = ProfileService.migrate_v1_to_v2(v1)
        self.assertEqual(v2["codec"], "h264")
        self.assertEqual(v2["bit_rate"], 4_000_000)
        self.assertEqual(v2["resolution"], "720")

    def test_adds_defaults_for_new_fields(self):
        v2 = ProfileService.migrate_v1_to_v2({"codec": "h264"})
        self.assertIsNone(v2["max_fps"])
        self.assertEqual(v2["audio_source"], "playback")
        self.assertTrue(v2["turn_screen_off"])
        self.assertTrue(v2["stay_awake"])

    def test_does_not_strip_unknown_keys(self):
        v1 = {"codec": "h264", "legacy_field": "keep me"}
        v2 = ProfileService.migrate_v1_to_v2(v1)
        self.assertEqual(v2["legacy_field"], "keep me")

    def test_idempotent(self):
        v1 = {"codec": "h264", "bit_rate": 4_000_000}
        once = ProfileService.migrate_v1_to_v2(v1)
        twice = ProfileService.migrate_v1_to_v2(once)
        self.assertEqual(once, twice)


# ─── load_profile · TODO-P3 ────────────────────────────────────────

class LoadProfileContract(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.svc = _make_service(self.tmp)

    def test_unknown_profile_returns_not_found(self):
        r = self.svc.load_profile("ghost")
        self.assertFalse(r.success)
        self.assertEqual(r.error, ErrorCode.PROFILE_NOT_FOUND)

    def test_missing_config_file_returns_not_found(self):
        self.assertFalse((self.tmp / "config.json").exists())
        r = self.svc.load_profile("any")
        self.assertFalse(r.success)
        self.assertEqual(r.error, ErrorCode.PROFILE_NOT_FOUND)

    def test_loads_v2_profile_cleanly(self):
        self.svc.save_profile(Profile(
            name="cinema", codec=Codec.H265, bit_rate=20_000_000,
            resolution="1440",
        ))
        r = self.svc.load_profile("cinema")
        self.assertTrue(r.success)
        self.assertEqual(r.data.name, "cinema")
        self.assertEqual(r.data.codec, Codec.H265)
        self.assertEqual(r.data.bit_rate, 20_000_000)

    def test_loads_v1_profile_migrating_to_v2(self):
        v1_file = {
            "profiles": {
                "legacy": {
                    "codec": "h264",
                    "bit_rate": 4_000_000,
                    "resolution": "720",
                    "video_source": "display",
                },
            },
        }
        (self.tmp / "config.json").write_text(json.dumps(v1_file))
        r = self.svc.load_profile("legacy")
        self.assertTrue(r.success)
        self.assertEqual(r.data.schema_version, _CURRENT_SCHEMA_VERSION)
        self.assertIsNone(r.data.max_fps)
        self.assertEqual(r.data.audio_source, "playback")

    def test_corrupt_json_returns_config_corrupt(self):
        (self.tmp / "config.json").write_text("not-json {[")
        r = self.svc.load_profile("any")
        self.assertFalse(r.success)
        self.assertEqual(r.error, ErrorCode.CONFIG_CORRUPT)

    def test_root_not_dict_returns_corrupt(self):
        (self.tmp / "config.json").write_text("[1,2,3]")
        r = self.svc.load_profile("any")
        self.assertFalse(r.success)
        self.assertEqual(r.error, ErrorCode.CONFIG_CORRUPT)


# ─── save_profile · TODO-P3 ────────────────────────────────────────

class SaveProfileContract(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.svc = _make_service(self.tmp)

    def test_creates_config_dir_and_file(self):
        svc = ProfileService(config_dir=self.tmp / "new_dir")
        r = svc.save_profile(Profile(name="first"))
        self.assertTrue(r.success)
        self.assertTrue((self.tmp / "new_dir" / "config.json").exists())

    def test_roundtrip_preserves_all_fields(self):
        original = Profile(
            name="studio", codec=Codec.H265, bit_rate=6_000_000,
            resolution="1440", video_source="camera",
            max_fps=30.0, audio_source="mic",
            turn_screen_off=False, stay_awake=False,
        )
        self.svc.save_profile(original)
        r = self.svc.load_profile("studio")
        self.assertTrue(r.success)
        self.assertEqual(r.data.codec, original.codec)
        self.assertEqual(r.data.bit_rate, original.bit_rate)
        self.assertEqual(r.data.resolution, original.resolution)
        self.assertEqual(r.data.video_source, original.video_source)
        self.assertEqual(r.data.max_fps, original.max_fps)
        self.assertEqual(r.data.audio_source, original.audio_source)
        self.assertFalse(r.data.turn_screen_off)
        self.assertFalse(r.data.stay_awake)

    def test_preserves_other_profiles(self):
        self.svc.save_profile(Profile(name="a", bit_rate=1_000_000))
        self.svc.save_profile(Profile(name="b", bit_rate=2_000_000))
        self.svc.save_profile(Profile(name="a", bit_rate=3_000_000))
        r = self.svc.load_profile("b")
        self.assertEqual(r.data.bit_rate, 2_000_000)

    def test_overwrites_same_name(self):
        self.svc.save_profile(Profile(name="x", resolution="720"))
        self.svc.save_profile(Profile(name="x", resolution="1080"))
        r = self.svc.load_profile("x")
        self.assertEqual(r.data.resolution, "1080")

    def test_atomic_write_leaves_original_on_failure(self):
        self.svc.save_profile(Profile(name="keep", resolution="720"))

        with patch(
            "scrcpy_dock.services.profile_service.os.replace",
            side_effect=OSError("disk full"),
        ):
            r = self.svc.save_profile(Profile(name="new", resolution="1080"))
            self.assertFalse(r.success)

        # El original debe seguir intacto
        original = self.svc.load_profile("keep")
        self.assertTrue(original.success)
        self.assertEqual(original.data.resolution, "720")
        # 'new' no debe existir
        ghost = self.svc.load_profile("new")
        self.assertFalse(ghost.success)

    def test_corrupt_file_is_not_silently_overwritten(self):
        (self.tmp / "config.json").write_text("not-json")
        r = self.svc.save_profile(Profile(name="x"))
        self.assertFalse(r.success)
        self.assertEqual(r.error, ErrorCode.CONFIG_CORRUPT)
        # El archivo corrupto sigue ahí
        self.assertEqual(
            (self.tmp / "config.json").read_text(), "not-json",
        )


# ─── list_profiles / delete_profile · TODO-P4 ──────────────────────

class ListProfilesContract(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.svc = _make_service(self.tmp)

    def test_empty_when_file_missing(self):
        r = self.svc.list_profiles()
        self.assertTrue(r.success)
        self.assertEqual(r.data, [])

    def test_sorted_alphabetically(self):
        for name in ["zeta", "alpha", "mu"]:
            self.svc.save_profile(Profile(name=name))
        r = self.svc.list_profiles()
        self.assertEqual(r.data, ["alpha", "mu", "zeta"])

    def test_corrupt_file_returns_error(self):
        (self.tmp / "config.json").write_text("not-json")
        r = self.svc.list_profiles()
        self.assertFalse(r.success)
        self.assertEqual(r.error, ErrorCode.CONFIG_CORRUPT)


class DeleteProfileContract(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.svc = _make_service(self.tmp)

    def test_delete_existing(self):
        self.svc.save_profile(Profile(name="doomed"))
        r = self.svc.delete_profile("doomed")
        self.assertTrue(r.success)
        self.assertNotIn("doomed", self.svc.list_profiles().data)

    def test_delete_unknown_is_noop(self):
        r = self.svc.delete_profile("ghost")
        self.assertTrue(r.success)

    def test_delete_preserves_others(self):
        self.svc.save_profile(Profile(name="a"))
        self.svc.save_profile(Profile(name="b"))
        self.svc.delete_profile("a")
        self.assertEqual(self.svc.list_profiles().data, ["b"])

    def test_delete_on_missing_file_is_noop(self):
        r = self.svc.delete_profile("any")
        self.assertTrue(r.success)


if __name__ == "__main__":
    unittest.main()
