#!/usr/bin/env python3
"""Requirement Traceability coverage checker with implementation links.

Parses requirements from docs/RTM.md, extracts test markers via AST,
and optionally links tests to source files via .coverage DB or AST
import analysis.

Usage:
    python scripts/req_coverage.py                   # summary
    python scripts/req_coverage.py --detail          # per-req test list
    python scripts/req_coverage.py --implementation  # req → code → test links
    python scripts/req_coverage.py --strict          # exit 1 on gaps
"""

from __future__ import annotations

import ast
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Source prefix to match in imports and coverage DB
SRC_PREFIX = "calculator"


# ---------------------------------------------------------------------------
# 1. Parse requirements & capabilities from docs/RTM.md
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


def _load_capabilities() -> dict[str, tuple[str, list[str]]]:
    """Parse capability sections and their requirements from RTM.md.

    Returns {cap_id: (cap_name, [req_ids])} from headers like
    ``## CAP-01: Basic Arithmetic`` followed by requirement rows.
    """
    rtm = ROOT / "docs" / "RTM.md"
    if not rtm.exists():
        return {}
    caps: dict[str, tuple[str, list[str]]] = {}
    current_cap: str | None = None
    current_name: str = ""
    current_reqs: list[str] = []
    cap_pattern = re.compile(r"^##\s+(CAP-\d+):\s*(.+)$")
    req_pattern = re.compile(r"^\|\s*(REQ-CALC-\d{3})\s*\|")
    for line in rtm.read_text().splitlines():
        m = cap_pattern.match(line)
        if m:
            if current_cap:
                caps[current_cap] = (current_name, current_reqs)
            current_cap = m.group(1)
            current_name = m.group(2).strip()
            current_reqs = []
            continue
        m = req_pattern.match(line)
        if m and current_cap:
            current_reqs.append(m.group(1))
    if current_cap:
        caps[current_cap] = (current_name, current_reqs)
    return caps


# ---------------------------------------------------------------------------
# 2. Extract @pytest.mark.req markers via AST
# ---------------------------------------------------------------------------


