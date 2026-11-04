"""Conservative interpretation of My_Junie's prose, with explicit ambiguity policy.

No caption-language selection can prove a video's spoken language. A caller may
supply a preferred language; without one, tied candidates cause abstention.
"""
NON_CAPTIONS = {'live_chat', 'danmaku'}

def tracks(mapping):
    return {k: v for k, v in (mapping or {}).items()
            if k not in NON_CAPTIONS and isinstance(v, list)
            and any(isinstance(f, dict) and f.get('ext') in {'vtt','srt','ttml','srv1','srv2','srv3','json3'}
                    and (f.get('url') or f.get('data')) for f in v)}

def one(keys, origin):
    return (origin, keys[0]) if len(keys) == 1 else None

def select(info, preferred=None):
    manual, auto = tracks(info.get('subtitles')), tracks(info.get('automatic_captions'))
    language = preferred or info.get('language') or info.get('original_language')
    if not language:
        audio_languages = {f['language'] for f in info.get('formats', [])
                           if f.get('language') and f.get('acodec') not in (None, 'none')}
        language = next(iter(audio_languages)) if len(audio_languages) == 1 else None
    if language:
        # Exact code precedes base-language matches; manual wins within a tier.
        for matches in [lambda k: k == language,
                        lambda k: k.removesuffix('-orig').split('-')[0] == language.split('-')[0]]:
            for origin, mapping in [('manual', manual), ('auto', auto)]:
                keys = sorted(k for k in mapping if matches(k))
                if keys:
                    return one(keys, origin)
        return None
    if manual:
        return one(sorted(manual), 'manual')
    originals = sorted(k for k in auto if k.endswith('-orig'))
    if originals:
        return one(originals, 'auto')
    return one(sorted(auto), 'auto')
