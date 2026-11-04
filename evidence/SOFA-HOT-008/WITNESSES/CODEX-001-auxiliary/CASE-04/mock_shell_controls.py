"""Exercise corrected shell capture with mocked curl when localhost bind is denied."""
import json
import os
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import command,utc

folder=Path(__file__).resolve().parent
receipt=dict(started_utc=utc(),commands=[],checks=[],transport='mocked curl; no sockets')
def check(name,actual,expected):receipt['checks'].append(dict(name=name,actual=actual,expected=expected,passed=actual==expected,label='EXECUTED'))
with tempfile.TemporaryDirectory(prefix='codex008-shell-mock-') as tmp:
    root=Path(tmp)
    mock=root/'curl'
    mock.write_text('''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
args=sys.argv[1:]
Path(os.environ['MOCK_ARGS']).write_text(json.dumps(args))
Path(args[args.index('--output')+1]).write_text(os.environ['MOCK_BODY'])
Path(args[args.index('--dump-header')+1]).write_text('HTTP/1.1 '+os.environ['MOCK_STATUS']+' Synthetic\\r\\nContent-Type: '+os.environ['MOCK_TYPE']+'\\r\\nRetry-After: 7\\r\\n\\r\\n')
print(os.environ['MOCK_STATUS'],end='')
''')
    mock.chmod(0o700)
    payload=root/'payload with spaces.json';payload.write_text('{"content":"synthetic"}')
    for status,ctype,body in [(403,'application/json','{"message":"synthetic denial"}'),(403,'text/html','<html>denial</html>'),
                              (404,'application/json','{}'),(429,'application/json','{"retry_after":7}'),(204,'text/plain','')]:
        url='http://127.0.0.1:8800/mock?x=a=b'
        env={**os.environ,'PATH':str(root)+':/usr/bin:/bin','WEBHOOK_URL':url,'PAYLOAD_FILE':str(payload),
             'MOCK_STATUS':str(status),'MOCK_BODY':body,'MOCK_TYPE':ctype,'MOCK_ARGS':str(root/'args.json')}
        r=command(['bash',str(folder/'corrected.sh')],env=env);receipt['commands'].append(r)
        args=json.loads((root/'args.json').read_text())
        name=str(status)+'_'+ctype
        check(name+'_exit',r['exit_code'],0)
        check(name+'_status','STATUS='+str(status) in r['stdout'],True)
        check(name+'_action','ACTION='+('rate_limit' if status==429 else 'success' if status==204 else 'investigate') in r['stdout'],True)
        check(name+'_URL_preserved',args[-1],url)
        check(name+'_JSON_header','Content-Type: application/json' in args,True)
        check(name+'_payload_path_quoted','@'+str(payload) in args,True)
        check(name+'_separate_body_and_header_files',args[args.index('--output')+1]!=args[args.index('--dump-header')+1],True)
receipt['finished_utc']=utc();receipt['all_checks_passed']=all(x['passed'] for x in receipt['checks'])
with (folder/'mock-shell-receipt.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(dict(checks=len(receipt['checks']),all_checks_passed=receipt['all_checks_passed'])))
raise SystemExit(not receipt['all_checks_passed'])
