"""Response policy over synthetic HTTP results, not a webhook client."""
import json

def classify(status, content_type, body, retry_after=None, attempts=0, ceiling=3):
    parsed = None
    if content_type.split(';')[0].strip().lower() == 'application/json':
        try: parsed = json.loads(body)
        except (ValueError,TypeError): pass
    if status == 429:
        raw = retry_after if retry_after is not None else (parsed.get('retry_after') if isinstance(parsed,dict) else None)
        try: delay = max(0.0,float(raw))
        except (ValueError,TypeError): delay = 2 ** attempts
        return {'action':'retry' if attempts < ceiling else 'stop', 'delay':delay, 'regenerate':False}
    return {'action':'success' if 200<=status<300 else 'investigate', 'delay':None,'regenerate':False}
