"""HERESY-011: bounded, isolated Linux pathname TOCTOU reproduction.

No privilege, external files, timing-dependent race wins or network.
A parent atomically swaps the path after the unsafe child checks it and before
opening. The blocking FIFO case is terminated by a hard child timeout.
"""
from __future__ import annotations

import ctypes
import json
import os
import platform
import re
import select
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

GOOD_HEAD = b"a" * 64
WRONG_HEAD = b"0" * 64
CHILD_TIMEOUT = 1.2
RENAME_EXCHANGE = 2
AT_FDCWD = -100
CLAIMS = (
    "path_check_to_open_fifo_can_block",
    "path_check_to_open_symlink_can_follow",
    "same_descriptor_nonblocking_nofollow_rejects_nonregular",
    "real_linux_nofollow_constant_matches_supported_arch",
)


def _rename_exchange(left: Path, right: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        call = libc.renameat2
    except AttributeError as exc:
        raise RuntimeError("renameat2 unavailable on this Linux libc") from exc
    call.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                     ctypes.c_char_p, ctypes.c_uint)
    call.restype = ctypes.c_int
    if call(AT_FDCWD, os.fsencode(left), AT_FDCWD, os.fsencode(right),
            RENAME_EXCHANGE) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))


def _read_anchor_from_descriptor(path: Path) -> str:
    """Fixed pattern: no-follow/nonblocking, fstat, bounded same-FD read."""
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError("opened descriptor is not a regular file")
        raw = handle.read(66)
    if raw.endswith(b"\n"):
        raw = raw[:-1]
    if re.fullmatch(rb"[0-9a-f]{64}", raw) is None:
        raise ValueError("anchor must be exactly 64 lowercase hex digits")
    return raw.decode("ascii")


def _child(mode: str, path: Path) -> int:
    try:
        if mode == "unsafe":
            if not stat.S_ISREG(os.lstat(path).st_mode):
                raise ValueError("anchor pathname is not a regular file")
        print("READY", flush=True)
        if sys.stdin.readline() != "GO\n":
            return 2
        if mode == "unsafe":
            # Intentionally vulnerable model; can block forever on an exchanged FIFO.
            with path.open("rb") as handle:
                head = handle.read(66).rstrip(b"\n").decode("ascii")
        else:
            head = _read_anchor_from_descriptor(path)
        print(json.dumps({"status": "read", "head": head}, sort_keys=True))
    except (OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({"status": "rejected", "error_type": type(exc).__name__},
                         sort_keys=True))
    return 0


def _exchange_case(mode: str, substituted: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="heresy011-") as directory:
        root = Path(directory)
        anchor, alternative = root / "anchor", root / "swap"
        anchor.write_bytes(GOOD_HEAD + b"\n")
        if substituted == "fifo":
            os.mkfifo(alternative, 0o600)
        elif substituted == "symlink":
            wrong = root / "different-head"
            wrong.write_bytes(WRONG_HEAD + b"\n")
            alternative.symlink_to(wrong)
        else:
            raise ValueError("unsupported substitution")

        child = subprocess.Popen(
            [sys.executable, __file__, "--child", mode, str(anchor)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
        )
        try:
            # Deterministic interleaving, not an unreliable lucky stress loop.
            ready, _, _ = select.select([child.stdout], [], [], 4)
            if not ready or child.stdout.readline() != "READY\n":
                raise RuntimeError("child did not reach deterministic exchange point")
            _rename_exchange(anchor, alternative)
            try:
                stdout, stderr = child.communicate("GO\n", timeout=CHILD_TIMEOUT)
                timed_out = False
            except subprocess.TimeoutExpired:
                child.kill()
                stdout, stderr = child.communicate(timeout=2)
                timed_out = True
            if stderr:
                raise RuntimeError("child emitted unexpected stderr")
            if not timed_out and child.returncode != 0:
                raise RuntimeError("child did not complete normally")
            status = json.loads(stdout) if not timed_out else None
            return {
                "mode": mode,
                "substitute": substituted,
                "timed_out": timed_out,
                "status": status["status"] if status else "timeout_killed",
                "head_is_wrong": bool(status and status.get("head") == WRONG_HEAD.decode("ascii")),
                "head_is_good": bool(status and status.get("head") == GOOD_HEAD.decode("ascii")),
            }
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=2)


