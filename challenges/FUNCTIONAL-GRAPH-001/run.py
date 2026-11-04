#!/usr/bin/env python3
"""Deterministic functional-graph audit; ETQ-inspired edge-walk invariants.

No ETQ-303 CRT order is used as a graph walk. No network or dependencies.
The algorithms below solve a different, general n-state directed problem.
"""
from __future__ import annotations

from collections import defaultdict, deque
from itertools import product
import gc
import hashlib
import json
import platform
from pathlib import Path
import sys
import argparse
import random
import statistics
import time
import tracemalloc


def signed_walk(edges: list[int]) -> list[int]:
    """ETQ-inspired directed-edge walk, encoded in one answer array, O(n).

    Each node follows exactly edges[v]; its sign is its current state:
    0=unseen, -1=active on this walk, positive=solved visit count.
    ETQ-303's 303-event CRT orbit is deliberately NOT used here.
    """
    answer = [0] * len(edges)
    for start in range(len(edges)):
        if answer[start] != 0:
            continue
        path = []
        v = start
        while answer[v] == 0:
            answer[v] = -1
            path.append(v)
            v = edges[v]
        if answer[v] == -1:
            cycle_start = path.index(v)
            length = len(path) - cycle_start
            for node in path[cycle_start:]:
                answer[node] = length
            del path[cycle_start:]
        for node in reversed(path):
            answer[node] = answer[edges[node]] + 1
    return answer


def edge_walk(edges: list[int]) -> list[int]:
    """An ETQ-style adjacency-respecting walk with cycle accounting, O(n)."""
    n = len(edges)
    state = bytearray(n)  # 0 unseen, 1 current walk, 2 solved
    answer = [0] * n
    for start in range(n):
        if state[start]:
            continue
        path = []
        v = start
        while state[v] == 0:
            state[v] = 1
            path.append(v)
            v = edges[v]
        if state[v] == 1:
            length = 1
            u = edges[v]
            while u != v:
                length += 1
                u = edges[u]
            while path:
                u = path.pop()
                answer[u] = length
                state[u] = 2
                if u == v:
                    break
        while path:
            u = path.pop()
            answer[u] = 1 + answer[edges[u]]
            state[u] = 2
    return answer


def indegree_peel(edges: list[int]) -> list[int]:
    """Kahn peel + cycle lengths + reverse topological DP, O(n)."""
    n = len(edges)
    degree = [0] * n
    for v in edges:
        degree[v] += 1
    queue = deque(i for i, d in enumerate(degree) if d == 0)
    removed = []
    while queue:
        v = queue.popleft()
        removed.append(v)
        u = edges[v]
        degree[u] -= 1
        if degree[u] == 0:
            queue.append(u)
    answer = [0] * n
    for start in range(n):
        if degree[start] == 0 or answer[start] != 0:
            continue
        length = 1
        v = edges[start]
        while v != start:
            v = edges[v]
            length += 1
        v = start
        while answer[v] == 0:
            answer[v] = length
            v = edges[v]
    for v in reversed(removed):
        answer[v] = 1 + answer[edges[v]]
    return answer


def path_index(edges: list[int]) -> list[int]:
    """Three-state forward-walk variant of a previously published SOFA answer."""
    n = len(edges)
    state = [0] * n
    answer = [0] * n
    for start in range(n):
        if state[start]:
            continue
        path = []
        v = start
        while state[v] == 0:
            state[v] = 1
            path.append(v)
            v = edges[v]
        if state[v] == 1:
            i = path.index(v)
            length = len(path) - i
            for u in path[i:]:
                state[u] = 2
                answer[u] = length
            del path[i:]
        for u in reversed(path):
            state[u] = 2
            answer[u] = 1 + answer[edges[u]]
    return answer


def reverse_graph(edges: list[int]) -> list[int]:
    """Reverse-adjacency + cycle-seeding strategy from the question, restated."""
    n = len(edges)
    parents = defaultdict(set)
    for u, v in enumerate(edges):
        parents[v].add(u)
    seen = set()
    solved = set()
    answer = [0] * n
    q = deque()
    for start in range(n):
        v = start
        path = []
        pos = {}
        while v not in seen:
            pos[v] = len(path)
            path.append(v)
            seen.add(v)
            v = edges[v]
        if v in pos:
            cycle_length = len(path) - pos[v]
            for u in path[pos[v]:]:
                answer[u] = cycle_length
                q.append((u, cycle_length))
                solved.add(u)
        while q:
            u, value = q.popleft()
            answer[u] = value
            for p in parents[u]:
                if p not in solved:
                    solved.add(p)
                    q.append((p, value + 1))
    return answer


