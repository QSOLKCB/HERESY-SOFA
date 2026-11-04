"""Independent stdlib controls for the community functional-graph ETQ-inspired audit."""
from __future__ import annotations

import importlib.util
from itertools import product
import json
from pathlib import Path
import random
import unittest

HERE = Path(__file__).resolve().parents[1] / "challenges" / "FUNCTIONAL-GRAPH-001"


def load():
    spec = importlib.util.spec_from_file_location("functional_graph_run", HERE / "run.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("missing graph experiment")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FunctionalGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.alg = load()

    def test_given_and_adversarial_examples(self):
        fixtures = [
            ([1, 2, 0, 0], [3, 3, 3, 4]),
            ([1, 2, 3, 4, 0], [5, 5, 5, 5, 5]),
            ([1, 0], [2, 2]),
            ([1, 0, 3, 2], [2, 2, 2, 2]),
            ([1, 2, 3, 4, 5, 4], [6, 5, 4, 3, 2, 2]),
        ]
        for edges, expected in fixtures:
            self.assertEqual(self.alg.oracle(edges), expected)
            for label, solution in self.alg.CANDIDATES.items():
                with self.subTest(label=label, edges=edges):
                    self.assertEqual(solution(edges), expected)

    def test_exhaustive_functional_graphs_without_self_loops(self):
        ncases = 0
        for n in range(2, 7):
            choices = [tuple(v for v in range(n) if v != i) for i in range(n)]
            for edge_tuple in product(*choices):
                edges = list(edge_tuple)
                expected = self.alg.oracle(edges)
                for label, solution in self.alg.CANDIDATES.items():
                    self.assertEqual(solution(edges), expected, (label, edges))
                ncases += 1
        self.assertEqual(ncases, 16739)

    def test_deterministic_random_cross_check(self):
        rng = random.Random(1703)
        for _ in range(1000):
            n = rng.randrange(2, 31)
            edges = [rng.randrange(n - 1) for _ in range(n)]
            edges = [v + (v >= i) for i, v in enumerate(edges)]
            expected = self.alg.oracle(edges)
            for label, solution in self.alg.CANDIDATES.items():
                self.assertEqual(solution(edges), expected, (label, edges))

    def test_long_chain_and_cycle_at_constraint_limit(self):
        n = 100000
        edges = list(range(1, n)) + [n - 2]
        for solution in (self.alg.signed_walk, self.alg.indegree_peel):
            out = solution(edges)
            self.assertEqual(len(out), n)
            self.assertEqual(out[0], n)
            self.assertEqual(out[n - 3], 3)
            self.assertEqual(out[n - 2:], [2, 2])
        edges = list(range(1, n)) + [0]
        for solution in (self.alg.signed_walk, self.alg.indegree_peel):
            self.assertEqual(solution(edges), [n] * n)

    def test_no_scalar_answer_from_global_reachability(self):
        graph = [1, 2, 0, 0]
        self.assertEqual(len(set(range(len(graph)))), 4)
        self.assertEqual(self.alg.signed_walk(graph), [3, 3, 3, 4])
        self.assertNotEqual(self.alg.signed_walk(graph), 4)

    def test_etq_edge_identity_and_scoped_method(self):
        # Each signed-walk transition reads edges[v]; no ETQ-303 event order.
        source = (HERE / "run.py").read_text(encoding="utf-8")
        self.assertIn("v = edges[v]", source)
        self.assertIn("303-event CRT orbit is deliberately NOT used", source)
        self.assertNotIn("n % 101", source)
        self.assertNotIn("n % 3", source)

    def test_historical_local_evidence_source_identity(self):
        report = json.loads((HERE / "LOCAL-PYTHON-313.json").read_text())
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["source_sha256"], self.alg.hashlib.sha256((HERE / "run.py").read_bytes()).hexdigest())
        self.assertEqual(report["exhaustive_graphs_n2_to_n6"], 16739)
        self.assertEqual(report["random_graphs_seed1703"], 20000)
        self.assertEqual(report["benchmark_n"], 100000)
        self.assertEqual(report["benchmark_repeats"], 3)
        self.assertEqual(len(report["benchmarks"]), 20)
        self.assertTrue(all(r["median_seconds"] > 0 and r["peak_extra_bytes"] > 0 for r in report["benchmarks"]))


if __name__ == "__main__":
    unittest.main()
