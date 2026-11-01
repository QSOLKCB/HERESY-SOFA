"""Small standard-library reference for a finite-number JSON API boundary.

This is a test fixture and design example, not a production HTTP server.
License: MPL-2.0.  No private data, credentials, or network services required.
"""

from __future__ import annotations

import json
import math
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY_BYTES = 4096
MAX_SAFE_INTEGER = 2**53 - 1
DOMAIN_ABS_MAX = 1_000_000


class BoundaryError(ValueError):
    pass


def reject_constant(token: str):
    raise BoundaryError(f"non-JSON numeric token: {token}")


def finite_float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise BoundaryError("non-finite float conversion")
    return value


def bounded_int(token: str) -> int:
    # This is an *application* decision for IEEE-754 interoperable APIs.
    # JSON itself imposes no 53-bit signed-integer bound.
    value = int(token)
    if abs(value) > MAX_SAFE_INTEGER:
        raise BoundaryError("integer exceeds safe cross-runtime range")
    return value


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for name, value in pairs:
        if name in result:
            raise BoundaryError(f"duplicate object key: {name}")
        result[name] = value
    return result


def parse_body(body: bytes):
    if len(body) > MAX_BODY_BYTES:
        raise BoundaryError("request body exceeds size limit")
    try:
        decoded = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise BoundaryError("not valid UTF-8") from exc
    try:
        return json.loads(
            decoded,
            parse_constant=reject_constant,
            parse_float=finite_float,
            parse_int=bounded_int,
            object_pairs_hook=unique_object,
        )
    except json.JSONDecodeError as exc:
        raise BoundaryError("not valid JSON") from exc


def domain_value(obj):
    if type(obj) is not dict or "value" not in obj:
        raise BoundaryError("expected object with numeric 'value'")
    n = obj["value"]
    # A bool is an int subclass, but not an acceptable numeric measurement.
    if type(n) not in (int, float):
        raise BoundaryError("value must be a JSON number")
    if abs(n) > DOMAIN_ABS_MAX:
        raise BoundaryError("value outside application range")
    return n


def strict_json(value) -> bytes:
    return json.dumps(value, allow_nan=False, separators=(",", ":")).encode("utf-8")


def create_handler():
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            pass

        def reply(self, status, body):
            payload = strict_json(body)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self):
            if self.path != "/measure":
                return self.reply(404, {"error": "not found"})
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                return self.reply(415, {"error": "expected application/json"})
            try:
                size_text = self.headers.get("Content-Length")
                if size_text is None or not size_text.isascii() or not size_text.isdigit():
                    return self.reply(411, {"error": "valid Content-Length required"})
                size = int(size_text)
                if size > MAX_BODY_BYTES:
                    self.close_connection = True
                    return self.reply(413, {"error": "request body exceeds size limit"})
                document = parse_body(self.rfile.read(size))
                value = domain_value(document)
            except BoundaryError as exc:
                return self.reply(400, {"error": str(exc)})
            return self.reply(200, {"accepted": True, "value": value})

    return Handler


def start_loopback_server():
    return ThreadingHTTPServer(("127.0.0.1", 0), create_handler())