"""Bounded, starvation-free mock scheduler. No claim about SPN2 service quotas.

503 on submission is ambiguous: do not blindly resubmit a possibly accepted job.
Read-only polls can retry 429/503. 429 submission rejection is assumed definite
in this synthetic protocol. Production needs a documented API contract.
"""
from collections import deque
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from enum import Enum
import json
import urllib.error

class State(str,Enum):
    QUEUED='queued'
    PENDING='pending'
    SUCCESS='success'
    ERROR='error'
    UNCERTAIN='uncertain'
    DEFERRED='deferred'

@dataclass
class Task:
    url:str
    state:State=State.QUEUED
    job:str|None=None
    deadline:float=0
    attempts:int=0
    polls:int=0
    reason:str=''

def retry_delay(error, now, fallback=30):
    value=error.headers.get('Retry-After') if error.headers else None
    if value is not None:
        try:return max(0.,float(value))
        except ValueError:
            try:return max(0.,parsedate_to_datetime(value).timestamp()-now)
            except (ValueError,TypeError,OverflowError):pass
    return fallback

def run(urls,api,clock,concurrency=3,max_attempts=3,max_polls=6,poll_interval=15):
    tasks={u:Task(u) for u in urls}  # Deduplicate exact input URLs, not semantic equivalents.
    queue=deque(tasks.values());inflight={};submission_deadline=0.;admission_closed=False
    # Every API attempt consumes one bounded task attempt or poll count.
    while queue or inflight:
        now=clock.now
        # Poll every due job before submitting anything. Submission backoff cannot starve polls.
        for job,task in list(inflight.items()):
            if task.deadline>now:continue
            task.polls+=1
            try:
                response=json.loads(api('https://web.archive.org/save/status/'+job,None).read())
            except urllib.error.HTTPError as error:
                if error.code in (429,503) and task.polls<max_polls:
                    task.deadline=now+max(1,retry_delay(error,now));continue
                task.state=State.UNCERTAIN;task.reason='poll_retry_exhausted_or_http_error'
            else:
                status=response.get('status')
                if status=='pending' and task.polls<max_polls:
                    task.deadline=now+poll_interval;continue
                if status=='success':task.state=State.SUCCESS
                elif status=='pending':task.state=State.UNCERTAIN;task.reason='poll_ceiling'
                elif status=='error':task.state=State.ERROR;task.reason='api_error'
                else:task.state=State.UNCERTAIN;task.reason='unknown_status'
            if task.state==State.UNCERTAIN:admission_closed=True
            del inflight[job]
        # At most the queue length present at entry; deque append/popleft are constant-time.
        count=len(queue)
        for _ in range(count):
            if admission_closed or len(inflight)>=concurrency or clock.now<submission_deadline:break
            task=queue.popleft();task.attempts+=1
            try:
                response=json.loads(api('https://web.archive.org/save',None,'POST',
                    {'url':task.url,'if_not_archived_within':'30d'}).read())
            except urllib.error.HTTPError as error:
                if error.code==429 and task.attempts<max_attempts:
                    submission_deadline=clock.now+max(1,retry_delay(error,clock.now))
                    queue.append(task)
                else:
                    task.state=State.UNCERTAIN if error.code==503 else State.ERROR
                    task.reason='ambiguous_submission' if error.code==503 else 'submission_retry_exhausted_or_http_error'
                    if task.state==State.UNCERTAIN:admission_closed=True
                continue
            job=response.get('job_id')
            if isinstance(job,str) and job:
                if job in inflight:
                    task.state=State.UNCERTAIN;task.reason='duplicate_job_id';admission_closed=True;continue
                task.job=job;task.state=State.PENDING;task.deadline=clock.now+poll_interval
                inflight[job]=task
            elif response.get('status')=='success':task.state=State.SUCCESS
            else:task.state=State.UNCERTAIN;task.reason='missing_job_id';admission_closed=True
        # An unknown remote outcome must not silently release capacity for new work.
        # Preserve unsubmitted tasks for reconciliation, while continuing existing polls.
        if admission_closed:
            while queue:
                task=queue.popleft();task.state=State.DEFERRED;task.reason='reconcile_uncertain_work_before_submission'
        deadlines=[t.deadline for t in inflight.values()]
        if queue and len(inflight)<concurrency:deadlines.append(max(clock.now,submission_deadline))
        if deadlines:clock.sleep(max(0,min(deadlines)-clock.now))
    return {u:dict(state=t.state.value,job=t.job,attempts=t.attempts,polls=t.polls,reason=t.reason) for u,t in tasks.items()}
