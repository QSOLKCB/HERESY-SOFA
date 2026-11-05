#!/usr/bin/env python3
"""Independent conservative oracle for offline caption metadata selection."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_NON_CAPTIONS = frozenset(("live_chat", "danmaku"))


def _canon(value: str) -> str:
    return value.strip().casefold()


def _without_orig(value: str) -> str:
    value = _canon(value)
    return value[:-5] if value.endswith("-orig") else value


def _base(value: str) -> str:
    return _without_orig(value).split("-", 1)[0]


def _usable_track(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for item in value:
        if not isinstance(item, Mapping):
            continue
        url = item.get("url")
        data = item.get("data")
        if (isinstance(url, str) and url.strip()) or (
            isinstance(data, str) and data
        ):
            return True
    return False


def _eligible(value: Any, origin: str) -> list[dict[str, str]]:
    if not isinstance(value, Mapping):
        return []
    candidates: list[dict[str, str]] = []
    for raw_key, formats in value.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        canonical = _canon(raw_key)
        if canonical in _NON_CAPTIONS or not _usable_track(formats):
            continue
        candidates.append(
            {
                "origin": origin,
                "language": raw_key,
                "canonical": canonical,
                "base": _base(raw_key),
                "is_original": str(canonical.endswith("-orig")).lower(),
            }
        )
    return sorted(
        candidates,
        key=lambda item: (item["canonical"], item["language"], item["origin"]),
    )


def _valid_hint(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _resolve_target(metadata: Mapping[str, Any], preferred: Any) -> dict[str, Any]:
    if preferred is not None:
        value = _valid_hint(preferred)
        if value is None:
            return {
                "target": None,
                "status": "invalid_explicit_preference",
                "hints": [],
            }
        return {
            "target": value,
            "status": "explicit_preference",
            "hints": [{"source": "preferred", "language": value}],
        }

    explicit: list[dict[str, str]] = []
    for field in ("language", "original_language"):
        value = _valid_hint(metadata.get(field))
        if value is not None:
            explicit.append({"source": field, "language": value})
    if explicit:
        bases = {_base(item["language"]) for item in explicit}
        if len(bases) != 1:
            return {
                "target": None,
                "status": "conflicting_metadata_hints",
                "hints": explicit,
            }
        preferred_source = next(
            (item for item in explicit if item["source"] == "language"),
            explicit[0],
        )
        return {
            "target": preferred_source["language"],
            "status": "metadata_language_hint",
            "hints": explicit,
        }

    audio: list[dict[str, str]] = []
    formats = metadata.get("formats")
    if isinstance(formats, list):
        for item in formats:
            if not isinstance(item, Mapping):
                continue
            language = _valid_hint(item.get("language"))
            acodec = item.get("acodec")
            if (
                language is not None
                and isinstance(acodec, str)
                and acodec.casefold() != "none"
            ):
                audio.append({"source": "audio_format", "language": language})
    unique = sorted({_canon(item["language"]) for item in audio})
    if len(unique) == 1:
        representative = next(
            item["language"] for item in audio if _canon(item["language"]) == unique[0]
        )
        return {
            "target": representative,
            "status": "unique_audio_hint",
            "hints": audio,
        }
    if len(unique) > 1:
        return {
            "target": None,
            "status": "ambiguous_audio_hints",
            "hints": audio,
        }
    return {"target": None, "status": "no_language_hint", "hints": []}


def _result(
    *,
    decision: str,
    reason: str,
    manual: list[dict[str, str]],
    automatic: list[dict[str, str]],
    hint: dict[str, Any],
    chosen: dict[str, str] | None = None,
) -> dict[str, Any]:
    selected = chosen is not None
    return {
        "decision": decision,
        "origin": chosen["origin"] if chosen else None,
        "language": chosen["language"] if chosen else None,
        "reason": reason,
        "language_resolution": hint["status"],
        "hints": hint["hints"],
        "eligible": {
            "manual": [item["language"] for item in manual],
            "automatic": [item["language"] for item in automatic],
        },
        "outcomes": {
            "METADATA_AVAILABLE": bool(manual or automatic),
            "TRACK_SELECTED": selected,
            "SUBTITLE_DOWNLOADED_AND_VERIFIED": "NOT_TESTED",
        },
    }


def select_reference(metadata: Any, preferred: Any = None) -> dict[str, Any]:
    """Return one deterministic selection or an explicit abstention.

    Ranking is exact language before base language, with manual captions ahead
    of automatic captions *within* each rank.  A tie in the best non-empty rank
    abstains; insertion order is never a tiebreaker.
    """

    if not isinstance(metadata, Mapping):
        empty_hint = {"target": None, "status": "metadata_not_mapping", "hints": []}
        return _result(
            decision="ABSTAIN",
            reason="metadata_not_mapping",
            manual=[],
            automatic=[],
            hint=empty_hint,
        )

    manual = _eligible(metadata.get("subtitles"), "manual")
    automatic = _eligible(metadata.get("automatic_captions"), "automatic")
    hint = _resolve_target(metadata, preferred)

    if hint["status"] in {
        "invalid_explicit_preference",
        "conflicting_metadata_hints",
        "ambiguous_audio_hints",
    }:
        return _result(
            decision="ABSTAIN",
            reason=hint["status"],
            manual=manual,
            automatic=automatic,
            hint=hint,
        )

    target = hint["target"]
    if target is not None:
        target_canonical = _canon(target)
        target_base = _base(target)
        ranks = (
            ("manual_exact", [item for item in manual if item["canonical"] == target_canonical]),
            ("automatic_exact", [item for item in automatic if item["canonical"] == target_canonical]),
            ("manual_base", [item for item in manual if item["base"] == target_base]),
            ("automatic_base", [item for item in automatic if item["base"] == target_base]),
        )
        for rank, candidates in ranks:
            if not candidates:
                continue
            if len(candidates) == 1:
                return _result(
                    decision="SELECT",
                    reason=rank,
                    manual=manual,
                    automatic=automatic,
                    hint=hint,
                    chosen=candidates[0],
                )
            return _result(
                decision="ABSTAIN",
                reason=f"ambiguous_{rank}",
                manual=manual,
                automatic=automatic,
                hint=hint,
            )
        reason = (
            "preferred_language_unavailable"
            if hint["status"] == "explicit_preference"
            else "target_language_unavailable"
        )
        return _result(
            decision="ABSTAIN",
            reason=reason,
            manual=manual,
            automatic=automatic,
            hint=hint,
        )

    if manual:
        if len(manual) == 1:
            return _result(
                decision="SELECT",
                reason="unique_manual_without_language",
                manual=manual,
                automatic=automatic,
                hint=hint,
                chosen=manual[0],
            )
        return _result(
            decision="ABSTAIN",
            reason="ambiguous_manual_without_language",
            manual=manual,
            automatic=automatic,
            hint=hint,
        )

    originals = [item for item in automatic if item["is_original"] == "true"]
    if originals:
        if len(originals) == 1:
            return _result(
                decision="SELECT",
                reason="unique_original_automatic",
                manual=manual,
                automatic=automatic,
                hint=hint,
                chosen=originals[0],
            )
        return _result(
            decision="ABSTAIN",
            reason="ambiguous_original_automatic",
            manual=manual,
            automatic=automatic,
            hint=hint,
        )

    if len(automatic) == 1:
        return _result(
            decision="SELECT",
            reason="single_automatic_without_language",
            manual=manual,
            automatic=automatic,
            hint=hint,
            chosen=automatic[0],
        )
    if automatic:
        return _result(
            decision="ABSTAIN",
            reason="ambiguous_automatic_without_language",
            manual=manual,
            automatic=automatic,
            hint=hint,
        )
    return _result(
        decision="ABSTAIN",
        reason="no_eligible_tracks",
        manual=manual,
        automatic=automatic,
        hint=hint,
    )
