#!/usr/bin/env python3
"""Collect @pytest.mark.req markers and report requirement coverage.

Usage:
    python scripts/req_coverage.py                 # summary
    python scripts/req_coverage.py --detail        # per-req test list
    python scripts/req_coverage.py --implementation  # req → code → test links
    python scripts/req_coverage.py --strict        # exit 1 on gaps
"""

from __future__ import annotations

import ast
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

# All known requirements
ALL_REQS = [f"REQ-YG-{i:03d}" for i in range(1, 66)]

# Capability grouping: (cap_id, name, [reqs])
CAPABILITIES: dict[str, tuple[str, list[str]]] = {
    "CAP-01": (
        "Config Loading & Validation",
        [
            "REQ-YG-001",
            "REQ-YG-002",
            "REQ-YG-003",
            "REQ-YG-004",
        ],
    ),
    "CAP-02": (
        "Graph Compilation",
        [
            "REQ-YG-005",
            "REQ-YG-006",
            "REQ-YG-007",
            "REQ-YG-008",
        ],
    ),
    "CAP-03": (
        "Node Execution",
        [
            "REQ-YG-009",
            "REQ-YG-010",
            "REQ-YG-011",
            "REQ-YG-050",
        ],
    ),
    "CAP-04": (
        "Prompt Execution",
        [
            "REQ-YG-012",
            "REQ-YG-013",
            "REQ-YG-014",
            "REQ-YG-015",
            "REQ-YG-016",
        ],
    ),
    "CAP-05": (
        "Tool & Agent Integration",
        [
            "REQ-YG-017",
            "REQ-YG-018",
            "REQ-YG-019",
            "REQ-YG-020",
        ],
    ),
    "CAP-06": (
        "Routing & Flow Control",
        [
            "REQ-YG-021",
            "REQ-YG-022",
            "REQ-YG-023",
        ],
    ),
    "CAP-07": (
        "State Persistence",
        [
            "REQ-YG-024",
            "REQ-YG-025",
            "REQ-YG-026",
        ],
    ),
    "CAP-08": (
        "Error Handling",
        [
            "REQ-YG-027",
            "REQ-YG-028",
            "REQ-YG-029",
            "REQ-YG-030",
            "REQ-YG-031",
        ],
    ),
    "CAP-09": (
        "CLI Interface",
        [
            "REQ-YG-032",
            "REQ-YG-033",
            "REQ-YG-034",
            "REQ-YG-035",
        ],
    ),
    "CAP-10": (
        "Export & Serialization",
        [
            "REQ-YG-036",
            "REQ-YG-037",
            "REQ-YG-038",
            "REQ-YG-039",
        ],
    ),
    "CAP-11": (
        "Subgraph & Map",
        [
            "REQ-YG-040",
            "REQ-YG-041",
            "REQ-YG-042",
        ],
    ),
    "CAP-12": (
        "Utilities",
        [
            "REQ-YG-043",
            "REQ-YG-044",
            "REQ-YG-045",
            "REQ-YG-046",
        ],
    ),
    "CAP-13": ("LangSmith Tracing", ["REQ-YG-047"]),
    "CAP-14": ("Graph-Level Streaming", ["REQ-YG-048", "REQ-YG-049", "REQ-YG-065"]),
    "CAP-15": ("Expression Language", ["REQ-YG-051", "REQ-YG-052"]),
    "CAP-16": ("Linter Cross-Reference", ["REQ-YG-053", "REQ-YG-054"]),
    "CAP-17": (
        "Execution Safety Guards",
        [
            "REQ-YG-055",
            "REQ-YG-056",
            "REQ-YG-057",
            "REQ-YG-058",
            "REQ-YG-059",
            "REQ-YG-060",
            "REQ-YG-061",
            "REQ-YG-062",
            "REQ-YG-064",
        ],
    ),
    "CAP-18": ("Testing & Quality", ["REQ-YG-063"]),
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


def _module_to_path(module: str) -> str:
    """Convert dotted module name to filesystem path.

    ``yamlgraph.utils.llm_factory`` → ``yamlgraph/utils/llm_factory.py``
    ``yamlgraph.cli`` → ``yamlgraph/cli/__init__.py`` (if directory exists)
    """
    parts = module.split(".")
    candidate = "/".join(parts) + ".py"
    pkg_init = "/".join(parts) + "/__init__.py"
    root = Path(__file__).parent.parent
    if (root / candidate).exists():
        return candidate
    if (root / pkg_init).exists():
        return pkg_init
    # Default: assume .py file (even if missing — the import may be removed code)
    return candidate


def _collect_yamlgraph_imports(nodes: list[ast.stmt]) -> set[str]:
    """Extract yamlgraph/ file paths from import statements in AST nodes."""
    paths: set[str] = set()
    for node in ast.walk(ast.Module(body=nodes, type_ignores=[])):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("yamlgraph")
        ):
            paths.add(_module_to_path(node.module))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("yamlgraph"):
                    paths.add(_module_to_path(alias.name))
    return paths


