#!/usr/bin/env python3
"""Literal single-track implementation of the SOFA TIL's prose policy.

The TIL supplies prose, not executable source.  This examiner-authored module
intentionally makes the smallest conventional ``first matching key`` choice
where that prose does not specify a tie rule.  It is preserved as the policy
under test, not attributed to the TIL author as their implementation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


NON_CAPTION_KEYS = {"live_chat", "danmaku"}


def _ordered_keys(value: Any) -> list[str]:
    if not isinstance(value, Mapping):
        return []
    return [
        key
        for key in value
        if isinstance(key, str) and key.casefold() not in NON_CAPTION_KEYS
    ]


def _canonical(value: str) -> str:
    return value.strip().casefold()


def _base(value: str) -> str:
    canonical = _canonical(value)
    if canonical.endswith("-orig"):
        canonical = canonical[:-5]
    return canonical.split("-", 1)[0]


def _decision(
    decision: str,
    reason: str,
    origin: str | None = None,
    language: str | None = None,
) -> dict[str, str | None]:
    return {
        "decision": decision,
        "origin": origin,
        "language": language,
        "reason": reason,
    }


def select_literal(metadata: Any, preferred: Any = None) -> dict[str, str | None]:
    """Translate the posted ordering into one selected key or ``ABSTAIN``.

    Track values are not validated because the TIL does not define validity.
    Multiple candidates in a named tier are resolved by mapping iteration
    order, exposing the missing ambiguity rule under adversarial reordering.
    """

    if not isinstance(metadata, Mapping):
        return _decision("ABSTAIN", "metadata_not_mapping")

    manual = _ordered_keys(metadata.get("subtitles"))
    automatic = _ordered_keys(metadata.get("automatic_captions"))

    target: str | None = None
    if isinstance(preferred, str) and preferred.strip():
        target = preferred
    else:
        for field in ("language", "original_language"):
            candidate = metadata.get(field)
            if isinstance(candidate, str) and candidate.strip():
                target = candidate
                break
        if target is None:
            audio_languages: list[str] = []
            formats = metadata.get("formats")
            if isinstance(formats, list):
                for item in formats:
                    if not isinstance(item, Mapping):
                        continue
                    language = item.get("language")
                    acodec = item.get("acodec")
                    if (
                        isinstance(language, str)
                        and language.strip()
                        and isinstance(acodec, str)
                        and acodec.casefold() != "none"
                    ):
                        audio_languages.append(language)
            unique = sorted({_canonical(item) for item in audio_languages})
            if len(unique) == 1:
                target = audio_languages[0]

    if target is not None:
        target_canonical = _canonical(target)
        target_base = _base(target)
        for tier_name, matcher in (
            ("exact", lambda key: _canonical(key) == target_canonical),
            ("base", lambda key: _base(key) == target_base),
        ):
            for origin, keys in (("manual", manual), ("automatic", automatic)):
                matches = [key for key in keys if matcher(key)]
                if matches:
                    return _decision(
                        "SELECT",
                        f"first_{origin}_{tier_name}",
                        origin,
                        matches[0],
                    )
        return _decision("ABSTAIN", "target_language_unavailable")

    if manual:
        return _decision("SELECT", "first_manual_without_language", "manual", manual[0])

    originals = [key for key in automatic if _canonical(key).endswith("-orig")]
    if originals:
        return _decision(
            "SELECT",
            "first_original_automatic_without_language",
            "automatic",
            originals[0],
        )

    if len(automatic) == 1:
        return _decision(
            "SELECT",
            "single_automatic_without_language",
            "automatic",
            automatic[0],
        )
    return _decision("ABSTAIN", "automatic_not_unique_or_absent")
