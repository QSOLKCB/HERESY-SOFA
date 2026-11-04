#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import tempfile
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from corrected import (BoundaryError, PLACEHOLDER, POST_PATTERNS, REFINED_PATTERNS,
                       bounded_request, redacted_scan)

SEED = 26051108
FAKE_SECRET = "FAKE_" + hashlib.sha256(str(SEED).encode()).hexdigest()


class FixtureHandler(BaseHTTPRequestHandler):
    expected = FAKE_SECRET
    peer_redirect = None
    received_real = 0
    received_placeholder = 0

    def log_message(self, *args):
        return

    def do_POST(self):
        auth = self.headers.get("Authorization", "")
        if self.expected in auth:
            type(self).received_real += 1
        if PLACEHOLDER in auth:
            type(self).received_placeholder += 1
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", self.peer_redirect)
            self.send_header("X-Request-ID", "redirect-fixture")
            self.end_headers()
            return
        if self.expected not in auth:
            self.send_response(403)
            self.send_header("X-Request-ID", "denied-fixture")
            self.end_headers()
            self.wfile.write(b"placeholder rejected")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("X-Request-ID", "accepted-fixture")
        self.end_headers()
        # Deliberately echo the synthetic value to test the response boundary.
        self.wfile.write(("echo=" + self.expected).encode())


def start_server(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def raw_request(url, authorization):
    request = urllib.request.Request(url, data=b"{}", method="POST",
                                     headers={"Authorization": authorization})
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def main(receipt_path):
    started = datetime.now(timezone.utc).isoformat()
    checks = []

    def check(name, actual, expected, classification="EXECUTED"):
        checks.append({"name": name, "actual": actual, "expected": expected,
                       "passed": actual == expected, "classification": classification})

    with tempfile.TemporaryDirectory(prefix="codex001-case02-") as tmp:
        root = Path(tmp)
        secret_store = root / "credential.store"
        memory_leaky = root / "memory-leaky.txt"
        memory_pointer = root / "memory-pointer.txt"
        uri_file = root / "short-uri.txt"
        benign_file = root / "benign.txt"
        secret_store.write_text(FAKE_SECRET)
        os.chmod(secret_store, 0o600)
        memory_leaky.write_text("Authorization: Bearer " + FAKE_SECRET + "\n")
        memory_pointer.write_text("credential_ref=" + str(secret_store) + "\n")
        uri_file.write_text("postgresql://agent:p7@localhost:5432/db\n")
        benign_file.write_text(
            "/srv/build/01234567-89ab-cdef-0123-456789abcdef/artifacts/output-file\n"
        )

        check("synthetic_loader_reinjects_embedded_value",
              FAKE_SECRET in memory_leaky.read_text(), True)
        check("pointer_only_memory_excludes_value",
              FAKE_SECRET in memory_pointer.read_text(), False)
        check("secret_file_mode", oct(secret_store.stat().st_mode & 0o777), "0o600")
        check("posted_patterns_find_token_shape",
              bool(redacted_scan(memory_leaky.read_text(), POST_PATTERNS)), True)
        check("posted_patterns_miss_short_uri",
              bool(redacted_scan(uri_file.read_text(), POST_PATTERNS)), False)
        check("refined_patterns_find_short_uri",
              "credential_uri" in redacted_scan(uri_file.read_text(), REFINED_PATTERNS), True)
        check("broad_pattern_false_positive_path_uuid",
              "broad_long_run" in redacted_scan(benign_file.read_text(), POST_PATTERNS), True)
        check("refined_patterns_reject_path_uuid",
              redacted_scan(benign_file.read_text(), REFINED_PATTERNS), {})
        check("pointer_only_refined_scan_clean",
              redacted_scan(memory_pointer.read_text(), REFINED_PATTERNS), {})

        class AllowedHandler(FixtureHandler):
            received_real = 0
            received_placeholder = 0

        class OtherHandler(FixtureHandler):
            received_real = 0
            received_placeholder = 0

        allowed, allowed_thread = start_server(AllowedHandler)
        other, other_thread = start_server(OtherHandler)
        allowed_origin = f"http://127.0.0.1:{allowed.server_port}"
        other_origin = f"http://127.0.0.1:{other.server_port}"
        AllowedHandler.peer_redirect = other_origin + "/allowed"
        try:
            status, _ = raw_request(allowed_origin + "/allowed", "Bearer " + PLACEHOLDER)
            check("plain_placeholder_rejected", status, 403)

            status, echoed = raw_request(other_origin + "/allowed", "Bearer " + FAKE_SECRET)
            check("unrestricted_injector_reaches_wrong_destination", status, 200)
            check("unrestricted_response_echoes_value", FAKE_SECRET in echoed, True)

            safe = bounded_request(allowed_origin + "/allowed", "POST",
                                   '{"credential":"' + PLACEHOLDER + '"}',
                                   FAKE_SECRET, allowed_origin, {"/allowed", "/redirect"})
            check("bounded_approved_operation_succeeds", safe["status"], 200)
            check("bounded_response_excludes_value", FAKE_SECRET in json.dumps(safe), False)

            rejected = False
            try:
                bounded_request(other_origin + "/allowed", "POST", PLACEHOLDER,
                                FAKE_SECRET, allowed_origin, {"/allowed", "/redirect"})
            except BoundaryError:
                rejected = True
            check("bounded_wrong_destination_rejected_before_send", rejected, True)

            redirected = bounded_request(allowed_origin + "/redirect", "POST", PLACEHOLDER,
                                         FAKE_SECRET, allowed_origin, {"/allowed", "/redirect"})
            check("automatic_redirect_disabled", redirected["status"], 302)
            check("redirect_target_never_received_secret", OtherHandler.received_real, 1)
            # The count is one only because the intentionally unrestricted control ran first.
        finally:
            allowed.shutdown()
            other.shutdown()
            allowed.server_close()
            other.server_close()
            allowed_thread.join(timeout=2)
            other_thread.join(timeout=2)

    passed = all(item["passed"] for item in checks)
    receipt = {
        "case": "CASE-02",
        "source_id": "02c83759-175f-4e00-8b7b-8962f3ba33c4",
        "source_author": "scaffolding",
        "reply_authors": ["tcsenpai-ccode", "Muse", "WorkerBee", "Muse"],
        "seed": SEED,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "command": "uv run --no-project --offline --no-managed-python python test_case_02.py --receipt receipt.json",
        "process_exit_code": 0 if passed else 1,
        "candidate_values_logged": False,
        "external_services": "none; two loopback HTTP fixtures only",
        "checks": checks,
        "limitations": [
            "Synthetic loader proves a conditional mechanism, not that every agent product auto-loads memory.",
            "Regex scanning is heuristic and cannot establish absence of secrets.",
            "TLS, DNS rebinding, real adapters, remote stores, and real credentials were not tested."
        ],
        "conclusion": {
            "classification": "PARTIALLY_CORRECT",
            "executed": "Pointer-only storage excluded the synthetic value; URI augmentation and bounded injection worked.",
            "defect": "The original scan misses a short URI password and broad token heuristics false-positive benign paths/UUIDs. Substitution alone leaks to an unauthorized destination and through an echo response.",
            "minimal_correction": "Keep pointer-only storage, redact scan output, add URI-shape checks, and enforce destination/method/redirect plus response-field boundaries at injection."
        }
    }
    # JSON uses the actual Python Boolean; no candidate value is serialized.
    receipt["candidate_values_logged"] = False
    Path(receipt_path).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"case": "CASE-02", "passed": passed, "checks": len(checks),
                      "candidate_values_logged": False}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    raise SystemExit(main(parser.parse_args().receipt))
