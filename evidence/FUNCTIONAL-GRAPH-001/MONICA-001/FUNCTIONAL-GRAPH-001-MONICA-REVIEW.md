# FUNCTIONAL-GRAPH-001 — Independent Hostile Review

## Verdict

**PASS.** The specified source identity was verified before execution: commit `42af1d99d736802214ed61ffe950e6ad809b1aee` and SHA-256 `84ff9073190b28e766df5be53dd43c833ae6e45bd0be6901704c95dd63d3ba85` for `challenges/FUNCTIONAL-GRAPH-001/run.py`. The isolated checkout remained clean after all runs. The prescribed CPython 3.14.4 canonical unittest command completed with exit code 0 and **7 tests passed**. The prescribed canonical runner completed with exit code 0 and emitted the preserved raw JSON evidence reporting **25 example assertions**, **16,739 exhaustive no-self-loop graphs**, **20,000 seeded random graphs**, and **20 benchmark records**.

This is a constrained empirical verdict. It supports correctness under the exercised functional-digraph constraints; it is not a formal proof for every input size, an online-judge result, or evidence of a universal speed winner.

## Independent challenge, not repetition

The independent harness did **not** call the repository `oracle()` function. Instead, for each start node it allocated a fresh local map of first-seen vertices, repeatedly executed the graph successor relation, and returned the count when a node first repeated. Five algorithms were compared: `signed_walk`, `edge_walk`, `indegree_peel`, `path_index`, and `reverse_graph`.

| Check family | Executed quantity | Result |
| --- | ---: | --- |
| Supplied examples | 5 graphs | All five implementations matched expected arrays |
| Additional adversarial structures | 5 graphs | All five implementations matched independent oracle |
| Exhaustive no-self-loop graphs | 16,739 (n=2 through n=6) | 83,695 comparisons; zero mismatch |
| Independent deterministic random graphs | 20,000; seed 981723; n=2 through n=60 | 100,000 comparisons; zero mismatch |
| Boundary-size graphs | 4 graphs × 100,000 nodes | All five implementations agreed; structured cases matched independently derived arrays |
| Total small-graph checks | 36,749 graphs | 183,745 algorithm comparisons; zero mismatch |

The boundary inputs covered a 100,000-node single cycle, a 100,000-node long chain entering a 2-cycle, a 100,000-node star entering a 2-cycle, and a 100,000-node deterministic random functional graph. Brute-force per-start checking was deliberately not used for the 100,000-node random graph; it was instead cross-checked between implementations. That distinction matters.

## Negative controls

The verification did not merely accept canonical outputs. Three isolated faulty implementations were run against `[1, 2, 0, 0]`, whose independently derived expected array is `[3, 3, 3, 4]`.

| Fault injected outside canonical source | Actual faulty output | Rejected? | Reason |
| --- | --- | --- | --- |
| One global visited-node scalar | `4` | Yes | Wrong output type and value; the task requires per-start values |
| One corrupt element | `[4, 3, 3, 4]` | Yes | First element differs from expected `3` |
| Wrong cycle length (labels all cycles as length 1) | `[1, 1, 1, 2]` | Yes | Fails to account for the 3-cycle |

These controls demonstrate that the independent comparator can detect both structural/output-shape errors and numerical corruption.

## 1. Is every implementation correct within the stated constraints?

**Within the exercised constraint set, yes.** There were zero mismatches in 183,745 small-graph algorithm comparisons under the independent brute-force oracle. The canonical run separately passed the expected exhaustive and random coverage. On all four 100,000-node shapes, each implementation produced an output of length 100,000 and all five agreed; the three regular shapes also matched independently derived structural answers.

The word “every” must be bounded. The experiment does not constitute a mathematical proof over all `n`, malformed edge arrays, self-loop-inclusive variants, or resource-constrained runtimes. It establishes a credible empirical witness for the declared family: finite functional digraphs with exactly one outgoing edge per node and no self-loops.