def _collect_mock_patch_targets(nodes: list[ast.stmt]) -> set[str]:
    """Extract yamlgraph/ file paths from mock.patch("yamlgraph...") calls."""
    paths: set[str] = set()
    for node in ast.walk(ast.Module(body=nodes, type_ignores=[])):
        if not isinstance(node, ast.Call):
            continue
        # Match @patch("yamlgraph.x.y.z") or mock.patch("yamlgraph.x.y.z")
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
            and arg.value.startswith("yamlgraph")
        ):
            # "yamlgraph.utils.llm_factory.create_llm" → "yamlgraph.utils.llm_factory"
            dotted = arg.value.rsplit(".", 1)[0]
            paths.add(_module_to_path(dotted))
    return paths


def _extract_imports_from_test(filepath: Path, test_key: str) -> set[str]:
    """Extract yamlgraph/ source file paths from a test file using AST analysis.

    Parses both module-level imports and inline imports within the specific
    test function identified by *test_key* (``stem::Class::method`` or
    ``stem::function``).  Also resolves ``mock.patch("yamlgraph.X.Y.func")``
    targets.

    Returns set of relative paths like ``{"yamlgraph/utils/llm_factory.py"}``.
    """
    try:
        tree = ast.parse(filepath.read_text(), filename=str(filepath))
    except SyntaxError:
        return set()

    # Parse test_key: "test_foo::ClassName::method" or "test_foo::func"
    parts = test_key.split("::")
    # parts[0] is stem (ignored — we already have filepath)
    class_name = parts[1] if len(parts) == 3 else None
    func_name = parts[-1]

    # 1. Module-level imports (always included)
    module_nodes = [n for n in tree.body if isinstance(n, ast.Import | ast.ImportFrom)]
    paths = _collect_yamlgraph_imports(module_nodes)

    # 2. Find the specific test function and extract inline imports + mock targets
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
        paths |= _collect_yamlgraph_imports(func_body)
        paths |= _collect_mock_patch_targets(func_body)

    # Also check class-level decorators for mock.patch
    if class_name:
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                paths |= _collect_mock_patch_targets(node.decorator_list)
                break

    return paths


def _load_req_descriptions(root: Path) -> dict[str, str]:
    """Parse requirement descriptions from ARCHITECTURE.md.

    Matches lines like ``| REQ-YG-001 | Load graph configurations... | modules |``
    and returns ``{"REQ-YG-001": "Load graph configurations..."}``.
    """
    arch_path = root / "ARCHITECTURE.md"
    if not arch_path.exists():
        return {}
    descriptions: dict[str, str] = {}
    pattern = re.compile(r"^\|\s*(REQ-YG-\d{3})\s*\|\s*(.+?)\s*\|")
    for line in arch_path.read_text().splitlines():
        m = pattern.match(line)
        if m:
            req_id, desc = m.group(1), m.group(2).strip()
            # First match wins (avoid duplicate REQ-YG-047 rows)
            if req_id not in descriptions:
                descriptions[req_id] = desc
    return descriptions


