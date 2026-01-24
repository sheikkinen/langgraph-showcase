"""Graph runner for yamlgraph-generator execution validation."""

import subprocess
from pathlib import Path


def run_graph(graph_path: str, variables: dict | None = None) -> dict:
    """Run the generated graph with real LLM execution.

    Args:
        graph_path: Path to the graph.yaml file
        variables: Dict of variables to pass (--var key=value)

    Returns dict: {valid: bool, stdout: str, stderr: str, errors: list[str]}
    """
    if not Path(graph_path).exists():
        return {
            "valid": False,
            "stdout": "",
            "stderr": "",
            "errors": [f"Graph file not found: {graph_path}"],
        }

    args = ["yamlgraph", "graph", "run", graph_path]

    if variables:
        for key, value in variables.items():
            args.extend(["--var", f"{key}={value}"])

    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=300,  # 5 minute max
    )

    errors = _parse_run_errors(result.stderr) if result.returncode != 0 else []

    return {
        "valid": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "errors": errors,
    }


def _parse_run_errors(stderr: str) -> list[str]:
    """Parse runtime errors into structured list."""
    errors = []
    in_traceback = False

    for line in stderr.split("\n"):
        if "Traceback" in line:
            in_traceback = True
        elif in_traceback:
            # End of traceback is the actual error message
            if (
                line.strip()
                and not line.startswith(" ")
                and not line.startswith("\t")
                and ("Error" in line or "Exception" in line)
            ):
                errors.append(line.strip())
                in_traceback = False
        elif "Error" in line or "error:" in line.lower():
            errors.append(line.strip())

    return errors if errors else [stderr.strip()] if stderr.strip() else []


def run_graph_with_test_inputs(graph_path: str, pattern: str) -> dict:
    """Run graph with pattern-appropriate test inputs.

    Generates test inputs based on detected pattern.
    """
    test_inputs = {
        "router": {"message": "Test classification message"},
        "map": {"items": '["item1", "item2", "item3"]'},
        "linear": {"topic": "Test topic"},
        "interview": {},  # Interactive, can't auto-test
    }

    variables = test_inputs.get(pattern, {})
    return run_graph(graph_path, variables)
