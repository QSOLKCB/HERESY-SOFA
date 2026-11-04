#!/usr/bin/env python3
"""Bounded NetworkX Louvain experiment with isolated hash-seed workers."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


EXPERIMENT_ID = "HERESY-006"
ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = Path(__file__).resolve().parent
SOURCE_FILES = ("experiment.json", "experiment.md", "run.py")
EVIDENCE_PATHS = tuple(EXPERIMENT_DIR / name for name in SOURCE_FILES) + (
    ROOT / "tests" / "test_heresy006.py",
)
FIXTURES = ("separated_cliques", "symmetric_cycle", "bridge_node")
ORDERS = ("natural", "reversed", "interleaved")
SEED_SWEEP = tuple(range(64))
ORDER_SEEDS = (0, 17, 63)
FIXED_SEED = 17
HASH_SEEDS = (0, 1, 7, 42)
FIXED_REPEATS = 3
WORKER_TIMEOUT_SECONDS = 30.0
MODULARITY_TOLERANCE = 1e-12
CLAIMS = (
    "fixed_seed_identical_construction_reproducible",
    "partition_varies_across_random_seeds",
    "partition_varies_across_construction_order",
    "partition_varies_across_process_hash_seed",
    "all_partitions_are_valid_and_modularity_consistent",
    "networkx_contract_violation",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_revision() -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=3, check=True,
        ).stdout.strip()
        evidence_arguments = [str(path.relative_to(ROOT)) for path in EVIDENCE_PATHS]
        dirty = bool(subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all", "--"] + evidence_arguments,
            capture_output=True, text=True, timeout=3, check=True,
        ).stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return {"git_commit": None, "evidence_tree_dirty": None}
    return {"git_commit": commit, "evidence_tree_dirty": dirty}


def _evidence_hashes() -> list[dict[str, str]]:
    return [
        {
            "path": str(path.relative_to(ROOT)),
            "sha256": _sha256(path),
        }
        for path in EVIDENCE_PATHS
    ]


def _os_release() -> str:
    try:
        values = {}
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"')
        return values.get("PRETTY_NAME", platform.system())
    except OSError:
        return platform.system()


def _fixture_spec(name: str) -> tuple[list[int], list[tuple[int, int, float]]]:
    if name == "separated_cliques":
        nodes = list(range(15))
        edges = []
        for start in (0, 5, 10):
            for left in range(start, start + 5):
                for right in range(left + 1, start + 5):
                    edges.append((left, right, 1.0))
        edges.extend(((4, 5, 0.05), (9, 10, 0.05), (14, 0, 0.05)))
        return nodes, edges
    if name == "symmetric_cycle":
        nodes = list(range(16))
        return nodes, [(node, (node + 1) % 16, 1.0) for node in nodes]
    if name == "bridge_node":
        # Four identical triangles surround two symmetric bridge nodes.  Each
        # bridge has an equal-weight edge into every triangle, creating ties.
        nodes = list(range(14))
        edges = []
        for start in (0, 3, 6, 9):
            edges.extend((
                (start, start + 1, 1.0),
                (start + 1, start + 2, 1.0),
                (start + 2, start, 1.0),
            ))
        for bridge in (12, 13):
            for start in (0, 3, 6, 9):
                edges.append((bridge, start, 0.5))
        edges.append((12, 13, 0.5))
        return nodes, edges
    raise ValueError("unknown fixture: " + name)


def _ordered(values: list[Any], order: str) -> list[Any]:
    if order == "natural":
        return list(values)
    if order == "reversed":
        return list(reversed(values))
    if order == "interleaved":
        return list(values[::2]) + list(values[1::2])
    raise ValueError("unknown insertion order: " + order)


def _build_graph(nx: Any, fixture: str, order: str) -> Any:
    nodes, edges = _fixture_spec(fixture)
    graph = nx.Graph()
    graph.add_nodes_from(_ordered(nodes, order))
    for left, right, weight in _ordered(edges, order):
        graph.add_edge(left, right, weight=weight)
    return graph


def _topology_sha256(graph: Any) -> str:
    topology = {
        "nodes": sorted(graph.nodes()),
        "edges": sorted(
            (min(left, right), max(left, right), float(data.get("weight", 1.0)))
            for left, right, data in graph.edges(data=True)
        ),
    }
    encoded = json.dumps(topology, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _sha256_bytes(encoded)


def canonical_partition(communities: Iterable[Iterable[int]]) -> list[list[int]]:
    return [list(group) for group in sorted(tuple(sorted(group)) for group in communities)]


def _partition_key(partition: list[list[int]]) -> str:
    return json.dumps(partition, separators=(",", ":"))


def _evaluate(nx: Any, fixture: str, order: str, seed: int) -> dict[str, Any]:
    graph = _build_graph(nx, fixture, order)
    raw_partition = nx.community.louvain_communities(graph, weight="weight", seed=seed)
    partition = canonical_partition(raw_partition)
    flattened = [node for community in partition for node in community]
    covers_exactly_once = (
        sorted(flattened) == sorted(graph.nodes())
        and len(flattened) == len(set(flattened))
        and all(community for community in partition)
    )
    modularity = nx.community.modularity(graph, raw_partition, weight="weight")
    canonical_sets = [set(community) for community in partition]
    modularity_recomputed = nx.community.modularity(graph, canonical_sets, weight="weight")
    modularity_consistent = abs(modularity - modularity_recomputed) <= MODULARITY_TOLERANCE
    return {
        "fixture": fixture,
        "insertion_order": order,
        "seed": seed,
        "topology_sha256": _topology_sha256(graph),
        "partition": partition,
        "community_count": len(partition),
        "community_sizes": sorted(len(group) for group in partition),
        "modularity": modularity,
        "modularity_recomputed": modularity_recomputed,
        "modularity_consistent": modularity_consistent,
        "covers_nodes_exactly_once": covers_exactly_once,
    }


def _worker(args: argparse.Namespace) -> int:
    try:
        import networkx as nx
    except ImportError as error:
        print(json.dumps({"error": "networkx unavailable", "error_type": type(error).__name__}, sort_keys=True))
        return 3
    seeds = tuple(int(value) for value in args.seeds.split(","))
    results = [
        _evaluate(nx, fixture, args.order, seed)
        for fixture in FIXTURES
        for seed in seeds
    ]
    print(json.dumps({
        "networkx_version": nx.__version__,
        "python": platform.python_version(),
        "hash_seed": os.environ.get("PYTHONHASHSEED"),
        "scenario": args.scenario,
        "results": results,
    }, separators=(",", ":"), sort_keys=True))
    return 0


def _worker_command(scenario: str, order: str, seeds: tuple[int, ...]) -> list[str]:
    return [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--scenario", scenario,
        "--order", order,
        "--seeds", ",".join(str(seed) for seed in seeds),
    ]


def _normalized_command(command: list[str]) -> list[str]:
    normalized = []
    for part in command:
        if part == sys.executable:
            normalized.append("python3")
        elif part == str(Path(__file__).resolve()):
            normalized.append("experiments/HERESY-006/run.py")
        else:
            normalized.append(part)
    return normalized


def run_worker_process(
    scenario: str,
    order: str,
    seeds: tuple[int, ...],
    hash_seed: int,
    repeat: int | None = None,
    timeout: float = WORKER_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    command = _worker_command(scenario, order, seeds)
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONHASHSEED": str(hash_seed),
        "PYTHONIOENCODING": "utf-8",
    }
    base = {
        "scenario": scenario,
        "insertion_order": order,
        "seeds": list(seeds),
        "hash_seed": hash_seed,
        "repeat": repeat,
        "command": _normalized_command(command),
    }
    try:
        completed = subprocess.run(
            command, cwd=EXPERIMENT_DIR, env=environment,
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return dict(base, exit_code=124, timed_out=True, stderr="worker timed out", output=None)
    except OSError as error:
        return dict(base, exit_code=127, timed_out=False, stderr=type(error).__name__ + ": worker unavailable", output=None)
    try:
        output = json.loads(completed.stdout)
    except ValueError:
        output = None
    return dict(
        base,
        exit_code=completed.returncode,
        timed_out=False,
        stderr=completed.stderr,
        output=output,
    )


def validate_worker(record: dict[str, Any]) -> tuple[bool, str]:
    """Reject timeout, failure, malformed output, or an incorrect observation."""
    if record.get("timed_out"):
        return False, "worker timed out"
    if record.get("exit_code") != 0:
        return False, "worker exit code was nonzero"
    output = record.get("output")
    if not isinstance(output, dict) or not isinstance(output.get("results"), list):
        return False, "worker did not return a JSON result list"
    expected_count = len(FIXTURES) * len(record.get("seeds", ()))
    if len(output["results"]) != expected_count:
        return False, "worker result count did not match its configuration"
    expected = {
        (fixture, seed)
        for fixture in FIXTURES
        for seed in record.get("seeds", ())
    }
    actual = set()
    for result in output["results"]:
        if not isinstance(result, dict):
            return False, "worker result was not an object"
        actual.add((result.get("fixture"), result.get("seed")))
        if result.get("insertion_order") != record.get("insertion_order"):
            return False, "worker insertion order did not match its command"
        if not result.get("covers_nodes_exactly_once") or not result.get("modularity_consistent"):
            return False, "partition coverage or modularity check failed"
    if actual != expected:
        return False, "worker fixture/seed coverage was incomplete"
    return True, "all configured results passed integrity checks"


def _dependency_probe() -> dict[str, Any]:
    command = [sys.executable, "-c", "import networkx as nx; print(nx.__version__)"]
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONHASHSEED": "0",
        "PYTHONIOENCODING": "utf-8",
    }
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=5, check=False,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "command": ["python3", "-c", "import networkx as nx; print(nx.__version__)"],
            "exit_code": 124 if isinstance(error, subprocess.TimeoutExpired) else 127,
            "version": None,
            "stderr": type(error).__name__,
        }
    return {
        "command": ["python3", "-c", "import networkx as nx; print(nx.__version__)"],
        "exit_code": completed.returncode,
        "version": completed.stdout.strip() if completed.returncode == 0 else None,
        "stderr": completed.stderr,
    }


def _base_report(command: list[str]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "title": "The Louvain Shape-Shifter",
        "generated_at": _utc_now(),
        "source_revision": _source_revision(),
        "runtime": {
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "os": _os_release(),
            "kernel": platform.release(),
            "machine": platform.machine(),
            "networkx": None,
            "dependencies": {},
            "virtual_environment": sys.prefix != sys.base_prefix,
        },
        "invocation": command,
        "commands": [],
        "child_exit_codes": [],
        "expected": {
            "stability_control": "strongly separated cliques should remain three five-node communities",
            "seed_sweep": "symmetric fixtures may produce more than one valid canonical partition across seeds 0-63",
            "fixed_repeat": "identical seed, construction order, and process hash seed should reproduce the same partition",
            "integrity": "every partition covers each node exactly once and recomputed modularity agrees within 1e-12",
        },
        "fixtures": {
            "separated_cliques": "three K5 cliques joined in a ring by weight-0.05 edges",
            "symmetric_cycle": "unweighted 16-node cycle",
            "bridge_node": "four triangles and two symmetric bridge nodes with equal-weight choices",
        },
        "configurations": {
            "seed_sweep": {"seeds": list(SEED_SWEEP), "order": "natural", "hash_seed": 0},
            "fixed_repeat": {"seed": FIXED_SEED, "order": "natural", "hash_seed": 0, "processes": FIXED_REPEATS},
            "construction_order": {"seeds": list(ORDER_SEEDS), "orders": list(ORDERS), "hash_seed": 0},
            "process_hash_seed": {"seed": FIXED_SEED, "order": "natural", "hash_seeds": list(HASH_SEEDS)},
        },
        "actual": {},
        "evidence": _evidence_hashes(),
        "claims": {claim: "not_tested" for claim in CLAIMS},
        "limitations": [
            "Louvain is a heuristic; a different valid partition is not by itself a NetworkX bug or contract violation.",
            "The tested fixtures, seeds, insertion orders, interpreter, and NetworkX version do not establish behavior for other configurations.",
            "No upstream contract violation is claimed without a separately reviewed specification boundary.",
        ],
    }


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    results = []
    for record in records:
        if record.get("output"):
            for item in record["output"]["results"]:
                enriched = dict(item)
                enriched.update({
                    "scenario": record["scenario"],
                    "hash_seed": record["hash_seed"],
                    "repeat": record["repeat"],
                })
                results.append(enriched)

    by_fixture: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        by_fixture[result["fixture"]].append(result)

    fixture_summaries = {}
    for fixture in FIXTURES:
        items = by_fixture[fixture]
        unique_partitions = {}
        for item in items:
            key = _partition_key(item["partition"])
            unique_partitions.setdefault(key, {
                "partition": item["partition"],
                "community_count": item["community_count"],
                "community_sizes": item["community_sizes"],
                "modularity_scores": [],
            })["modularity_scores"].append(item["modularity"])
        alternatives_by_score: dict[float, set[str]] = defaultdict(set)
        for item in items:
            # The fixtures produce rational scores that are exactly stable in
            # one runtime.  Group within the declared tolerance, not by text.
            matching_score = next(
                (score for score in alternatives_by_score
                 if abs(score - item["modularity"]) <= MODULARITY_TOLERANCE),
                item["modularity"],
            )
            alternatives_by_score[matching_score].add(_partition_key(item["partition"]))
        fixture_summaries[fixture] = {
            "tested_configuration_count": len(items),
            "unique_partition_count": len(unique_partitions),
            "unique_partitions": list(unique_partitions.values()),
            "community_counts": sorted({item["community_count"] for item in items}),
            "community_size_sets": sorted({tuple(item["community_sizes"]) for item in items}),
            "modularity_scores": sorted({item["modularity"] for item in items}),
            "topology_hashes": sorted({item["topology_sha256"] for item in items}),
            "equal_modularity_alternatives": [
                {"modularity": score, "distinct_partition_count": len(partitions)}
                for score, partitions in sorted(alternatives_by_score.items())
                if len(partitions) > 1
            ],
        }

    def partition_set(scenario: str, fixture: str, **filters: Any) -> set[str]:
        return {
            _partition_key(item["partition"])
            for item in results
            if item["scenario"] == scenario and item["fixture"] == fixture
            and all(item.get(key) == value for key, value in filters.items())
        }

    fixed_reproducible = all(
        len(partition_set("fixed_repeat", fixture)) == 1 for fixture in FIXTURES
    )
    seed_variation = {
        fixture: len(partition_set("seed_sweep", fixture)) > 1 for fixture in FIXTURES
    }
    order_variation = {}
    for fixture in FIXTURES:
        order_variation[fixture] = any(
            len({
                _partition_key(item["partition"])
                for item in results
                if item["scenario"] == "construction_order"
                and item["fixture"] == fixture and item["seed"] == seed
            }) > 1
            for seed in ORDER_SEEDS
        )
    hash_variation = {
        fixture: len(partition_set("process_hash_seed", fixture)) > 1
        for fixture in FIXTURES
    }
    all_integrity = all(
        item["covers_nodes_exactly_once"] and item["modularity_consistent"]
        for item in results
    )
    stable_control = (
        fixture_summaries["separated_cliques"]["unique_partition_count"] == 1
        and fixture_summaries["separated_cliques"]["community_counts"] == [3]
        and fixture_summaries["separated_cliques"]["community_size_sets"] == [(5, 5, 5)]
    )
    return {
        "results": results,
        "fixture_summaries": fixture_summaries,
        "fixed_seed_reproducible": fixed_reproducible,
        "variation_across_seeds": seed_variation,
        "variation_across_construction_order": order_variation,
        "variation_across_process_hash_seed": hash_variation,
        "all_partitions_cover_nodes_once_and_modularity_is_consistent": all_integrity,
        "stability_control_passed": stable_control,
        "contract_violations_observed": [],
    }


def run_experiment(args: argparse.Namespace) -> int:
    report = _base_report(["python3", "experiments/HERESY-006/run.py", "--output", args.output.name])
    dependency = _dependency_probe()
    report["commands"].append(dependency)
    report["runtime"]["networkx"] = dependency["version"]
    if dependency["exit_code"] != 0 or dependency["version"] is None:
        report["run_status"] = "NOT_RUN"
        report["conclusion"] = "UNCONFIRMED"
        report["actual"] = {"reason": "NetworkX is unavailable in the selected Python environment"}
        _write_report(args.output, report)
        print(json.dumps({"experiment_id": EXPERIMENT_ID, "run_status": "NOT_RUN", "report": args.output.name}, sort_keys=True))
        return 3

    report["runtime"]["dependencies"] = {
        "networkx": dependency["version"],
        "additional_mandatory_third_party_packages_used": {},
    }

    records = []
    records.append(run_worker_process("seed_sweep", "natural", SEED_SWEEP, 0, timeout=args.timeout))
    for repeat in range(FIXED_REPEATS):
        records.append(run_worker_process("fixed_repeat", "natural", (FIXED_SEED,), 0, repeat=repeat, timeout=args.timeout))
    for order in ORDERS:
        records.append(run_worker_process("construction_order", order, ORDER_SEEDS, 0, timeout=args.timeout))
    for hash_seed in HASH_SEEDS:
        records.append(run_worker_process("process_hash_seed", "natural", (FIXED_SEED,), hash_seed, timeout=args.timeout))

    validations = []
    for record in records:
        accepted, reason = validate_worker(record)
        record["accepted"] = accepted
        record["validation"] = reason
        validations.append(accepted)
        report["commands"].append({
            "command": record["command"],
            "scenario": record["scenario"],
            "hash_seed": record["hash_seed"],
            "exit_code": record["exit_code"],
            "timed_out": record["timed_out"],
        })
        report["child_exit_codes"].append({
            "scenario": record["scenario"],
            "insertion_order": record["insertion_order"],
            "hash_seed": record["hash_seed"],
            "repeat": record["repeat"],
            "exit_code": record["exit_code"],
            "timed_out": record["timed_out"],
        })

    if not all(validations):
        report["run_status"] = "FAIL"
        report["conclusion"] = "UNCONFIRMED"
        report["actual"] = {
            "worker_validations": [
                {
                    "scenario": record["scenario"],
                    "order": record["insertion_order"],
                    "hash_seed": record["hash_seed"],
                    "repeat": record["repeat"],
                    "accepted": record["accepted"],
                    "validation": record["validation"],
                }
                for record in records
            ],
        }
        report["claims"] = {claim: "not_tested" for claim in CLAIMS}
        _write_report(args.output, report)
        print(json.dumps({"experiment_id": EXPERIMENT_ID, "run_status": "FAIL", "report": args.output.name}, sort_keys=True))
        return 1

    actual = _summarize(records)
    report["actual"] = actual
    report["claims"][CLAIMS[0]] = "executed"
    report["claims"][CLAIMS[1]] = "executed" if any(actual["variation_across_seeds"].values()) else "unsupported"
    report["claims"][CLAIMS[2]] = "executed" if any(actual["variation_across_construction_order"].values()) else "unsupported"
    report["claims"][CLAIMS[3]] = "executed" if any(actual["variation_across_process_hash_seed"].values()) else "unsupported"
    report["claims"][CLAIMS[4]] = "executed"
    report["claims"][CLAIMS[5]] = "unsupported"
    hypothesis_observed = any(actual["variation_across_seeds"].values()) or any(actual["variation_across_construction_order"].values())
    report["run_status"] = "PASS"
    report["conclusion"] = "CONFIRMED" if hypothesis_observed else "UNCONFIRMED"
    _write_report(args.output, report)
    print(json.dumps({"experiment_id": EXPERIMENT_ID, "run_status": "PASS", "conclusion": report["conclusion"], "report": args.output.name}, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("HERESY-006-report.json"))
    parser.add_argument("--timeout", type=float, default=WORKER_TIMEOUT_SECONDS)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--scenario", choices=("seed_sweep", "fixed_repeat", "construction_order", "process_hash_seed"), help=argparse.SUPPRESS)
    parser.add_argument("--order", choices=ORDERS, help=argparse.SUPPRESS)
    parser.add_argument("--seeds", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.worker:
        if args.scenario is None or args.order is None or args.seeds is None:
            parser.error("worker mode requires scenario, order, and seeds")
        return _worker(args)
    if not 0.1 <= args.timeout <= 120:
        parser.error("--timeout must be between 0.1 and 120 seconds")
    return run_experiment(args)


if __name__ == "__main__":
    raise SystemExit(main())
