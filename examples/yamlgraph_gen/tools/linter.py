"""Graph linter wrapper for yamlgraph-generator."""

import subprocess
from pathlib import Path


def lint_graph(graph_path: str) -> dict:
    """Run yamlgraph graph lint on the generated graph.

    Returns dict: {valid: bool, output: str, errors: list[str]}
    """
    if not Path(graph_path).exists():
        return {
            "valid": False,
            "output": "",
            "errors": [f"Graph file not found: {graph_path}"],
        }

    result = subprocess.run(
        ["yamlgraph", "graph", "lint", graph_path],
        capture_output=True,
        text=True,
    )

    errors = _parse_lint_errors(result.stderr) if result.returncode != 0 else []

    return {
        "valid": result.returncode == 0,
        "output": result.stdout,
        "errors": errors,
        "lint_result": {
            "valid": result.returncode == 0,
            "errors": errors,
        },
    }


def _parse_lint_errors(stderr: str) -> list[str]:
    """Parse lint error output into structured list."""
    errors = []
    for line in stderr.strip().split("\n"):
        line = line.strip()
        # Skip traceback noise, keep meaningful errors
        if (
            line
            and not line.startswith("Traceback")
            and ("Error" in line or "error" in line or "missing" in line.lower())
        ):
            errors.append(line)
    return errors if errors else [stderr.strip()] if stderr.strip() else []


def lint_graph_node(state: dict) -> dict:
    """Yamlgraph node wrapper for lint_graph.

    Extracts graph_path from state.output_dir.
    """
    output_dir = state.get("output_dir", "")
    graph_path = str(Path(output_dir) / "graph.yaml")
    return lint_graph(graph_path)