def extract_req_markers(filepath: Path) -> dict[str, list[str]]:
    """Extract @pytest.mark.req(...) markers from a test file.

    Returns mapping of requirement ID -> list of test keys.
    Uses class-qualified keys (Class::method) to avoid collisions.
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
        key = f"{stem}::{class_name}::{node.name}" if class_name else f"{stem}::{node.name}"
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
    """Extract REQ-CALC-XXX strings from a decorator node."""
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


# ---------------------------------------------------------------------------
# 3. AST import fallback — resolve test → source file via imports
# ---------------------------------------------------------------------------


def _module_to_path(module: str) -> str:
    """Convert module name to filesystem path relative to src/.

    ``calculator`` → ``src/calculator.py``
    """
    parts = module.split(".")
    candidate = "src/" + "/".join(parts) + ".py"
    pkg_init = "src/" + "/".join(parts) + "/__init__.py"
    if (ROOT / candidate).exists():
        return candidate
    if (ROOT / pkg_init).exists():
        return pkg_init
    return candidate


def _collect_src_imports(nodes: list[ast.stmt]) -> set[str]:
    """Extract src/ file paths from import statements in AST nodes."""
    paths: set[str] = set()
    for node in ast.walk(ast.Module(body=nodes, type_ignores=[])):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(SRC_PREFIX):
            paths.add(_module_to_path(node.module))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(SRC_PREFIX):
                    paths.add(_module_to_path(alias.name))
    return paths


def _collect_mock_patch_targets(nodes: list[ast.stmt]) -> set[str]:
    """Extract src/ file paths from mock.patch("calculator...") calls."""
    paths: set[str] = set()
    for node in ast.walk(ast.Module(body=nodes, type_ignores=[])):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_patch = (isinstance(func, ast.Attribute) and func.attr == "patch") or (
            isinstance(func, ast.Name) and func.id == "patch"
        )
        if not is_patch or not node.args:
            continue
        arg = node.args[0]
        if (
            isinstance(arg, ast.Constant)
            and isinstance(arg.value, str)
            and arg.value.startswith(SRC_PREFIX)
        ):
            dotted = arg.value.rsplit(".", 1)[0]
            paths.add(_module_to_path(dotted))
    return paths


def _extract_imports_from_test(filepath: Path, test_key: str) -> set[str]:
    """Extract src/ source file paths from a test file using AST analysis.

    Parses both module-level imports and inline imports within the specific
    test function identified by *test_key*.  Also resolves mock.patch targets.

    Returns set of relative paths like ``{"src/calculator.py"}``.
    """
    try:
        tree = ast.parse(filepath.read_text(), filename=str(filepath))
    except SyntaxError:
        return set()

    # Parse test_key: "test_foo::ClassName::method" or "test_foo::func"
    parts = test_key.split("::")
    class_name = parts[1] if len(parts) == 3 else None
    func_name = parts[-1]

    # 1. Module-level imports (always included)
    module_nodes = [n for n in tree.body if isinstance(n, ast.Import | ast.ImportFrom)]
    paths = _collect_src_imports(module_nodes)

    # 2. Find the specific test function — inline imports + mock targets
    func_body: list[ast.stmt] = []
    for node in ast.iter_child_nodes(tree):
        if class_name and isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if (
                    isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
                    and item.name == func_name
                ):
                    func_body = item.body + item.decorator_list  # type: ignore[operator]
                    break
            break
        elif (
            not class_name
            and isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.name == func_name
        ):
            func_body = node.body + node.decorator_list  # type: ignore[operator]
            break

    if func_body:
        paths |= _collect_src_imports(func_body)
        paths |= _collect_mock_patch_targets(func_body)

    # Class-level decorators for mock.patch
    if class_name:
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                paths |= _collect_mock_patch_targets(node.decorator_list)
                break

    return paths


# ---------------------------------------------------------------------------
# 4. Coverage DB — resolve test → source file via .coverage SQLite
# ---------------------------------------------------------------------------


def _load_coverage_map() -> dict[str, set[str]]:
    """Load test→source file mapping from .coverage SQLite DB.

    Requires a prior run of ``pytest --cov=src --cov-context=test``.
    Returns mapping of test key → set of source files (relative paths).
    """
    db_path = ROOT / ".coverage"
    if not db_path.exists():
        return {}

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Check that contexts were recorded
    cursor.execute("SELECT COUNT(*) FROM context WHERE context != ''")
    if cursor.fetchone()[0] == 0:
        conn.close()
        return {}

    cursor.execute(
        "SELECT DISTINCT f.path, ctx.context "
        "FROM line_bits lb "
        "JOIN file f ON lb.file_id = f.id "
        "JOIN context ctx ON lb.context_id = ctx.id "
        "WHERE ctx.context != ''"
    )

    test_files: dict[str, set[str]] = defaultdict(set)
    root_str = str(ROOT) + "/"
    for file_path, context in cursor.fetchall():
        # context format: "tests/test_calculator.py::test_add_positive|run"
        test_id = context.split("|")[0]
        parts = test_id.split("::", 1)
        test_stem = Path(parts[0]).stem
        test_id = f"{test_stem}::{parts[1]}" if len(parts) > 1 else test_stem
        # Convert to relative path, filter to src/ source only
        rel_path = file_path.replace(root_str, "")
        if rel_path.startswith("src/") and "/test" not in rel_path:
            test_files[test_id].add(rel_path)

    conn.close()
    return dict(test_files)


# ---------------------------------------------------------------------------
# 5. Report
# ---------------------------------------------------------------------------


def main() -> None:
    reqs = _load_requirements()
    caps = _load_capabilities()
    all_reqs = sorted(reqs.keys())
    tests_dir = ROOT / "tests"

    # Collect all markers
    all_markers: dict[str, list[str]] = defaultdict(list)
    test_key_to_file: dict[str, Path] = {}
    for tf in sorted(tests_dir.rglob("test_*.py")):
        markers = extract_req_markers(tf)
        for req, tests in markers.items():
            all_markers[req].extend(tests)
            for t in tests:
                test_key_to_file[t] = tf

    # Stats
    total_pairs = sum(len(tests) for tests in all_markers.values())
    unique_tests = {t for tests in all_markers.values() for t in tests}
    covered = [r for r in all_reqs if r in all_markers]
    uncovered = [r for r in all_reqs if r not in all_markers]

    print("=" * 70)
    print("REQUIREMENT TRACEABILITY REPORT")
    print("=" * 70)
    print(f"\nRequirements: {len(covered)}/{len(all_reqs)} covered")
    print(f"Tagged tests: {len(unique_tests)} unique, {total_pairs} test-req pairs")
    print()

    # Per-capability summary
    if caps:
        print("CAPABILITY COVERAGE")
        print("-" * 70)
        for cap_id, (cap_name, cap_reqs) in caps.items():
            cap_covered = sum(1 for r in cap_reqs if r in all_markers)
            cap_tests = sum(len(all_markers.get(r, [])) for r in cap_reqs)
            status = "✅" if cap_covered == len(cap_reqs) else "⚠️ " if cap_covered > 0 else "❌"
            print(
                f"  {status} {cap_id} {cap_name}: "
                f"{cap_covered}/{len(cap_reqs)} reqs, {cap_tests} tests"
            )

    # Uncovered requirements
    if uncovered:
        print(f"\nUNCOVERED REQUIREMENTS ({len(uncovered)})")
        print("-" * 70)
        for req in uncovered:
            print(f"  ❌ {req}  {reqs.get(req, '')}")

    # Detail: per-requirement test list
    if "--detail" in sys.argv:
        print("\nDETAILED MAPPING")
        print("-" * 70)
        for req in all_reqs:
            tests = all_markers.get(req, [])
            desc = reqs.get(req, "")
            if tests:
                print(f"\n  {req}  {desc}  ({len(tests)} tests):")
                for t in tests:
                    print(f"    - {t}")
            else:
                print(f"\n  {req}  {desc}: NO TESTS")

    # Implementation: req → source files (coverage DB + AST fallback) → tests
    if "--implementation" in sys.argv:
        coverage_map = _load_coverage_map()
        has_coverage = bool(coverage_map)
        if not has_coverage:
            print(
                "\n⚠️  No .coverage database. For coverage-based links, run:\n"
                "    pytest --cov=src --cov-context=test\n"
                "  Falling back to AST import analysis.\n"
            )

        print("\nIMPLEMENTATION TRACEABILITY")
        print("=" * 70)
        ast_resolved_count = 0
        still_unresolved_count = 0

        cap_items = caps.items() if caps else [("", ("Ungrouped", all_reqs))]
        for cap_id, (cap_name, cap_reqs) in cap_items:
            cap_tests_total = sum(len(all_markers.get(r, [])) for r in cap_reqs)
            header = f"{cap_id} {cap_name}" if cap_id else cap_name
            print(f"\n── {header} ({len(cap_reqs)} reqs, {cap_tests_total} tests) {'─' * 20}")

            for req in cap_reqs:
                desc = reqs.get(req, "")
                tests = all_markers.get(req, [])
                if not tests:
                    print(f"\n    {req}  {desc}")
                    print("      NO TESTS")
                    continue

                # Aggregate source files across all tests for this req
                source_files: set[str] = set()
                matched_tests: list[str] = []
                ast_tests: list[str] = []
                unmatched_tests: list[str] = []
                for test in tests:
                    files = coverage_map.get(test, set())
                    if files:
                        source_files.update(files)
                        matched_tests.append(test)
                    else:
                        # AST fallback: parse imports from test file
                        test_file = test_key_to_file.get(test)
                        if test_file:
                            ast_files = _extract_imports_from_test(test_file, test)
                            if ast_files:
                                source_files.update(ast_files)
                                ast_tests.append(test)
                                ast_resolved_count += 1
                                continue
                        unmatched_tests.append(test)
                        still_unresolved_count += 1

                print(f"\n    {req}  {desc}")
                print(f"      ({len(source_files)} files, {len(tests)} tests)")
                if source_files:
                    print("      Implementation:")
                    for sf in sorted(source_files):
                        print(f"        {sf}")
                if matched_tests:
                    print("      Tests (coverage):")
                    for t in matched_tests:
                        print(f"        {t}")
                if ast_tests:
                    print("      Tests (AST imports):")
                    for t in ast_tests:
                        print(f"        {t}")
                if unmatched_tests:
                    print("      Tests (no link):")
                    for t in unmatched_tests:
                        print(f"        {t}")

        print(
            f"\n  Summary: {ast_resolved_count} tests resolved via AST fallback, "
            f"{still_unresolved_count} unresolvable"
        )

    # Exit code: fail if any requirement uncovered
    if uncovered and "--strict" in sys.argv:
        sys.exit(1)


if __name__ == "__main__":
    main()
