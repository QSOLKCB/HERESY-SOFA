import hashlib
import json


source = b"@echo off\r\necho tribunal\n"
naive = source.replace(b"\n", b"\r\n")


def normalize_crlf(data):
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n").replace(b"\n", b"\r\n")


normalized = normalize_crlf(source)
normalized_twice = normalize_crlf(normalized)
print(
    json.dumps(
        {
            "claims": {
                "naive_lf_conversion_can_duplicate_carriage_returns": "executed",
                "normalization_is_idempotent_for_fixture": "executed",
                "cmd_exe_interpretation": "not_tested",
            },
            "observations": {
                "source_hex": source.hex(),
                "naive_hex": naive.hex(),
                "naive_contains_crcrlf": b"\r\r\n" in naive,
                "normalized_hex": normalized.hex(),
                "normalization_idempotent": normalized == normalized_twice,
                "source_sha256": hashlib.sha256(source).hexdigest(),
                "cmd_exe_status": "not_tested: this experiment ran on Linux",
            },
            "mitigation": "Normalize line endings in bytes by canonicalizing CRLF/CR to LF before emitting CRLF.",
        },
        sort_keys=True,
    )
)
