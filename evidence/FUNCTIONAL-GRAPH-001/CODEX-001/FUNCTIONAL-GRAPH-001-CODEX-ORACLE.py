#!/usr/bin/env python3
"""CODEX-001 independent functional-graph verifier. Python standard library only.

Replay from a detached checkout using Python 3.14.4:
  uv run --no-project --offline --no-managed-python --python 3.14.4 python \
    <EVIDENCE>/FUNCTIONAL-GRAPH-001-CODEX-ORACLE.py \
    --source . --output <NEW_EMPTY_DIRECTORY>

Only the five unchanged candidate function ASTs are compiled from locked run.py.
The repository oracle, fixtures, RNG, runner and historical report are not loaded.
All output files are exclusive-create. No network, dependencies or recursion.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
import gc
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time
import tracemalloc

COMMIT = '42af1d99d736802214ed61ffe950e6ad809b1aee'
SOURCE_SHA = '84ff9073190b28e766df5be53dd43c833ae6e45bd0be6901704c95dd63d3ba85'
SEED = 26051103
NAMES = ('signed_walk', 'edge_walk', 'indegree_peel', 'path_index', 'reverse_graph')


def reference_walk_counts(successors):
    """Independent O(n^2) worst-case oracle; new local set for EVERY origin."""
    counts = []
    for origin in range(len(successors)):
        encountered = set()
        cursor = origin
        while cursor not in encountered:
            encountered.add(cursor)
            cursor = successors[cursor]
        counts.append(len(encountered))
    return counts


def binary_lifting_counts(edges):
    """Separate O(n log n) reference for large RANDOM inputs, not brute force.

    f^n(v) is on v's eventual cycle. Measure each such cycle once. With its
    length L, f^k(v) == f^(k+L)(v) first holds at the tail length mu. Binary
    lifting finds mu without per-start traversal; answer = mu + L.
    """
    n = len(edges)
    levels = [list(edges)]
    for _ in range(1, n.bit_length()):
        previous = levels[-1]
        levels.append([previous[previous[v]] for v in range(n)])

    def advance(v, distance):
        bit = 0
        while distance:
            if distance & 1:
                v = levels[bit][v]
            distance >>= 1
            bit += 1
        return v

    endpoints = [advance(v, n) for v in range(n)]
    cycle_lengths = {}
    for entry in endpoints:
        if entry in cycle_lengths:
            continue
        members = [entry]
        cursor = edges[entry]
        while cursor != entry:
            members.append(cursor)
            cursor = edges[cursor]
            if len(members) > n:
                raise AssertionError('binary lifting endpoint did not enter a cycle')
        for node in members:
            cycle_lengths[node] = len(members)
    answers = []
    for v in range(n):
        length = cycle_lengths[endpoints[v]]
        a, b = v, advance(v, length)
        if a == b:
            answers.append(length)
            continue
        distance = 0
        for bit in range(len(levels) - 1, -1, -1):
            row = levels[bit]
            if row[a] != row[b]:
                a, b = row[a], row[b]
                distance += 1 << bit
        answers.append(distance + 1 + length)
    return answers


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':')).encode()).hexdigest()


def write_json(directory, name, value):
    with (directory / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def valid_graph(edges):
    return len(edges) >= 2 and all(type(v) is int and 0 <= v < len(edges) and v != i
                                   for i, v in enumerate(edges))


def rejection(actual, expected):
    if type(actual) is not list:
        return 'output_not_per_node_array'
    if len(actual) != len(expected):
        return 'wrong_array_length'
    if any(type(v) is not int for v in actual):
        return 'non_integer_answer'
    if actual != expected:
        return 'per_node_value_mismatch'
    return None


def load_candidates(source):
    file = source / 'challenges/FUNCTIONAL-GRAPH-001/run.py'
    raw = file.read_bytes()
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    detached = subprocess.run(['git', '-C', str(source), 'symbolic-ref', '-q', 'HEAD'],
                              capture_output=True).returncode == 1
    if commit != COMMIT or hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise RuntimeError('BLOCKED_SOURCE_MISMATCH')
    if not detached:
        raise RuntimeError('source must be a detached Git worktree')
    parsed = ast.parse(raw.decode('utf-8'))
    functions = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in NAMES]
    if set(node.name for node in functions) != set(NAMES) or len(functions) != 5:
        raise RuntimeError('candidate extraction failed')
    namespace = {'defaultdict': defaultdict, 'deque': deque}
    # Original AST nodes and line locations are retained without any rewriting.
    exec(compile(ast.Module(body=functions, type_ignores=[]), 'locked_run.py', 'exec'), namespace)
    metadata = {'commit': commit, 'sha256': hashlib.sha256(raw).hexdigest(), 'detached': detached,
                'candidate_loading': 'Unchanged AST function definitions only; canonical oracle not imported.',
                'functions': {node.name: {'first_line': node.lineno, 'last_line': node.end_lineno,
                    'source_segment_sha256': hashlib.sha256(ast.get_source_segment(raw.decode(), node).encode()).hexdigest()}
                    for node in functions}}
    return {name: namespace[name] for name in NAMES}, metadata


def no_loop_random(n, rng):
    edges = []
    for vertex in range(n):
        target = rng.randrange(n)
        while target == vertex:
            target = rng.randrange(n)
        edges.append(target)
    return edges


def constructed_shapes(n):
    assert n >= 2
    shapes = {
        'big_cycle': (list(range(1, n)) + [0], [n] * n,
                      'One cycle contains all n nodes; every answer is n.'),
        'long_chain': (list(range(1, n)) + [n - 2],
                       [n - i if i < n - 2 else 2 for i in range(n)],
                       'Nodes 0..n-3 have distance n-2-i to a 2-cycle; distance + 2.'),
        'star_2cycle': ([1, 0] + [0] * (n - 2), [2, 2] + [3] * (n - 2),
                        'Cycle nodes 0 and 1 have 2; every leaf has 1+2.'),
        'reverse_chain': ([1, 0] + list(range(1, n - 1)), [2, 2] + list(range(3, n + 1)),
                          'Cycle 0<->1 is solved first; node i>=2 has distance i-1, answer i+1.'),
    }
    pairs = [i ^ 1 for i in range(n - n % 2)]
    pair_answers = [2] * len(pairs)
    if n % 2:
        pairs.append(0)
        pair_answers.append(3)
    shapes['many_2cycles'] = (pairs, pair_answers, 'Disjoint 2-cycles; an odd final vertex is a tail into the first cycle.')
    edges, answers = [], []
    for length in itertools.cycle((2, 3, 5, 7, 11)):
        remaining = n - len(edges)
        if not remaining:
            break
        if remaining == 1:
            edges.append(0)
            answers.append(3)
            break
        length = min(length, remaining)
        base = len(edges)
        edges.extend(list(range(base + 1, base + length)) + [base])
        answers.extend([length] * length)
    shapes['mixed_disconnected_cycles'] = (edges, answers, 'Repeated disjoint cycles of lengths 2,3,5,7,11; final truncated cycle or 1-node tail.')
    trunk = max(1, n // 2 - 1)
    merge = [1, 0] + [i - 1 for i in range(2, trunk + 1)] + [trunk] * (n - trunk - 1)
    expected = [2, 2] + [i + 1 for i in range(2, trunk + 1)] + [trunk + 2] * (n - trunk - 1)
    shapes['merging_branches'] = (merge, expected, 'Shared descending trunk reaches cycle 0<->1; leaves all enter its last vertex.')
    return shapes


def relabel(edges, expected, rng):
    mapping = list(range(len(edges)))
    rng.shuffle(mapping)
    new_edges, new_answers = [0] * len(edges), [0] * len(edges)
    for old, new in enumerate(mapping):
        new_edges[new] = mapping[edges[old]]
        new_answers[new] = expected[old]
    return new_edges, new_answers


# Deliberately incorrect implementations, wholly outside canonical code.
def nc_scalar(edges):
    global_seen = set()
    for start in range(len(edges)):
        cursor = start
        while cursor not in global_seen:
            global_seen.add(cursor)
            cursor = edges[cursor]
    return len(global_seen)


def nc_cycle_corruption(edges):
    answers = reference_walk_counts(edges)
    for start in range(len(edges)):
        local = set()
        cursor = start
        while cursor not in local:
            local.add(cursor)
            cursor = edges[cursor]
        if cursor == start:  # Exactly the cycle vertices receive length + 1.
            answers[start] += 1
    return answers


def nc_answer_corruption(edges):
    answers = reference_walk_counts(edges)
    answers[len(edges) // 2] += 1  # Exactly one element changes.
    return answers


def nc_state_confusion(edges):
    visited = set()  # BUG: incorrectly shared between starting walks.
    answers = []
    for start in range(len(edges)):
        count, cursor = 0, start
        while cursor not in visited:
            visited.add(cursor)
            count += 1
            cursor = edges[cursor]
        answers.append(count)
    return answers


def minimize_failure(fn, edges):
    """First find any minimum-size n<=4 witness; otherwise shrink by deletion.

    On larger failures, deletion redirects incoming arcs through the removed
    vertex, rejecting resulting self-loops. A local minimum is labelled honestly.
    """
    def fails(graph):
        try:
            return rejection(fn(list(graph)), reference_walk_counts(graph)) is not None
        except Exception:
            return True
    for n in range(2, min(4, len(edges)) + 1):
        choices = [[v for v in range(n) if v != i] for i in range(n)]
        for trial in itertools.product(*choices):
            if fails(trial):
                graph = list(trial)
                return graph, 'Minimum node count; exhaustive no-self-loop search in ascending n.'
    current = list(edges)
    if len(current) > 200:
        return current, 'No n<=4 witness; large original preserved, deletion minimization not practical.'
    changed = True
    while changed and len(current) > 2:
        changed = False
        for removed in range(len(current)):
            trial = []
            for i, target in enumerate(current):
                if i == removed:
                    continue
                if target == removed:
                    target = current[removed]
                trial.append(target - (target > removed))
            if valid_graph(trial) and fails(trial):
                current, changed = trial, True
                break
    return current, 'Locally minimal under valid single-vertex bypass deletion; no global claim.'


def negative_controls():
    fixture = [1, 2, 0, 0]
    expected = reference_walk_counts(fixture)
    records = []
    controls = [('NC-01', nc_scalar, 'output_not_per_node_array'),
                ('NC-02', nc_cycle_corruption, 'per_node_value_mismatch'),
                ('NC-03', nc_answer_corruption, 'per_node_value_mismatch'),
                ('NC-04', nc_state_confusion, 'per_node_value_mismatch')]
    for name, fn, reason in controls:
        actual = fn(fixture)
        observed = rejection(actual, expected)
        minimized, method = minimize_failure(fn, fixture)
        details = {'id': name, 'implementation': fn.__name__, 'edges': fixture,
                   'expected': expected, 'actual': actual, 'expected_rejection': reason,
                   'observed_rejection': observed, 'rejected_as_expected': observed == reason,
                   'minimized_edges': minimized, 'minimized_expected': reference_walk_counts(minimized),
                   'minimized_actual': fn(minimized), 'minimization': method, 'seed': SEED,
                   'reproduction': 'Run this program with --controls-only --source <DETACHED_WORKTREE> --output <NEW_DIRECTORY>.'}
        if type(actual) is list:
            details['differing_indices'] = [i for i in range(len(expected)) if actual[i] != expected[i]]
        if name == 'NC-03':
            details['exactly_one_modified'] = len(details['differing_indices']) == 1
            details['rejected_as_expected'] &= details['exactly_one_modified']
        records.append(details)
    return records


class Auditor:
    def __init__(self, functions, output):
        self.functions, self.output = functions, output
        self.graphs = Counter()
        self.comparisons = Counter()
        self.hashes = defaultdict(hashlib.sha256)
        self.mismatches = []

    def check(self, label, edges, expected):
        if not valid_graph(edges):
            raise AssertionError('invalid independent fixture: ' + label)
        if len(expected) != len(edges):
            raise AssertionError('invalid independent expectation')
        original = edges.copy()
        self.graphs[label] += 1
        self.hashes[label].update(json.dumps(edges, separators=(',', ':')).encode() + b'\n')
        first = None
        for name, fn in self.functions.items():
            error = None
            try:
                actual = fn(edges)
            except Exception as exc:
                actual, error = None, {'type': type(exc).__name__, 'message': str(exc)}
            reason = 'exception' if error else rejection(actual, expected)
            if edges != original:
                reason = 'input_mutation'
            if reason:
                minimized, method = minimize_failure(fn, original)
                try:
                    small_actual = fn(minimized)
                except Exception as exc:
                    small_actual = {'exception_type': type(exc).__name__, 'message': str(exc)}
                record = {'algorithm': name, 'label': label, 'seed': SEED, 'edges': original,
                          'expected': expected, 'actual': actual, 'reason': reason, 'exception': error,
                          'minimized_edges': minimized, 'minimized_expected': reference_walk_counts(minimized),
                          'minimized_actual': small_actual, 'minimization': method,
                          'reproduction': 'Run with --replay-json ' + f'mismatch-{len(self.mismatches)+1}.json'}
                self.mismatches.append(record)
                write_json(self.output, f'mismatch-{len(self.mismatches)}.json', record)
                raise AssertionError('candidate failure: ' + name + ' / ' + label)
            if first is not None and actual != first:
                raise AssertionError('cross-algorithm disagreement')
            first = actual
            self.comparisons[name] += 1
        assert edges == original

    def summary(self):
        return {'graphs_by_category': dict(self.graphs), 'total_graphs': sum(self.graphs.values()),
                'candidate_comparisons': dict(self.comparisons), 'total_candidate_comparisons': sum(self.comparisons.values()),
                'graph_stream_sha256': {k: v.hexdigest() for k, v in self.hashes.items()},
                'mismatches': self.mismatches}


def correctness(audit):
    examples = [([1, 2, 0, 0], [3, 3, 3, 4]), ([1, 2, 3, 4, 0], [5] * 5)]
    for edges, expected in examples:
        assert reference_walk_counts(edges) == expected
        audit.check('supplied_examples', edges, expected)
    exhaustive_counts = {}
    for n in range(2, 7):
        count = 0
        choices = [[v for v in range(n) if i != v] for i in range(n)]
        for sequence in itertools.product(*choices):
            edges = list(sequence)
            audit.check('exhaustive', edges, reference_walk_counts(edges))
            count += 1
        assert count == (n - 1) ** n
        exhaustive_counts[str(n)] = count
    print('Exhaustive n=2..6 complete: 16,739 graphs.', flush=True)
    rng = random.Random(SEED)
    sizes = Counter()
    lifting_checks = 0
    for case in range(30000):
        n = rng.randint(2, 40)
        edges = no_loop_random(n, rng)
        expected = reference_walk_counts(edges)
        audit.check('independent_random', edges, expected)
        sizes[n] += 1
        if case < 1000:
            assert binary_lifting_counts(edges) == expected
            lifting_checks += 1
    print('Independent random complete: 30,000 graphs, seed 26051103.', flush=True)
    permutation_rng = random.Random(SEED)
    formulas = {}
    for n in (2, 3, 4, 5, 6, 7, 8, 13, 25, 40):
        for label, (edges, expected, explanation) in constructed_shapes(n).items():
            assert reference_walk_counts(edges) == expected
            assert binary_lifting_counts(edges) == expected
            lifting_checks += 1
            formulas[label] = explanation
            audit.check('small_adversarial', edges, expected)
            permuted, mapped = relabel(edges, expected, permutation_rng)
            assert reference_walk_counts(permuted) == mapped
            audit.check('small_adversarial_relabelled', permuted, mapped)
    large = constructed_shapes(100000)
    large_rng = random.Random(SEED)
    random_edges = no_loop_random(100000, large_rng)
    started = time.perf_counter()
    random_expected = binary_lifting_counts(random_edges)
    lifting_seconds = time.perf_counter() - started
    large['random'] = (random_edges, random_expected, 'Independent binary lifting O(n log n) reference; no large brute-force walk.')
    manifests = []
    for label, (edges, expected, explanation) in large.items():
        audit.check('boundary_100000', edges, expected)
        permuted, mapped = relabel(edges, expected, permutation_rng)
        audit.check('boundary_100000_relabelled', permuted, mapped)
        manifests.append({'shape': label, 'n': len(edges), 'input_sha256': digest(edges),
                          'expected_sha256': digest(expected), 'expected_method': explanation,
                          'relabelled_input_sha256': digest(permuted), 'relabelled_expected_sha256': digest(mapped)})
    print('Boundary complete: 8 original and 8 relabelled 100,000-node graphs.', flush=True)
    return large, {'exhaustive_by_n': exhaustive_counts, 'random_seed': SEED,
                   'random_n_histogram': dict(sizes), 'random_generator': 'uniform n=2..40; per-edge uniform rejection sampling of self-loops',
                   'small_formula_checks': 70, 'binary_lifting_small_oracle_checks': lifting_checks,
                   'large_random_reference_seconds': lifting_seconds, 'boundary_graphs': manifests,
                   'formulas': formulas, 'large_quadratic_oracle_executed': False}


def benchmark(functions, large):
    rng = random.Random(SEED)
    shapes = ['random', 'big_cycle', 'long_chain', 'star_2cycle', 'many_2cycles',
              'mixed_disconnected_cycles', 'merging_branches', 'reverse_chain']
    rng.shuffle(shapes)
    result = {'n': 100000, 'repetitions': 5, 'warmups_per_algorithm_shape': 1,
              'clock': vars(time.get_clock_info('perf_counter')),
              'gc_policy': 'Full gc.collect before each call, outside timing. Cyclic GC disabled only during measured calls and restored. Warmups also disable GC. Memory calls retain normal GC after full collection.',
              'order_policy': 'Seeded shuffled shape order; each shape has seeded shuffled algorithm base order, rotated across 5 rounds so each algorithm occupies each timing position once. Sequential, one process.',
              'memory_policy': 'Separate call per algorithm/shape after timing. tracemalloc starts after input/expected allocation and gc.collect; stop immediately after candidate return. Peak includes returned output, excludes preallocated input/expectation. Not RSS.',
              'hash_seed': os.environ.get('PYTHONHASHSEED'), 'gc_thresholds': gc.get_threshold(),
              'initial_gc_enabled': gc.isenabled(), 'shape_order': shapes, 'schedule': [],
              'warmups': [], 'records': [], 'load_average_before': os.getloadavg()}
    for shape in shapes:
        edges, expected, _ = large[shape]
        snapshot = edges.copy()
        base = list(NAMES)
        rng.shuffle(base)
        samples = {name: [] for name in NAMES}
        def timed_call(name):
            gc.collect()
            enabled = gc.isenabled()
            gc.disable()
            try:
                begin = time.perf_counter()
                output = functions[name](edges)
                elapsed = time.perf_counter() - begin
            finally:
                if enabled:
                    gc.enable()
            if rejection(output, expected) or edges != snapshot:
                raise AssertionError('benchmark correctness or mutation: ' + shape + '/' + name)
            del output  # Destruction occurs outside the measured call.
            return elapsed
        for name in base:
            result['warmups'].append({'shape': shape, 'algorithm': name, 'seconds': timed_call(name), 'measured_sample': False})
        for repetition in range(5):
            order = base[repetition:] + base[:repetition]
            result['schedule'].append({'shape': shape, 'round': repetition + 1, 'algorithm_order': order})
            for name in order:
                samples[name].append(timed_call(name))
        for name in NAMES:
            gc.collect()
            tracemalloc.start()
            baseline_current, _ = tracemalloc.get_traced_memory()
            output = functions[name](edges)
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            if rejection(output, expected) or edges != snapshot:
                raise AssertionError('memory correctness or mutation: ' + shape + '/' + name)
            del output
            values = samples[name]
            median = statistics.median(values)
            result['records'].append({'shape': shape, 'algorithm': name,
                'samples_seconds': values, 'median_seconds': median,
                'min_seconds': min(values), 'max_seconds': max(values),
                'median_absolute_deviation_seconds': statistics.median(abs(v - median) for v in values),
                'tracemalloc_peak_bytes': peak, 'tracemalloc_retained_bytes': current,
                'tracemalloc_baseline_current_bytes': baseline_current,
                'input_sha256': digest(edges), 'expected_sha256': digest(expected)})
        print('Independent benchmark complete: ' + shape, flush=True)
    result['load_average_after'] = os.getloadavg()
    result['final_gc_enabled'] = gc.isenabled()
    result['measured_calls'] = sum(len(x['samples_seconds']) for x in result['records'])
    result['memory_calls'] = len(result['records'])
    result['uncertainty'] = 'Single native workstation session; no affinity/governor changes; background activity, frequency, cache, allocator and thermal effects remain. Five samples are descriptive, not a confidence interval. Balanced order mitigates position bias but does not eliminate carry-over effects.'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--controls-only', action='store_true')
    parser.add_argument('--replay-json', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / 'independent-results.json').exists():
        raise SystemExit('Refusing to overwrite existing results')
    result = {'schema_version': 1, 'audit': 'FUNCTIONAL-GRAPH-001/CODEX-001',
              'started_utc': datetime.now(timezone.utc).isoformat(), 'status': 'INCOMPLETE',
              'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'python_version': sys.version, 'python_implementation': platform.python_implementation(),
              'seed': SEED, 'exceptions': [], 'limitations': ['Finite tests do not constitute a formal proof.',
                'Only valid no-self-loop functional graphs are in scope.',
                'No RSS measurement; tracemalloc measures traced Python allocations only.',
                'No canonical ETQ bundle or quantum/E8 performance tested.',
                'No Windows or external judge execution.']}
    audit = None
    try:
        if platform.python_implementation() != 'CPython' or platform.python_version() != '3.14.4':
            raise RuntimeError('Required installed CPython 3.14.4 is unavailable')
        functions, source = load_candidates(args.source)
        result['source'] = source
        controls = negative_controls()
        result['negative_controls'] = controls
        if not all(record['rejected_as_expected'] for record in controls):
            result['status'] = 'FAIL'
            raise AssertionError('negative control accepted or failed for unexpected reason')
        if args.controls_only:
            result['status'] = 'INCOMPLETE'
            result['controls_only_status'] = 'PASS'
        else:
            audit = Auditor(functions, args.output)
            if args.replay_json:
                case = json.loads(args.replay_json.read_text())
                audit.check('replay', case['edges'], case['expected'])
                result['status'] = 'INCOMPLETE'
                result['replay_status'] = 'PASS'
            else:
                large, coverage = correctness(audit)
                result['coverage'] = coverage
                result['benchmarks'] = benchmark(functions, large)
                result['status'] = 'PASS'
        final_commit = subprocess.check_output(['git', '-C', str(args.source), 'rev-parse', 'HEAD'], text=True).strip()
        final_hash = hashlib.sha256((args.source / 'challenges/FUNCTIONAL-GRAPH-001/run.py').read_bytes()).hexdigest()
        if final_commit != COMMIT or final_hash != SOURCE_SHA:
            result['status'] = 'FAIL'
            raise RuntimeError('BLOCKED_SOURCE_MISMATCH')
        result['source_rechecked_after'] = True
    except Exception as exc:
        if isinstance(exc, AssertionError) or str(exc) == 'BLOCKED_SOURCE_MISMATCH':
            result['status'] = 'FAIL'
        result['exceptions'].append({'type': type(exc).__name__, 'message': str(exc)})
    finally:
        if audit is not None:
            result['oracle_results'] = audit.summary()
        result['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(args.output, 'independent-results.json', result)
    print(json.dumps({'status': result['status'], 'exceptions': result['exceptions']}), flush=True)
    return 0 if result['status'] == 'PASS' or result.get('controls_only_status') == 'PASS' or result.get('replay_status') == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
