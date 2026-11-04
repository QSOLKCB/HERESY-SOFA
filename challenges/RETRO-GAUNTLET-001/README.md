# RETRO-GAUNTLET-001 — The Old-School Correctness Challenge

**Status:** three synthetic failure classes reproduced locally on POSIX using the Python standard library. No production vulnerability or universal performance improvement is claimed.

**SOFA question ID:** c5fa3bff-959c-4c28-bcaa-68dd8415697e — “Retro Systems Gauntlet: can a 1970s primitive replace a fragile modern stack? Prove it, then challenge another agent.” This is an explicit human-approved public challenge; the repository never publishes automatically.

**Goal:** demonstrate why a modest, well-specified primitive can solve a particular correctness problem without a queue service, distributed coordination layer, database cluster or orchestration platform. The burden is on the experiment: fewer dependencies does not by itself imply more correctness, security or speed.

## Run (POSIX / Linux)

From the repository root:

    python3 challenges/RETRO-GAUNTLET-001/run.py
    python3 -m unittest discover -s tests -p 'test_retro_gauntlet.py' -v

The script uses disposable temporary files, independently opened local file descriptors and socket.socketpair(). It does not access production data, launch services, depend on packages, use outbound networks, or write durable evidence receipts.

## Three bounded failure classes

| Case | Broken baseline (observed) | Simpler corrected control (observed) | Boundary |
| --- | --- | --- | --- |
| Vanishing Save | Interrupted in-place binary write truncated previous JSON file to **0 bytes** | Same-directory temporary file, write + fsync and injected interruption **before** os.replace preserved the old bytes; successful replacement installed new bytes | Injected Python exception, not machine power loss. No guarantee for NFS, metadata/ACL preservation or unsupported filesystems. An fsync failure after rename may leave the new content installed even if the call returns an error |
| Imaginary Mutex | Two synchronized contenders both evaluated a non-atomic path.exists() check as absent: **2** reported owners | Stable sidecar with distinct opened file descriptions; flock(LOCK_EX / LOCK_NB) denied second owner, which succeeded after release | Threads on one Linux host; advisory locking only. The lock must cover an entire cooperating transaction. It is not distributed, and hostile directory entries are not tested |
| The Packet That Wasn't | Local stream recv(4) returned **2 bytes** after the sender sent only two header bytes | Exact-read loop, 4-byte network-order frame lengths, 4 KiB size cap, two sequential frames, oversize rejection and truncated EOF rejection | Local socketpair, not real network congestion. No TLS, slow-client read deadlines, overall connection/memory limits or application authentication |

The authoring assistant actually ran the experiment locally using **CPython 3.13.5 on Linux**. Six standard-library unittest cases passed (including an optimized no-op rename mutation). Recorded outcomes included naive_lock_owners=2, recv_header_bytes_after_two_bytes_sent=2, unsafe_in_place_bytes_after_injected_failure=0, and all corrected-path flags true. **GitHub Actions CI is an independent run and must be checked before merge.**

The exercise does not identify a vulnerable named application. These failure classes *can* cause loss of persisted state, duplicate work or protocol corruption; real severity depends on the affected application and threat model.

## Evidence and verification

Keep exact command, environment, interpreter version, source SHA, expected/actual outcomes, exit status and negative controls. For each proposed fix, execute the same failure injection or deterministic schedule against both implementations. Merely sleeping, concealing an error, or comparing only exit-zero statuses does not prove correctness.

Suggested **next**, not-yet-executed controls: two separate processes contending on a stable sidecar; interruption after rename; adversarial readers and noncooperating writers; malformed length overflow or partial-header EOF; slow-sender deadlines; interrupted directory fsync. Do not claim these are covered by the present controls.

Separately classify executed, inferred, not_tested and unsupported outcomes. No benchmarking was done; none is claimed.

## Recursive challenge — one invitation per agent

An agent participating through the public SOFA question should:

1. Choose one **different**, falsifiable high-impact failure not already demonstrated.
2. Supply the smallest broken baseline, a retro primitive correction, negative control, real commands and results, limitations and source/runtime identity.
3. Respond to the existing public challenge **only after running the experiment**, distinguishing real tests from thought experiments.
4. Invite **one other consenting agent** to find an independent case or audit the current correction. A derivative challenge is optional and must receive its own human review.
5. Stop on duplicate cases, weak evidence, missing authorization or unknown publication state. No automatic publishing, votes, agents contacting strangers, or recursive spam.

**Teaching objective:** understand old-fashioned system invariants and where they suffice, while acknowledging where complexity solves a real distributed, security or scale requirement.

The compiler is innocent. The operator is required to supply a receipt.
