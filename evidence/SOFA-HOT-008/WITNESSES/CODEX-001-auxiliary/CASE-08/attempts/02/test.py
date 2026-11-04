import ast
from collections import deque
from email.message import Message
from email.utils import formatdate
import io
import json
from pathlib import Path
import sys
import urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import Evidence
from corrected import run,retry_delay

e=Evidence(8)
class BudgetStop(Exception):pass
class Clock:
    def __init__(self):self.now=0.;self.sleeps=[]
    def sleep(self,seconds):self.sleeps.append(seconds);self.now+=seconds
class API:
    def __init__(self,clock,submissions=None,polls=None,limit=40):
        self.clock=clock;self.submissions={k:list(v) for k,v in (submissions or {}).items()}
        self.polls={k:list(v) for k,v in (polls or {}).items()};self.limit=limit
        self.events=[];self.next_id=0;self.accepted=[]
    def __call__(self,url,auth,method='GET',params=None):
        if len(self.events)>=self.limit:raise BudgetStop('bounded at '+str(self.limit)+' requests')
        submit=method=='POST';key=params['url'] if submit else url.rsplit('/',1)[-1]
        self.events.append(dict(t=self.clock.now,operation='submit' if submit else 'poll',key=key))
        outcomes=(self.submissions if submit else self.polls).get(key,[])
        if outcomes:
            outcome=outcomes.pop(0) if len(outcomes)>1 else outcomes[0]
        elif submit:
            self.next_id+=1;outcome={'job_id':'J'+str(self.next_id)}
        else:outcome={'status':'success'}
        if isinstance(outcome,tuple):
            code,after,*rest=outcome
            if rest and rest[0]=='accepted':self.accepted.append(key)
            headers=Message()
            if after is not None:headers['Retry-After']=str(after)
            raise urllib.error.HTTPError(url,code,'synthetic '+str(code),headers,io.BytesIO(b'{}'))
        if submit and outcome.get('job_id'):self.accepted.append(key)
        return io.BytesIO(json.dumps(outcome).encode())

original=e.folder/'source-da4cf061-dba9-4c01-b42c-f94e6f3b6279-block-02.py'
tree=ast.parse(original.read_text())
tree.body=[n for n in tree.body if not(isinstance(n,ast.FunctionDef) and n.name=='spn_request')]
code=compile(tree,str(original),'exec')
(e.folder/'adaptation.json').write_text(json.dumps(dict(
    original=original.name,transformation='AST removes only the ellipsis spn_request wrapper stub; the exact posted constants and loops are executed',
    globals='json, urllib, urls_to_submit, auth=None, fake time, fake spn_request, record_result collector',
    bound='BudgetStop after 40 attempted fake API calls; no real time.sleep or HTTP transport'),indent=2)+'\n')

def execute(name,urls,submissions=None,polls=None,reference=False):
    clock=Clock();api=API(clock,submissions,polls);records=[]
    state=dict(json=json,urllib=urllib,urls_to_submit=urls,auth=None,time=clock,spn_request=api,
               record_result=lambda u,s:records.append(dict(url=u,status=s)))
    exception=None;tasks=None
    try:
        if reference:tasks=run(urls,api,clock)
        else:exec(code,state)
    except Exception as exc:exception=dict(type=type(exc).__name__,message=str(exc))
    result=dict(name=name,reference=reference,events=api.events,accepted=api.accepted,records=records,
                fake_elapsed=clock.now,sleeps=clock.sleeps,exception=exception,tasks=tasks,
                remaining_inflight=state.get('inflight'),remaining_queue=state.get('queue'))
    e.data.setdefault('simulations',[]).append(result)
    return result

r=execute('positive_pending_success',['a'],polls={'J1':[{'status':'pending'},{'status':'success'}]})
e.check('original_positive_terminal',r['records'],[{'url':'a','status':{'status':'success'}}])
for status in [429,503]:
    r=execute('repeated_'+str(status),['a','b'],submissions={'b':[(status,'7')]})
    e.check('original_starves_existing_poll_'+str(status),sum(x['operation']=='poll' for x in r['events']),0,kind='negative')
    e.check('original_unbounded_retry_'+str(status),r['exception']['type'],'BudgetStop',kind='negative')
    e.check('original_ignores_Retry_After_'+str(status),set(r['sleeps'])=={900},True,kind='negative')
r=execute('transient_429',['a','b'],submissions={'b':[(429,'7'),{'job_id':'B'}]})
e.check('first_poll_delayed_by_900',next(x['t'] for x in r['events'] if x['operation']=='poll'),915.,kind='negative')
for name,response in [('error',{'status':'error'}),('unknown',{'status':'mystery'}),('missing_status',{})]:
    r=execute('original_'+name,['a'],polls={'J1':[response]})
    e.check('original_records_terminal_'+name,len(r['records']),1,kind='negative' if name!='error' else 'positive')
    e.check('original_deletes_'+name,len(r['remaining_inflight']),0,kind='negative' if name!='error' else 'positive')
for name,response in [('missing_job',{}),('existing_success',{'status':'success','timestamp':'synthetic'})]:
    r=execute(name,['a'],submissions={'a':[response]})
    e.check('original_silently_drops_'+name,len(r['records']),0,kind='negative')
r=execute('forever_pending',['a'],polls={'J1':[{'status':'pending'}]})
e.check('original_pending_has_no_ceiling',r['exception']['type'],'BudgetStop',kind='negative')
for status in [429,503]:
    r=execute('poll_http_'+str(status),['a'],polls={'J1':[(status,'7')]})
    e.check('original_poll_error_unhandled_'+str(status),r['exception']['type'],'HTTPError',kind='negative')
