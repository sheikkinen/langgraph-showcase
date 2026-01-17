"""Graph commands for universal graph runner.

Implements:
- graph run <path> --var key=value
- graph list
- graph info <path>
"""

import sys
from argparse import Namespace
from pathlib import Path

import yaml


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


def cmd_graph_run(args: Namespace) -> None:
    """Run any graph with provided variables.

    Usage:
        showcase graph run graphs/showcase.yaml --var topic=AI --var style=casual
    """
    from showcase.graph_loader import load_and_compile

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

        # Show result summary
        print("=" * 60)
        print("RESULT")
        print("=" * 60)

        # Show key fields from result
        skip_keys = {"messages", "errors", "_loop_counts"}
        for key, value in result.items():
            if key.startswith("_") or key in skip_keys:
                continue
            if value is not None:
                value_str = str(value)[:200]
                if len(str(value)) > 200:
                    value_str += "..."
                print(f"  {key}: {value_str}")

        # Export if requested
        if args.export:
            from showcase.storage.export import export_result

            # Get export config from graph if available
            with open(graph_path) as f:
                graph_config = yaml.safe_load(f)

            export_config = graph_config.get("exports", {})
            if export_config:
                paths = export_result(result, export_config)
                if paths:
                    print("\n📁 Exported:")
                    for p in paths:
                        print(f"   {p}")

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


def cmd_graph_validate(args: Namespace) -> None:
    """Validate a graph YAML file.

    Checks:
    - File exists and is valid YAML
    - Required fields present (name, nodes, edges)
    - Node references are valid
    - Edge references match existing nodes
    """
    graph_path = Path(args.graph_path)

    if not graph_path.exists():
        print(f"❌ Graph file not found: {graph_path}")
        sys.exit(1)

    errors = []
    warnings = []

    try:
        with open(graph_path) as f:
            config = yaml.safe_load(f)

        # Check required fields
        if not config.get("name"):
            errors.append("Missing required field: name")

        nodes = config.get("nodes", {})
        if not nodes:
            errors.append("Missing required field: nodes")

        edges = config.get("edges", [])
        if not edges:
            warnings.append("No edges defined")

        # Validate node references in edges
        node_names = set(nodes.keys()) | {"START", "END"}
        for i, edge in enumerate(edges):
            from_node = edge.get("from", "")
            to_node = edge.get("to", "")

            if from_node not in node_names:
                errors.append(f"Edge {i + 1}: unknown 'from' node '{from_node}'")

            # Handle conditional edges where 'to' is a list
            if isinstance(to_node, list):
                for t in to_node:
                    if t not in node_names:
                        errors.append(f"Edge {i + 1}: unknown 'to' node '{t}'")
            elif to_node not in node_names:
                errors.append(f"Edge {i + 1}: unknown 'to' node '{to_node}'")

        # Validate node configurations
        for node_name, node_config in nodes.items():
            node_type = node_config.get("type", "llm")
            if node_type == "agent":
                if not node_config.get("tools"):
                    warnings.append(f"Node '{node_name}': agent has no tools")

        # Report results
        name = config.get("name", graph_path.stem)
        if errors:
            print(f"\n❌ {graph_path.name} ({name}) - INVALID\n")
            for err in errors:
                print(f"   ✗ {err}")
            for warn in warnings:
                print(f"   ⚠ {warn}")
            print()
            sys.exit(1)
        elif warnings:
            print(f"\n⚠️  {graph_path.name} ({name}) - VALID with warnings\n")
            for warn in warnings:
                print(f"   ⚠ {warn}")
            print()
        else:
            print(f"\n✅ {graph_path.name} ({name}) - VALID\n")
            print(f"   Nodes: {len(nodes)}")
            print(f"   Edges: {len(edges)}")
            print()

    except yaml.YAMLError as e:
        print(f"❌ Invalid YAML: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error validating graph: {e}")
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
    else:
        print(f"Unknown graph command: {args.graph_command}")
        sys.exit(1)
