# HERESY-005 — The CUDA Apparition

**Status: placeholder; hardware evidence review pending.** The standalone runner exists, but the harness manifest intentionally remains `placeholder` with no entrypoint. A missing compiler, driver, or device produces `NOT_RUN` and a nonzero exit; it is never a pass.

## Falsifiable hypothesis

A controlled CUDA device-side assertion can be reported as `cudaErrorAssert` (numeric value 710) when the host synchronizes rather than when it checks the kernel launch. The broader claim that subsequent work is rejected by the poisoned context is deliberately **not tested**: this experiment makes no further CUDA call after observing 710.

## Safety and isolation

`assertion.cu` launches exactly one block with one thread. The control asserts true; the fault child asserts false exactly once. Each trial is a new process, the parent applies a short timeout, and a timed-out process is terminated by Python's bounded `subprocess.run`. There are no out-of-bounds writes, resets, driver changes, stress loops, persistent kernels, or post-assert CUDA operations.

Real GPU use requires the explicit `--hardware` flag:

```sh
python3 experiments/HERESY-005/run.py --hardware \
  --repeats 2 \
  --output experiments/HERESY-005/HERESY-005-report.json
```

The runner records `nvidia-smi`, `nvcc --version`, compiler-supported GPU code targets, a compiled runtime/device probe, every child exit code, launch/synchronization codes, and diagnostic stderr. It executes default launch behavior and `CUDA_LAUNCH_BLOCKING=1` without assuming either must change the error site. A fault trial is accepted only when its child exits 10 and either the launch-status query or synchronization returns exactly 710.

## Expected versus actual

Expected control: launch 0, synchronization 0, exit 0. Expected fault: exactly one 710 observation and exit 10. Actual observations belong in the generated sanitized report; a report whose `run_status` is `NOT_RUN` or `FAIL` is negative evidence, not a receipt of success.

## Reproduction and verification

The report contains repository-relative commands, the exact Git commit, an evidence-tree dirty flag, toolchain/runtime/device versions when available, source SHA-256 hashes, classifications, limitations, and all trial records. Regenerate it from a clean checkout of the recorded commit and compare source hashes:

```sh
sha256sum experiments/HERESY-005/{experiment.json,experiment.md,run.py,assertion.cu}
python3 -m unittest tests.test_heresy005 -v
```

The report is not a harness receipt, does not promote the manifest, and does not establish behavior on another CUDA stack. Raw `receipts/generated/` output remains local and uncommitted.

## Recorded preflight result and SOFA status (2026-11-04)

The committed [HERESY-005-report.json](HERESY-005-report.json) records clean evidence source `bb9042f9e8f626cf59bcac0113cf19dfbea801d7` and a real CUDA 12.4 compile (exit 0). `nvidia-smi` exited 9 because it could not communicate with the NVIDIA driver; the native compiled probe exited 30 with `device_count_status=100`, `device_count=0`. No control/fault child trial ran, no error 710 was observed, and context poisoning remains `not_tested`. **The assertion hypothesis is `NOT_RUN / UNCONFIRMED`**, irrespective of the successful compile.

The [published SOFA preflight TIL](https://agents.stackoverflow.com/tils/dd9e3bfe-edeb-4596-8d59-26af83f26572) describes exactly that limited finding. This Markdown update does not change the historical report's source hash or promote the placeholder manifest.
