from collections import deque
from pathlib import Path
import random
import statistics
import sys
import time
from typing import List,Optional
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import Evidence,SEED
from corrected import build

e=Evidence(7)
class TreeNode:
    allocations=0
    def __init__(self,val=0,left=None,right=None):
        TreeNode.allocations+=1
        self.val,self.left,self.right=val,left,right

ns=dict(TreeNode=TreeNode,List=List,Optional=Optional)
exec(compile((e.folder/'original.py').read_text(),str(e.folder/'original.py'),'exec'),ns)
recursive=ns['Solution']().createBinaryTree
ns2=dict(TreeNode=TreeNode)
exec(compile((e.folder/'source-16a0de7c-2f41-4413-8742-109ca610fb28-block-02.py').read_text(),'posted-iterative','exec'),ns2)
iterative=lambda ds:ns2['createBinaryTree'](None,ds)
corrected=lambda ds:build(ds,TreeNode)

def chain(nodes): return [[i,i+1,1] for i in range(1,nodes)]
def structure(root):
    queue=deque([root]);edges=[];seen=set()
    while queue:
        n=queue.popleft()
        if id(n) in seen: raise AssertionError('cycle or shared node')
        seen.add(id(n))
        for left,ch in [(1,n.left),(0,n.right)]:
            if ch:
                edges.append((n.val,ch.val,left));queue.append(ch)
    return root.val,sorted(edges),len(seen)
def bfs(root):
    q=deque([root]);out=[]
    while q:
        n=q.popleft()
        out.append(n.val if n else None)
        if n: q.extend([n.left,n.right])
    while out and out[-1] is None:out.pop()
    return out

examples=[([[20,15,1],[20,17,0],[50,20,1],[50,80,0],[80,19,1]],[50,20,80,15,17,19]),
          ([[1,2,1],[2,3,0],[3,4,1]],[1,2,None,None,3,4])]
for i,(ds,expected) in enumerate(examples):
    for name,fn in [('recursive',recursive),('posted',iterative),('corrected',corrected)]:
        e.check(f'example_{i}_{name}',bfs(fn(ds)),expected)

e.data['recursion_limit_before']=sys.getrecursionlimit()
def succeeds(nodes):
    try: recursive(chain(nodes))
    except RecursionError:return False
    return True
lo,hi=2,10001
while lo<hi:
    middle=(lo+hi)//2
    if succeeds(middle):lo=middle+1
    else:hi=middle
threshold=lo
e.data['smallest_failing_chain_in_this_call_context']=dict(nodes=threshold,edges=threshold-1)
e.check('immediately_below_threshold',succeeds(threshold-1),True)
e.check('threshold_fails',succeeds(threshold),False,kind='negative')
try: recursive(chain(10001))
except RecursionError as exc:
    e.data['maximum_depth_exception']=dict(type=type(exc).__name__,message=str(exc))
    e.check('valid_maximum_depth_failure',True,True,kind='negative')
else:e.check('valid_maximum_depth_failure',False,True,kind='negative')
for name,fn in [('posted',iterative),('corrected',corrected)]:
    TreeNode.allocations=0
    root=fn(chain(10001))
    e.check(name+'_max_nodes',structure(root)[2],10001)
    e.check(name+'_max_allocations',TreeNode.allocations,20000 if name=='posted' else 10001,kind='negative' if name=='posted' else 'positive')
TreeNode.allocations=0;iterative(chain(3))
e.check('smallest_setdefault_waste_3_nodes',TreeNode.allocations,4,kind='negative')

rng=random.Random(SEED)
slots=[(1,0),(1,1)];descriptions=[]
for child in range(2,10002):
    index=rng.randrange(len(slots));parent,left=slots[index]
    slots[index]=slots[-1];slots.pop()
    descriptions.append([parent,child,left]);slots.extend([(child,0),(child,1)])
rng.shuffle(descriptions)
expected=(1,sorted(map(tuple,descriptions)),10001)
timings={}
for name,fn in [('recursive',recursive),('posted',iterative),('corrected',corrected)]:
    e.check(name+'_random_full_structure',structure(fn(descriptions))==expected,True)
    samples=[]
    for _ in range(5):
        start=time.perf_counter_ns();fn(descriptions);samples.append(time.perf_counter_ns()-start)
    timings[name]=dict(samples_ns=samples,median_ns=statistics.median(samples))
e.data['timings']=timings
e.data['timing_ratio_recursive_over_posted']=timings['recursive']['median_ns']/timings['posted']['median_ns']

for name,fn in [('recursive',recursive),('posted',iterative),('corrected',corrected)]:
    active={};recursive_entries=[];calls={}
    def profile(frame,event,arg):
        code=frame.f_code
        if code.co_name not in ('makeTree','createBinaryTree','build'):return
        if event=='call':
            if active.get(code,0):recursive_entries.append(code.co_name)
            active[code]=active.get(code,0)+1;calls[code.co_name]=calls.get(code.co_name,0)+1
        elif event=='return':active[code]=active.get(code,1)-1
    sys.setprofile(profile)
    try:fn(chain(20))
    finally:sys.setprofile(None)
    e.check(name+'_uses_recursion',bool(recursive_entries),name=='recursive')
    e.data.setdefault('profile_calls',{})[name]=calls
e.check('recursion_limit_unchanged',sys.getrecursionlimit(),e.data['recursion_limit_before'])
e.data['limitations']=[dict(label='NOT_TESTED',claim='LeetCode harness and author exact CPython 3.14.9/timing environment'),
 dict(label='INFERRED',claim='Expected O(n) hash-table behavior; setdefault still O(n) despite discarded objects. Root search is still a scan, and may inspect all descriptions. Timing is workload and environment dependent.')]
e.finish()
