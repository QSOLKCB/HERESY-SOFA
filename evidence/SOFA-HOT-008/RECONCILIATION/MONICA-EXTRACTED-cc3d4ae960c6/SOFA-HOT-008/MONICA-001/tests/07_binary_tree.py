#!/usr/bin/env python3
"""Offline binary-tree audit using independent iterative reference and valid generated inputs."""
from __future__ import annotations
import json, random, sys
from dataclasses import dataclass

SEED=51120268
@dataclass
class Node:
    val:int
    left:'Node|None'=None
    right:'Node|None'=None

def submitted(descriptions):
    roots={d[0] for d in descriptions}; tree={}
    for p,c,left in descriptions:
        if p not in tree: tree[p]=[None,None]
        tree[p][0 if left else 1]=c
        roots.discard(c)
    def make(node):
        if node is None:return None
        out=Node(node)
        if node in tree:
            out.left=make(tree[node][0]);out.right=make(tree[node][1])
        return out
    return make(next(iter(roots)))

def iterative_reference(descriptions):
    nodes={}; children=set()
    for p,c,left in descriptions:
        parent=nodes.setdefault(p,Node(p)); child=nodes.setdefault(c,Node(c)); children.add(c)
        if left: parent.left=child
        else: parent.right=child
    root=next(v for v in nodes if v not in children)
    return nodes[root], nodes

def serialize(root):
    out=[]; stack=[root]
    while stack:
        n=stack.pop()
        if n is None: out.append(None); continue
        out.append(n.val); stack.extend([n.right,n.left])
    while out and out[-1] is None:out.pop()
    return out

def main():
  original=[[20,15,1],[20,17,0],[50,20,1],[50,80,0],[80,19,1]]
  original2=[[1,2,1],[2,3,0],[3,4,1]]
  rng=random.Random(SEED); shuffled=original[:];rng.shuffle(shuffled)
  assertions=0
  for x in (original,original2,shuffled):
    a=serialize(submitted(x)); b=serialize(iterative_reference(x)[0]); assert a==b;assertions+=1
  # valid 10,000-node skewed description: reference must finish; submitted recursion fails at default limit.
  n=10_000; deep=[[i,i+1,1] for i in range(1,n)]
  ref,_=iterative_reference(deep);assert ref.val==1;assertions+=1
  try: submitted(deep); recursive_failed=False
  except RecursionError: recursive_failed=True
  assert recursive_failed;assertions+=1
  # setdefault detail: default Node construction is evaluated eagerly even if existing key retained.
  made=[]
  d={1:Node(1)}
  def default(): made.append('discarded');return Node(1)
  got=d.setdefault(1,default());assert got is d[1] and made==['discarded'];assertions+=1
  print(json.dumps({'case_id':'4a28aa43-10aa-4476-b33b-85cc91998975','seed':SEED,'execution':'offline CPython generated valid trees','assertions':assertions,'original_examples_preserved':[original,original2],'negative_controls':[{'name':'recursive_depth_10000','minimized_failing_input':'a 10000-node valid left-skewed tree','detected':recursive_failed,'exception':'RecursionError at default CPython recursion limit'},{'name':'setdefault_eager_default','detected':True,'result':'factory expression constructed a discarded Node for existing key'}],'verified':'Parent/child mapping and root identification are O(n); iterative node linking avoids recursion-depth failure.','correction':'Build Node instances as descriptions are read with explicit lookup or setdefault only when accepting eager default evaluation; return root iteratively.','existing_reply_assessment':'The reply is correct about asymptotic O(n), but its lazy recursive construction is not robust for the stated 10^4-node skewed constraint.'},indent=2))
if __name__=='__main__':main()
