"""Example discovery tools for implementation agent.

Find usage examples and error handling patterns across the codebase.
"""

from __future__ import annotations

import ast
from pathlib import Path


def find_example(
    symbol_name: str,
    project_path: str,
    max_examples: int = 3,
) -> dict:
    """Find real usage examples of a function/class.

    Prioritizes:
    1. Test files (most complete examples)
    2. Main modules (production usage)
    3. Examples folder

    Args:
        symbol_name: Name of the symbol to find examples for
        project_path: Root path to search
        max_examples: Maximum examples to return

    Returns:
        dict with 'examples' list of {file, line, snippet}
        or dict with 'error' key if failed
    """
    project = Path(project_path)
    if not project.exists():
        return {"error": f"Project path not found: {project_path}"}

    examples = []
    test_examples = []
    other_examples = []

    # Search all Python files
    for py_file in project.rglob("*.py"):
        try:
            source = py_file.read_text()
        except (OSError, UnicodeDecodeError):
            continue

        # Skip if symbol is defined here (we want usages, not definitions)
        if _is_definition(source, symbol_name):
            continue

        # Find all occurrences
        lines = source.splitlines()
        for i, line in enumerate(lines, 1):
            if symbol_name in line and _is_usage(line, symbol_name):
                # Extract context (3 lines before and after)
                start = max(0, i - 3)
                end = min(len(lines), i + 3)
                snippet = "\n".join(lines[start:end])

                example = {
                    "file": str(py_file),
                    "line": i,
                    "snippet": snippet,
                }

                # Prioritize test files
                if "test" in py_file.name.lower():
                    test_examples.append(example)
                else:
                    other_examples.append(example)

    # Combine: tests first, then others
    examples = test_examples + other_examples

    return {"examples": examples[:max_examples]}


def _is_definition(source: str, symbol_name: str) -> bool:
    """Check if this file defines the symbol."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == symbol_name:
                return True
        elif isinstance(node, ast.ClassDef):
            if node.name == symbol_name:
                return True

    return False


def _is_usage(line: str, symbol_name: str) -> bool:
    """Check if line contains actual usage (not import or def)."""
    stripped = line.strip()

    # Skip definitions
    if stripped.startswith("def ") and f"def {symbol_name}" in stripped:
        return False
    if stripped.startswith("class ") and f"class {symbol_name}" in stripped:
        return False

    # Skip import-only lines
    if stripped.startswith("from ") and stripped.endswith(f"import {symbol_name}"):
        return False

    # Must be a call or reference
    return f"{symbol_name}(" in line or f"{symbol_name}." in line


def find_error_handling(project_path: str) -> dict:
    """Analyze error handling patterns in a project.

    Args:
        project_path: Root path to analyze

    Returns:
        dict with:
        - exceptions: List of exception types used
        - patterns: List of pattern names found
        - logging: Dict with logging info
        or dict with 'error' key if failed
    """
    project = Path(project_path)
    if not project.exists():
        return {"error": f"Project path not found: {project_path}"}

    exceptions: set[str] = set()
    patterns: list[str] = []
    uses_logging = False
    uses_dict_error = False

    for py_file in project.rglob("*.py"):
        try:
            source = py_file.read_text()
        except (OSError, UnicodeDecodeError):
            continue

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        # Find exception types
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type:
                    exc_types = _extract_exception_types(node.type)
                    exceptions.update(exc_types)

        # Check for dict error pattern
        if 'return {"error"' in source or "return {'error'" in source:
            uses_dict_error = True

        # Check for logging
        if "logger.error" in source or "logging.error" in source:
            uses_logging = True

    # Build patterns list
    if uses_dict_error:
        patterns.append("dict_error")
    if exceptions:
        patterns.append("try_except")

    return {
        "exceptions": sorted(exceptions),
        "patterns": patterns,
        "logging": {"uses_logging": uses_logging},
    }


def _extract_exception_types(node: ast.expr) -> list[str]:
    """Extract exception type names from except clause."""
    types = []

    if isinstance(node, ast.Name):
        types.append(node.id)
    elif isinstance(node, ast.Tuple):
        for elt in node.elts:
            if isinstance(elt, ast.Name):
                types.append(elt.id)
    elif isinstance(node, ast.Attribute):
        # e.g., requests.exceptions.Timeout
        types.append(node.attr)

    return types
