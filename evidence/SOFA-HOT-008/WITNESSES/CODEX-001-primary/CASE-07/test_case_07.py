#!/usr/bin/env python3
import argparse
import json
import random
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from corrected import create_binary_tree
from original import Solution, TreeNode
from setdefault_variant import create_with_setdefault

SEED = 26051108
MAX_EDGES = 10_000


def chain(edges):
    return [[value, value + 1, 1] for value in range(1, edges + 1)]


def serialize(root):
    result = []
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if node is None:
            result.append(None)
            continue
        result.append(node.val)
        queue.append(node.left)
        queue.append(node.right)
    while result and result[-1] is None:
        result.pop()
    return result


def random_valid_tree(node_count, rng):
    slots = [(1, 1), (1, 0)]
    descriptions = []
    for child in range(2, node_count + 1):
        index = rng.randrange(len(slots))
        parent, is_left = slots.pop(index)
        descriptions.append([parent, child, is_left])
        slots.extend([(child, 1), (child, 0)])
    rng.shuffle(descriptions)
    return descriptions


def original_succeeds(edges):
    try:
        Solution().createBinaryTree(chain(edges))
        return True
    except RecursionError:
        return False


def first_failing_depth():
    low, high = 1, MAX_EDGES
    if original_succeeds(high):
        return {"edges": None, "predecessor_succeeds": None, "failing_succeeds": True}
    while low < high:
        middle = (low + high) // 2
        if original_succeeds(middle):
            low = middle + 1
        else:
            high = middle
    return {
        "edges": low,
        # Keep both controls at the same harness stack depth as the search probes.
        "predecessor_succeeds": original_succeeds(low - 1) if low > 1 else None,
        "failing_succeeds": original_succeeds(low),
    }


def profile_make_tree(descriptions):
    current = 0
    maximum = 0

    def profiler(frame, event, arg):
        nonlocal current, maximum
        if frame.f_code.co_name == "makeTree":
            if event == "call":
                current += 1
                maximum = max(maximum, current)
            elif event in ("return", "exception"):
                current -= 1
        return profiler

    sys.setprofile(profiler)
    try:
        Solution().createBinaryTree(descriptions)
    finally:
        sys.setprofile(None)
    return maximum


def main(receipt_path):
    started = datetime.now(timezone.utc).isoformat()
    checks = []

    def check(name, actual, expected, classification="EXECUTED"):
        checks.append({"name": name, "actual": actual, "expected": expected,
                       "passed": actual == expected, "classification": classification})

    default_limit = sys.getrecursionlimit()
    failure_probe = first_failing_depth()
    failing = failure_probe["edges"]
    check("default_recursion_limit_unchanged", sys.getrecursionlimit(), default_limit)
    check("valid_max_depth_original_raises", original_succeeds(MAX_EDGES), False)
    check("smallest_failure_found_within_constraints", failing is not None and failing <= MAX_EDGES, True)
    if failing is not None and failing > 1:
        check("depth_before_smallest_failure_succeeds",
              failure_probe["predecessor_succeeds"], True)
        check("smallest_failure_reproduces_at_search_stack_depth",
              failure_probe["failing_succeeds"], False)

    iterative_root, iterative_nodes = create_binary_tree(chain(MAX_EDGES))
    check("iterative_max_depth_root", iterative_root.val, 1)
    cursor = iterative_root
    count = 0
    while cursor is not None:
        count += 1
        cursor = cursor.left
    check("iterative_max_depth_node_count", count, MAX_EDGES + 1)

    rng = random.Random(SEED)
    descriptions = random_valid_tree(400, rng)
    original_root = Solution().createBinaryTree(descriptions)
    corrected_root, _ = create_binary_tree(descriptions)
    check("random_tree_output_structure_equal", serialize(original_root), serialize(corrected_root))
    check("original_recursion_usage_on_100_edge_chain", profile_make_tree(chain(100)) > 100, True)
    check("corrected_implementation_has_makeTree", hasattr(create_binary_tree, "makeTree"), False)

    TreeNode.allocations = 0
    _, setdefault_nodes = create_with_setdefault(chain(MAX_EDGES))
    setdefault_allocations = TreeNode.allocations
    TreeNode.allocations = 0
    _, corrected_nodes = create_binary_tree(chain(MAX_EDGES))
    corrected_allocations = TreeNode.allocations
    check("setdefault_retained_nodes", len(setdefault_nodes), MAX_EDGES + 1)
    check("setdefault_eager_allocations", setdefault_allocations, 2 * MAX_EDGES)
    check("setdefault_throwaway_allocations",
          setdefault_allocations - len(setdefault_nodes), MAX_EDGES - 1)
    check("membership_variant_exact_allocations", corrected_allocations, MAX_EDGES + 1)
    check("membership_variant_retained_nodes", len(corrected_nodes), MAX_EDGES + 1)

    passed = all(item["passed"] for item in checks)
    receipt = {
        "case": "CASE-07",
        "source_id": "4a28aa43-10aa-4476-b33b-85cc91998975",
        "source_author": "Abbie",
        "reply_attribution": [
            {"id": "1b36564a-1547-4a56-a3c9-c65c88a9311e", "author": "Milo Humanizer"},
            {"id": "16a0de7c-2f41-4413-8742-109ca610fb28", "author": "Cerebrate's Claude Code"}
        ],
        "seed": SEED,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "command": "uv run --no-project --offline --no-managed-python python test_case_07.py --receipt receipt.json",
        "process_exit_code": 0 if passed else 1,
        "default_recursion_limit": default_limit,
        "smallest_failing_edge_count": failing,
        "smallest_failure_probe": failure_probe,
        "max_valid_edge_count": MAX_EDGES,
        "allocations": {"setdefault": setdefault_allocations,
                        "explicit_membership": corrected_allocations,
                        "retained": MAX_EDGES + 1},
        "checks": checks,
        "timing_claim": {"classification": "NOT_TESTED",
                         "reason": "The reported ~2x speedup is environment-specific and unnecessary to establish correctness."},
        "conclusion": {
            "classification": "CONFIRMED_DEFECT",
            "correct": "The original and iterative algorithms are both O(n) time and O(n) storage and agree on shallow valid trees.",
            "defect": "The original raises RecursionError on a valid maximum-depth chain. The setdefault variant allocates every default eagerly.",
            "minimal_correction": "Link cached nodes iteratively and use explicit membership checks before constructing TreeNode objects."
        }
    }
    Path(receipt_path).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"case": "CASE-07", "passed": passed, "checks": len(checks),
                      "first_failing_edges": failing}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    raise SystemExit(main(parser.parse_args().receipt))
