# HERESY-002 — The stdin Custody Battle

- **Hypothesis:** Bash cannot deliver a pipeline as Python's standard input when a heredoc has already assigned that same descriptor to Python source; an upstream writer may then receive `SIGPIPE`.
- **Environment:** Linux, Bash, and Python 3 standard library.
- **Minimal reproduction:** `yes | python3 - <<'PY'` runs the heredoc as Python source, not the pipe as `sys.stdin`. `pipefail` captures the pipeline status.
- **Expected behaviour:** The heredoc takes custody of stdin; the upstream pipe has no reader and may terminate with signal 13 (`SIGPIPE`, commonly status 141 in Bash).
- **Actual observations:** The JSON output records the heredoc run, pipeline status, whether SIGPIPE was observed, and a working pipe example. SIGPIPE is labelled `inferred` unless the actual upstream status is 141.
- **Mitigation:** Use `python3 -c` for code that reads the pipe, or capture heredoc source into a command string so Python's stdin remains available for the pipeline.
- **Limitations:** Signal scheduling and shell conventions can affect the exact status. No claim is made for shells other than the Bash runtime actually used.
- **Evidence provenance:** The fixture runs Bash subprocesses with fixed input and records their output and exit statuses in the receipt.