def oracle(edges: list[int]) -> list[int]:
    result = []
    for start in range(len(edges)):
        visited = set()
        u = start
        while u not in visited:
            visited.add(u)
            u = edges[u]
        result.append(len(visited))
    return result


CANDIDATES = {
    "signed_edge_walk": signed_walk,
    "etq_edge_walk": edge_walk,
    "indegree_peel": indegree_peel,
    "sofa_path_index": path_index,
    "reverse_graph": reverse_graph,
}


def verified_examples():
    cases = [
        ([1, 2, 0, 0], [3, 3, 3, 4]),
        ([1, 2, 3, 4, 0], [5] * 5),
        ([1, 0], [2, 2]),
        ([1, 2, 3, 4, 5, 4], [6, 5, 4, 3, 2, 2]),
        ([1, 0, 3, 2], [2] * 4),
    ]
    count = 0
    for edges, expected in cases:
        if oracle(edges) != expected:
            raise AssertionError("bad oracle fixture")
        for name, fn in CANDIDATES.items():
            if fn(edges) != expected:
                raise AssertionError((name, edges, expected, fn(edges)))
            count += 1
    return count


def exhaustive():
    count = 0
    for n in range(2, 7):
        choices = [tuple(x for x in range(n) if x != i) for i in range(n)]
        for edges in product(*choices):
            expected = oracle(edges)
            for name, fn in CANDIDATES.items():
                actual = fn(edges)
                if actual != expected:
                    raise AssertionError(f"{name} mismatch {edges}: {actual} != {expected}")
            count += 1
    return count


def random_checks():
    rng = random.Random(1703)
    count = 0
    for _ in range(20000):
        n = rng.randrange(2, 31)
        edges = [rng.randrange(n-1) for _ in range(n)]
        edges = [v+(v>=i) for i, v in enumerate(edges)]  # force no self-loops
        expected = oracle(edges)
        for name, fn in CANDIDATES.items():
            actual = fn(edges)
            if actual != expected:
                raise AssertionError(f"{name} mismatch {edges}: {actual} != {expected}")
        count += 1
    return count


def shapes(n=100000):
    rng = random.Random(1703)
    perm = list(range(n))
    rng.shuffle(perm)
    random_edges = [rng.randrange(n-1) for _ in range(n)]
    random_edges = [v+(v>=i) for i,v in enumerate(random_edges)]
    chain = list(range(1,n)) + [n-2]
    star = [1, 0] + [0]*(n-2)
    big_cycle = list(range(1,n)) + [0]
    return {"random":random_edges,"big_cycle":big_cycle,"long_chain":chain,"star_2cycle":star}


def bench(size=100000, repeats=3):
    records = []
    for shape, edges in shapes(size).items():
        expected = edge_walk(edges)
        for name, fn in CANDIDATES.items():
            times = []
            for _ in range(repeats):
                gc.collect()
                t0 = time.perf_counter()
                output = fn(edges)
                times.append(time.perf_counter() - t0)
                if output != expected:
                    raise AssertionError("benchmark output mismatch")
            gc.collect()
            tracemalloc.start()
            out = fn(edges)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            if out != expected:
                raise AssertionError("memory run mismatch")
            records.append({"shape":shape,"implementation":name,"median_seconds":round(statistics.median(times),6),"peak_extra_bytes":peak})
    return records


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", action="store_true", help="opt into 100,000-node timing and allocation comparisons")
    args = parser.parse_args(argv)
    result = {
        "schema_version": 1,
        "status": "PASS",
        "input_family": "functional digraph; one directed edge per node; no self-loops",
        "oracle": "independent per-start visited-set traversal",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "examples_assertions": verified_examples(),
        "exhaustive_graphs_n2_to_n6": exhaustive(),
        "random_graphs_seed1703": random_checks(),
        "benchmark_n": 100000 if args.benchmark else None,
        "benchmark_repeats": 3 if args.benchmark else 0,
        "benchmarks": bench() if args.benchmark else [],
        "limits": "single local CPython workstation; timings are environment-sensitive; tracemalloc excludes input allocation and process RSS; no SOFA/LeetCode judge execution",
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
