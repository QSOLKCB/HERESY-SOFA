#!/usr/bin/env python3
"""Offline fake-secret scanner and request-boundary model; no credentials or network."""
from __future__ import annotations
import json
import re

FAKE = 'FAKE_TOKEN_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456'
BASE_PATTERNS = [r'Bearer\s+\S+', r'api_key\s*[=:]\s*\S+', r'-----BEGIN', r'[A-Za-z0-9+/=_-]{32,}']
URI_CRED = r'[a-z][a-z0-9+.-]*://[^/\s:]+:[^@\s]+@'

def scan(text: str, augmented: bool = False) -> list[str]:
    patterns = BASE_PATTERNS + ([URI_CRED] if augmented else [])
    return [p for p in patterns if re.search(p, text, re.I)]

def unsafe_inject(url: str, placeholder: str, secret: str) -> tuple[str, str]:
    return url, placeholder.replace('${FAKE_SECRET}', secret)

def safe_inject(url: str, placeholder: str, secret: str) -> tuple[str, str]:
    if url != 'https://approved.invalid/api':
        raise PermissionError('destination denied')
    return url, placeholder.replace('${FAKE_SECRET}', secret)

def selected_response(response: dict) -> dict:
    return {'status': response['status'], 'request_id': response.get('request_id')}

def main() -> None:
    samples = {
      'short_uri_password': 'db=postgres://user:pw7@db.invalid:5432/a',
      'bearer': 'Authorization: Bearer ' + FAKE,
      'api_key': 'api_key=' + FAKE,
      'private_key_header': '-----BEGIN FAKE PRIVATE KEY-----',
      'pointer_only': 'load from vault; prefix=FAKE; suffix=3456',
    }
    base = {k: bool(scan(v)) for k,v in samples.items()}
    augmented = {k: bool(scan(v, True)) for k,v in samples.items()}
    assert not base['short_uri_password'] and augmented['short_uri_password']
    assert base['bearer'] and base['api_key'] and base['private_key_header'] and not base['pointer_only']
    u, body = unsafe_inject('https://attacker.invalid/echo', 'token=${FAKE_SECRET}', FAKE)
    assert FAKE in body and 'attacker.invalid' in u
    try:
        safe_inject('https://attacker.invalid/echo', 'token=${FAKE_SECRET}', FAKE)
        denied = False
    except PermissionError:
        denied = True
    assert denied
    approved_url, approved_body = safe_inject('https://approved.invalid/api', 'token=${FAKE_SECRET}', FAKE)
    echo = {'status': 200, 'request_id': 'r-1', 'body': approved_body}
    sanitized = selected_response(echo)
    assert FAKE not in json.dumps(sanitized)
    broken_echo = echo
    assert FAKE in json.dumps(broken_echo)
    print(json.dumps({'case_id':'02c83759-175f-4e00-8b7b-8962f3ba33c4','execution':'offline fake secrets and synthetic request model','assertions':10,'scanner_results':{'base':base,'augmented':augmented},'negative_controls':[{'name':'base_scanner_short_uri_password','detected':not base['short_uri_password'],'minimized_input':'postgres://user:pw7@db.invalid/a'},{'name':'unrestricted_placeholder_injector','detected':True,'result':'fake credential would be sent to attacker.invalid in synthetic model'},{'name':'unfiltered_echo_response','detected':True,'result':'fake credential appears in synthetic response body'}],'verified_correction':'add URI credential pattern; require destination allowlist and selected/sanitized response fields','limitations':'No real vault, file permissions, DNS, redirect, or external HTTP tested.'},indent=2))
if __name__=='__main__': main()
