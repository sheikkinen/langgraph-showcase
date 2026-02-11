"""YamlGraph CLI - Command-line interface for yamlgraph.

This package provides the CLI entry point and command implementations.

Usage:
    yamlgraph graph run examples/demos/yamlgraph/graph.yaml --var topic="AI"
    yamlgraph graph info examples/npc/npc-creation.yaml
"""

import argparse

from yamlgraph.cli.graph_commands import cmd_graph_dispatch
from yamlgraph.cli.schema_commands import cmd_schema_dispatch

__all__ = [
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

    # Graph command group (universal runner)

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
    graph_run_parser.add_argument(
        "--full", "-f", action="store_true", help="Show full output without truncation"
    )
    graph_run_parser.add_argument(
        "--async",
        "-a",
        action="store_true",
        dest="use_async",
        help="Use async execution for parallel map nodes (recommended for Mistral)",
    )
    graph_run_parser.add_argument(
        "--share-trace",
        action="store_true",
        dest="share_trace",
        help="Share LangSmith trace publicly and display the URL",
    )
    graph_run_parser.add_argument(
        "--recursion-limit",
        type=int,
        default=None,
        dest="recursion_limit",
        help="Override LangGraph recursion limit (default: from YAML config or 50)",
    )

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

    # graph lint
    graph_lint_parser = graph_subparsers.add_parser(
        "lint", help="Lint graph for issues (missing state, unused tools, etc.)"
    )
    graph_lint_parser.add_argument(
        "graph_path", nargs="+", help="Path(s) to graph YAML file(s)"
    )

    # graph codegen (FR-008)
    graph_codegen_parser = graph_subparsers.add_parser(
        "codegen", help="Generate TypedDict Python code for IDE support"
    )
    graph_codegen_parser.add_argument("graph_path", help="Path to graph YAML file")
    graph_codegen_parser.add_argument(
        "--output", "-o", type=str, help="Output file (default: stdout)"
    )
    graph_codegen_parser.add_argument(
        "--include-base",
        action="store_true",
        help="Include infrastructure fields (thread_id, errors, etc.)",
    )

    graph_parser.set_defaults(func=cmd_graph_dispatch)

    # === Schema commands (FR-009) ===
    schema_parser = subparsers.add_parser(
        "schema", help="JSON Schema export for IDE support"
    )
    schema_subparsers = schema_parser.add_subparsers(
        dest="schema_command", help="Schema subcommands"
    )

    # schema export
    schema_export_parser = schema_subparsers.add_parser(
        "export", help="Export graph schema as JSON Schema"
    )
    schema_export_parser.add_argument(
        "--output", "-o", type=str, help="Output file (default: stdout)"
    )

    # schema path
    schema_subparsers.add_parser("path", help="Print path to bundled JSON Schema")

    schema_parser.set_defaults(func=cmd_schema_dispatch)

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
