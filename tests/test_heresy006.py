"""HERESY-006 matrix integrity and false-green regression tests."""
from __future__ import annotations

import copy
import importlib.util
import json
import platform
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
            nodes, edges = self.runner._fixture_spec(fixture)
            results.append({
                "fixture": fixture,
                "seed": 17,
                "insertion_order": "natural",
                "topology_sha256": self.runner._topology_spec_sha256(nodes, edges),
                "partition": [nodes],
                "community_count": 1,
                "community_sizes": [len(nodes)],
                "modularity": 0.0,
                "modularity_recomputed": 0.0,
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
            "output": {
                "networkx_version": "test-version",
                "python": platform.python_version(),
                "scenario": "fixed_repeat",
                "hash_seed": "0",
                "results": results,
            },
        }

    def assert_worker_rejected(self, record):
        self.assertFalse(self.runner.validate_worker(
            record, expected_networkx="test-version",
            expected_python=platform.python_version(),
        )[0])

    def test_partition_canonicalization_uses_membership_not_return_order(self):
        left = self.runner.canonical_partition([{4, 3}, {2, 0, 1}])
        right = self.runner.canonical_partition([{1, 0, 2}, {3, 4}])
        self.assertEqual(left, [[0, 1, 2], [3, 4]])
        self.assertEqual(left, right)

    def test_worker_failure_timeout_and_wrong_observation_fail_closed(self):
        valid = self.valid_worker()
        self.assertTrue(self.runner.validate_worker(
            valid, expected_networkx="test-version",
            expected_python=platform.python_version(),
        )[0])

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
        wrong_topology = json.loads(json.dumps(valid))
        wrong_topology["output"]["results"][0]["topology_sha256"] = "0" * 64
        mutations.append(wrong_topology)
        wrong_version = json.loads(json.dumps(valid))
        wrong_version["output"]["networkx_version"] = "wrong-version"
        mutations.append(wrong_version)
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assert_worker_rejected(mutation)

    def test_forged_success_booleans_cannot_hide_missing_or_duplicate_nodes(self):
        omitted = copy.deepcopy(self.valid_worker())
        omitted_result = omitted["output"]["results"][0]
        omitted_result["partition"] = [[0]]
        omitted_result["community_count"] = 1
        omitted_result["community_sizes"] = [1]
        self.assertTrue(omitted_result["covers_nodes_exactly_once"])
        self.assertTrue(omitted_result["modularity_consistent"])
        self.assert_worker_rejected(omitted)

        duplicated = copy.deepcopy(self.valid_worker())
        duplicated_result = duplicated["output"]["results"][0]
        nodes = duplicated_result["partition"][0]
        duplicated_result["partition"] = [[nodes[0]], nodes]
        duplicated_result["community_count"] = 2
        duplicated_result["community_sizes"] = [1, len(nodes)]
        self.assert_worker_rejected(duplicated)

    def test_self_consistent_alternate_graph_forgery_is_rejected(self):
        alternate_graph = copy.deepcopy(self.valid_worker())
        fixture = self.runner.FIXTURES[0]
        nodes, edges = self.runner._fixture_spec(fixture)
        forged_edges = list(edges) + [(0, 5, 0.75)]
        forged = alternate_graph["output"]["results"][0]
        forged["topology_sha256"] = self.runner._topology_spec_sha256(nodes, forged_edges)
        # One community has modularity zero on both the expected and forged
        # graph, so the forged graph/partition/score are internally coherent.
        forged["partition"] = [nodes]
        forged["community_count"] = 1
        forged["community_sizes"] = [len(nodes)]
        forged["modularity"] = 0.0
        forged["modularity_recomputed"] = 0.0
        self.assert_worker_rejected(alternate_graph)

    def test_identity_substitution_is_rejected_against_parent_invocation(self):
        for key, value in (("scenario", "seed_sweep"), ("hash_seed", "42")):
            substituted = copy.deepcopy(self.valid_worker())
            substituted["output"][key] = value
            with self.subTest(key=key, value=value):
                self.assert_worker_rejected(substituted)

    def test_nonfinite_modularity_is_rejected_before_tolerance(self):
        for nonfinite in (float("nan"), float("inf"), float("-inf")):
            forged = copy.deepcopy(self.valid_worker())
            forged_result = forged["output"]["results"][0]
            forged_result["modularity"] = nonfinite
            forged_result["modularity_recomputed"] = nonfinite
            with self.subTest(nonfinite=nonfinite):
                self.assert_worker_rejected(forged)

    def test_failed_controls_cannot_confirm_or_claim_reproducibility(self):
        actual = {
            "fixed_seed_reproducible": False,
            "variation_across_seeds": {fixture: True for fixture in self.runner.FIXTURES},
            "variation_across_construction_order": {fixture: True for fixture in self.runner.FIXTURES},
            "variation_across_process_hash_seed": {fixture: False for fixture in self.runner.FIXTURES},
            "all_partitions_cover_nodes_once_and_modularity_is_consistent": True,
            "stability_control_passed": True,
        }
        claims = self.runner.classify_claims(actual)
        self.assertEqual(
            claims["fixed_seed_identical_construction_reproducible"],
            "unsupported",
        )
        self.assertFalse(self.runner.hypothesis_confirmed(actual))
        actual["fixed_seed_reproducible"] = True
        actual["stability_control_passed"] = False
        self.assertFalse(self.runner.hypothesis_confirmed(actual))

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


    def test_failed_worker_report_keeps_sanitized_counterexample(self):
        original = self.valid_worker()["output"]
        original["results"][0]["partition"] = [[0], [0]]
        original["results"][0]["unexpected_private_field"] = "do-not-export-this-value"
        original["unexpected_private_field"] = "do-not-export-this-value"

        def failed_worker(scenario, order, seeds, hash_seed, repeat=None, timeout=None):
            return {
                "scenario": scenario, "insertion_order": order,
                "seeds": list(seeds), "hash_seed": hash_seed,
                "repeat": repeat, "command": ["python3", "worker"],
                "exit_code": 9, "timed_out": False,
                "stderr": (
                    'File "/home/example/private/run.py", line 12\n'
                    'ValueError: token=sensitive@example.com\n'
                ),
                "output": copy.deepcopy(original),
            }

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "failed.json"
            dependency = {"command": ["python3"], "exit_code": 0, "version": "test-version", "stderr": ""}
            with mock.patch.object(self.runner, "_dependency_probe", return_value=dependency), \
                 mock.patch.object(self.runner, "run_worker_process", side_effect=failed_worker):
                exit_code = self.runner.run_experiment(Namespace(output=output, timeout=1.0))
            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["run_status"], "FAIL")
        self.assertEqual(report["conclusion"], "UNCONFIRMED")
        failures = report["actual"]["failed_worker_diagnostics"]
        self.assertTrue(failures)
        self.assertEqual(failures[0]["exit_code"], 9)
        self.assertEqual(failures[0]["observation"]["results"][0]["partition"], [[0], [0]])
        self.assertIn("ValueError", failures[0]["stderr_excerpt"])
        self.assertIn("<path>", failures[0]["stderr_excerpt"])
        text = json.dumps(report, sort_keys=True)
        for secret in ("/home/example", "sensitive@example.com", "do-not-export-this-value"):
            self.assertNotIn(secret, text)

    def test_malformed_worker_stdout_is_bounded_and_redacted(self):
        record = {
            "scenario": "fixed_repeat", "insertion_order": "natural",
            "hash_seed": 0, "repeat": 0, "exit_code": 1,
            "timed_out": False, "validation": "malformed JSON",
            "stderr": "RuntimeError: password=very-secret",
            "stdout": '/tmp/private/path token=not-public ' + "A" * 10000,
            "output": None,
        }
        evidence = self.runner._failed_worker_diagnostic(record)
        self.assertIn("<path>", evidence["malformed_stdout_excerpt"])
        self.assertNotIn("not-public", json.dumps(evidence))
        self.assertNotIn("very-secret", json.dumps(evidence))
        self.assertIn("<truncated>", evidence["malformed_stdout_excerpt"])
        self.assertLessEqual(len(evidence["malformed_stdout_excerpt"]), self.runner.MAX_DIAGNOSTIC_CHARS + 11)

    def test_failed_controls_make_top_level_experiment_nonzero(self):
        actual = {
            "fixed_seed_reproducible": True,
            "variation_across_seeds": {fixture: True for fixture in self.runner.FIXTURES},
            "variation_across_construction_order": {fixture: False for fixture in self.runner.FIXTURES},
            "variation_across_process_hash_seed": {fixture: False for fixture in self.runner.FIXTURES},
            "all_partitions_cover_nodes_once_and_modularity_is_consistent": True,
            "stability_control_passed": True,
        }

        def nominal_worker(scenario, order, seeds, hash_seed, repeat=None, timeout=None):
            return {
                "scenario": scenario, "insertion_order": order,
                "seeds": list(seeds), "hash_seed": hash_seed,
                "repeat": repeat, "command": ["python3", "worker"],
                "exit_code": 0, "timed_out": False,
                "stderr": "", "output": {},
            }

        dependency = {"command": ["python3"], "exit_code": 0, "version": "test-version", "stderr": ""}
        for failed_control in ("fixed_seed_reproducible", "stability_control_passed"):
            with self.subTest(failed_control=failed_control), tempfile.TemporaryDirectory() as directory:
                failing = copy.deepcopy(actual)
                failing[failed_control] = False
                output = Path(directory) / "report.json"
                with mock.patch.object(self.runner, "_dependency_probe", return_value=dependency), \
                     mock.patch.object(self.runner, "run_worker_process", side_effect=nominal_worker), \
                     mock.patch.object(self.runner, "validate_worker", return_value=(True, "validated")), \
                     mock.patch.object(self.runner, "_summarize", return_value=failing):
                    exit_code = self.runner.run_experiment(Namespace(output=output, timeout=1.0))
                report = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(exit_code, 1)
                self.assertEqual(report["run_status"], "FAIL")
                self.assertEqual(report["conclusion"], "UNCONFIRMED")

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
