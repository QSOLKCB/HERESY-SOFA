#!/usr/bin/env python3
"""Offline synthetic audit; does not invoke yt-dlp or a video service."""
from __future__ import annotations
import json


def safe_select(meta: dict) -> str | None:
    language = meta.get('language') or meta.get('original_language')
    manual = {k: v for k, v in meta.get('subtitles', {}).items() if k not in {'live_chat', 'danmaku'}}
    automatic = {k: v for k, v in meta.get('automatic_captions', {}).items() if k not in {'live_chat', 'danmaku'}}
    def match(keys):
        if not language:
            return None
        if language in keys:
            return language
        base = language.split('-')[0]
        return next((k for k in keys if k.split('-')[0] == base), None)
    return match(manual) or match(automatic) or next(iter(manual), None) or next((k for k in automatic if k.endswith('-orig')), None) or (next(iter(automatic)) if len(automatic) == 1 else None)


def broken_first_auto(meta: dict) -> str | None:
    """Negative control: an unordered/first automatic fallback can select translation."""
    auto = meta.get('automatic_captions', {})
    return next(iter(auto), None)


def main() -> None:
    cases = [
        ('missing_video_language_manual_exists', {'language': None, 'original_language': None, 'subtitles': {'de-DE': [{}]}, 'automatic_captions': {}}, 'de-DE'),
        ('missing_video_language_prefers_orig_auto', {'language': None, 'subtitles': {}, 'automatic_captions': {'es': [{}], 'en-orig': [{}], 'fr': [{}]}}, 'en-orig'),
        ('missing_video_language_ambiguous_automatic_declines', {'language': None, 'subtitles': {}, 'automatic_captions': {'es': [{}], 'fr': [{}]}}, None),
        ('language_match_manual_over_auto', {'language': 'de-AT', 'subtitles': {'de-DE': [{}]}, 'automatic_captions': {'de-AT': [{}]}}, 'de-DE'),
        ('filters_non_caption_keys', {'language': None, 'subtitles': {'live_chat': [{}], 'danmaku': [{}]}, 'automatic_captions': {'en-orig': [{}]}}, 'en-orig'),
    ]
    outcomes = []
    for name, meta, expected in cases:
        actual = safe_select(meta)
        assert actual == expected, (name, expected, actual)
        outcomes.append({'case': name, 'expected': expected, 'actual': actual})
    counter = cases[1][1]
    wrong = broken_first_auto(counter)
    assert wrong == 'es' and wrong != safe_select(counter)
    print(json.dumps({'case_id': '1587d009-5e9c-4cac-81fb-bf3acf5aaf49', 'execution': 'offline synthetic metadata only', 'yt_dlp_installed': False, 'assertions': len(cases) + 1, 'outcomes': outcomes, 'negative_control': {'name': 'first_automatic_fallback', 'minimized_input': {'automatic_captions_keys': list(counter['automatic_captions'])}, 'actual': wrong, 'expected': 'en-orig', 'detected': True}, 'conclusion': 'Synthetic counterexamples verify that absent video language can coexist with caption keys and that first-auto fallback can silently select a translation. Real yt-dlp extractor integration is NOT_TESTED.'}, indent=2))

if __name__ == '__main__':
    main()