def run() -> int:
    machine = platform.machine().lower()
    supported = platform.system() == "Linux" and machine in ("x86_64", "aarch64", "arm64")
    if not supported:
        print(json.dumps({"claims": {key: "not_tested" for key in CLAIMS},
                          "observations": {"supported_target": False},
                          "scope": "Linux x86-64/AArch64 only"}, sort_keys=True))
        return 2
    expected = 0o400000 if machine == "x86_64" else 0o100000
    observations = [_exchange_case(mode, kind)
                    for kind in ("fifo", "symlink")
                    for mode in ("unsafe", "safe")]
    lookup = {(r["mode"], r["substitute"]): r for r in observations}
    checks = {
        CLAIMS[0]: lookup[("unsafe", "fifo")]["timed_out"],
        CLAIMS[1]: (not lookup[("unsafe", "symlink")]["timed_out"]
                    and lookup[("unsafe", "symlink")]["head_is_wrong"]),
        CLAIMS[2]: all(not lookup[("safe", kind)]["timed_out"]
                       and lookup[("safe", kind)]["status"] == "rejected"
                       for kind in ("fifo", "symlink")),
        CLAIMS[3]: os.O_NOFOLLOW == expected,
    }
    with tempfile.TemporaryDirectory(prefix="heresy011-regular-") as directory:
        anchor = Path(directory) / "anchor"
        anchor.write_bytes(GOOD_HEAD + b"\n")
        checks["regular_file_positive_control"] = (
            _read_anchor_from_descriptor(anchor) == GOOD_HEAD.decode("ascii")
        )
    wrong_flag_result = "not_tested_on_this_architecture"
    if machine in ("aarch64", "arm64"):
        # Deliberately misuse the x86-64 flag *only in this disposable fixture*.
        with tempfile.TemporaryDirectory(prefix="heresy011-abi-") as directory:
            root = Path(directory)
            wrong = root / "wrong-head"
            wrong.write_bytes(WRONG_HEAD + b"\n")
            link = root / "link"
            link.symlink_to(wrong)
            fd = os.open(link, os.O_RDONLY | os.O_NONBLOCK | 0o400000)
            with os.fdopen(fd, "rb") as handle:
                wrong_flag_result = handle.read(65) == WRONG_HEAD + b"\n"
            checks["arm64_x86_literal_follows_symlink"] = wrong_flag_result
    success = all(checks.values())
    print(json.dumps({
        "claims": {key: "executed" if success else "not_tested" for key in CLAIMS},
        "observations": {
            "all_checks_passed": success,
            "checks": checks,
            "exchange_cases": observations,
            "architecture": machine,
            "observed_o_nofollow_octal": oct(os.O_NOFOLLOW),
            "expected_o_nofollow_octal": oct(expected),
            "unsafe_fifo_timeout_was_forcibly_terminated": lookup[("unsafe", "fifo")]["timed_out"],
            "arm64_wrong_x86_flag_follows_symlink": wrong_flag_result,
        },
        "limitations": (
            "Forced deterministic interleaving is not a stochastic stress test; "
            "Python reproducer models the syscall pattern, not TOMBSTONE CLI execution. "
            "ARM64 behavior is executed only on an ARM64 runner; neither target "
            "proves all kernels, mount points, or hardware."
        ),
        "mitigation": "Use target-correct O_NOFOLLOW with O_NONBLOCK, fstat and bounded same-FD read.",
    }, sort_keys=True))
    return 0 if success else 1


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--child":
        raise SystemExit(_child(sys.argv[2], Path(sys.argv[3])))
    if len(sys.argv) != 1:
        raise SystemExit(2)
    raise SystemExit(run())