## 2. Is the signed-state implementation genuinely O(n)?

**Yes, under the stated graph model.** `signed_walk` stores state in `answer`: zero means unseen, negative one means active on the current walk, and positive means solved. The traversal itself follows the genuine adjacency transition `v = edges[v]` in `run.py:40`; it does not substitute an external event sequence.

The potential objection is `path.index(v)`. A single call can scan a path of length O(n), but it occurs only when a current, previously unseen path closes a cycle. Once processed, every node in that path receives a positive final answer and will not be appended to a new path. Consequently, the summed scan lengths over all calls are at most n. The same aggregate argument applies to `path_index`, which uses an explicit state array. Thus neither contains a hidden O(n²) behavior on functional graphs under this global finalization invariant.

| Implementation | Worst-case time | Auxiliary space, excluding input | Audit basis |
| --- | --- | --- | --- |
| `signed_walk` | O(n) | O(n) output plus O(longest path) | Each node enters one active path; total `index` scans are O(n) |
| `edge_walk` | O(n) | O(n) output, state, path | Nodes/cycles processed a constant number of times |
| `indegree_peel` | O(n) | O(n) answer, degree, queue, removal order | Kahn peel plus one cycle-labeling pass |
| `path_index` | O(n) | O(n) output, state, path | Same globally disjoint path-index argument |
| `reverse_graph` | O(n) | O(n) answer, reverse parents, sets/maps/queue | n edges; reverse propagation solves each node once |

## 3. Which implementation is most readable?

**`indegree_peel` is the most readable for a general reviewer**, even though it allocates more working structures than the signed-state approach. Its three conceptual stages—peel indegree-zero tails, label residual cycles, and unwind tails—make its invariant explicit and are familiar graph-algorithm vocabulary. `signed_walk` is the most compact algorithm with a persuasive local invariant, but it overloads the answer array as both state and result. That is elegant, yet imposes a higher review burden. `reverse_graph` is conceptually direct but operationally container-heavy; `edge_walk` is correct but its internal pop-to-cycle logic is less immediately legible.

## 4. Which uses the least additional memory on the tested workloads?

The independent `tracemalloc` measurements show no universal winner. The values below are **peak traced Python allocations during the algorithm call**, excluding input construction and not measuring total process RSS.

| Topology | Lowest traced allocation | Peak bytes | Qualification |
| --- | --- | ---: | --- |
| seeded_random | path_index | 0.022140 | signed_walk | 2,309,728 |
| one_large_cycle | signed_walk | 0.007009 | indegree_peel | 1,601,488 |
| long_chain_two_cycle | signed_walk | 0.009335 | edge_walk | 4,092,217 |
| star_two_cycle | edge_walk | 0.017642 | signed_walk | 800,576 |

The signed-state method had the lowest traced allocation on seeded random and star inputs; indegree peeling did on the one-cycle input; and `edge_walk` did on the long-chain input. `reverse_graph` was materially larger on every measured topology because it builds reverse-parent containers and uses sets/maps. These are workload-specific observations, not a general memory theorem beyond the O(n) classifications.

## 5. Which performs best on each tested topology?

For these three-repetition CPython 3.14.4 medians on this AMD EPYC workstation, the independent benchmark found:

| Topology | Fastest measured implementation | Median seconds |
| --- | --- | ---: |
| seeded_random | path_index | 0.022140 |
| one_large_cycle | signed_walk | 0.007009 |
| long_chain_two_cycle | signed_walk | 0.009335 |
| star_two_cycle | edge_walk | 0.017642 |

This result does **not** identify a universal performance winner. The canonical runner, using its own seed and shape naming, also preserved 20 timing/allocation records and found topology-dependent outcomes. Neither this review nor the historical CPython 3.13.5 report should be read as a causal interpreter performance comparison: hardware and runtime conditions were not controlled across reports.

