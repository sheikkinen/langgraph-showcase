#!/usr/bin/env python
"""Helper script to run yamlgraph generation, linting, and execution.

Usage:
    python run_generator.py "Create a simple Q&A pipeline"
    python run_generator.py --output-dir ./my-graph "Create a router pipeline"
    python run_generator.py --run "Create a linear pipeline with 2 nodes"
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# Add parent to path for yamlgraph imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load .env from project root (before yamlgraph imports)
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from yamlgraph.graph_loader import load_and_compile  # noqa: E402
from yamlgraph.tools.graph_linter import lint_graph  # noqa: E402


def generate(request: str, output_dir: str) -> dict:
    """Run the yamlgraph generator."""
    print("\n🚀 Generating graph from request...")
    print(f"   Request: {request[:80]}{'...' if len(request) > 80 else ''}")
    print(f"   Output: {output_dir}")

    graph_path = Path(__file__).parent / "graph.yaml"
    graph = load_and_compile(str(graph_path)).compile()

    result = graph.invoke(
        {
            "request": request,
            "output_dir": output_dir,
        }
    )

    files_written = result.get("files_written", [])
    status = result.get("status", "unknown")

    print("\n✅ Generation complete!")
    print(f"   Status: {status}")
    print(f"   Files: {len(files_written)}")
    for f in files_written:
        print(f"     - {f}")

    return result


def lint(output_dir: str) -> bool:
    """Lint the generated graph."""
    print("\n🔍 Linting generated graph...")

    graph_path = Path(output_dir) / "graph.yaml"
    if not graph_path.exists():
        print(f"   ❌ No graph.yaml found in {output_dir}")
        return False

    result = lint_graph(str(graph_path), output_dir)

    errors = [i for i in result.issues if i.severity == "error"]
    warnings = [i for i in result.issues if i.severity == "warning"]

    if errors:
        print(f"   ❌ {len(errors)} error(s), {len(warnings)} warning(s)")
        for issue in errors:
            print(f"     [{issue.code}] {issue.message}")
        return False
    elif warnings:
        print(f"   ⚠️  {len(warnings)} warning(s)")
        for issue in warnings:
            print(f"     [{issue.code}] {issue.message}")
    else:
        print("   ✅ No issues found")

    return True


def run_generated(output_dir: str, input_data: dict | None = None) -> dict:
    """Run the generated graph."""
    print("\n▶️  Running generated graph...")

    graph_path = Path(output_dir) / "graph.yaml"
    if not graph_path.exists():
        print(f"   ❌ No graph.yaml found in {output_dir}")
        return {}

    graph = load_and_compile(str(graph_path)).compile()

    # Use provided input or empty dict
    initial_state = input_data or {}

    print(f"   Input: {initial_state}")
    result = graph.invoke(initial_state)

    print("\n📊 Result:")
    for key, value in result.items():
        if key.startswith("_") or key in ("errors", "current_step"):
            continue
        display_value = (
            str(value)[:200] + "..." if len(str(value)) > 200 else str(value)
        )
        print(f"   {key}: {display_value}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate, lint, and run yamlgraph pipelines"
    )
    parser.add_argument(
        "request",
        nargs="?",  # Make optional for lint-only and run-only modes
        default="",
        help="Natural language request for the generator",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="./generated_graph",
        help="Output directory for generated files (default: ./generated_graph)",
    )
    parser.add_argument(
        "--run",
        "-r",
        action="store_true",
        help="Run the generated graph after generation",
    )
    parser.add_argument(
        "--input",
        "-i",
        nargs="*",
        help="Input key=value pairs for running the graph (e.g., question='What is 2+2?')",
    )
    parser.add_argument(
        "--clean",
        "-c",
        action="store_true",
        help="Clean output directory before generation",
    )
    parser.add_argument(
        "--lint-only",
        "-l",
        action="store_true",
        help="Only lint existing graph, don't generate",
    )
    parser.add_argument(
        "--run-only",
        action="store_true",
        help="Only run existing graph, don't generate",
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()

    # Parse input args
    input_data = {}
    if args.input:
        for item in args.input:
            if "=" in item:
                key, value = item.split("=", 1)
                input_data[key] = value

    # Lint only mode
    if args.lint_only:
        success = lint(str(output_dir))
        sys.exit(0 if success else 1)

    # Run only mode
    if args.run_only:
        lint(str(output_dir))
        run_generated(str(output_dir), input_data)
        print("\n✨ Done!")
        sys.exit(0)

    # Require request for generation
    if not args.request:
        parser.error("request is required for generation")

    # Clean if requested
    if args.clean and output_dir.exists():
        print(f"🧹 Cleaning {output_dir}")
        shutil.rmtree(output_dir)

    # Generate
    output_dir.mkdir(parents=True, exist_ok=True)
    generate(args.request, str(output_dir))

    # Lint
    lint_ok = lint(str(output_dir))

    # Run if requested
    if args.run:
        if not lint_ok:
            print("\n⚠️  Lint errors detected, running anyway...")
        run_generated(str(output_dir), input_data)

    print("\n✨ Done!")


if __name__ == "__main__":
    main()
