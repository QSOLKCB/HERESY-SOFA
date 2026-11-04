"""Redacting local scanner and bounded request-boundary credential injector."""

import re
import urllib.error
import urllib.parse
import urllib.request

PLACEHOLDER = "${SYNTHETIC_CREDENTIAL_REF}"

POST_PATTERNS = {
    "bearer_label": re.compile(r"(?i)\bBearer\b"),
    "api_key_label": re.compile(r"(?i)\bapi[_-]?key\b"),
    "pem_header": re.compile(r"-----BEGIN\b"),
    "broad_long_run": re.compile(r"[A-Za-z0-9_./+=-]{32,}"),
}

REFINED_PATTERNS = {
    "bearer_value": re.compile(r"(?i)\bBearer\s+\S+"),
    "api_key_value": re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*\S+"),
    "pem_header": re.compile(r"-----BEGIN\b"),
    "credential_uri": re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:]+:[^\s@]+@", re.I),
    "unbroken_hex": re.compile(r"(?<![0-9a-f])[0-9a-f]{32,}(?![0-9a-f])", re.I),
    "unbroken_base64": re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{32,}={0,2}(?![A-Za-z0-9+/=])"),
}


def redacted_scan(text, patterns):
    """Return pattern names and counts, never matched candidate values."""
    return {name: len(regex.findall(text)) for name, regex in patterns.items()
            if regex.search(text)}


class BoundaryError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def bounded_request(url, method, body, fake_credential, allowed_origin, allowed_paths):
    parsed = urllib.parse.urlsplit(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin != allowed_origin or parsed.path not in allowed_paths:
        raise BoundaryError("destination rejected")
    if method != "POST":
        raise BoundaryError("method rejected")
    if PLACEHOLDER not in body:
        raise BoundaryError("credential placeholder missing")

    wire_body = body.replace(PLACEHOLDER, fake_credential)
    request = urllib.request.Request(
        url, data=wire_body.encode(), method=method,
        headers={"Authorization": "Bearer " + fake_credential,
                 "Content-Type": "application/json"},
    )
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=2) as response:
            # Deliberately do not return the response body.
            return {"status": response.status,
                    "request_id": response.headers.get("X-Request-ID")}
    except urllib.error.HTTPError as exc:
        # Return selected metadata only; never return or log the response body.
        return {"status": exc.code, "request_id": exc.headers.get("X-Request-ID")}
