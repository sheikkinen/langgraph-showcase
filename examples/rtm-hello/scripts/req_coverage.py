#!/usr/bin/env python3
"""Minimal Requirement Traceability coverage checker.

Parses requirements from docs/RTM.md and test markers via AST.
Verifies every requirement has at least one tagged test.

Usage:
    python scripts/req_coverage.py              # summary
    python scripts/req_coverage.py --detail     # per-req test list
    python scripts/req_coverage.py --strict     # exit 1 if gaps
"""

from __future__ import annotations

import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 1. Parse requirements from docs/RTM.md
# ---------------------------------------------------------------------------


def _load_requirements() -> dict[str, str]:
    """Return {req_id: description} from the RTM table."""
    rtm = ROOT / "docs" / "RTM.md"
    if not rtm.exists():
        sys.exit(f"ERROR: {rtm} not found")
    reqs: dict[str, str] = {}
    for line in rtm.read_text().splitlines():
        m = re.match(r"^\|\s*(REQ-CALC-\d{3})\s*\|\s*(.+?)\s*\|", line)
        if m:
            reqs[m.group(1)] = m.group(2).strip()
    return reqs


# ---------------------------------------------------------------------------
# 2. Extract @pytest.mark.req markers via AST
# ---------------------------------------------------------------------------


def _extract_markers(test_file: Path) -> dict[str, list[str]]:
    """Return {test_name: [req_ids]} from a test file."""
    tree = ast.parse(test_file.read_text(), filename=str(test_file))
    result: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            reqs: list[str] = []
            for dec in node.decorator_list:
                reqs.extend(_reqs_from_decorator(dec))
            result[node.name] = reqs
    return result


def _reqs_from_decorator(dec: ast.expr) -> list[str]:
    """Extract REQ-CALC-XXX strings from a @pytest.mark.req(...) decorator."""
    # Match: pytest.mark.req("REQ-CALC-001", "REQ-CALC-002")
    if not isinstance(dec, ast.Call):
        return []
    func = dec.func
    # pytest.mark.req
    if isinstance(func, ast.Attribute) and func.attr == "req":
        return [
            arg.value
            for arg in dec.args
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
        ]
    return []


# ---------------------------------------------------------------------------
# 3. Build coverage map
# ---------------------------------------------------------------------------


def _build_map() -> dict[str, list[str]]:
    """Return {req_id: [test_node_ids]}."""
    tests_dir = ROOT / "tests"
    mapping: dict[str, list[str]] = defaultdict(list)
    for tf in sorted(tests_dir.rglob("test_*.py")):
        rel = tf.relative_to(ROOT)
        markers = _extract_markers(tf)
        for test_name, req_ids in markers.items():
            node_id = f"{rel}::{test_name}"
            for req in req_ids:
                mapping[req].append(node_id)
    return dict(mapping)


# ---------------------------------------------------------------------------
# 4. Report
# ---------------------------------------------------------------------------


def main() -> None:
    detail = "--detail" in sys.argv
    strict = "--strict" in sys.argv

    reqs = _load_requirements()
    mapping = _build_map()

    covered = 0
    gaps: list[str] = []

    for req_id in sorted(reqs):
        tests = mapping.get(req_id, [])
        desc = reqs[req_id]
        if tests:
            covered += 1
            if detail:
                print(f"  {req_id}  {desc}")
                for t in tests:
                    print(f"    - {t}")
            else:
                print(f"  {req_id}  {desc}  ({len(tests)} tests)")
        else:
            gaps.append(req_id)
            marker = "MISSING" if strict else "no tests"
            print(f"  {req_id}  {desc}  ** {marker} **")

    total = len(reqs)
    print(f"\n  {covered}/{total} requirements covered")

    if strict and gaps:
        print(f"\n  STRICT FAIL: {len(gaps)} requirement(s) with no tests:")
        for g in gaps:
            print(f"    - {g}")
        sys.exit(1)


if __name__ == "__main__":
    main()
