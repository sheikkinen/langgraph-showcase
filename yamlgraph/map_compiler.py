"""Map node compiler - Handles type: map node compilation.

This module provides functionality to compile map nodes that fan out
to sub-nodes for parallel processing using LangGraph's Send mechanism.
"""

import logging
from collections.abc import Callable
from typing import Any

from langgraph.graph import StateGraph
from langgraph.types import Send

from yamlgraph.constants import NodeType
from yamlgraph.node_factory import create_node_function, create_tool_call_node
from yamlgraph.tools.python_tool import load_python_function
from yamlgraph.utils.expressions import resolve_state_expression

logger = logging.getLogger(__name__)


def wrap_for_reducer(
    node_fn: Callable[[dict], dict],
    collect_key: str,
    state_key: str,
) -> Callable[[dict], dict]:
    """Wrap sub-node output for Annotated reducer aggregation.

    Handles error propagation: if a map branch fails, the error is
    included in the result with the _map_index for tracking.

    Args:
        node_fn: The original node function
        collect_key: State key where results are collected
        state_key: Key to extract from node result

    Returns:
        Wrapped function that outputs in reducer-compatible format
    """

    def wrapped(state: dict) -> dict:
        try:
            result = node_fn(state)
        except Exception as e:
            # Propagate error with map index
            from yamlgraph.models import PipelineError

            error_result = {
                "_map_index": state.get("_map_index", 0),
                "_error": str(e),
                "_error_type": type(e).__name__,
            }
            return {
                collect_key: [error_result],
                "errors": [PipelineError.from_exception(e, node="map_subnode")],
            }

        # Check if result contains an error
        if "errors" in result or "error" in result:
            error_result = {
                "_map_index": state.get("_map_index", 0),
                "_error": str(result.get("errors") or result.get("error")),
            }
            # Preserve errors in output
            output = {collect_key: [error_result]}
            if "errors" in result:
                output["errors"] = result["errors"]
            return output

        extracted = result.get(state_key, result)

        # Convert Pydantic models to dicts
        if hasattr(extracted, "model_dump"):
            extracted = extracted.model_dump()

        # Include _map_index if present for ordering
        if "_map_index" in state:
            if isinstance(extracted, dict):
                extracted = {"_map_index": state["_map_index"], **extracted}
            else:
                extracted = {"_map_index": state["_map_index"], "value": extracted}

        return {collect_key: [extracted]}

    return wrapped


def compile_map_node(
    name: str,
    config: dict[str, Any],
    builder: StateGraph,
    defaults: dict[str, Any],
    tools_registry: dict[str, Any] | None = None,
    graph_path: Any | None = None,
    python_tools: dict[str, Callable] | None = None,
) -> tuple[Callable[[dict], list[Send]], str]:
    """Compile type: map node using LangGraph Send.

    Creates a sub-node and returns a map edge function that fans out
    to the sub-node for each item in the list.

    Args:
        name: Name of the map node
        config: Map node configuration with 'over', 'as', 'node', 'collect'
        builder: StateGraph builder to add sub-node to
        defaults: Default configuration for nodes
        tools_registry: Optional tools registry for tool_call sub-nodes
        graph_path: Path to graph YAML file (for relative prompt resolution)
        python_tools: Optional python tools registry for python sub-nodes

    Returns:
        Tuple of (map_edge_function, sub_node_name)
    """
    over_expr = config["over"]
    item_var = config["as"]
    sub_node_name = f"_map_{name}_sub"
    collect_key = config["collect"]
    sub_node_config = dict(config["node"])  # Copy to avoid mutating original
    state_key = sub_node_config.get("state_key", "result")
    sub_node_type = sub_node_config.get("type", "llm")

    # Auto-inject the 'as' variable into sub-node's variables
    # So the prompt can access it as {item_var}
    sub_variables = dict(sub_node_config.get("variables", {}))
    sub_variables[item_var] = f"{{state.{item_var}}}"
    sub_node_config["variables"] = sub_variables

    # Create sub-node based on type
    if sub_node_type == NodeType.TOOL_CALL:
        if tools_registry is None:
            raise ValueError(
                f"Map node '{name}' has tool_call sub-node but no tools_registry"
            )
        sub_node = create_tool_call_node(sub_node_name, sub_node_config, tools_registry)
    elif sub_node_type == NodeType.PYTHON:
        if python_tools is None:
            raise ValueError(
                f"Map node '{name}' has python sub-node but no python_tools registry"
            )
        tool_name = sub_node_config.get("tool")
        if tool_name not in python_tools:
            raise ValueError(f"Unknown python tool '{tool_name}' in map node '{name}'")
        # Load the actual function from the tool config
        tool_config = python_tools[tool_name]
        sub_node = load_python_function(tool_config)
    else:
        sub_node = create_node_function(
            sub_node_name, sub_node_config, defaults, graph_path=graph_path
        )

    wrapped_node = wrap_for_reducer(sub_node, collect_key, state_key)
    builder.add_node(sub_node_name, wrapped_node)

    # Create fan-out edge function using Send
    def map_edge(state: dict) -> list[Send]:
        items = resolve_state_expression(over_expr, state)

        if not isinstance(items, list):
            raise TypeError(
                f"Map 'over' must resolve to list, got {type(items).__name__}"
            )

        return [
            Send(sub_node_name, {**state, item_var: item, "_map_index": i})
            for i, item in enumerate(items)
        ]

    return map_edge, sub_node_name
