# FUNCTIONAL-GRAPH-001 — ETQ-inspired edge accounting

**State:** independently tested local algorithm audit; SOFA question reviewed; **no new reply published**. This is a community research case, **not** a newly discovered HERESY defect, a Windows/GPU investigation, or a claim about the canonical ETQ-303 operator.

The [SOFA problem](https://agents.stackoverflow.com/questions/67036c1f-629f-404e-b2f8-9622e627146a) asks for the number of distinct nodes visited from **every** start in a finite directed functional graph: `edges[v]` is the sole outgoing edge from `v`. Unlike a global reachability count, the result must be an array of length `n`.

## Audited implementation

[run.py](run.py) contains five independent implementation styles and a per-start visited-set reference oracle:

- `signed_walk`: **ETQ-inspired edge-verified finite walk**, encoding `0` unseen, `-1` active on this walk, `>0` finalized count in one array. A path stack preserves exact edge order.
- `edge_walk`: bytearray three-state walk with a separate cycle traversal.
- `indegree_peel`: remove indegree-zero tails, label residual cycles, then unwind the removed nodes in reverse topological order.
- `path_index`: locally restated version of the existing SOFA three-state path approach, which is **correct and also O(n)**.
- `reverse_graph`: locally restated version of the question's reverse-parent/queue method, which is **also correct and O(n)**, but allocates more containers.

The original other SOFA reply returns one integer, not the required per-node array; its global visit count is `4` for `[1,2,0,0]`, whereas the expected answer is `[3,3,3,4]`. It therefore does not solve this question. We do not attribute its incorrectness to the two correct replies.

### Compact signed-state solution

```python
def countVisitedNodes(edges: list[int]) -> list[int]:
    answer = [0] * len(edges)             # 0 unseen, -1 active, >0 solved
    for start in range(len(edges)):
        if answer[start]:
            continue
        path = []
        v = start
        while answer[v] == 0:
            answer[v] = -1
            path.append(v)
            v = edges[v]                  # a genuine directed graph edge

        if answer[v] == -1:               # cycle discovered in this walk
            cut = path.index(v)
            length = len(path) - cut
            for u in path[cut:]:
                answer[u] = length
            del path[cut:]

        for u in reversed(path):          # each tail has a solved successor
            answer[u] = answer[edges[u]] + 1
    return answer
```

**Proof sketch.** Every functional-graph walk either enters an already solved node or a repeated node on its current path. The repeated suffix is one directed cycle: each node in it visits exactly the cycle length. Each preceding node visits itself once plus the distinct nodes from its successor. Reverse path order makes that successor's count available. At loop completion all nodes on the current path have positive final values; no node is first visited twice globally. Each cycle is indexed once, and all discovered paths are disjoint, so even `path.index` contributes only **O(n)** aggregate time. Space is **O(n)** for the answer and longest path, with no recursion or reverse adjacency.

### ETQ boundary

This design borrows **edge-accounted traversal and deterministic checks** from the ETQ Graph Walk work in `QSOLKCB/Audio-To-Video` (`a2v/etq.py`) and `QSOLKCB/EDGEWALK`. It is **not** ETQ-303's 101×3 Cartesian graph, tensor operator, or 303-step CRT canonical event stream. That event stream is *not an adjacency walk*, and using its address permutation as the edges of an unrelated functional graph would be incorrect. `signed_walk` is a newly authored, general-purpose finite-state graph algorithm, not a canonical ETQ algorithm.

## Independently executed local checks

[LOCAL-PYTHON-313.json](LOCAL-PYTHON-313.json) records an actual local CPython **3.13.5** run, source SHA-256 `84ff9073190b28e766df5be53dd43c833ae6e45bd0be6901704c95dd63d3ba85` (matched to the exact committed `run.py` bytes).

- Five worked example fixtures: **25 assertions**.
- **16,739 exhaustive functional digraphs**, for all graphs with 2–6 nodes and no self-loops.
- **20,000 seeded random graphs**, with 2–30 nodes.
- Four 100,000-node graph shapes. Three timing repetitions per shape/algorithm; reported median time; separate tracemalloc peak Python allocations, excluding input creation.

All five algorithms agreed with the independent brute-force oracle on every small graph and produced matching results on the large shapes. This is **executed local evidence**, not a proof of correctness on every graph or an executed LeetCode judge result.

| 100,000-node shape | Signed walk | SOFA path | Indegree peel | Reverse graph |
| --- | ---: | ---: | ---: | ---: |
| Seeded random | 0.049 s | 0.078 s | **0.040 s** | 0.181 s |
| Single big cycle | 0.011 s | **0.011 s** | 0.018 s | 0.085 s |
| Long chain to 2-cycle | **0.013 s** | 0.016 s | 0.026 s | 0.080 s |
| Star to 2-cycle | **0.026 s** | 0.026 s | 0.028 s | 0.078 s |

Peak **additional traced Python allocation** on the star shape: signed-state walk **0.76 MiB** versus reverse graph **45.53 MiB**. On a single large cycle, indegree peeling and bytearray walk may use less memory than signed-state (the exact values are in the JSON report). There is no one universal winner; benchmarking controls, hardware and input topology matter. Neither traced memory nor reported wall time measures total process RSS or guarantees another Python interpreter's performance.

## Run offline

From repository root:

```sh
uv run --offline --no-managed-python python challenges/FUNCTIONAL-GRAPH-001/run.py
uv run --offline --no-managed-python python -m unittest discover -s tests -p 'test_functional_graph.py' -v

# Optional non-CI timing and memory comparisons:
uv run --offline --no-managed-python python challenges/FUNCTIONAL-GRAPH-001/run.py --benchmark
```

No Docker, Node/NPM, package downloads, cloud endpoints or optional runtime libraries. The test suite checks source identity and strict example, exhaustive, seeded random and 100,000-node regression controls. The benchmark is intentionally opt-in.

**Publication and archival boundary:** Existing SOFA answers were inspected and the correct O(n) alternative explicitly credited. A distinct, human-authorized [QSOL HERESY dual-witness reply](https://agents.stackoverflow.com/questions/67036c1f-629f-404e-b2f8-9622e627146a) was published (reply ID `871ae4a2-b826-47f6-945c-e883145e9caf`). The [immutable evidence archive](../../evidence/FUNCTIONAL-GRAPH-001/README.md) preserves the two agents' supplied original bytes and reconciliation. Monica executed in a Cloudflare-named microVM, not a verified native workstation; benchmark speed claims remain bounded to each environment. No automated posting, new HERESY case, canonical ETQ-303 event walk or universal-performance claim is implied.