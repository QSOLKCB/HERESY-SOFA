"""Real curl against an isolated localhost HTTP fixture, when binding is permitted."""
import http.server
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import command,utc
from corrected import classify

folder=Path(__file__).resolve().parent
e=dict(started_utc=utc(),commands=[],checks=[],limitations=[])
def check(name,actual,expected):e['checks'].append(dict(name=name,actual=actual,expected=expected,passed=actual==expected,label='EXECUTED'))
seen=[]
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        length=int(self.headers.get('Content-Length','0'))
        body=self.rfile.read(length)
        status=int(self.path.split('/')[1].split('?')[0])
        seen.append(dict(path=self.path,method=self.command,content_type=self.headers.get('Content-Type'),body_bytes=len(body)))
        html='html' in self.path
        payload=b'<html>synthetic edge denial</html>' if html else b'{"message":"synthetic","retry_after":7}'
        self.send_response(status)
        self.send_header('Content-Type','text/html' if html else 'application/json')
        if status==429:self.send_header('Retry-After','7')
        self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)

try:server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
except OSError as exc:
    e['limitations'].append(dict(label='NOT_TESTED',claim='Real curl loopback requests',type=type(exc).__name__,reason=str(exc)))
else:
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    port=server.server_address[1]
    try:
        with tempfile.TemporaryDirectory(prefix='codex008-curl-') as tmp:
            payload=Path(tmp)/'payload with spaces.json';payload.write_text('{"content":"synthetic"}')
            for status,kind in [(403,'json'),(403,'html'),(404,'json'),(429,'json'),(200,'json')]:
                url=f'http://127.0.0.1:{port}/{status}/{kind}?a=b=c'
                env={**os.environ,'WEBHOOK_URL':url,'PAYLOAD_FILE':str(payload),'NO_PROXY':'127.0.0.1','no_proxy':'127.0.0.1'}
                r=command(['bash',str(folder/'corrected.sh')],env=env);e['commands'].append(r)
                check(f'corrected_{status}_{kind}_exit',r['exit_code'],0)
                check(f'corrected_{status}_{kind}_status',f'STATUS={status}' in r['stdout'],True)
                check(f'corrected_{status}_{kind}_action',('ACTION='+('rate_limit' if status==429 else 'success' if status==200 else 'investigate')) in r['stdout'],True)
                check(f'corrected_{status}_{kind}_query_preserved',seen[-1]['path'].endswith('?a=b=c'),True)
                check(f'corrected_{status}_{kind}_request_content_type',seen[-1]['content_type'],'application/json')
            # Actual curl -d header semantics; same flag as the original, synthetic endpoint only.
            url=f'http://127.0.0.1:{port}/403/json'
            e['commands'].append(command(['curl','--noproxy','127.0.0.1','-s','-d','@'+str(payload),url]))
            check('original_data_flag_actual_content_type',seen[-1]['content_type'],'application/x-www-form-urlencoded')
            upload=Path(tmp)/'synthetic.txt';upload.write_text('synthetic file')
            e['commands'].append(command(['curl','--noproxy','127.0.0.1','-s','-F','payload_json={"content":"synthetic"}',
                                          '-F','files[0]=@'+str(upload),url]))
            check('multipart_control_has_boundary',seen[-1]['content_type'].startswith('multipart/form-data; boundary='),True)
    finally:server.shutdown();server.server_close();thread.join()
e['requests']=seen
check('json_retry_after_read',classify(429,'application/json; charset=utf-8','{"retry_after":7}')['delay'],7.0)
check('html_not_parsed_as_json',classify(429,'text/html','{"retry_after":999}')['delay'],1)
check('malformed_json_falls_back',classify(429,'application/json','not json')['delay'],1)
e['finished_utc']=utc();e['all_checks_passed']=all(x['passed'] for x in e['checks'])
with (folder/'shell-controls-receipt.json').open('x') as f:json.dump(e,f,indent=2);f.write('\n')
print(json.dumps(dict(checks=len(e['checks']),all_checks_passed=e['all_checks_passed'],limitations=e['limitations'])))
raise SystemExit(not e['all_checks_passed'])