## 6. Is there a simpler or faster implementation worth investigating?

Yes. For an implementation intended for broad maintenance, investigate an explicit local-position-map traversal that records index on entry rather than using `path.index`; it preserves an obvious cycle boundary at the cost of a per-walk dictionary. For a performance-oriented implementation, investigate a preallocated integer position array plus walk identifier, avoiding both dictionary allocation and a linear cycle lookup. It must be measured against the current `signed_walk` rather than presumed faster: the existing implementation already achieves O(n) aggregate time and was fast on two of four independent benchmark shapes.

A production-facing selection should prioritize the target environment: `indegree_peel` is an excellent clarity baseline; `signed_walk` is compact and allocation-efficient in two tested cases; `edge_walk` was best on the star; and the reverse-graph solution may be useful when reverse adjacency is independently needed elsewhere.

## 7. What evidence would be needed to support stronger claims?

Stronger correctness claims require a formal invariant proof with explicit preconditions, property-based testing with independently generated shrinkable counterexamples, self-loop and malformed-input policy tests if those are in scope, and at least one separate implementation language or runtime. Stronger performance claims require fixed hardware, pinned interpreter builds, CPU-frequency controls, substantially more repetitions, confidence intervals, per-shape distribution plots, allocation/RSS profiling, and tests across multiple `n` values. Claims relating to quantum computing, E8, or an ETQ-native advantage would require a separate, precisely defined mechanism and experiments that compare that mechanism against relevant baselines; nothing in this functional-graph audit supplies such evidence.

## ETQ claim boundary

> `signed_walk` is an adjacency-respecting functional-graph traversal. It follows `edges[v]`; it is not the ETQ-303 CRT event sequence.

This boundary is directly supported by `run.py:24-30` and `run.py:36-40`, which explicitly describe the scoped design and perform the directed successor transition. The repository documentation at `README.md:48-50` independently states that the ETQ-303 303-event CRT orbit is not an adjacency walk. The experiment therefore supports graph-theoretic correctness and local implementation measurements only. It supports no quantum-computing, E8, or ETQ-native performance claim.

## Historical comparison and publication recommendation

The historical `challenges/FUNCTIONAL-GRAPH-001/LOCAL-PYTHON-313.json` report and the present CPython 3.14.4 canonical execution agree on source SHA-256, PASS status, 25 examples, 16,739 exhaustive graphs, 20,000 canonical random graphs, 100,000-node benchmark size, three repeats, and 20 benchmark records. **No correctness contradiction was found.** Differences in raw timing are not treated as regression or improvement evidence.

The evidence is sufficient to justify a **distinct, narrowly scoped SOFA reply only if needed**: it would add an independent source-integrity check, a different seeded oracle campaign, boundary-shape coverage, negative controls, and an explicit ETQ-claim boundary. Any such reply should be self-contained, cite the repository, exact SHA, file paths, and line numbers as plain text, contain no outbound clickable links, and avoid claims beyond these executed experiments.

## Reproducibility manifest

| Artifact | Role |
| --- | --- |
| `FUNCTIONAL-GRAPH-001-MONICA-RAW.json` | Exact stdout of the prescribed canonical runner; not regenerated or edited after capture |
| `FUNCTIONAL-GRAPH-001-MONICA-REPORT.json` | Machine-readable independent synthesis including commands, exit codes, checks, benchmark samples, and limitations |
| `FUNCTIONAL-GRAPH-001-MONICA-REVIEW.md` | This hostile review |
| `independent_verify.py` / `independent_verify.json` | Separate oracle and negative-control harness/results, retained in the evidence directory |
| `independent_benchmark.py` / `independent_benchmark.json` | Separate timing and tracemalloc harness/results, retained in the evidence directory |

The three requested artifacts are externally hashed after generation. Their SHA-256 values and byte sizes appear in the final delivery message and are also recorded in the machine-readable report once final checks are complete.
