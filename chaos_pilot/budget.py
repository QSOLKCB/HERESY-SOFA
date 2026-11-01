"""Conservative reservation ledger. POSIX single-host lock; USD micro-units.

Only covers calls made through this process, not the user's API organization.
"""
import fcntl
import json
import os
import uuid
from contextlib import contextmanager
from pathlib import Path

STOP_MICRO_USD = 17_000_000
PROJECT_CEILING_MICRO_USD = 20_000_000
# Deliberately overestimates short-context Standard Sol costs: input at $3/1M
# (covers ordinary input and hypothetical cache writes), output at $10/1M.
RESERVE_INPUT_MICRO = 3
OUTPUT_MICRO = 10
MAX_REQUEST_BYTES = 16_000
MAX_OUTPUT_TOKENS = 4_096

class BudgetExhausted(RuntimeError):
    pass


def reserve_cost(payload, max_output_tokens):
    if not isinstance(payload, bytes) or len(payload) > MAX_REQUEST_BYTES:
        raise ValueError("request too large or not bytes")
    if not 1 <= max_output_tokens <= MAX_OUTPUT_TOKENS:
        raise ValueError("output token limit out of scope")
    # This is an upper-bound *estimate*, not a provider billing guarantee.
    input_tokens_buffered = 4 * len(payload) + 4096
    return RESERVE_INPUT_MICRO * input_tokens_buffered + OUTPUT_MICRO * max_output_tokens


def observed_cost(input_tokens, output_tokens):
    if type(input_tokens) is not int or type(output_tokens) is not int or min(input_tokens, output_tokens) < 0:
        raise ValueError("invalid usage counters")
    return input_tokens * RESERVE_INPUT_MICRO + output_tokens * OUTPUT_MICRO


class Ledger:
    def __init__(self, directory):
        self.root = Path(directory)
        if self.root.is_symlink():
            raise ValueError("state directory cannot be symlink")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.file = self.root / "ledger.json"
        self.lock = self.root / "ledger.lock"

    @contextmanager
    def locked(self):
        with self.lock.open("a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield

    def read(self):
        if not self.file.exists():
            return {"schema_version": 1, "requests": []}
        data = json.loads(self.file.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("requests"), list):
            raise ValueError("ledger corrupted")
        return data

    def write(self, data):
        tmp = self.root / ("ledger." + uuid.uuid4().hex + ".tmp")
        try:
            fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, sort_keys=True, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.file)
        finally:
            tmp.unlink(missing_ok=True)

    def reserve(self, request_bytes, max_output_tokens):
        cost = reserve_cost(request_bytes, max_output_tokens)
        with self.locked():
            data = self.read()
            cumulative = sum(int(x["charged_micro_usd"]) for x in data["requests"])
            if cumulative + cost > STOP_MICRO_USD:
                raise BudgetExhausted("local US$17 stop threshold reached")
            identity = uuid.uuid4().hex
            data["requests"].append({"id": identity, "status": "reserved_uncertain",
                                     "charged_micro_usd": cost, "reserved_micro_usd": cost})
            self.write(data)
            return identity

    def settle(self, identity, usage=None):
        with self.locked():
            data = self.read()
            rows = [x for x in data["requests"] if x["id"] == identity]
            if len(rows) != 1 or rows[0]["status"] != "reserved_uncertain":
                raise ValueError("reservation already settled or missing")
            row = rows[0]
            if usage is not None:
                estimated = observed_cost(usage["input_tokens"], usage["output_tokens"])
                row["charged_micro_usd"] = max(0, estimated)
                row["status"] = "usage_recorded"
            else:
                # Keep full reservation on HTTP error/timeout/uncertain usage.
                row["status"] = "unknown_usage_reservation_retained"
            self.write(data)
            return row["charged_micro_usd"]

    def total(self):
        with self.locked():
            return sum(int(x["charged_micro_usd"]) for x in self.read()["requests"])