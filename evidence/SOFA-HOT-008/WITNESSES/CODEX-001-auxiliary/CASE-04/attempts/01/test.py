import json
import os
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import Evidence
from corrected import classify

e=Evidence(4)
original=e.folder/'source-f0fe3b78-0122-4a92-bbe8-f82802926099-block-02.sh'
with tempfile.TemporaryDirectory(prefix='codex008-webhook-') as tmp:
    root=Path(tmp)
    curl=root/'curl'
    curl.write_text('#!/usr/bin/python3\nimport json,os,sys\nfrom pathlib import Path\nPath(os.environ["MOCK_ARGS"]).write_text(json.dumps(sys.argv[1:]))\nprint(os.environ["MOCK_BODY"]+"\\n"+os.environ["MOCK_STATUS"])\n')
    curl.chmod(0o700)
    envfile=root/'synthetic.env'
    envfile.write_text('WEBHOOK_URL=http://127.0.0.1:8800/mock?q=a=b\n')
    (root/'payload.json').write_text('{"content":"synthetic only"}')
    safe=original.read_text().replace('~/.hermes/discord.env',str(envfile))
    # Only the credential-file path changes. curl is a mock executable placed first in PATH.
    safe+='\nprintf "\\nPARSED_STATUS=<%s>\\nPARSED_BODY=<%s>\\n" "$STATUS" "$BODY"\n'
    (e.folder/'adapted-local.sh').write_text(safe)
    script=root/'test.sh'
    script.write_text(safe)
    for status,body,ctype in [(403,'{"message":"forbidden"}','application/json'),
                              (403,'<html>edge denied</html>','text/html'),
                              (404,'{"message":"unknown webhook"}','application/json'),
                              (429,'{"retry_after":2}','application/json'),(403,'','text/plain')]:
        env={**os.environ,'PATH':str(root)+':/usr/bin:/bin','MOCK_ARGS':str(root/'args.json'),
             'MOCK_BODY':body,'MOCK_STATUS':str(status)}
        r=e.run(['bash',str(script)],cwd=root,env=env)
        args=json.loads((root/'args.json').read_text())
        name=str(status)+'_'+ctype
        e.check('body_erased_'+name,'PARSED_BODY=<>' in r['stdout'],True,kind='negative')
        if body:
            e.check('nonempty_body_breaks_numeric_status_'+name,'integer expression expected' in r['stderr'],True,kind='negative')
            e.check('403_regeneration_not_reached_'+name,'403 detected' in r['stdout'],False,kind='negative')
        else:
            e.check('empty_body_triggers_unjustified_regeneration','403 detected' in r['stdout'],True,kind='negative')
        e.check('URL_cut_loses_equals_'+name,'http://127.0.0.1:8800/mock?q' in args,True,kind='negative')
        e.check('explicit_json_content_type_missing_'+name,any('Content-Type:' in x for x in args),False,kind='negative')
        e.check('headers_not_captured_'+name,any(x in args for x in ['-i','-I','-D','--dump-header','--include']),False,kind='negative')
        e.check('corrected_status_policy_'+name,classify(status,ctype,body)['action'],'retry' if status==429 else 'investigate')
    (root/'a1').touch(); (root/'a2').touch()
    envfile.write_text('WEBHOOK_URL=http://127.0.0.1:8800/mock a*\n')
    e.run(['bash',str(script)],cwd=root,env=env)
    args=json.loads((root/'args.json').read_text())
    e.check('unquoted_expansion_splits_and_globs','a1' in args and 'a2' in args,True,kind='negative')
for status in [403,404,429]:
    p=classify(status,'application/json','{"retry_after":7}',retry_after='11')
    e.check('no_regeneration_'+str(status),p['regenerate'],False)
e.check('retry_after_honored',classify(429,'application/json','{}','11')['delay'],11.0)
e.check('retry_ceiling',classify(429,'application/json','{}',attempts=3)['action'],'stop',kind='negative')
e.check('204_success',classify(204,'application/json','')['action'],'success')
e.data['limitations']=[dict(label='INFERRED',claim='curl -d without explicit Content-Type uses form encoding; test directly proves the header omission, not a Discord payload response'),
 dict(label='UNSUPPORTED',claim='403 alone proves token invalidity, channel rename invalidates token, rate limits generally return 403, or webhook recreation is necessary'),
 dict(label='NOT_TESTED',claim='Actual Discord causes, current API status semantics, user-agent blocking, permissions, audit events and production shell environment'),
 dict(label='EXECUTED',claim='No real URLs or requests; the original snippet was run with only its file path adapted and curl mocked. The snippet contains a regeneration comment, not an implemented regeneration API call.')]
e.finish()
