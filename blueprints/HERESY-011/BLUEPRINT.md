## When this design is useful

A CLI or service reads a small, security-sensitive file through a pathname—for example, an independently retained SHA-256 chain head. The directory or pathname can change concurrently. The requirement is to reject invalid input promptly, without opening an attacker-substituted file or treating a successful hash comparison as proof of the anchor's custody.

This is HERESY-011, "The Anchor That Became a FIFO": a case where one security fix introduced a second, architecture-specific mistake.

## Failure modes

**Pathname check versus file actually opened.** Checking `lstat` or `symlink_metadata` and then calling a separate blocking `open` is a time-of-check/time-of-use (TOCTOU) gap. A pathname that pointed to a regular file during validation might point to a FIFO or symlink during the second lookup. FIFO opens can wait for a writer; symlinks can redirect reads to a different, *syntactically valid* head. Valid hex does not establish correct identity.

**Correct syscall intent, wrong ABI flag.** Linux x86-64 uses `O_NOFOLLOW = 0o400000`; Linux AArch64 uses `O_NOFOLLOW = 0o100000`. Copying the x86-64 numeric literal to AArch64 silently fails to request the intended symlink protection. Treat these as target-specific ABI values, not portable source constants.

## Reusable defensive blueprint

1. Define the anchor's trust boundary **before** reading it. The expected head must come from a verifier-controlled, independently retained source, not be copied from the chain being checked.
2. On supported Linux targets, open the pathname once with native `O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC` constants. Prefer platform-provided symbolic constants over numeric literals. Reject unsupported targets rather than guessing.
3. Check the **opened file descriptor** with `fstat` (Rust: metadata on the opened `File`). Require a regular file. The check and subsequent read must refer to the same descriptor.
4. Read at most 66 bytes: 64 lowercase ASCII hexadecimal bytes, optionally followed by exactly one LF, plus a byte to detect excess. Reject any malformed, nonregular, truncated, oversized, or ambiguous value.
5. Pass the resulting 32 raw bytes to the chain verifier. Keep failures fail-closed and errors free of untrusted path contents. Never relabel a locally self-consistent head as independently authenticated custody.

Python-oriented reference outline:

```python
fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
with os.fdopen(fd, "rb") as handle:
    if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
        raise ValueError("anchor must be a regular file")
    raw = handle.read(66)
# Enforce exactly 64 lowercase hex bytes plus optional final LF.
# Reject other lengths, extra bytes, CR, whitespace and uppercase.
```

Rust can use `OpenOptionsExt` with architecture-correct flags, then `File::metadata`, then a bounded read on that same `File`. The precise flag source is part of the portability contract.

## Verification matrix

Use only disposable files and an outer timeout; never risk hanging the real CLI or a production anchor.

| Scenario | Required result |
| --- | --- |
| Ordinary 64-hex regular file | Accept exact head |
| Path changes to a FIFO between pathname check and open | Unsafe pattern may block; fixed reader refuses promptly |
| Path changes to a symlink pointing at a different valid 64-hex head | Unsafe pattern can read wrong head; fixed reader refuses |
| Wrong flag literal on AArch64 | Negative control exposes symlink following |
| Correct native no-follow flag on both Linux targets | Symlink is refused |
| Overlong, truncated, uppercase, or otherwise malformed anchor | Reject |
| Internally valid rewritten chain with original independently held head | Reject incorrect chain |

A deterministic parent/child synchronization point can prove the check/open gap is exploitable without depending on winning a lucky race. Separately stress the actual application with atomic rename exchange and hard child timeouts. A green x86-64 job cannot stand in for an AArch64 test.

## Executed evidence (two separate scopes)

**Independent Python syscall-pattern reproduction:** HERESY-SOFA experiment HERESY-011, reviewed source commit `bbc666ff26fb66552c069d49e22308cc30242a46`. Its Linux x86-64 and AArch64 CI jobs both passed (run `41332181292`), including isolated FIFO and symlink controls, correct-descriptor checks, and an AArch64-only wrong-flag negative control. Its repository regression and evidence checks also passed (run `41332181270`). The harness generated and verified platform-specific receipts. This independently demonstrates the Linux syscall pattern; it is **not** a re-execution of the Rust application.

**Upstream Rust CLI:** TOMBSTONE Phase 16, reviewed commit `339a57d3b19dc0e6d223ac3e1e033a66a2feeb4e`. Its separate eight-configuration Linux x86-64/AArch64 × GCC/Clang × OpenSSL/HACL suite passed (run `41331092253`). An earlier candidate failed all four AArch64 jobs because it used the x86-64 `O_NOFOLLOW` literal. The corrected head subsequently received a code review with no major issues. These upstream observations must not be conflated with the independent Python reproduction.

## Tradeoffs and limitations

- `O_NOFOLLOW` blocks following a symlink in the **final** component. To constrain ancestors too, investigate directory-relative opens and Linux `openat2` resolution flags, and test that expanded threat model separately.
- A same-descriptor `fstat` prevents the pathname/type substitution described here; it does not freeze file contents against concurrent writes, guarantee all filesystems behave alike, or defend against a malicious kernel.
- `O_NONBLOCK` addresses FIFO opens, not every possible untrusted I/O stall. Keep an outer deadline.
- None of this proves signer identity, independent custody of a head, chronology, actual deletion, or physical storage erasure.
- The reported executions cover the declared Linux targets only; Windows and other architectures are not verified.

**Decision rule:** validate *the opened descriptor*, not *the pathname you checked earlier*. Test syscall flag values on every target architecture you actually support.

The pathname had an alibi. The descriptor had the evidence.
