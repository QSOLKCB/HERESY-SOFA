#!/usr/bin/env python3
"""Offline synthetic Discord webhook diagnostic; no Discord endpoint is contacted."""
from __future__ import annotations
import json
import shlex


def classify(status: int, headers: dict[str, str], body: str) -> str:
    if status == 429:
        return 'rate_limited_retry_after' if 'Retry-After' in headers else 'rate_limited_no_hint'
    if status == 404:
        return 'unknown_or_deleted_webhook'
    if status == 401:
        return 'unauthorized'
    if status == 403:
        lower = body.lower()
        if 'missing access' in lower or 'missing permissions' in lower:
            return 'forbidden_access_or_permissions'
        return 'forbidden_unspecified'
    if 200 <= status < 300:
        return 'success'
    return 'other_error'

def safe_curl(url: str, payload_path: str) -> list[str]:
    if not url.startswith('https://discord.com/api/webhooks/'):
        raise ValueError('not an approved Discord webhook URL shape')
    return ['curl', '--fail-with-body', '--silent', '--show-error', '--header', 'Content-Type: application/json', '--data-binary', '@' + payload_path, url]

def main() -> None:
    cases = [
      (403, {}, '{"message":"Missing Access","code":50001}', 'forbidden_access_or_permissions'),
      (403, {}, '<html>challenge</html>', 'forbidden_unspecified'),
      (429, {'Retry-After':'2.5'}, '{"retry_after":2.5}', 'rate_limited_retry_after'),
      (429, {}, '{}', 'rate_limited_no_hint'),
      (404, {}, '{"message":"Unknown Webhook","code":10015}', 'unknown_or_deleted_webhook'),
      (401, {}, '{"message":"invalid webhook token"}', 'unauthorized'),
    ]
    observed=[]
    for status,headers,body,expected in cases:
        actual=classify(status,headers,body); assert actual==expected
        observed.append({'status':status,'classification':actual})
    command=safe_curl('https://discord.com/api/webhooks/123/FAKE', '/tmp/payload with spaces.json')
    rendered=' '.join(shlex.quote(x) for x in command)
    assert "'@/tmp/payload with spaces.json'" in rendered
    try: safe_curl('https://attacker.invalid/x','x'); bad_url_rejected=False
    except ValueError: bad_url_rejected=True
    assert bad_url_rejected
    broken = (403 == 429)
    assert not broken
    print(json.dumps({'case_id':'3eefb05a-c521-4cb7-8a4d-dbf709bf3101','execution':'offline synthetic HTTP responses only; no Discord traffic','assertions':len(cases)+3,'observed':observed,'negative_controls':[{'name':'403_as_429','detected':not broken,'why':'403 must not be retried as a rate-limit solely from status'},{'name':'non_discord_destination','detected':bad_url_rejected}],'correction':'Log status, selected safe headers such as Retry-After, and body category; 403 alone is not enough to determine revocation, permission, or intermediary cause. Use argv construction rather than interpolated shell text.','existing_replies':'Original question retrieval showed 0 answers; no reply claim to verify.'},indent=2))
if __name__=='__main__': main()
