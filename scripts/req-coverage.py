#!/usr/bin/env python3
"""Collect @pytest.mark.req markers and report requirement coverage.

Usage:
    pytest --collect-only -q 2>/dev/null | python scripts/req-coverage.py
    # or directly:
    python scripts/req-coverage.py
"""

from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path

# All known requirements
ALL_REQS = [f"REQ-YG-{i:03d}" for i in range(1, 59)]

# Capability grouping
CAPABILITIES = {
    "1. Config Loading & Validation": [
        "REQ-YG-001",
        "REQ-YG-002",
        "REQ-YG-003",
        "REQ-YG-004",
    ],
    "2. Graph Compilation": ["REQ-YG-005", "REQ-YG-006", "REQ-YG-007", "REQ-YG-008"],
    "3. Node Execution": ["REQ-YG-009", "REQ-YG-010", "REQ-YG-011", "REQ-YG-050"],
    "4. Prompt Execution": [
        "REQ-YG-012",
        "REQ-YG-013",
        "REQ-YG-014",
        "REQ-YG-015",
        "REQ-YG-016",
    ],
    "5. Tool & Agent Integration": [
        "REQ-YG-017",
        "REQ-YG-018",
        "REQ-YG-019",
        "REQ-YG-020",
    ],
    "6. Routing & Flow Control": ["REQ-YG-021", "REQ-YG-022", "REQ-YG-023"],
    "7. State Persistence": ["REQ-YG-024", "REQ-YG-025", "REQ-YG-026"],
    "8. Error Handling": [
        "REQ-YG-027",
        "REQ-YG-028",
        "REQ-YG-029",
        "REQ-YG-030",
        "REQ-YG-031",
    ],
    "9. CLI Interface": ["REQ-YG-032", "REQ-YG-033", "REQ-YG-034", "REQ-YG-035"],
    "10. Export & Serialization": [
        "REQ-YG-036",
        "REQ-YG-037",
        "REQ-YG-038",
        "REQ-YG-039",
    ],
    "11. Subgraph & Map": ["REQ-YG-040", "REQ-YG-041", "REQ-YG-042"],
    "12. Utilities": ["REQ-YG-043", "REQ-YG-044", "REQ-YG-045", "REQ-YG-046"],
    "13. LangSmith Tracing": ["REQ-YG-047"],
    "14. Graph-Level Streaming": ["REQ-YG-048", "REQ-YG-049"],
    "15. Expression Language": ["REQ-YG-051", "REQ-YG-052"],
    "16. Linter Cross-Reference": ["REQ-YG-053", "REQ-YG-054"],
    "17. Execution Safety Guards": [
        "REQ-YG-055",
        "REQ-YG-056",
        "REQ-YG-057",
        "REQ-YG-058",
    ],
}


def extract_req_markers(filepath: Path) -> dict[str, list[str]]:
    """Extract @pytest.mark.req(...) markers from a test file.

    Returns mapping of requirement ID -> list of test names.
    Uses class-qualified keys (Class::method) to avoid collisions
    when multiple classes share method names.
    """
    try:
        tree = ast.parse(filepath.read_text(), filename=str(filepath))
    except SyntaxError:
        return {}

    req_map: dict[str, list[str]] = defaultdict(list)
    stem = filepath.stem

    def _process_func(
        node: ast.FunctionDef | ast.AsyncFunctionDef, class_name: str | None
    ) -> None:
        if not node.name.startswith("test"):
            return
        key = (
            f"{stem}::{class_name}::{node.name}"
            if class_name
            else f"{stem}::{node.name}"
        )
        for decorator in node.decorator_list:
            reqs = _extract_req_from_decorator(decorator)
            for req in reqs:
                req_map[req].append(key)

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    _process_func(item, node.name)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            _process_func(node, None)

    return dict(req_map)


def _extract_req_from_decorator(node: ast.expr) -> list[str]:
    """Extract REQ-YG-XXX strings from a decorator node."""
    # @pytest.mark.req("REQ-YG-014")
    # @pytest.mark.req("REQ-YG-014", "REQ-YG-031")
    if isinstance(node, ast.Call):
        func = node.func
        if _is_req_marker(func):
            return [
                arg.value
                for arg in node.args
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
            ]
    return []


def _is_req_marker(node: ast.expr) -> bool:
    """Check if node represents pytest.mark.req."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "req"
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
    )


def main() -> None:
    root = Path(__file__).parent.parent
    test_dirs = [root / "tests" / "unit", root / "tests" / "integration"]

    # Collect all markers
    all_markers: dict[str, list[str]] = defaultdict(list)
    for test_dir in test_dirs:
        if not test_dir.exists():
            continue
        for filepath in sorted(test_dir.rglob("test_*.py")):
            markers = extract_req_markers(filepath)
            for req, tests in markers.items():
                all_markers[req].extend(tests)

    # Report
    total_pairs = sum(len(tests) for tests in all_markers.values())
    unique_tests = {t for tests in all_markers.values() for t in tests}
    covered = [r for r in ALL_REQS if r in all_markers]
    uncovered = [r for r in ALL_REQS if r not in all_markers]

    print("=" * 70)
    print("REQUIREMENT TRACEABILITY REPORT")
    print("=" * 70)
    print(f"\nRequirements: {len(covered)}/{len(ALL_REQS)} covered")
    print(f"Tagged tests: {len(unique_tests)} unique, {total_pairs} test-req pairs")
    print()

    # Per-capability summary
    print("CAPABILITY COVERAGE")
    print("-" * 70)
    for cap_name, reqs in CAPABILITIES.items():
        cap_covered = sum(1 for r in reqs if r in all_markers)
        cap_tests = sum(len(all_markers.get(r, [])) for r in reqs)
        status = "✅" if cap_covered == len(reqs) else "⚠️ " if cap_covered > 0 else "❌"
        print(
            f"  {status} {cap_name}: {cap_covered}/{len(reqs)} reqs, {cap_tests} tests"
        )

    # Uncovered requirements
    if uncovered:
        print(f"\nUNCOVERED REQUIREMENTS ({len(uncovered)})")
        print("-" * 70)
        for req in uncovered:
            print(f"  ❌ {req}")

    # Detail: per-requirement test list
    if "--detail" in sys.argv:
        print("\nDETAILED MAPPING")
        print("-" * 70)
        for req in ALL_REQS:
            tests = all_markers.get(req, [])
            if tests:
                print(f"\n  {req} ({len(tests)} tests):")
                for t in tests:
                    print(f"    - {t}")
            else:
                print(f"\n  {req}: NO TESTS")

    # Exit code: fail if any requirement uncovered
    if uncovered and "--strict" in sys.argv:
        sys.exit(1)


if __name__ == "__main__":
    main()
