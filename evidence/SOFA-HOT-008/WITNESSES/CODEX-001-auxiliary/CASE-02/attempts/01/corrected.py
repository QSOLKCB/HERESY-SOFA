"""Synthetic request-boundary policy; no real network or credentials."""
from urllib.parse import urlsplit

def inject(api, credential, url, method='POST', payload=None):
    parsed = urlsplit(url)
    if (parsed.scheme, parsed.hostname, parsed.port, parsed.path, parsed.query,
        parsed.fragment, parsed.username, parsed.password, method) != (
        'http', '127.0.0.1', 8801, '/approved', '', '', None, None, 'POST'):
        raise ValueError('Destination or operation denied')
    response = api(url, method, credential, payload)
    if 300 <= response['status'] < 400:
        raise ValueError('Redirect denied')
    # Restrict both field names and value types. A selected string can still echo a secret.
    return {'status': response['status'] if type(response.get('status')) is int else 502,
            'ok': response.get('ok') is True}
