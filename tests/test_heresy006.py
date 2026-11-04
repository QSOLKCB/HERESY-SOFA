"""HERESY-006 matrix integrity and false-green regression tests."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments" / "HERESY-006" / "run.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("heresy006_runner", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Heresy006Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner()

    def valid_worker(self):
        results = []
        for fixture in self.runner.FIXTURES:
            results.append({
                "fixture": fixture,
                "seed": 17,
                "insertion_order": "natural",
                "partition": [[0]],
                "covers_nodes_exactly_once": True,
                "modularity_consistent": True,
            })
        return {
            "scenario": "fixed_repeat",
            "insertion_order": "natural",
            "seeds": [17],
            "hash_seed": 0,
            "repeat": 0,
            "exit_code": 0,
            "timed_out": False,
            "output": {"results": results},
        }

    def test_partition_canonicalization_uses_membership_not_return_order(self):
        left = self.runner.canonical_partition([{4, 3}, {2, 0, 1}])
        right = self.runner.canonical_partition([{1, 0, 2}, {3, 4}])
        self.assertEqual(left, [[0, 1, 2], [3, 4]])
        self.assertEqual(left, right)

    def test_worker_failure_timeout_and_wrong_observation_fail_closed(self):
        valid = self.valid_worker()
        self.assertTrue(self.runner.validate_worker(valid)[0])

        mutations = [
            dict(valid, exit_code=9),
            dict(valid, timed_out=True, exit_code=124),
            dict(valid, output=None),
            dict(valid, output={"results": valid["output"]["results"][:-1]}),
        ]
        broken_integrity = json.loads(json.dumps(valid))
        broken_integrity["output"]["results"][0]["modularity_consistent"] = False
        mutations.append(broken_integrity)
        wrong_order = json.loads(json.dumps(valid))
        wrong_order["output"]["results"][0]["insertion_order"] = "reversed"
        mutations.append(wrong_order)
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assertFalse(self.runner.validate_worker(mutation)[0])

    def test_missing_dependency_report_is_not_run_and_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            unavailable = {
                "command": ["python3", "-c", "import networkx as nx; print(nx.__version__)"],
                "exit_code": 1,
                "version": None,
                "stderr": "ModuleNotFoundError",
            }
            with mock.patch.object(self.runner, "_dependency_probe", return_value=unavailable):
                result = self.runner.run_experiment(Namespace(output=output, timeout=1.0))
            self.assertEqual(result, 3)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["run_status"], "NOT_RUN")
            self.assertEqual(report["conclusion"], "UNCONFIRMED")
            self.assertTrue(all(value == "not_tested" for value in report["claims"].values()))

    @unittest.skipUnless(importlib.util.find_spec("networkx"), "NetworkX is optional")
    def test_fixture_topology_is_equivalent_across_insertion_orders(self):
        import networkx as nx

        for fixture in self.runner.FIXTURES:
            hashes = {
                self.runner._topology_sha256(self.runner._build_graph(nx, fixture, order))
                for order in self.runner.ORDERS
            }
            with self.subTest(fixture=fixture):
                self.assertEqual(len(hashes), 1)

    def test_declared_matrix_covers_required_seeds_and_repeat_axes(self):
        self.assertEqual(self.runner.SEED_SWEEP, tuple(range(64)))
        self.assertGreaterEqual(self.runner.FIXED_REPEATS, 3)
        self.assertEqual(set(self.runner.ORDERS), {"natural", "reversed", "interleaved"})
        self.assertGreaterEqual(len(self.runner.HASH_SEEDS), 3)


if __name__ == "__main__":
    unittest.main()
