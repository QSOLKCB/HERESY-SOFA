FUNCTIONAL-GRAPH-001 / CODEX-001 — independent workstation review

**PASS — executed.** All five algorithms passed the required source checks, canonical tests, independent correctness comparisons and negative-control gate. No candidate bug, input mutation, exception or counterexample was observed. This verdict covers the specified valid no-self-loop functional graphs and finite test coverage; the mathematical arguments below are independent source reasoning, not a formal proof certificate.

The source is QSOLKCB/HERESY-SOFA at exact detached commit 42af1d99d736802214ed61ffe950e6ad809b1aee. challenges/FUNCTIONAL-GRAPH-001/run.py has SHA-256 84ff9073190b28e766df5be53dd43c833ae6e45bd0be6901704c95dd63d3ba85 before and after execution. All four requested source files remained byte-identical. Both the original checkout and detached checkout remained clean; the original HEAD remained unchanged. No tracked file, canonical algorithm or historical evidence was edited. No push, PR, SOFA post, upload, package installation or system setting change occurred.

**Execution and independence — executed.** The final runs used the local native Ubuntu 26.04.1 LTS host, Linux 7.0.0-42-generic, x86_64, AMD Ryzen 9 5950X (16 cores / 32 logical CPUs), CPython 3.14.4 built with GCC 15.2.0, and uv 0.12.1. The installed /usr/bin/python3.14 resolved from uv --python 3.14.4. Every required Python run used --no-project --offline --no-managed-python, with PYTHONDONTWRITEBYTECODE=1 and PYTHONHASHSEED=0. Actual UTC start times, compiler/build fields, CPU affinity, microcode, memory totals, load and governor are in the report. No CPU affinity or governor was changed.

An initial tool-sandbox run was preserved in a separate preliminary directory and excluded from this final package. Its environment probe said container-other, exposing an incorrect initial native-execution assumption. The full suite was repeated outside that sandbox; both final systemd-detect-virt probes reported none. The tests and benchmark processes were sequential, never concurrent. The final evidence uses only the native repeats. This is a disclosed execution correction, not a silently replaced result.

Monica's output was not opened. The README and historical JSON were hashed without reading their conclusions or benchmark values. The mandated regression test itself automatically reads historical JSON fields to check integrity; that required behavior is explicitly disclosed. No cross-version claim or historical performance comparison is made. The canonical oracle body was excluded from displayed source inspection. The independent verifier compiles only the five original candidate function ASTs, without changing their code or importing the repository oracle, fixtures, RNG or runner.

**Correctness coverage — executed.** The committed unittest command ran seven tests and exited 0. The unmodified canonical runner with --benchmark exited 0: 25 example assertions, 16,739 exhaustive graphs, 20,000 seed-1703 random graphs and 20 benchmark rows. Its stdout is preserved byte-for-byte as FUNCTIONAL-GRAPH-001-CODEX-RAW.json; stderr was empty. Canonical stdout/stderr and exact commands/exit codes are separately preserved.

The independent audit used seed 26051103. Each starting vertex receives a newly allocated local visited set, follows only its supplied successor, and stops before adding any repeated vertex. It returns one integer per starting vertex. It does not use candidate answers to construct small-case expectations.

| Independent category | Input instances | Comparisons per algorithm |
|---|---:|---:|
| Supplied examples | 2 | 2 |
| Exhaustive n=2..6, no self-loops | 16,739 | 16,739 |
| Independent random n=2..40 | 30,000 | 30,000 |
| Small adversarial constructions | 70 | 70 |
| Relabelled small constructions | 70 | 70 |
| Boundary n=100,000 | 8 | 8 |
| Relabelled boundary n=100,000 | 8 | 8 |
| Total | 46,897 | 46,897 |

That is 234,485 candidate comparisons, excluding separate benchmark/control checks. Counts denote executed instances, not unique random graphs. Exhaustive counts by n are 1, 8, 81, 1,024 and 15,625, respectively. The random size histogram covers every n from 2 to 40; each successor is independently rejection-sampled until it differs from its origin. Graph-stream hashes bind generated fixtures for replay.

