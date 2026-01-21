"""Graph commands for universal graph runner.

Implements:
- graph run <path> --var key=value
- graph list
- graph info <path>
- graph lint <path>
- graph mermaid <path>
- graph validate <path>
"""

import sys
from argparse import Namespace
from pathlib import Path

import yaml

# Import from split modules
from yamlgraph.cli.graph_mermaid import cmd_graph_mermaid
from yamlgraph.cli.graph_validate import cmd_graph_lint, cmd_graph_validate


def parse_vars(var_list: list[str] | None) -> dict[str, str]:
    """Parse --var key=value arguments into a dict.

    Args:
        var_list: List of "key=value" strings

    Returns:
        Dict mapping keys to values

    Raises:
        ValueError: If a var doesn't contain '='
    """
    if not var_list:
        return {}

    result = {}
    for item in var_list:
        if "=" not in item:
            raise ValueError(f"Invalid var format: '{item}' (expected key=value)")
        key, value = item.split("=", 1)
        result[key] = value

    return result


def _display_result(result: dict, truncate: bool = True) -> None:
    """Display result summary to console.

    Args:
        result: Graph execution result dict
        truncate: Whether to truncate long values (default: True)
    """
    print("=" * 60)
    print("RESULT")
    print("=" * 60)

    skip_keys = {"messages", "errors", "_loop_counts"}
    for key, value in result.items():
        if key.startswith("_") or key in skip_keys:
            continue
        if value is not None:
            value_str = str(value)
            if truncate and len(value_str) > 200:
                value_str = value_str[:200] + "..."
            print(f"  {key}: {value_str}")


def _handle_export(graph_path: Path, result: dict) -> None:
    """Handle optional result export.

    Args:
        graph_path: Path to the graph YAML file
        result: Graph execution result dict
    """
    from yamlgraph.storage.export import export_result

    with open(graph_path) as f:
        graph_config = yaml.safe_load(f)

    export_config = graph_config.get("exports", {})
    if export_config:
        paths = export_result(result, export_config)
        if paths:
            print("\n📁 Exported:")
            for p in paths:
                print(f"   {p}")


def cmd_graph_run(args: Namespace) -> None:
    """Run any graph with provided variables.

    Usage:
        yamlgraph graph run graphs/yamlgraph.yaml --var topic=AI --var style=casual
    """
    from yamlgraph.graph_loader import load_and_compile

    graph_path = Path(args.graph_path)

    if not graph_path.exists():
        print(f"❌ Graph file not found: {graph_path}")
        sys.exit(1)

    # Parse variables
    try:
        initial_state = parse_vars(args.var)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    print(f"\n🚀 Running graph: {graph_path.name}")
    if initial_state:
        print(f"   Variables: {initial_state}")
    print()

    try:
        graph = load_and_compile(str(graph_path))
        app = graph.compile()

        # Add thread_id if provided
        config = {}
        if args.thread:
            config["configurable"] = {"thread_id": args.thread}
            initial_state["thread_id"] = args.thread

        result = app.invoke(initial_state, config=config if config else None)

        _display_result(result, truncate=not getattr(args, "full", False))

        if args.export:
            _handle_export(graph_path, result)

        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def cmd_graph_list(args: Namespace) -> None:
    """List available graphs in graphs/ directory."""
    graphs_dir = Path("graphs")

    if not graphs_dir.exists():
        print("❌ graphs/ directory not found")
        return

    yaml_files = sorted(graphs_dir.glob("*.yaml"))

    if not yaml_files:
        print("No graphs found in graphs/")
        return

    print(f"\n📋 Available graphs ({len(yaml_files)}):\n")

    for path in yaml_files:
        try:
            with open(path) as f:
                config = yaml.safe_load(f)
            description = config.get("description", "")
            print(f"  {path.name}")
            if description:
                print(f"    {description[:60]}")
        except Exception:
            print(f"  {path.name} (invalid)")

    print()


def cmd_graph_info(args: Namespace) -> None:
    """Show information about a graph."""
    graph_path = Path(args.graph_path)

    if not graph_path.exists():
        print(f"❌ Graph file not found: {graph_path}")
        sys.exit(1)

    try:
        with open(graph_path) as f:
            config = yaml.safe_load(f)

        name = config.get("name", graph_path.stem)
        description = config.get("description", "No description")
        state_class = config.get("state_class", "default")
        nodes = config.get("nodes", {})
        edges = config.get("edges", [])

        print(f"\n📊 Graph: {name}")
        print(f"   {description}")
        print(f"\n   State: {state_class}")

        # Show nodes
        print(f"\n   Nodes ({len(nodes)}):")
        for node_name, node_config in nodes.items():
            node_type = node_config.get("type", "prompt")
            print(f"     - {node_name} ({node_type})")

        # Show edges
        print(f"\n   Edges ({len(edges)}):")
        for edge in edges:
            from_node = edge.get("from", "?")
            to_node = edge.get("to", "?")
            condition = edge.get("condition", "")
            if condition:
                print(f"     {from_node} → {to_node} (conditional)")
            else:
                print(f"     {from_node} → {to_node}")

        # Show required inputs if defined
        inputs = config.get("inputs", {})
        if inputs:
            print(f"\n   Inputs ({len(inputs)}):")
            for input_name, input_config in inputs.items():
                required = input_config.get("required", False)
                default = input_config.get("default", None)
                req_str = " (required)" if required else f" (default: {default})"
                print(f"     --var {input_name}=<value>{req_str}")

        print()

    except Exception as e:
        print(f"❌ Error reading graph: {e}")
        sys.exit(1)


def cmd_graph_dispatch(args: Namespace) -> None:
    """Dispatch to graph subcommands."""
    if args.graph_command == "run":
        cmd_graph_run(args)
    elif args.graph_command == "list":
        cmd_graph_list(args)
    elif args.graph_command == "info":
        cmd_graph_info(args)
    elif args.graph_command == "validate":
        cmd_graph_validate(args)
    elif args.graph_command == "lint":
        cmd_graph_lint(args)
    elif args.graph_command == "mermaid":
        cmd_graph_mermaid(args)
    else:
        print(f"Unknown graph command: {args.graph_command}")
        sys.exit(1)
