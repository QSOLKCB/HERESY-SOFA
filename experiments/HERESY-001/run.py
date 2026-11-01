import json
import math
from decimal import Decimal


parse_constant_calls = []


def record_constant(value):
    parse_constant_calls.append(value)
    raise ValueError("non-standard constant: " + value)


def finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite JSON number: " + value)
    return result


parsed = json.loads("1e999", parse_constant=record_constant)
strict_parse_rejected = False
try:
    json.loads("1e999", parse_constant=record_constant, parse_float=finite_float)
except ValueError:
    strict_parse_rejected = True

decimal_value = json.loads("1e999", parse_float=Decimal)
strict_serialize_rejected = False
try:
    json.dumps(float("inf"), allow_nan=False)
except ValueError:
    strict_serialize_rejected = True

print(
    json.dumps(
        {
            "claims": {
                "overflowing_json_number_becomes_infinity": "executed",
                "parse_constant_is_not_called_for_numeric_overflow": "executed",
                "finite_checking_parse_float_rejects_overflow": "executed",
                "decimal_preserves_large_finite_value": "executed",
                "strict_serialization_rejects_infinity": "executed",
            },
            "observations": {
                "parsed_is_infinite": math.isinf(parsed),
                "parse_constant_calls": parse_constant_calls,
                "finite_parse_rejected": strict_parse_rejected,
                "decimal_is_finite": decimal_value.is_finite(),
                "decimal_value": str(decimal_value),
                "strict_serialization_rejected": strict_serialize_rejected,
            },
            "mitigation": {
                "parse_float": "reject values for which math.isfinite(float(value)) is false",
                "decimal": "use parse_float=Decimal when decimal magnitude/precision is required",
                "serialization": "use json.dumps(value, allow_nan=False)",
            },
        },
        sort_keys=True,
    )
)