Adversarial shapes include cycles of lengths 2/3/5/7/11 in disconnected components, long tails, a descending chain that repeatedly reaches previously solved nodes, many branches merging into a shared trunk, one large cycle, many 2-cycles and a star entering a 2-cycle. Formula expectations were checked against the small oracle. The 100,000-node random shape uses a separate O(n log n) binary-lifting reference: f^n(v) identifies a cycle entry, each cycle is measured once, and powers of f locate the first k for which f^k(v)=f^(k+L)(v). That k is the tail length; the answer is k+L. This reference was checked against the fresh-set oracle on 1,070 small graphs. No O(n^2) boundary brute-force run is claimed. Large outputs were checked against independent expectations and against one another, including deterministic relabellings.

**Negative controls — executed.** On edges [1,2,0,0], the expected array is [3,3,3,4]. All four intentionally defective controls were rejected through the same output-validation function used for candidate checks.

| Control | Observed incorrect output | Observed rejection |
|---|---|---|
| NC-01 global scalar | 4 | Output is not a per-node array |
| NC-02 wrong cycle length | [4,4,4,4] | Values wrong at cycle indices 0,1,2 |
| NC-03 one changed answer | [3,3,4,4] | Value wrong at exactly index 2 |
| NC-04 shared visited state | [3,0,0,1] | Values wrong at indices 1,2,3 |

Every control also has a minimum-node-count witness [1,0], with expected [2,2]. The respective observed defective outputs are 2, [3,3], [2,3] and [2,0]. No smaller valid graph exists under n>=2/no-self-loops. Actual outputs, reasons, differing indices, minimization details and reproduction instructions are in the machine report. A control accepted by the verifier would force FAIL.

**Proof obligations — inferred from the locked source.** In a finite functional graph, a forward walk must repeat. Before its first repeat all visited vertices are distinct; the repeated vertex closes a simple cycle. A cycle vertex visits exactly that cycle's L vertices. A non-cycle vertex is absent from its successor's reachable set, so its answer is one plus its successor's answer. Applying that recurrence to a cycle without first seeding its length would be invalid.

signed_walk (run.py lines 24–49) marks unseen vertices -1, follows v=edges[v], identifies a repeated active vertex, seeds exactly the closed cycle suffix and resolves the remaining prefix in reverse order. Every active vertex becomes positive before the next outer iteration. Thus a -1 cannot belong to a previous walk. edge_walk (52–82) uses a bytearray for the equivalent 0/1/2 states and counts a complete real-edge cycle lap before popping the cycle and tail. path_index (118–142) uses a separate state list and the same current-path invariant. All three have solved successors when resolving tails, including paths that merge into an already solved component.

indegree_peel (85–115) removes precisely the acyclic part: cycle vertices cannot fall to indegree zero, while every finite non-cycle tree eventually peels. The residual graph is disjoint cycles; complete laps give their lengths. Reverse removal order then solves every tail with its successor ready. reverse_graph (145–177) constructs parents[v] only from actual edges[u]=v. Its discovery walks follow original directed edges; its propagation deliberately follows predecessor relations to perform backward dynamic programming. Local pos distinguishes this walk's cycle from globally seen vertices. All cycle vertices are marked solved before propagation, preventing erroneous cycle increments. solved prevents repeat enqueues. seen separately bounds forward discovery; a reverse-solved tail may later be forward-seen once without reusing a wrong count.

**Complexity — inferred.** The four array-based methods have worst-case aggregate Theta(n) time under the usual word-RAM/list-amortization model. signed_walk really is O(n). Each vertex enters a newly discovered path only once. There is at most one path.index call for that path, and the sum of lengths of all such paths is at most n. Even a scan near the end of a 100,000-node chain is charged once. The cycle slices, deletions and reverse-prefix passes also have O(n) aggregate length. The same argument applies to path_index; nested syntax alone does not imply quadratic work. edge_walk's additional full cycle laps collectively traverse at most n cycle vertices. indegree_peel processes each edge/queue entry a bounded number of times.

