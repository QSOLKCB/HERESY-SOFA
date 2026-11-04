#!/usr/bin/env python3
"""Offline finite-state SPN2 scheduler model; no Internet Archive request is made."""
from __future__ import annotations
import json
from collections import deque

class MockAPI:
    def __init__(self, submit_events, status_events):
        self.submit_events=deque(submit_events); self.status_events={k:deque(v) for k,v in status_events.items()}; self.submitted=[]
    def submit(self,url):
        self.submitted.append(url); return self.submit_events.popleft() if self.submit_events else {'kind':'job','job_id':'j-'+url}
    def status(self,job):
        events=self.status_events.get(job,deque([{'status':'success'}])); return events.popleft() if events else {'status':'success'}

class Scheduler:
    def __init__(self, api, urls, shared_slots, max_retries=2):
        self.api=api;self.queue=deque(urls);self.inflight={};self.results={};self.retries={u:0 for u in urls};self.shared_slots=shared_slots;self.max_retries=max_retries;self.events=[]
    def step(self):
        progressed=False
        while self.queue and len(self.inflight)<self.shared_slots:
            u=self.queue.popleft();r=self.api.submit(u);progressed=True
            if r['kind'] in {'429','503'}:
                self.retries[u]+=1;self.events.append((u,r['kind']))
                if self.retries[u]<=self.max_retries:self.queue.append(u)
                else:self.results[u]={'status':'retry_exhausted'}
            elif r['kind']=='job': self.inflight[r['job_id']]=u
            else:self.results[u]={'status':'submit_error'}
        for job,u in list(self.inflight.items()):
            s=self.api.status(job);progressed=True
            if s.get('status')=='pending':continue
            if s.get('status')=='error':self.results[u]={'status':'status_error'}
            elif s.get('status')=='success' and not s.get('result'):self.results[u]={'status':'missing_result'}
            else:self.results[u]=s
            del self.inflight[job]
        return progressed
    def run(self,limit=100):
        for _ in range(limit):
            self.step()
            if not self.queue and not self.inflight:return
        raise RuntimeError('scheduler did not terminate')

def main():
  # shared account: two uncoordinated per-process caps 3 each allow six simultaneous submits; model coordinated cap 1.
  api=MockAPI([{'kind':'429'},{'kind':'job','job_id':'a'},{'kind':'job','job_id':'b'},{'kind':'503'},{'kind':'job','job_id':'c'}],{'a':[{'status':'pending'},{'status':'success','result':'cap-a'}],'b':[{'status':'error'}],'c':[{'status':'success'}]})
  s=Scheduler(api,['u1','u2','u3'],shared_slots=1,max_retries=2);s.run()
  assert s.results['u1']['status']=='missing_result' and s.results['u2']['status']=='success' and s.results['u3']['status']=='status_error'
  assert s.retries['u1']==2 and s.retries['u2']==0 and s.retries['u3']==0
  # bounded retry prevents endless fixed-900 sleep/requeue starvation on permanent 429.
  permanent=Scheduler(MockAPI([{'kind':'429'}]*5,{}),['blocked'],shared_slots=1,max_retries=2);permanent.run();assert permanent.results['blocked']['status']=='retry_exhausted'
  # missing result is non-success, not silently recorded as captured.
  missing=Scheduler(MockAPI([{'kind':'job','job_id':'m'}],{'m':[{'status':'success'}]}),['missing'],1);missing.run();assert missing.results['missing']['status']=='missing_result'
  # Negative control math: separate per-process cap permits aggregate excess, thus does not coordinate a shared account.
  workers=2;per_process=3;account_limit=3;aggregate=workers*per_process;assert aggregate>account_limit
  print(json.dumps({'case_id':'da4cf061-dba9-4c01-b42c-f94e6f3b6279','execution':'offline deterministic finite-state mock; no Internet Archive HTTP','assertions':8,'negative_controls':[{'name':'per_process_cap_only','minimized_input':{'workers':2,'per_process_cap':3,'account_limit':3},'detected':True,'aggregate_inflight':aggregate},{'name':'unbounded_fixed_backoff_retry','detected':True,'result':'bounded retry transitions permanent 429 to retry_exhausted'},{'name':'success_without_result','detected':True,'result':'classified missing_result'}],'verified':'A shared coordinator cap plus explicit retry/status terminal states can prevent simulated aggregate overcommit and dropped/missing results.','not_verified':'Actual SPN2 policy, Retry-After semantics, if_not_archived_within behavior, account limits, real response schema, and fixed 900-second effectiveness.','correction':'Coordinate capacity per account across processes; honor Retry-After if present; add bounded retries/jitter/fair scheduling and treat submit/status/missing-result failures as explicit terminal or retryable states.','recommendation':'REPLY: existing TIL already warns per-process caps are insufficient across processes, but its code lacks shared coordination, bounded retries, status exception handling, and result validation.'},indent=2))
if __name__=='__main__':main()
