"""Graph commands for universal graph runner.

Implements:
- graph run <path> --var key=value
- graph info <path>
- graph lint <path>
- graph validate <path>
- graph codegen <path> [--output FILE] [--include-base]
"""

import sys
from argparse import Namespace
from pathlib import Path

import yaml

from yamlgraph.cli.graph_validate import cmd_graph_lint, cmd_graph_validate
from yamlgraph.cli.helpers import (
    GraphLoadError,
    load_graph_config,
    require_graph_config,
)
from yamlgraph.models.state_builder import generate_typeddict_code


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


def _get_interrupt_message(result: dict) -> str:
    """Extract human-readable message from interrupt.

    Args:
        result: Graph execution result containing __interrupt__

    Returns:
        Message to display to user
    """
    interrupt = result.get("__interrupt__", ())
    if interrupt and len(interrupt) > 0:
        # Interrupt is tuple of Interrupt objects
        interrupt_obj = interrupt[0]
        if hasattr(interrupt_obj, "value"):
            value = interrupt_obj.value
            # Value can be string or dict with message
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                return value.get("message", value.get("question", str(value)))
    # Fallback: check response in state
    return result.get("response", "Please provide input:")


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


def _print_trace_url(tracer: object | None, share: bool = False) -> None:
    """Print LangSmith trace URL after an invoke (FR-022).

    Args:
        tracer: LangChainTracer instance (or None).
        share: If True, share the trace publicly.
    """
    if tracer is None:
        return

    from yamlgraph.utils.tracing import get_trace_url, share_trace

    if share:
        url = share_trace(tracer)
        if url:
            print(f"🔗 Trace (public): {url}")
    else:
        url = get_trace_url(tracer)
        if url:
            print(f"🔗 Trace: {url}")


def cmd_graph_run(args: Namespace) -> None:
    """Run any graph with provided variables.

    Usage:
        yamlgraph graph run graphs/yamlgraph.yaml --var topic=AI --var style=casual
    """
    from yamlgraph.graph_loader import (
        compile_graph,
        get_checkpointer_for_graph,
        load_graph_config,
    )

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
        # Load config and compile with checkpointer
        graph_config = load_graph_config(str(graph_path))
        graph = compile_graph(graph_config)
        checkpointer = get_checkpointer_for_graph(graph_config)
        app = graph.compile(checkpointer=checkpointer)

        # FR-021: Merge data_files into initial state (input vars win on collision)
        if graph_config.data:
            merged_state = {**graph_config.data, **initial_state}
            initial_state = merged_state

        # Add thread_id if provided
        config = {}
        if args.thread:
            config["configurable"] = {"thread_id": args.thread}
            initial_state["thread_id"] = args.thread

        # FR-027: Wire recursion_limit into LangGraph config
        # CLI --recursion-limit overrides YAML config.recursion_limit
        recursion_limit = getattr(args, "recursion_limit", None)
        if recursion_limit is None:
            recursion_limit = graph_config.recursion_limit
        config["recursion_limit"] = recursion_limit

        # FR-022: Set up LangSmith tracing
        from yamlgraph.utils.tracing import (
            create_tracer,
            inject_tracer_config,
        )

        tracer = create_tracer()
        inject_tracer_config(config, tracer)
        share_flag = getattr(args, "share_trace", False)

        # Initial invoke
        if getattr(args, "use_async", False):
            import asyncio

            result = asyncio.run(
                app.ainvoke(initial_state, config=config if config else None)
            )
        else:
            result = app.invoke(initial_state, config=config if config else None)

        _print_trace_url(tracer, share_flag)

        # Interrupt loop - handle human-in-the-loop
        while "__interrupt__" in result:
            message = _get_interrupt_message(result)
            print(f"\n💬 {message}")
            user_input = input("\n> ").strip()

            if not user_input:
                print("❌ Empty input. Exiting.")
                sys.exit(0)

            # Resume with Command(resume=...)
            from langgraph.types import Command

            if getattr(args, "use_async", False):
                import asyncio

                result = asyncio.run(
                    app.ainvoke(Command(resume=user_input), config=config)
                )
            else:
                result = app.invoke(Command(resume=user_input), config=config)

            _print_trace_url(tracer, share_flag)

        _display_result(result, truncate=not getattr(args, "full", False))

        if args.export:
            _handle_export(graph_path, result)

        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def cmd_graph_info(args: Namespace) -> None:
    """Show information about a graph."""
    graph_path = Path(args.graph_path)

    try:
        config = require_graph_config(graph_path)

        name = config.get("name", graph_path.stem)
        description = config.get("description", "No description")
        nodes = config.get("nodes", {})
        edges = config.get("edges", [])

        print(f"\n📊 Graph: {name}")
        print(f"   {description}")

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

    except GraphLoadError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading graph: {e}")
        sys.exit(1)


def cmd_graph_codegen(args: Namespace) -> None:
    """Generate TypedDict Python code for IDE support (FR-008).

    Reads graph YAML, generates TypedDict code with proper type hints,
    and writes to file or stdout.
    """
    try:
        config = load_graph_config(args.graph_path)
        source_path = str(args.graph_path)
        include_base = getattr(args, "include_base", False)

        code = generate_typeddict_code(config, source_path, include_base)

        output_path = getattr(args, "output", None)
        if output_path:
            Path(output_path).write_text(code)
            print(f"✓ Generated TypedDict code: {output_path}")
        else:
            print(code)

    except GraphLoadError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error generating TypedDict code: {e}")
        sys.exit(1)


def cmd_graph_dispatch(args: Namespace) -> None:
    """Dispatch to graph subcommands."""
    if args.graph_command == "run":
        cmd_graph_run(args)
    elif args.graph_command == "info":
        cmd_graph_info(args)
    elif args.graph_command == "validate":
        cmd_graph_validate(args)
    elif args.graph_command == "lint":
        cmd_graph_lint(args)
    elif args.graph_command == "codegen":
        cmd_graph_codegen(args)
    else:
        print(f"Unknown graph command: {args.graph_command}")
        sys.exit(1)
