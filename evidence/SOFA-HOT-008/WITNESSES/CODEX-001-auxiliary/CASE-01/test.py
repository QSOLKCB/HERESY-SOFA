import inspect
import itertools
import json
from pathlib import Path
import socket
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import Evidence
from corrected import select

e = Evidence(1)
def t(name='x'):
    return [{'ext':'vtt', 'url':'https://captions.invalid/' + name}]
fixtures = [
 ('missing_language_uploaded', {'language':None, 'original_language':None, 'formats':[{'acodec':'aac'}], 'subtitles':{'de-DE':t()}}, ('manual','de-DE')),
 ('original_before_translations', {'automatic_captions':{'de':t(),'en-orig':t(),'fr':t()}}, ('auto','en-orig')),
 ('single_auto', {'automatic_captions':{'de-DE':t()}}, ('auto','de-DE')),
 ('translated_map_abstention', {'automatic_captions':{'de':t(),'en':t()}}, None),
 ('ambiguous_uploaded_abstention', {'subtitles':{'de':t(),'en':t()}}, None),
 ('ambiguous_originals_abstention', {'automatic_captions':{'de-orig':t(),'en-orig':t()}}, None),
 ('noncaption_and_empty', {'subtitles':{'live_chat':t(),'danmaku':t(),'de':[]}, 'automatic_captions':{'en':t()}}, ('auto','en')),
 ('noncaptions_only', {'subtitles':{'live_chat':t(),'danmaku':t()}}, None),
 ('known_exact_manual', {'language':'de-DE', 'subtitles':{'de-DE':t()}, 'automatic_captions':{'de-DE':t()}}, ('manual','de-DE')),
 ('known_exact_before_base', {'language':'de-DE','subtitles':{'de':t()},'automatic_captions':{'de-DE':t()}}, ('auto','de-DE')),
 ('known_base_manual', {'language':'de-AT','subtitles':{'de-DE':t()},'automatic_captions':{'de-orig':t()}}, ('manual','de-DE')),
 ('known_base_ambiguity', {'language':'en-AU','subtitles':{'en-GB':t(),'en-US':t()}}, None),
 ('known_language_absent', {'language':'de','subtitles':{'en':t()}}, None),
 ('audio_language', {'formats':[{'language':'de','acodec':'aac'}], 'subtitles':{'de':t(),'en':t()}}, ('manual','de')),
 ('ambiguous_audio', {'formats':[{'language':x,'acodec':'aac'} for x in ['en','de']], 'automatic_captions':{'de':t(),'en':t()}}, None),
]
for name, info, expected in fixtures:
    e.check(name, select(info), expected, kind='negative' if expected is None else 'positive')
    for key in ['subtitles','automatic_captions']:
        if key in info:
            for order in itertools.permutations(info[key]):
                reordered = dict(info, **{key: {k:info[key][k] for k in order}})
                e.check(name + '_order_' + ','.join(order), select(reordered), expected)
e.check('explicit_preference_resolves_uploaded_tie', select(fixtures[4][1], 'en'), ('manual','en'))
e.check('language_gate_misses_uploaded_caption', bool(fixtures[0][1]['language']), False, kind='negative')

try:
    import yt_dlp
    from yt_dlp import YoutubeDL
    from yt_dlp.version import __version__
except ImportError as exc:
    e.data['limitations'].append(dict(label='NOT_TESTED', claim='yt-dlp metadata processing', reason=str(exc)))
else:
    e.data['yt_dlp_version'] = __version__
    (e.folder/'installed-process_subtitles.py').write_text(inspect.getsource(YoutubeDL.process_subtitles))
    def blocked(*args, **kwargs):
        raise AssertionError('Network forbidden in this test')
    socket.socket.connect = blocked
    class Quiet:
        def debug(self, x): pass
        def warning(self, x): pass
        def error(self, x): pass
    with YoutubeDL(dict(writesubtitles=True, writeautomaticsub=True, subtitleslangs=['de-DE'], logger=Quiet())) as ydl:
        actual = ydl.process_subtitles('synthetic', {'de-DE':t('manual')}, {'de-DE':t('auto')})
        e.check('installed_selects_manual_without_video_language', actual['de-DE']['url'].endswith('/manual'), True)
    with YoutubeDL(dict(writesubtitles=False, writeautomaticsub=False, logger=Quiet())) as ydl:
        e.check('installed_no_write_flags_no_selection', ydl.process_subtitles('synthetic', {'de-DE':t()}, {}), None, kind='negative')
e.data['limitations'] += [dict(label='NOT_TESTED', claim='Remote extraction/download/conversion and YouTube -orig convention'),
                         dict(label='INFERRED', claim='The source supplies a selection policy, not code; tie abstention and caption-format filtering are examiner additions. No original implementation has been disproved.')]
e.finish()
