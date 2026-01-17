"""Showcase CLI - Command-line interface for the showcase app.

This package provides the CLI entry point and command implementations.

Usage:
    showcase graph run graphs/showcase.yaml --var topic="AI" --var style=casual
    showcase graph run graphs/router-demo.yaml --var message="hello"
    showcase graph list
    showcase list-runs
    showcase resume --thread-id abc123
    showcase trace --run-id <run-id>
"""

import argparse

# Import submodules for package access
from yamlgraph.cli import commands, validators
from yamlgraph.cli.commands import (
    cmd_export,
    cmd_list_runs,
    cmd_resume,
    cmd_trace,
)

__all__ = [
    # Submodules
    "commands",
    "validators",
    # Entry points
    "main",
    "create_parser",
]


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the CLI argument parser.

    Returns:
        Configured ArgumentParser for testing and main().
    """
    parser = argparse.ArgumentParser(
        description="YAMLGraph - YAML-first LLM Pipeline Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List runs command
    list_parser = subparsers.add_parser("list-runs", help="List recent runs")
    list_parser.add_argument(
        "--limit", "-l", type=int, default=10, help="Maximum runs to show"
    )
    list_parser.set_defaults(func=cmd_list_runs)

    # Resume command
    resume_parser = subparsers.add_parser("resume", help="Resume a pipeline")
    resume_parser.add_argument(
        "--thread-id", "-i", required=True, help="Thread ID to resume"
    )
    resume_parser.set_defaults(func=cmd_resume)

    # Trace command
    trace_parser = subparsers.add_parser("trace", help="Show execution trace")
    trace_parser.add_argument(
        "--run-id", "-r", help="Run ID (uses latest if not provided)"
    )
    trace_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Include timing details"
    )
    trace_parser.set_defaults(func=cmd_trace)

    # Export command
    export_parser = subparsers.add_parser("export", help="Export a run to JSON")
    export_parser.add_argument(
        "--thread-id", "-i", required=True, help="Thread ID to export"
    )
    export_parser.set_defaults(func=cmd_export)

    # Graph command group (universal runner)
    from yamlgraph.cli.graph_commands import cmd_graph_dispatch

    graph_parser = subparsers.add_parser(
        "graph", help="Universal graph runner and utilities"
    )
    graph_subparsers = graph_parser.add_subparsers(
        dest="graph_command", help="Graph commands"
    )

    # graph run
    graph_run_parser = graph_subparsers.add_parser("run", help="Run any graph")
    graph_run_parser.add_argument("graph_path", help="Path to graph YAML file")
    graph_run_parser.add_argument(
        "--var",
        "-v",
        action="append",
        default=[],
        help="Set state variable (key=value), can repeat",
    )
    graph_run_parser.add_argument(
        "--thread", "-t", type=str, default=None, help="Thread ID for persistence"
    )
    graph_run_parser.add_argument(
        "--export", "-e", action="store_true", help="Export results to files"
    )

    # graph list
    graph_subparsers.add_parser("list", help="List available graphs")

    # graph info
    graph_info_parser = graph_subparsers.add_parser(
        "info", help="Show graph information"
    )
    graph_info_parser.add_argument("graph_path", help="Path to graph YAML file")

    # graph validate
    graph_validate_parser = graph_subparsers.add_parser(
        "validate", help="Validate graph YAML schema"
    )
    graph_validate_parser.add_argument("graph_path", help="Path to graph YAML file")

    graph_parser.set_defaults(func=cmd_graph_dispatch)

    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
