"""CLI command implementations.

Contains all cmd_* functions for CLI subcommands.
"""

import sys
from argparse import Namespace
from typing import Any

from pydantic import BaseModel

from yamlgraph.cli.validators import validate_run_args

# Internal keys to skip when formatting results
_INTERNAL_KEYS = frozenset(
    {
        "_route",
        "_loop_counts",
        "thread_id",
        "current_step",
        "errors",
        "topic",
        "style",
        "word_count",
    }
)


def _format_value(value: Any, max_length: int = 200) -> str:
    """Format a single value for display.

    Args:
        value: The value to format (str, list, Pydantic model, etc.)
        max_length: Maximum length before truncation

    Returns:
        Formatted string representation
    """
    if isinstance(value, BaseModel):
        # Format Pydantic model as key: value pairs
        lines = []
        for field_name, field_value in value.model_dump().items():
            formatted = _format_value(field_value, max_length)
            lines.append(f"   {field_name}: {formatted}")
        return "\n" + "\n".join(lines)

    if isinstance(value, list):
        # Format list items
        if not value:
            return "[]"
        if len(value) <= 3:
            return str(value)
        return f"[{len(value)} items]"

    if isinstance(value, str):
        if len(value) > max_length:
            return value[:max_length] + "..."
        return value

    return str(value)


def _format_result(result: dict[str, Any]) -> None:
    """Format and print pipeline result generically.

    Iterates over all non-internal keys in the result dict
    and prints their values. Works with any Pydantic model.

    Args:
        result: Pipeline result dict with arbitrary Pydantic models
    """
    for key, value in result.items():
        if key in _INTERNAL_KEYS or value is None:
            continue

        print(f"\n📝 {key}:")
        formatted = _format_value(value)
        if formatted.startswith("\n"):
            print(formatted)
        else:
            print(f"   {formatted}")


def cmd_list_runs(args: Namespace) -> None:
    """List recent pipeline runs.

    .. deprecated:: 0.4.0
        Use LangSmith UI to browse runs instead.
    """
    import warnings

    warnings.warn(
        "yamlgraph list-runs is deprecated. Use LangSmith UI instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    print("⚠️  DEPRECATED: Use LangSmith UI to browse runs instead")

    from yamlgraph.storage import YamlGraphDB

    db = YamlGraphDB()
    runs = db.list_runs(limit=args.limit)

    if not runs:
        print("No runs found.")
        return

    print(f"\n📋 Recent runs ({len(runs)}):\n")
    print(f"{'Thread ID':<12} {'Status':<12} {'Updated':<20}")
    print("-" * 50)

    for run in runs:
        print(f"{run['thread_id']:<12} {run['status']:<12} {run['updated_at'][:19]}")

    print()


def cmd_resume(args: Namespace) -> None:
    """Resume a pipeline from saved state.

    .. deprecated:: 0.4.0
        Use `yamlgraph graph run <graph.yaml> --thread <id>` instead.
    """
    import warnings

    warnings.warn(
        "yamlgraph resume is deprecated. Use: "
        "yamlgraph graph run <graph.yaml> --thread <id>",
        DeprecationWarning,
        stacklevel=2,
    )
    print(
        "⚠️  DEPRECATED: Use 'yamlgraph graph run <graph.yaml> --thread <id>' instead"
    )

    from yamlgraph.builder import build_resume_graph
    from yamlgraph.storage import YamlGraphDB

    db = YamlGraphDB()
    state = db.load_state(args.thread_id)

    if not state:
        print(f"❌ No run found with thread_id: {args.thread_id}")
        return

    print(f"\n🔄 Resuming from: {state.get('current_step', 'unknown')}")

    # Check what's already completed
    if state.get("final_summary"):
        print("✅ Pipeline already complete!")
        return

    # Show what will be skipped vs run
    skipping = []
    running = []
    if state.get("generated"):
        skipping.append("generate")
    else:
        running.append("generate")
    if state.get("analysis"):
        skipping.append("analyze")
    else:
        running.append("analyze")
    running.append("summarize")  # Always runs if we get here

    if skipping:
        print(f"   Skipping: {', '.join(skipping)} (already in state)")
    print(f"   Running: {', '.join(running)}")

    graph = build_resume_graph().compile()
    result = graph.invoke(state)

    # Save updated state
    db.save_state(args.thread_id, result, status="completed")
    print("\n✅ Pipeline completed!")

    if summary := result.get("final_summary"):
        print(f"\n📊 Summary: {summary[:200]}...")


def cmd_trace(args: Namespace) -> None:
    """Show execution trace for a run.

    .. deprecated:: 0.4.0
        Use LangSmith UI directly to view traces.
    """
    import warnings

    warnings.warn(
        "yamlgraph trace is deprecated. Use LangSmith UI directly.",
        DeprecationWarning,
        stacklevel=2,
    )
    print("⚠️  DEPRECATED: Use LangSmith UI directly to view traces")

    from yamlgraph.utils import get_latest_run_id, get_run_url, print_run_tree

    run_id = args.run_id or get_latest_run_id()

    if not run_id:
        print("❌ No run ID provided and could not find latest run.")
        return

    print(f"\n📊 Execution trace for: {run_id}")
    print("─" * 50)
    print()
    print_run_tree(run_id, verbose=args.verbose)

    if url := get_run_url(run_id):
        print(f"\n🔗 View in LangSmith: {url}")

    print()


def cmd_export(args: Namespace) -> None:
    """Export a run to JSON.

    .. deprecated:: 0.4.0
        Use `yamlgraph graph run <graph.yaml> --export` instead.
    """
    import warnings

    warnings.warn(
        "yamlgraph export is deprecated. Use: yamlgraph graph run <graph.yaml> --export",
        DeprecationWarning,
        stacklevel=2,
    )
    print("⚠️  DEPRECATED: Use 'yamlgraph graph run <graph.yaml> --export' instead")

    from yamlgraph.storage import YamlGraphDB, export_state

    db = YamlGraphDB()
    state = db.load_state(args.thread_id)

    if not state:
        print(f"❌ No run found with thread_id: {args.thread_id}")
        return

    filepath = export_state(state)
    print(f"✅ Exported to: {filepath}")