def _load_coverage_map(root: Path) -> dict[str, set[str]]:
    """Load test→source file mapping from .coverage SQLite DB.

    Requires a prior run of ``pytest --cov=yamlgraph --cov-context=test``.
    Returns mapping of test node id → set of source files (relative paths).
    """
    db_path = root / ".coverage"
    if not db_path.exists():
        print(
            "⚠️  No .coverage database found. Run first:\n"
            "    pytest --cov=yamlgraph --cov-context=test\n"
        )
        return {}

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Check that contexts were recorded
    cursor.execute("SELECT COUNT(*) FROM context WHERE context != ''")
    if cursor.fetchone()[0] == 0:
        print(
            "⚠️  .coverage DB has no test contexts. Re-run with:\n"
            "    pytest --cov=yamlgraph --cov-context=test\n"
        )
        conn.close()
        return {}

    # line_bits stores (file_id, context_id, numbits) — existence = test touched file
    cursor.execute(
        "SELECT DISTINCT f.path, ctx.context "
        "FROM line_bits lb "
        "JOIN file f ON lb.file_id = f.id "
        "JOIN context ctx ON lb.context_id = ctx.id "
        "WHERE ctx.context != ''"
    )

    test_files: dict[str, set[str]] = defaultdict(set)
    root_str = str(root) + "/"
    for file_path, context in cursor.fetchall():
        # context format: "tests/unit/test_foo.py::Class::method|run"
        # Normalize to match AST marker keys: "test_foo::Class::method"
        test_id = context.split("|")[0]
        # Strip path prefix and .py extension from test file part
        parts = test_id.split("::", 1)
        test_stem = Path(parts[0]).stem  # "tests/unit/test_foo.py" → "test_foo"
        test_id = f"{test_stem}::{parts[1]}" if len(parts) > 1 else test_stem
        # Convert absolute source path to relative, filter to yamlgraph/ source only
        rel_path = file_path.replace(root_str, "")
        if rel_path.startswith("yamlgraph/") and "/test" not in rel_path:
            test_files[test_id].add(rel_path)

    conn.close()
    return dict(test_files)


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
    for cap_id, (cap_name, reqs) in CAPABILITIES.items():
        cap_covered = sum(1 for r in reqs if r in all_markers)
        cap_tests = sum(len(all_markers.get(r, [])) for r in reqs)
        status = "✅" if cap_covered == len(reqs) else "⚠️ " if cap_covered > 0 else "❌"
        print(
            f"  {status} {cap_id} {cap_name}: {cap_covered}/{len(reqs)} reqs, {cap_tests} tests"
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

    # Implementation: req → source files (from coverage + AST fallback) → tests
    if "--implementation" in sys.argv:
        coverage_map = _load_coverage_map(root)
        req_descriptions = _load_req_descriptions(root)

        # Build test_key → filepath index for AST fallback
        test_key_to_file: dict[str, Path] = {}
        for test_dir in test_dirs:
            if not test_dir.exists():
                continue
            for filepath in sorted(test_dir.rglob("test_*.py")):
                markers = extract_req_markers(filepath)
                for tests in markers.values():
                    for test_key in tests:
                        test_key_to_file[test_key] = filepath

        print("\nIMPLEMENTATION TRACEABILITY")
        print("=" * 70)
        ast_resolved_count = 0
        still_unresolved_count = 0

        for cap_id, (cap_name, cap_reqs) in CAPABILITIES.items():
            cap_tests_total = sum(len(all_markers.get(r, [])) for r in cap_reqs)
            print(
                f"\n── {cap_id} {cap_name} ({len(cap_reqs)} reqs, "
                f"{cap_tests_total} tests) {'─' * 20}"
            )

            for req in cap_reqs:
                desc = req_descriptions.get(req, "")
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
