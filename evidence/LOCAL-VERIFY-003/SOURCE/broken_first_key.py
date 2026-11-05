#!/usr/bin/env python3
"""Intentionally broken order-dependent selector used as a negative control."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def select_first_key(metadata: Any) -> tuple[str, str] | None:
    if not isinstance(metadata, Mapping):
        return None
    for origin, field in (("manual", "subtitles"), ("automatic", "automatic_captions")):
        tracks = metadata.get(field)
        if not isinstance(tracks, Mapping):
            continue
        for language in tracks:
            if isinstance(language, str) and language not in {"live_chat", "danmaku"}:
                return origin, language
    return None
