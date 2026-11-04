import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import Evidence, utc
from corrected import inject

e = Evidence(2)
# Every candidate is generated here; none comes from environment variables or user files.
fake = 'SYNTHETIC_ONLY_' + 'A9' * 24
pattern = re.compile(r'Bearer|api_key|-----BEGIN|[A-Za-z0-9+/]{32,}|[a-fA-F0-9]{32,}')
uri_pattern = r'[a-z][a-z0-9+.-]*://[^/[:space:]:]+:[^[:space:]]+@'
fixtures = {
    'token': 'Bearer ' + fake,
    'short_uri_password': 'postgres://test:xy@db.invalid:5432/demo',
    'long_path': '/tmp/' + 'projectdocumentation' * 3 + '/index.md',
    'compact_uuid': '123456781234123412341234567890ab',
    'hyphenated_uuid': '12345678-1234-1234-1234-1234567890ab',
    'pointer': 'Credential reference: vault://demo/service',
    'pointer_long_path': 'Load from /tmp/' + 'longdirectory' * 4 + '/key',
    'public_key_marker': '-----BEGIN PUBLIC KEY-----',
}
expected = dict(token=True, short_uri_password=False, long_path=True, compact_uuid=True,
                hyphenated_uuid=False, pointer=False, pointer_long_path=True, public_key_marker=True)
with tempfile.TemporaryDirectory(prefix='codex008-fakes-') as tmp:
    root = Path(tmp)
    for name, value in fixtures.items():
        path = root / (name + '.txt')
        path.write_text(value)
        e.check('token_heuristic_' + name, bool(pattern.search(value)), expected[name],
                kind='positive' if name in ('token','pointer') else 'negative')
    # Execute the reply's exact regex and -oIN flags, but NEVER persist its matching output.
    for name in ['short_uri_password','pointer','long_path']:
        argv = ['rg','-oIN',uri_pattern,str(root/(name+'.txt'))]
        start = utc()
        p = subprocess.run(argv,capture_output=True)
        e.data['commands'].append(dict(argv=argv,started_utc=start,finished_utc=utc(),exit_code=p.returncode,
            stdout='REDACTED synthetic match; values intentionally never logged',stdout_bytes=len(p.stdout),stderr=p.stderr.decode()))
        e.check('uri_regex_' + name, p.returncode, 0 if name == 'short_uri_password' else 1)
    secret_path = root/'fake-credential'
    secret_path.write_text(fake)
    secret_path.chmod(0o600)
    e.check('disposable_file_mode', stat.S_IMODE(secret_path.stat().st_mode), 0o600)
    e.check('reloaded_raw_context_contains_fake', fake in ('context: '+secret_path.read_text()), True, kind='negative')
    pointer_context = 'Load credential reference vault://demo/service'
    e.check('pointer_context_does_not_contain_fake', fake in pointer_context, False)
    destinations = []
    def api(url, method, credential, payload):
        destinations.append(url)
        if payload == 'redirect':
            return {'status':302, 'location':'http://127.0.0.1:8802/steal'}
        return {'status':200 if credential == fake else 403, 'ok':credential == fake,
                'echo':credential, 'diagnostic':credential}
    good = 'http://127.0.0.1:8801/approved'
    bad = 'http://127.0.0.1:8802/steal'
    e.check('unsubstituted_surrogate_rejected', api(good,'POST','PLACEHOLDER',None)['status'], 403)
    unrestricted = lambda url: api(url, 'POST', secret_path.read_text(), None)
    e.check('substitution_alone_authenticates', unrestricted(good)['status'], 200)
    e.check('substitution_alone_sends_to_other_destination', unrestricted(bad)['status'], 200, kind='negative')
    e.check('substitution_alone_echoes_credential', fake in json.dumps(unrestricted(good)), True, kind='negative')
    e.check('bounded_approved_request', inject(api, fake, good), {'status':200,'ok':True})
    e.check('bounded_response_has_no_fake', fake in json.dumps(inject(api,fake,good)), False)
    for label, url, method in [('origin',bad,'POST'),('path',good+'/other','POST'),('method',good,'GET'),
                               ('userinfo','http://user@127.0.0.1:8801/approved','POST'),('query',good+'?x=1','POST')]:
        before = len(destinations)
        try: inject(api,fake,url,method)
        except ValueError: denied = True
        else: denied = False
        e.check('bounded_denies_'+label, denied and len(destinations)==before, True, kind='negative')
    try: inject(api,fake,good,payload='redirect')
    except ValueError: denied=True
    else: denied=False
    e.check('bounded_refuses_redirect', denied, True, kind='negative')
    def malicious_response(*args): return {'status':fake,'ok':fake,'echo':fake}
    e.check('response_types_prevent_selected_field_echo', inject(malicious_response,fake,good), {'status':502,'ok':False}, kind='negative')
e.data['limitations'] = [dict(label='NOT_TESTED',claim="Muse's actual adapters, production environment, redirects, DNS, TLS, real memory and real credentials"),
    dict(label='INFERRED',claim='No finite pattern set proves absence of secrets; prefixes/suffixes and pointer targets also require context-sensitive review. Permission bits are not a model-context boundary.'),
    dict(label='EXECUTED',claim='Only synthetic in-process transports, generated fake credentials and disposable files were used.')]
e.finish()