| Implementation | Time model | Worst-case auxiliary space, excluding returned answer |
|---|---|---|
| signed_walk | Theta(n), deterministic graph work with amortized lists | Theta(n), path and temporary slice |
| edge_walk | Theta(n), deterministic graph work with amortized lists | Theta(n), bytearray and path |
| indegree_peel | Theta(n), deterministic graph work with amortized lists | Theta(n), degree/order/queue |
| path_index | Theta(n), deterministic graph work with amortized lists | Theta(n), state/path/slice |
| reverse_graph | Theta(n) hash/graph operations; expected/amortized Theta(n) time | Theta(n), adjacency/sets/queue/path/positions |

reverse_graph's strict runtime claim needs a qualification: Python dict/set operations have no universal deterministic O(1) guarantee. Allowing O(n) per hash operation gives a conservative O(n^2) upper bound; this audit does not establish a tight adverse hash bound for the restricted dense integer domain. This is a complexity-model caveat, not an observed correctness defect. All five use Theta(n) space including the output and are iterative. There is no recursion-limit hazard. Python-object overhead explains the reverse representation's large measured footprint; none constructs a superlinear graph-sized data structure. The word-RAM convention treats O(log n)-bit indices/counts as words.

**Performance — executed, native workstation only.** The following values are median milliseconds over five measured calls. Inputs were allocated before timing and the identical list object was passed to all algorithms on a shape. Each output and the unchanged input were checked outside the timing window. Random uses the canonical random graph family with the independent seed/generator, not the canonical seed-1703 array.

| Shape, n=100,000 | signed_walk | edge_walk | indegree_peel | path_index | reverse_graph |
|---|---:|---:|---:|---:|---:|
| random | 15.610 | 17.024 | 21.505 | 16.337 | 81.167 |
| big_cycle | 4.958 | 9.573 | 8.869 | 5.340 | 47.336 |
| long_chain | 6.218 | 8.773 | 12.325 | 6.542 | 46.049 |
| star_2cycle | 13.817 | 13.000 | 14.380 | 14.149 | 44.458 |
| many_2cycles | 14.289 | 11.679 | 9.287 | 14.311 | 52.144 |
| mixed_disconnected_cycles | 8.360 | 11.040 | 9.969 | 8.771 | 49.794 |
| merging_branches | 15.891 | 13.848 | 14.281 | 15.787 | 46.636 |
| reverse_chain | 15.339 | 13.519 | 12.513 | 15.339 | 44.460 |

signed_walk had the lowest median on four shapes; edge_walk on star and merging branches; indegree_peel on many 2-cycles and reverse chain. reverse_graph was slower on every measured shape. This does not make any timing winner universally best, and close measurements should not be overinterpreted. For example, random signed_walk samples ranged from 14.849 to 17.150 ms, overlapping path_index's 15.390 to 20.330 ms. On reverse_chain, signed_walk and path_index had effectively equal medians. All individual samples, ranges, median absolute deviations and call ordering are retained.

Each algorithm/shape had one separately recorded warm-up, after correctness tests had already exercised the functions. Shapes and base algorithm orders were seeded and shuffled. Five rotated rounds put every algorithm in each timing position exactly once. A full gc.collect ran before each call outside timing; cyclic GC was disabled only during timed calls and restored afterwards. Result destruction was outside timing. time.perf_counter supplied the clock. There were 200 measured calls, 40 warm-ups and 40 separate memory calls. No benchmark processes overlapped. This mitigates order and collection effects but does not eliminate cache, allocator, CPU-frequency, thermal, scheduler or background-load uncertainty. Five samples are not a confidence interval; no hardware-isolated or cold-start claim is made. Canonical and independent timing protocols are separately preserved and not pooled.

**Memory — executed.** The following are separate-call tracemalloc peaks in MiB (2^20 bytes). Input arrays and expected answers were allocated before tracing. Peaks include the returned output and candidate work storage. Normal GC was enabled for these separate memory calls. These values are Python traced allocations, not process RSS or total system memory.

