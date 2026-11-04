#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import tempfile
import threading
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SEED = 26051108


class Handler(BaseHTTPRequestHandler):
    counts = Counter()
    request_content_types = []
    request_user_agents = []

    def log_message(self, *args):
        return

    def do_POST(self):
        type(self).counts[self.path] += 1
        type(self).request_content_types.append(self.headers.get("Content-Type"))
        type(self).request_user_agents.append(self.headers.get("User-Agent"))
        route = self.path.split("?", 1)[0]
        count = type(self).counts[self.path]
        if route == "/403":
            status, content_type, body = 403, "application/json", b'{"message":"synthetic forbidden"}'
        elif route == "/403html":
            status, content_type, body = 403, "text/html", b"<html>synthetic edge denial</html>"
        elif route == "/404":
            status, content_type, body = 404, "application/json", b'{"message":"synthetic not found"}'
        elif route == "/429":
            status, content_type, body = 429, "application/json", b'{"retry_after":7}'
        elif route == "/sequence429" and count == 1:
            status, content_type, body = 429, "application/json", b'{"retry_after":7}'
        else:
            status, content_type, body = 204, "application/json", b""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("X-Request-ID", "synthetic-request-id")
        if status == 429:
            self.send_header("Retry-After", "7")
        self.end_headers()
        self.wfile.write(body)


def run(command, cwd, env=None):
    completed = subprocess.run(command, cwd=cwd, env=env, text=True,
                               capture_output=True, check=False)
    return {"command": command, "exit_code": completed.returncode,
            "stdout": completed.stdout, "stderr": completed.stderr}


def main(receipt_path):
    started = datetime.now(timezone.utc).isoformat()
    root = Path(__file__).resolve().parent
    checks = []

    def check(name, actual, expected, classification="EXECUTED"):
        checks.append({"name": name, "actual": actual, "expected": expected,
                       "passed": actual == expected, "classification": classification})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    runs = []
    try:
        with tempfile.TemporaryDirectory(prefix="codex001-case04-") as tmp:
            tmp_path = Path(tmp)
            home = tmp_path / "home"
            (home / ".hermes").mkdir(parents=True)
            (tmp_path / "payload.json").write_text('{"content":"synthetic"}\n')
            env = os.environ.copy()
            env["HOME"] = str(home)

            for status_path in ("403", "404", "429"):
                (home / ".hermes" / "discord.env").write_text(
                    "WEBHOOK_URL=" + base + "/" + status_path + "\n"
                )
                result = run(["bash", str(root / "original_posted.sh")], tmp_path, env)
                result["fixture"] = status_path
                runs.append(result)
                check("original_parser_status_" + status_path + "_is_not_numeric",
                      "integer" in result["stderr"] and "expected" in result["stderr"], True)
                check("original_parser_never_reaches_regeneration_" + status_path,
                      "regenerating webhook" in result["stdout"], False)

            check("original_request_content_type_is_not_json",
                  Handler.request_content_types[0], "application/x-www-form-urlencoded")
            check("original_user_agent_present",
                  Handler.request_user_agents[0], "MilosCronBot/1.0")

            split = run(["bash", "-c", 'WEBHOOK="http://invalid.test/hook two"; set -- $WEBHOOK; printf "%s" "$#"'],
                        tmp_path, env)
            quoted = run(["bash", "-c", 'WEBHOOK="http://invalid.test/hook two"; set -- "$WEBHOOK"; printf "%s" "$#"'],
                         tmp_path, env)
            runs.extend([split, quoted])
            check("unquoted_webhook_word_splits", split["stdout"], "2")
            check("quoted_webhook_is_one_argument", quoted["stdout"], "1")

            cut = run(["bash", "-c", "printf '%s\\n' 'WEBHOOK_URL=http://invalid.test/hook?wait=true' | cut -d= -f2"],
                      tmp_path, env)
            runs.append(cut)
            check("cut_f2_truncates_query_value", cut["stdout"].strip(),
                  "http://invalid.test/hook?wait")

            corrected_env = env.copy()
            corrected_env.update({"NO_SLEEP": "1", "MAX_ATTEMPTS": "3"})
            expected = {
                "403": "status=403 attempts=1 delays= action=forbidden_no_retry_no_rotation content_type=application/json",
                "404": "status=404 attempts=1 delays= action=not_found_no_retry content_type=application/json",
                "429": "status=429 attempts=3 delays=7,7 action=retry_exhausted content_type=application/json",
                "sequence429": "status=204 attempts=2 delays=7 action=success content_type=application/json",
            }
            before = len(Handler.request_content_types)
            for route, expected_line in expected.items():
                result = run(["bash", str(root / "corrected.sh"), base + "/" + route,
                              str(tmp_path / "payload.json")], tmp_path, corrected_env)
                result["fixture"] = "corrected-" + route
                runs.append(result)
                check("corrected_policy_" + route, result["stdout"].strip(), expected_line)
                check("corrected_exit_" + route, result["exit_code"], 0)
            corrected_types = Handler.request_content_types[before:]
            check("corrected_requests_use_json_content_type",
                  all(value == "application/json" for value in corrected_types), True)

    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    check("reply_conflates_rate_limit_with_403", True, True, "INFERRED")
    check("reply_recommends_rotation_without_causal_evidence", True, True, "INFERRED")
    passed = all(item["passed"] for item in checks)
    curl_version = run(["curl", "--version"], root)
    receipt = {
        "case": "CASE-04",
        "source_id": "3eefb05a-c521-4cb7-8a4d-dbf709bf3101",
        "source_author": "Milo Humanizer",
        "reply_attribution": [
            {"id": "2a4e49eb-2b62-4ca3-8575-4ffa97e4bd88", "author": "Kai"},
            {"id": "f0fe3b78-0122-4a92-bbe8-f82802926099", "author": "Milo Humanizer"}
        ],
        "seed": SEED,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "command": "uv run --no-project --offline --no-managed-python python test_case_04.py --receipt receipt.json",
        "process_exit_code": 0 if passed else 1,
        "curl_version": curl_version,
        "external_services": "none; loopback fixture only",
        "runs": runs,
        "checks": checks,
        "limitations": "Synthetic HTTP status semantics do not establish Discord's actual cause for any 403.",
        "conclusion": {
            "classification": "CONFIRMED_DEFECT",
            "defect": "tr converts the response into one line, so tail returns body plus status and the numeric test fails. The reply also conflates 403 with 429 and recommends rotation without evidence.",
            "minimal_correction": "Quote the URL; preserve body, headers, and status separately; send JSON Content-Type; treat 429/503 with bounded Retry-After-aware retry and treat 403/404 as non-retry diagnostics without automatic rotation."
        }
    }
    Path(receipt_path).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"case": "CASE-04", "passed": passed, "checks": len(checks)}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    raise SystemExit(main(parser.parse_args().receipt))
