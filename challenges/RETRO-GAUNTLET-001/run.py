"""RETRO-001 — isolated, standard-library demonstrations of classic correctness primitives.

No third-party packages, production files, services, or outbound network use.
Nothing here tests distributed locks, durability after power loss, or TLS.
"""
from __future__ import annotations

import fcntl
import json
import os
import socket
import struct
import tempfile
import threading
from pathlib import Path

MAX_FRAME_SIZE = 4096


def require(condition: bool, message: str) -> None:
    """Fail closed even when Python optimization removes bare assert statements."""
    if not condition:
        raise RuntimeError(message)


def atomic_replace(path: Path, data: bytes, *, interrupt_before_rename: bool = False) -> None:
    """Atomically replace file bytes on one POSIX filesystem, best-effort durable metadata."""
    temp = None
    try:
        fd, name = tempfile.mkstemp(prefix=".retro-", dir=path.parent)
        temp = Path(name)
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        if interrupt_before_rename:
            raise RuntimeError("injected failure before rename")
        os.replace(temp, path)
        temp = None
        dirfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def read_exact(sock: socket.socket, n: int) -> bytes:
    data = bytearray()
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise EOFError(f"frame truncated at {len(data)} / {n}")
        data.extend(chunk)
    return bytes(data)


def read_frame(sock: socket.socket, *, max_size: int = MAX_FRAME_SIZE) -> bytes:
    length = struct.unpack("!I", read_exact(sock, 4))[0]
    if length > max_size:
        raise ValueError("oversized announced frame")
    return read_exact(sock, length)


def run_demo() -> dict:
    with tempfile.TemporaryDirectory(prefix="retro-gauntlet-") as root:
        here = Path(root)
        # Data-loss baseline: open(..., 'wb') truncates even if the next operation fails.
        bad = here / "unsafe.json"
        bad.write_bytes(b'{"generation":1}')
        try:
            with bad.open("wb") as f:
                raise RuntimeError("injected failure before write")
        except RuntimeError:
            pass
        bad_bytes_after_failure = bad.read_bytes()
        require(bad_bytes_after_failure == b"", "unsafe truncation not reproduced")

        # Corrected transaction: before rename, original survives; after, full new bytes.
        good = here / "safe.json"
        good.write_bytes(b'{"generation":1}')
        try:
            atomic_replace(good, b'{"generation":2}', interrupt_before_rename=True)
        except RuntimeError:
            pass
        good_bytes_before_commit = good.read_bytes()
        require(good_bytes_before_commit == b'{"generation":1}', "atomic precommit preservation failed")
        atomic_replace(good, b'{"generation":2}')
        replacement_committed = good.read_bytes() == b'{"generation":2}'
        require(replacement_committed, "atomic replacement failed")

        # TOCTOU: two contenders both observe nonexistence before either creates.
        lock_file = here / "naive.lock"
        barrier = threading.Barrier(2)
        naive_owners = []
        errors = []

        def naive_contender(identity: int) -> None:
            try:
                absent = not lock_file.exists()
                barrier.wait(timeout=5)
                if absent:
                    with lock_file.open("w", encoding="ascii") as output:
                        output.write(str(identity))
                    naive_owners.append(identity)
            except Exception as error:
                errors.append(repr(error))

        threads = [threading.Thread(target=naive_contender, args=(i,)) for i in (1, 2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=6)
        require(not any(thread.is_alive() for thread in threads), "contender did not finish")
        require(not errors, "contender error: " + repr(errors))
        require(len(naive_owners) == 2, "naive lock race not observed")

        # POSIX stable sidecar lock: independent open descriptions do conflict.
        sidecar = here / "stable.lock"
        fd1 = os.open(sidecar, os.O_CREAT | os.O_RDWR, 0o600)
        fd2 = os.open(sidecar, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd1, fcntl.LOCK_EX | fcntl.LOCK_NB)
            second_denied = False
            try:
                fcntl.flock(fd2, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                second_denied = True
            require(second_denied, "second file lock was unexpectedly granted")
            fcntl.flock(fd1, fcntl.LOCK_UN)
            fcntl.flock(fd2, fcntl.LOCK_EX | fcntl.LOCK_NB)
            second_acquired_after_release = True
        finally:
            os.close(fd2)
            os.close(fd1)

        # SOCK_STREAM is a byte stream, not one message per recv().
        left, right = socket.socketpair()
        try:
            left.sendall(b"\x00\x00")
            short_header = right.recv(4)
            require(short_header == b"\x00\x00", "short header was not observed")
        finally:
            left.close()
            right.close()

        # Bounded, explicitly framed data handles concatenated frames and rejected lengths.
        left, right = socket.socketpair()
        try:
            messages = (b"ABCD", b"EF")
            left.sendall(b"".join(struct.pack("!I", len(m)) + m for m in messages))
            decoded = [read_frame(right) for _ in messages]
            require(decoded == list(messages), "frame decoding mismatched")
        finally:
            left.close()
            right.close()
        left, right = socket.socketpair()
        try:
            left.sendall(struct.pack("!I", MAX_FRAME_SIZE + 1))
            rejected_oversize = False
            try:
                read_frame(right)
            except ValueError:
                rejected_oversize = True
            require(rejected_oversize, "oversize frame was not rejected")
        finally:
            left.close()
            right.close()
        left, right = socket.socketpair()
        try:
            left.sendall(struct.pack("!I", 5) + b"X")
            left.shutdown(socket.SHUT_WR)
            rejected_partial_eof = False
            try:
                read_frame(right)
            except EOFError:
                rejected_partial_eof = True
            require(rejected_partial_eof, "truncated frame was not rejected")
        finally:
            left.close()
            right.close()

    return {
        "unsafe_in_place_bytes_after_injected_failure": len(bad_bytes_after_failure),
        "atomic_precommit_original_preserved": good_bytes_before_commit == b'{"generation":1}',
        "atomic_full_replacement_committed": replacement_committed,
        "naive_lock_owners": len(naive_owners),
        "stable_lock_second_contender_denied": second_denied,
        "stable_lock_reacquired_after_release": second_acquired_after_release,
        "recv_header_bytes_after_two_bytes_sent": len(short_header),
        "two_frames_decoded": len(decoded),
        "oversized_frame_rejected": rejected_oversize,
        "truncated_frame_eof_rejected": rejected_partial_eof,
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), sort_keys=True))
