"""Offline contracts for original Astra inventory and dormant live extractor."""
from __future__ import annotations

from contextlib import redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "evidence/LOCAL-VERIFY-004/RUNNER"
sys.path.insert(0, str(RUNNER))
import phase_a  # noqa: E402
import phase_b  # noqa: E402


class PhaseAContracts(unittest.TestCase):
    def test_source_hashes_and_eight_candidates(self):
        result = phase_a.verify_inputs()
        self.assertEqual((result["source_sha256_verified"], result["candidates_validated"], result["selected_validated"]), (2, 8, 5))
        self.assertEqual(result["subtitle_download"], "NOT_TESTED")

    def test_source_files_exactly_preserved(self):
        for name, digest in phase_a.SOURCE_HASHES.items():
            self.assertEqual(hashlib.sha256((phase_a.ROOT / name).read_bytes()).hexdigest(), digest)

    def test_selected_five_and_ui_disagreement(self):
        obj = json.loads((phase_a.INPUT / "LOCAL-VERIFY-004_youtube_inventory.json").read_text())
        self.assertEqual(obj["selection"]["video_ids_in_rank_order"], phase_a.SELECTED)
        self.assertEqual({c["video_id"] for c in obj["candidates"]}, phase_a.ALL_IDS)
        for c in obj["candidates"]:
            self.assertEqual(c["captions"]["actual_extractor_availability"], "NOT_TESTED")
            if c["video_id"] == phase_a.NEGATIVE:
                self.assertEqual(c["captions"]["visible_language_options"], [])
                self.assertEqual(c["suitability"]["case_type"], "negative_provisional")
            else:
                self.assertEqual(c["captions"]["visible_language_options"], ["English (auto-generated)"])
                self.assertTrue(any("unavailable" in s.lower() for s in c["evidence"]))

    def test_tampered_input_rejected_without_mutating_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "LOCAL-VERIFY-004"
            shutil.copytree(phase_a.ROOT, archive)
            data = archive / "INPUT/LOCAL-VERIFY-004_youtube_inventory.json"
            data.write_bytes(data.read_bytes().replace(b'"execution_status": "NOT_TESTED"', b'"execution_status": "PASSED"'))
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                phase_a.verify_inputs(archive)
        phase_a.verify_inputs()

    def test_manifest_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "LOCAL-VERIFY-004"
            shutil.copytree(phase_a.ROOT, archive)
            (archive / "SHA256SUMS.txt").write_text("oops\n")
            with self.assertRaisesRegex(ValueError, "ledger changed"):
                phase_a.verify_inputs(archive)

    def test_semantic_negative_control_even_with_updated_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "LOCAL-VERIFY-004"
            shutil.copytree(phase_a.ROOT, archive)
            name = "INPUT/LOCAL-VERIFY-004_youtube_inventory.json"
            p = archive / name
            data = json.loads(p.read_text())
            data["selection"]["video_ids_in_rank_order"][0] = phase_a.NEGATIVE
            p.write_text(json.dumps(data) + "\n")
            hashes = dict(phase_a.SOURCE_HASHES)
            hashes[name] = hashlib.sha256(p.read_bytes()).hexdigest()
            (archive / "SHA256SUMS.txt").write_text("".join(f"{h}  {n}\n" for n, h in sorted(hashes.items())))
            with mock.patch.dict(phase_a.SOURCE_HASHES, hashes, clear=True):
                with self.assertRaisesRegex(ValueError, "selected-five order"):
                    phase_a.verify_inputs(archive)


class PhaseBContracts(unittest.TestCase):
    def test_network_denied_by_default_even_when_env_set(self):
        with mock.patch.dict("os.environ", {"LOCAL_VERIFY_004_ALLOW_NETWORK": "YES"}, clear=True), mock.patch.object(phase_b.subprocess, "run", side_effect=AssertionError("network")):
            with redirect_stderr(io.StringIO()):
                self.assertEqual(phase_b.main(["--video-id", phase_a.SELECTED[0]]), 2)

    def test_explicit_gate_requires_environment_acknowledgement(self):
        args = type("Args", (), {"authorize_live": True, "authorize_subtitles": True, "video_id": phase_a.SELECTED[0]})()
        with self.assertRaisesRegex(ValueError, "NOT_AUTHORIZED"):
            phase_b.authorize(args, {})
        phase_b.authorize(args, {"LOCAL_VERIFY_004_ALLOW_NETWORK": "YES"})

    def test_ci_rejected_even_with_both_permissions(self):
        args = type("Args", (), {"authorize_live": True, "authorize_subtitles": True, "video_id": phase_a.SELECTED[0]})()
        with self.assertRaisesRegex(ValueError, "CI prohibited"):
            phase_b.authorize(args, {"LOCAL_VERIFY_004_ALLOW_NETWORK": "YES", "GITHUB_ACTIONS": "true"})

    def test_unlisted_video_denied(self):
        args = type("Args", (), {"authorize_live": True, "authorize_subtitles": False, "video_id": "AAAAAAAAAAA"})()
        with self.assertRaisesRegex(ValueError, "allowlist"):
            phase_b.authorize(args, {"LOCAL_VERIFY_004_ALLOW_NETWORK": "YES"})

    def test_english_selector_manual_precedence(self):
        metadata = {"subtitles": {"en": [{"ext": "vtt", "url": "https://example.invalid/manual"}]}, "automatic_captions": {"en": [{"ext": "vtt", "url": "https://example.invalid/auto"}]}}
        self.assertEqual(phase_b.choose_english(metadata), ("manual", "en"))
        metadata = {"subtitles": {"en-GB": [{"ext": "vtt", "url": "u"}]}, "automatic_captions": {"en": [{"ext": "vtt", "url": "u"}]}}
        self.assertEqual(phase_b.choose_english(metadata), ("automatic", "en"))

    def test_english_selector_no_first_key_or_invalid_format(self):
        self.assertIsNone(phase_b.choose_english({"subtitles": {"en-US": [{"ext": "vtt", "url": "u"}], "en-GB": [{"ext": "vtt", "url": "u"}]}}))
        self.assertIsNone(phase_b.choose_english({"automatic_captions": {"fr": [{"ext": "vtt", "url": "u"}]}}))
        self.assertIsNone(phase_b.choose_english({"automatic_captions": {"en": [{"ext": "srt", "url": "u"}]}}))
        self.assertEqual(phase_b.choose_english({"automatic_captions": {"en": [{"ext": "vtt", "url": "u"}]}}), ("automatic", "en"))

    def test_vtt_structural_validation(self):
        self.assertEqual(phase_b.check_vtt(b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nhello\n"), 1)
        for data in (b"", b"WEBVTT\n", b"WEBVTT\n\n00:00:02.000 --> 00:00:01.000\nno\n", b"WEBVTT\n\nx --> y\n", b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                phase_b.check_vtt(data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
