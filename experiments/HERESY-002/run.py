import json
import shutil
import subprocess


bash = shutil.which("bash")
if bash is None:
    print(json.dumps({"claims": {"bash_stdin_collision": "unsupported"}}))
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
            "pipeline_status=$?\n"
            "printf 'pipeline_status=%s\\n' \"$pipeline_status\"\n",
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
    pipe_status_line = next(
        (line for line in collision.stdout.splitlines() if line.startswith("pipeline_status=")),
        "",
    )
    try:
        upstream_status = int(pipe_status_line.split("=", 1)[1])
    except (IndexError, ValueError):
        upstream_status = None
    print(
        json.dumps(
            {
                "claims": {
                    "heredoc_occupies_python_stdin": "executed",
                    "pipe_writer_can_receive_sigpipe": "executed" if upstream_status == 141 else "inferred",
                    "command_string_preserves_pipe_stdin": "executed",
                },
                "observations": {
                    "bash_version": bash_version.stdout.splitlines()[0] if bash_version.stdout else "unavailable",
                    "collision_stdout": collision.stdout,
                    "collision_exit_code": collision.returncode,
                    "upstream_pipeline_status": upstream_status,
                    "sigpipe_observed": upstream_status == 141,
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
