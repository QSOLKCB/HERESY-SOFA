"""Executable literalization of the post's under-specified missing-language order.

This is not attributed source code: the post supplied prose, not an implementation.
Choosing the first mapping key exposes the missing tie-break rule.
"""

NON_CAPTION = {"live_chat", "danmaku"}


def literal_first_policy(metadata):
    manual = [k for k in metadata.get("subtitles", {}) if k not in NON_CAPTION]
    if manual:
        return ("manual", manual[0])
    original = [
        k for k in metadata.get("automatic_captions", {})
        if k not in NON_CAPTION and k.endswith("-orig")
    ]
    if original:
        return ("automatic", original[0])
    remaining = [
        k for k in metadata.get("automatic_captions", {}) if k not in NON_CAPTION
    ]
    if len(remaining) == 1:
        return ("automatic", remaining[0])
    return None