| Shape, n=100,000 | signed_walk | edge_walk | indegree_peel | path_index | reverse_graph |
|---|---:|---:|---:|---:|---:|
| random | 2.245 | 2.341 | 4.897 | 3.008 | 42.016 |
| big_cycle | 2.290 | 1.623 | 1.527 | 3.053 | 54.398 |
| long_chain | 4.571 | 3.903 | 5.335 | 5.334 | 50.608 |
| star_2cycle | 0.764 | 0.859 | 5.343 | 1.527 | 45.931 |
| many_2cycles | 0.764 | 0.859 | 1.527 | 1.527 | 40.604 |
| mixed_disconnected_cycles | 0.764 | 0.859 | 1.527 | 1.527 | 39.837 |
| merging_branches | 3.807 | 3.903 | 6.869 | 4.570 | 46.974 |
| reverse_chain | 3.807 | 3.903 | 5.335 | 4.570 | 44.844 |

signed_walk used the least traced peak on six of eight shapes. indegree_peel was best for the single large cycle (1,601,488 bytes); edge_walk was best for the long chain (4,092,281 bytes). Across this complete workload set, edge_walk had the lowest maximum peak: 4,092,337 bytes, versus signed_walk 4,793,328, path_index 5,593,416, indegree_peel 7,202,608 and reverse_graph 57,040,008. Thus signed_walk wins most per-shape comparisons while edge_walk demonstrates the best worst-observed peak. The reverse implementation's sets, dictionaries, predecessor containers and queue have substantial constants despite linear space.

**ETQ boundary — inspected and inferred, with an executed coordinate check.** The supported relationship is deterministic adjacency-respecting traversal and explicit accounting of visited/active/solved states. The signed-state algorithm is ETQ-inspired terminology, not an invocation of the canonical ETQ-303 operator or its 303-event sequence. No quantum, E8 or special physical performance property follows.

The separately source-locked context is QSOLKCB/Audio-To-Video commit 255794c166f70b535c3a1a8f8a6609882e9b8f17, a2v/etq.py lines 67–89 and 114–128, and QSOLKCB/EDGEWALK commit f575e2b4db2d71bfe63a8cf8af99fc3c16b9974f, edgewalk/core.py lines 123–164 plus edgewalk/etq.py. File hashes and excerpts are preserved. Audio-To-Video constructs an actual DFS edge walk with backtracking; its lifted graph edges change either site or fibre while preserving the other coordinate. EDGEWALK uses an event schedule to choose from actual neighbors; its adapter explicitly separates events from graph traversal. For addresses (i mod 101, i mod 3), all 303 consecutive transitions including wraparound change both coordinates. The independent coordinate check observed zero transitions preserving a coordinate, so none is an edge of that Cartesian-product graph. This is not validation or execution of a complete canonical ETQ bundle, and the receiver modules were inspected without importing third-party dependencies.

**Readability and contribution — auditor judgment.** indegree_peel is the most readable choice here because its peel, cycle and reverse-dependency phases state the proof structure directly, without overloaded sign meanings. signed_walk is compact and efficient; edge_walk offers a useful memory tradeoff. A distinct SOFA contribution is justified as an independent verification receipt with a different seed, an unshared oracle, observed negative controls and transparent workload-specific measurements. It does not justify a new algorithm, universal speed claim, or ETQ/quantum/E8 advantage. Any eventual contribution should cite plain-text repository names, exact commits, paths and line references, with no clickable outbound links. Nothing has been published.

**Reproducibility and remaining uncertainty.** FUNCTIONAL-GRAPH-001-CODEX-REPORT.json contains the full environment, exact commands/exit codes, canonical transcripts, source hashes, verifier hash, coverage, controls, individual timing samples, memory bytes, source reasoning, limitations and artifact identities. FUNCTIONAL-GRAPH-001-CODEX-ORACLE.py is standalone standard-library verification code; use --source for the exact detached checkout and --output for a fresh directory. Replay with the same uv flags and environment overrides; timing values will naturally vary. The native launcher is also preserved. FINALIZATION.json lists the byte sizes and SHA-256 values of the four required evidence files; SHA256SUMS.txt covers the distributable artifacts. Checksums are generated last and covered files are then left unchanged. No usernames, hostnames, private absolute workspace paths or credentials are part of the distributable evidence. Finite coverage, human source reasoning, timing uncertainty, hash-cost assumptions, unmeasured RSS and unexecuted Windows/external-judge/ETQ-bundle behavior remain explicit limits.
