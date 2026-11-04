"""Conservative deterministic metadata-only caption selector."""

NON_CAPTION = {"live_chat", "danmaku"}


def _track_keys(mapping):
    """Accept only yt-dlp-like caption format lists and return sorted keys."""
    keys = []
    for key, formats in (mapping or {}).items():
        if key in NON_CAPTION or not isinstance(formats, list):
            continue
        if any(isinstance(item, dict) and ("url" in item or "fragments" in item)
               for item in formats):
            keys.append(key)
    return sorted(keys, key=lambda value: (value.casefold(), value))


def _base(code):
    return code.casefold().replace("_", "-").split("-", 1)[0]


def _metadata_language(metadata):
    for field in ("language", "original_language"):
        value = metadata.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    audio = {
        str(fmt["language"]).strip()
        for fmt in metadata.get("formats", [])
        if isinstance(fmt, dict)
        and fmt.get("acodec") not in (None, "none")
        and isinstance(fmt.get("language"), str)
        and str(fmt["language"]).strip()
    }
    return next(iter(audio)) if len(audio) == 1 else None


def _unique_match(keys, language):
    normalized = language.casefold().replace("_", "-")
    exact = [key for key in keys if key.casefold().replace("_", "-") == normalized]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None
    base_matches = [key for key in keys if _base(key) == _base(language)]
    return base_matches[0] if len(base_matches) == 1 else None


def select_caption(metadata):
    """Return {source, language, reason}, or abstain with an explicit reason."""
    manual = _track_keys(metadata.get("subtitles", {}))
    automatic = _track_keys(metadata.get("automatic_captions", {}))
    language = _metadata_language(metadata)

    if language:
        chosen = _unique_match(manual, language)
        if chosen:
            return {"source": "manual", "language": chosen, "reason": "known-language"}
        chosen = _unique_match(automatic, language)
        if chosen:
            return {"source": "automatic", "language": chosen, "reason": "known-language"}
        return {"source": None, "language": None, "reason": "no-unique-language-match"}

    if len(manual) == 1:
        return {"source": "manual", "language": manual[0], "reason": "sole-manual"}
    if len(manual) > 1:
        return {"source": None, "language": None, "reason": "ambiguous-manual"}

    originals = [key for key in automatic if key.endswith("-orig")]
    if len(originals) == 1:
        return {"source": "automatic", "language": originals[0], "reason": "sole-original-asr"}
    if len(originals) > 1:
        return {"source": None, "language": None, "reason": "ambiguous-original-asr"}
    if len(automatic) == 1:
        return {"source": "automatic", "language": automatic[0], "reason": "sole-automatic"}
    return {"source": None, "language": None, "reason": "no-safe-unique-choice"}
