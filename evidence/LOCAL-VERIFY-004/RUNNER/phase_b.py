#!/usr/bin/env python3
"""Manual-only, single-video yt-dlp inspection; NEVER invoked by CI.

Live traffic requires both an explicit CLI flag and a separate local environment
acknowledgement. All outputs are private scratch evidence outside the repository.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from phase_a import NEGATIVE, ROOT, SELECTED, verify_inputs

EXPECTED_YTDLP = "2026.03.17"


def authorize(args: argparse.Namespace, environ: dict[str, str] | None = None) -> None:
    env = os.environ if environ is None else environ
    if (not args.authorize_live or env.get("LOCAL_VERIFY_004_ALLOW_NETWORK") != "YES"
            or env.get("GITHUB_ACTIONS", "").lower() == "true"
            or env.get("CI", "").lower() == "true"):
        raise ValueError("live execution NOT_AUTHORIZED (CLI + local env acknowledgement required; CI prohibited)")
    if args.video_id not in SELECTED:
        raise ValueError("video is not on the frozen selected-five allowlist")
    if args.authorize_subtitles and not args.authorize_live:
        raise ValueError("subtitle download requires live authorization")


def choose_english(metadata: dict) -> tuple[str, str] | None:
    """Exact-before-base, manual-within-tier, unique-key English selection."""
    sources = (("subtitles", "manual"), ("automatic_captions", "automatic"))
    for tier in ("exact", "regional"):
        for field, mode in sources:
            tracks = metadata.get(field) or {}
            if not isinstance(tracks, dict):
                return None
            matched = []
            for key, formats in tracks.items():
                if not isinstance(key, str) or not isinstance(formats, list):
                    continue
                norm = key.lower().replace("_", "-")
                is_match = norm == "en" if tier == "exact" else norm.startswith("en-")
                if is_match and any(isinstance(fmt, dict) and fmt.get("ext") == "vtt"
                                    and isinstance(fmt.get("url"), str) and fmt["url"]
                                    for fmt in formats):
                    matched.append(key)
            if len(matched) > 1:
                return None
            if len(matched) == 1:
                return mode, matched[0]
    return None


def check_vtt(data: bytes) -> int:
    """Minimal structural check, not a semantic transcript accuracy claim."""
    if len(data) > 5_000_000 or not data.startswith((b"WEBVTT\n", b"WEBVTT\r\n")):
        raise ValueError("subtitle is missing WEBVTT header or exceeds 5 MB")
    content = data.decode("utf-8-sig", errors="strict")
    cues = 0
    for line in content.splitlines():
        if " --> " not in line:
            continue
        a, b = line.split(" --> ", 1)
        a, b = a.strip(), b.split()[0] if b.split() else ""
        def millis(value: str) -> int:
            if not re.fullmatch(r"(?:\d{2}:)?\d{2}:\d{2}\.\d{3}", value):
                raise ValueError("invalid WebVTT timestamp")
            parts = value.split(":")
            return (int(parts[-3]) * 3600000 if len(parts) == 3 else 0) + int(parts[-2]) * 60000 + int(parts[-1].split(".")[0]) * 1000 + int(parts[-1].split(".")[1])
        if millis(b) <= millis(a):
            raise ValueError("nonpositive WebVTT cue interval")
        cues += 1
    # A timeline without any spoken/textual caption payload is not validated content.
    nonempty_cue_text = any(line.strip() and " --> " not in line and not line.startswith("WEBVTT")
                            and not line.strip().isdigit() for line in content.splitlines()[1:])
    if not cues or not nonempty_cue_text:
        raise ValueError("subtitle contains no usable cue text")
    return cues


def secure_write(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)


def command_prefix(exe: str) -> list[str]:
    return [exe, "--ignore-config", "--no-playlist", "--no-cache-dir", "--retries", "0",
            "--extractor-retries", "0", "--fragment-retries", "0", "--socket-timeout", "10"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--authorize-live", action="store_true")
    parser.add_argument("--authorize-subtitles", action="store_true")
    parser.add_argument("--yt-dlp", default="yt-dlp")
    args = parser.parse_args(argv)
    try:
        verify_inputs()
        authorize(args)
        exe = shutil.which(args.yt_dlp)
        if exe is None:
            raise ValueError("yt-dlp executable not available")
        ver = subprocess.run([exe, "--version"], text=True, capture_output=True, timeout=10, check=False)
        if ver.returncode or ver.stdout.strip() != EXPECTED_YTDLP:
            raise ValueError("yt-dlp pinned version mismatch; expected " + EXPECTED_YTDLP)
        # No automatic retries, one allowlisted video and at most two yt-dlp invocations.
        output = Path(tempfile.mkdtemp(prefix="local-verify-004-private-")).resolve()
        os.chmod(output, 0o700)
        url = "https://www.youtube.com/watch?v=" + args.video_id
        prefix = command_prefix(exe)
        receipt = {"experiment": "LOCAL-VERIFY-004", "video_id": args.video_id,
                   "time_utc": datetime.now(timezone.utc).isoformat(),
                   "yt_dlp_version": EXPECTED_YTDLP,
                   "yt_dlp_executable_sha256": hashlib.sha256(Path(exe).read_bytes()).hexdigest(),
                   "source": "owner-identified public channel; signed-out; no cookies",
                   "metadata": "NOT_TESTED", "subtitle": "NOT_TESTED", "scope": "one public video"}
        cmd = prefix + ["--skip-download", "--dump-single-json", url]
        res = subprocess.run(cmd, capture_output=True, timeout=60, check=False)
        secure_write(output / "metadata.stdout.private", res.stdout)
        secure_write(output / "metadata.stderr.private", res.stderr)
        receipt["metadata_exit_code"] = res.returncode
        receipt["metadata_sha256"] = hashlib.sha256(res.stdout).hexdigest()
        receipt["metadata_stderr_sha256"] = hashlib.sha256(res.stderr).hexdigest()
        if res.returncode:
            receipt["metadata"] = "FAILED"
        else:
            try:
                metadata = json.loads(res.stdout)
                if not isinstance(metadata, dict) or metadata.get("id") != args.video_id:
                    raise ValueError("extractor returned different video identity")
                receipt["metadata"] = "RETRIEVED"
                match = choose_english(metadata)
                receipt["eligible_english_track"] = "SELECTED" if match else "ABSTAIN"
                if args.video_id == NEGATIVE:
                    receipt["ui_negative_comparison"] = "CONTRADICTED" if match else "NO_ELIGIBLE_ENGLISH_TRACK"
                elif not match:
                    receipt["ui_positive_comparison"] = "UNCONFIRMED"
                if match and args.video_id != NEGATIVE and args.authorize_subtitles:
                    mode, key = match
                    receipt["selected_kind"] = mode
                    receipt["selected_key"] = key
                    captions = output / "captions"
                    captions.mkdir(mode=0o700)
                    cmd = prefix + ["--skip-download", "--write-subs" if mode == "manual" else "--write-auto-subs",
                                    "--sub-langs", "^" + re.escape(key) + "$", "--sub-format", "vtt",
                                    "--output", str(captions / "%(id)s.%(ext)s"), url]
                    done = subprocess.run(cmd, capture_output=True, timeout=60, check=False)
                    secure_write(output / "download.stdout.private", done.stdout)
                    secure_write(output / "download.stderr.private", done.stderr)
                    receipt["subtitle_exit_code"] = done.returncode
                    vtts = sorted(captions.glob("*.vtt"))
                    if done.returncode or len(vtts) != 1 or len(list(captions.iterdir())) != 1:
                        receipt["subtitle"] = "FAILED_OR_MISSING"
                    else:
                        data = vtts[0].read_bytes()
                        try:
                            cues = check_vtt(data)
                        except (UnicodeError, ValueError):
                            receipt["subtitle"] = "INVALID_CONTENT"
                        else:
                            receipt["subtitle"] = "DOWNLOADED_AND_STRUCTURALLY_VERIFIED"
                            receipt["subtitle_sha256"] = hashlib.sha256(data).hexdigest()
                            receipt["subtitle_bytes"] = len(data)
                            receipt["subtitle_cue_count"] = cues
            except (json.JSONDecodeError, ValueError) as exc:
                receipt["metadata"] = "INVALID_OR_UNEXPECTED"
                receipt["validation_error"] = str(exc)
        secure_write(output / "receipt.private.json", (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
        print("private_receipt_directory=" + str(output))
        print("metadata_status=" + receipt["metadata"])
        print("subtitle_status=" + receipt["subtitle"])
        return 0 if receipt["metadata"] == "RETRIEVED" and (not args.authorize_subtitles or receipt["subtitle"] == "DOWNLOADED_AND_STRUCTURALLY_VERIFIED" or args.video_id == NEGATIVE) else 1
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print("LOCAL-VERIFY-004: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
