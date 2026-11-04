"""Enumerate a finite scripted API state space; no time, network or random input."""
from collections import Counter
from email.message import Message
import io
import itertools
import json
from pathlib import Path
import sys
import urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import utc
from corrected import run

class Clock:
    now=0.
    def sleep(self,seconds):
        assert seconds>=0
        self.now+=seconds

sub_modes=['ok','once429','always429','ambiguous503','missing_job','immediate_success']
poll_modes=['success','once_pending','always_pending','error','unknown','always429','always503']
rows=[];failures=[];start=utc()
for sub_choice in itertools.product(sub_modes,repeat=3):
    for poll_mode in poll_modes:
        clock=Clock();sub_count=Counter();poll_count=Counter();live=set();events=[];maximum=[0]
        modes=dict(zip(['a','b','c'],sub_choice))
        def error(code):
            headers=Message();headers['Retry-After']='7'
            raise urllib.error.HTTPError('https://synthetic.invalid',code,'synthetic',headers,None)
        def api(url,auth,method='GET',params=None):
            assert len(events)<100,'finite request ceiling exceeded'
            if method=='POST':
                key=params['url'];sub_count[key]+=1;mode=modes[key]
                events.append(['submit',key,clock.now])
                if mode=='always429' or mode=='once429' and sub_count[key]==1:error(429)
                if mode=='ambiguous503':
                    live.add(key);maximum[0]=max(maximum[0],len(live));error(503)
                if mode=='missing_job':
                    live.add(key);maximum[0]=max(maximum[0],len(live));response={}
                elif mode=='immediate_success':response={'status':'success'}
                else:
                    live.add(key);maximum[0]=max(maximum[0],len(live));response={'job_id':key}
            else:
                key=url.rsplit('/',1)[-1];poll_count[key]+=1;events.append(['poll',key,clock.now])
                if poll_mode=='always429':error(429)
                if poll_mode=='always503':error(503)
                status='pending' if poll_mode=='always_pending' or poll_mode=='once_pending' and poll_count[key]==1 else 'success' if poll_mode in ('success','once_pending') else poll_mode
                response={'status':status}
                if status in ('success','error'):live.discard(key)
            return io.BytesIO(json.dumps(response).encode())
        try:
            tasks=run(['a','b','c'],api,clock,concurrency=2)
            properties={
              'all_inputs_accounted':set(tasks)=={'a','b','c'},
              'all_local_states_terminal':all(t['state'] not in ('queued','pending') for t in tasks.values()),
              'submission_ceiling':all(t['attempts']<=3 for t in tasks.values()),
              'poll_ceiling':all(t['polls']<=6 for t in tasks.values()),
              'no_ambiguous_resubmit':all(sub_count[u]<=1 for u in modes if modes[u]=='ambiguous503'),
              'synthetic_possible_remote_concurrency_cap':maximum[0]<=2,
            }
            passed=all(properties.values())
        except Exception as exc:
            passed=False;properties={'exception':type(exc).__name__+': '+str(exc)};tasks={}
        row=dict(submissions=sub_choice,poll_mode=poll_mode,passed=passed,properties=properties,
                 request_count=len(events),fake_elapsed=clock.now,max_possible_live=maximum[0],
                 terminal_states={u:t['state'] for u,t in tasks.items()})
        rows.append(row)
        if not passed:failures.append(dict(row=row,events=events))
receipt=dict(started_utc=start,finished_utc=utc(),label='EXECUTED',scenarios=len(rows),
             model='Three unique URLs, concurrency 2; 6^3 submit scripts x 7 poll scripts; synthetic 429 definitively rejects; synthetic 503/missing-ID may accept',
             failures=failures,all_checks_passed=not failures,results=rows,
             limitations='Finite model coverage, not a proof over arbitrary HTTP/JSON, concurrent clients or real service semantics.')
with (Path(__file__).resolve().parent/'state-space-receipt.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps({k:receipt[k] for k in ['scenarios','all_checks_passed','failures']}))
raise SystemExit(bool(failures))