r=execute('duplicate_input',['a','a'])
e.check('original_duplicate_submissions',r['accepted'].count('a'),2,kind='negative')
r=execute('accepted_but_503',['a'],submissions={'a':[(503,'7','accepted'),{'job_id':'J'}]})
e.check('original_ambiguous_retry_duplicates',r['accepted'].count('a'),2,kind='negative')
r=execute('duplicate_job_id',['a','b'],submissions={'a':[{'job_id':'J'}],'b':[{'job_id':'J'}]})
e.check('original_duplicate_job_overwrites',r['records'],[{'url':'b','status':{'status':'success'}}],kind='negative')

for status in [429,503]:
    r=execute('reference_backoff_'+str(status),['a','b'],submissions={'b':[(status,'7')]},reference=True)
    e.check('reference_polls_inflight_'+str(status),any(x['operation']=='poll' and x['key']=='J1' and x['t']==15 for x in r['events']),True)
    e.check('reference_bounded_'+str(status),r['exception'],None)
    e.check('reference_retry_limit_'+str(status),r['tasks']['b']['attempts'],3 if status==429 else 1)
r=execute('reference_transient',['a','b'],submissions={'b':[(429,'7'),{'job_id':'B'}]},reference=True)
e.check('reference_retry_after_7',[x['t'] for x in r['events'] if x['operation']=='submit' and x['key']=='b'],[0.,7.])
r=execute('reference_fair_queue',['b','c'],submissions={'b':[(429,'7')]},reference=True)
e.check('reference_later_url_succeeds',r['tasks']['c']['state'],'success')
e.check('reference_poll_despite_retry',any(x['operation']=='poll' for x in r['events']),True)
for status in [429,503]:
    r=execute('reference_poll_retry_'+str(status),['a'],polls={'J1':[(status,'7')]},reference=True)
    e.check('reference_poll_retry_bounded_'+str(status),r['tasks']['a']['polls'],6)
    e.check('reference_poll_retry_7_'+str(status),[x['t'] for x in r['events'] if x['operation']=='poll'],[15.,22.,29.,36.,43.,50.])
for name,response,want in [('pending',{'status':'pending'},'error'),('success',{'status':'success'},'success'),
                            ('error',{'status':'error'},'error'),('unknown',{'status':'mystery'},'uncertain'),('missing',{},'uncertain')]:
    r=execute('reference_'+name,['a'],polls={'J1':[response]},reference=True)
    e.check('reference_explicit_state_'+name,r['tasks']['a']['state'],want)
for name,response,want in [('missing_job',{},'uncertain'),('existing_success',{'status':'success'},'success')]:
    r=execute('reference_'+name,['a'],submissions={'a':[response]},reference=True)
    e.check('reference_submission_state_'+name,r['tasks']['a']['state'],want)
r=execute('reference_duplicate_input',['a','a'],reference=True)
e.check('reference_deduplication',r['accepted'].count('a'),1)
r=execute('reference_ambiguous',['a'],submissions={'a':[(503,'7','accepted'),{'job_id':'J'}]},reference=True)
e.check('reference_avoids_ambiguous_resubmit',r['accepted'].count('a'),1)
e.check('reference_uncertain_state',r['tasks']['a']['state'],'uncertain')
r=execute('reference_collision',['a','b'],submissions={'a':[{'job_id':'J'}],'b':[{'job_id':'J'}]},reference=True)
e.check('reference_collision_preserves_first',r['tasks']['a']['state'],'success')
e.check('reference_collision_marks_second',r['tasks']['b']['state'],'uncertain')

for raw,expected in [('7',7.),(formatdate(90,usegmt=True),90.),('nonsense',30.),('-1',0.)]:
    headers=Message();headers['Retry-After']=raw
    error=urllib.error.HTTPError('https://mock.invalid',429,'synthetic',headers,None)
    e.check('retry_after_parser_'+raw,retry_delay(error,0),expected)

class CountList(list):
    shifts=0
    def pop(self,index=-1):
        if index==0:self.shifts+=len(self)-1
        return super().pop(index)
    def insert(self,index,value):
        if index==0:self.shifts+=len(self)
        return super().insert(index,value)
cost=[]
for n in [1,2,10,100,1000]:
    q=CountList(range(n))
    while q:q.pop(0)
    e.check('front_pop_shift_count_'+str(n),q.shifts,n*(n-1)//2,kind='negative')
    d=deque(range(n));operations=0
    while d:d.popleft();operations+=1
    cost.append(dict(n=n,list_pointer_shifts=q.shifts,deque_popleft_calls=operations))
q=CountList(range(100));u=q.pop(0);q.insert(0,u)
e.check('one_front_requeue_shifts_twice_remaining',q.shifts,198,kind='negative')
e.data['queue_cost']=cost
e.data['limitations']=[dict(label='NOT_TESTED',claim='Actual IA quota, concurrency, account budget, if_not_archived_within semantics or CDX verification'),
 dict(label='UNSUPPORTED',claim='Recent captures spend none of any budget, or single-digit concurrency is a controlled account ceiling'),
 dict(label='INFERRED',claim='Finite admitted work terminates under modeled statuses and ceilings. Submission 503 is uncertain; exactly-once remote execution requires service-supported idempotency or reconciliation. Large deadlines are honored in fake time, never real sleeping.')]
e.finish()
