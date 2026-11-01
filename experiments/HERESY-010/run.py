"""JCS key-order divergence: code points vs UTF-16 units; not full JCS."""
import hashlib
import json
import sys

CLAIMS=("supplementary_plane_key_order_diverges", "different_bytes_produce_different_digest",
        "utf16_sort_repairs_key_order", "bmp_only_control_agrees")

def serialize(keys):
    # Narrow fixture: flat objects with string keys and integer values only.
    return "{"+",".join(json.dumps(k,ensure_ascii=False,separators=(",",":"))+":1" for k in keys)+"}"

def run():
    astral="\U0001F600"     # UTF-16 lead surrogate D83D
    high_bmp="\uE000"     # E000 > D83D, but code point < 1F600
    names=[astral, high_bmp]
    cp=sorted(names)
    units=sorted(names,key=lambda k:k.encode("utf-16-be"))
    cp_json=serialize(cp).encode("utf-8")
    jcs_json=serialize(units).encode("utf-8")
    bmp=["a","\uE000", "\uFFFD"]
    bmp_equal=sorted(bmp)==sorted(bmp,key=lambda k:k.encode("utf-16-be"))
    repaired_again=serialize(sorted(names,key=lambda k:k.encode("utf-16-be"))).encode("utf-8")
    h=lambda b: hashlib.sha256(b).hexdigest()
    checks={
        "supplementary_plane_key_order_diverges": cp!=units and units==[astral,high_bmp],
        "different_bytes_produce_different_digest": cp_json!=jcs_json and h(cp_json)!=h(jcs_json),
        "utf16_sort_repairs_key_order": repaired_again==jcs_json and json.loads(jcs_json)==json.loads(cp_json),
        "bmp_only_control_agrees": bmp_equal,
    }
    passed=all(checks.values())
    print(json.dumps({"claims":{k:"executed" if passed else "not_tested" for k in CLAIMS},
       "observations":{"all_checks_passed":passed,"checks":checks,
           "python_default_key_order":["U+{:04X}".format(ord(k)) for k in cp],
           "utf16_code_unit_key_order":["U+{:04X}".format(ord(k)) for k in units],
           "default_sha256":h(cp_json),"utf16_sha256":h(jcs_json),
           "scope":"Python-only key-order reference; neither full RFC 8785 JCS nor JS runtime executed"},
       "mitigation":"Canonicalize JSON object keys by UTF-16 code units at every nesting level, and test byte-identical cross-language vectors. Also implement JCS number/escaping rules."},sort_keys=True))
    return 0 if passed else 1

if __name__=="__main__":sys.exit(run())