import json
import shutil
import subprocess
import sys


def recorded_status(output, prefix):
    matches = [line for line in output.splitlines() if line.startswith(prefix + "=")]
    if len(matches) != 1:
        return None
    try:
        return int(matches[0].split("=", 1)[1])
    except ValueError:
        return None


bash = shutil.which("bash")
if bash is None:
    print(json.dumps({"claims": {
        "heredoc_occupies_python_stdin": "unsupported",
        "pipe_writer_can_receive_sigpipe": "unsupported",
        "command_string_preserves_pipe_stdin": "unsupported",
    }}))
    sys.exit(1)
else:
    bash_version = subprocess.run(
        [bash, "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=5,
        check=False,
    )
    collision = subprocess.run(
        [
            bash,
            "-c",
            "set -o pipefail\n"
            "yes | python3 - <<'PY'\n"
            "print('heredoc supplied Python source')\n"
            "PY\n"
            "statuses=(\"${PIPESTATUS[@]}\")\n"
            "printf 'producer_status=%s\\n' \"${statuses[0]}\"\n"
            "printf 'consumer_status=%s\\n' \"${statuses[1]}\"\n",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )
    working = subprocess.run(
        [
            bash,
            "-c",
            "printf 'pipe payload\\n' | python3 -c "
            "\"$(cat <<'PY'\nimport sys\nprint(sys.stdin.read().strip())\nPY\n)\"",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )
    producer_status = recorded_status(collision.stdout, "producer_status")
    consumer_status = recorded_status(collision.stdout, "consumer_status")
    collision_ok = (
        collision.returncode == 0
        and consumer_status == 0
        and producer_status in (0, 141)
        and collision.stdout.splitlines().count("heredoc supplied Python source") == 1
    )
    working_ok = working.returncode == 0 and working.stdout == "pipe payload\n"
    # A broken writer alone is not evidence that Python actually executed.
    sigpipe_claim = (
        "executed" if collision_ok and producer_status == 141
        else "inferred" if collision_ok else "not_tested"
    )
    print(
        json.dumps(
            {
                "claims": {
                    "heredoc_occupies_python_stdin": "executed" if collision_ok else "not_tested",
                    "pipe_writer_can_receive_sigpipe": sigpipe_claim,
                    "command_string_preserves_pipe_stdin": "executed" if working_ok else "not_tested",
                },
                "observations": {
                    "bash_version": bash_version.stdout.splitlines()[0] if bash_version.stdout else "unavailable",
                    "collision_stdout": collision.stdout,
                    "collision_exit_code": collision.returncode,
                    "upstream_pipeline_status": consumer_status if consumer_status not in (None, 0) else producer_status,
                    "producer_exit_code": producer_status,
                    "consumer_exit_code": consumer_status,
                    "sigpipe_observed": collision_ok and producer_status == 141,
                    "collision_stderr": collision.stderr,
                    "working_stdout": working.stdout,
                    "working_exit_code": working.returncode,
                    "working_stderr": working.stderr,
                },
                "mitigations": [
                    "Use python3 -c when the program must read the pipe on stdin.",
                    "Capture a heredoc as a command string, then pass the input pipe to Python.",
                ],
            },
            sort_keys=True,
        )
    )
    sys.exit(0 if collision_ok and working_ok and bash_version.returncode == 0 else 1)
