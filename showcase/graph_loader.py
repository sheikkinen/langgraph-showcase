"""YAML Graph Loader - Compile YAML to LangGraph.

This module provides functionality to load graph definitions from YAML files
and compile them into LangGraph StateGraph instances.
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from langgraph.graph import END, StateGraph
from langgraph.types import Send

from showcase.constants import NodeType
from showcase.models.state_builder import build_state_class
from showcase.node_factory import create_node_function, resolve_class
from showcase.routing import make_expr_router_fn, make_router_fn
from showcase.tools.agent import create_agent_node
from showcase.tools.nodes import create_tool_node
from showcase.tools.python_tool import create_python_node, parse_python_tools
from showcase.tools.shell import parse_tools
from showcase.utils.expressions import resolve_state_expression
from showcase.utils.validators import validate_config

# Type alias for dynamic state
GraphState = dict[str, Any]

logger = logging.getLogger(__name__)


class GraphConfig:
    """Parsed graph configuration from YAML."""

    def __init__(self, config: dict):
        """Initialize from parsed YAML dict.

        Args:
            config: Parsed YAML configuration dictionary

        Raises:
            ValueError: If config is invalid
        """
        # Validate before storing
        validate_config(config)

        self.version = config.get("version", "1.0")
        self.name = config.get("name", "unnamed")
        self.description = config.get("description", "")
        self.defaults = config.get("defaults", {})
        self.nodes = config.get("nodes", {})
        self.edges = config.get("edges", [])
        self.tools = config.get("tools", {})
        self.state_class = config.get("state_class", "")
        self.loop_limits = config.get("loop_limits", {})
        # Store raw config for dynamic state building
        self.raw_config = config


def load_graph_config(path: str | Path) -> GraphConfig:
    """Load and parse a YAML graph definition.

    Args:
        path: Path to the YAML file

    Returns:
        GraphConfig instance

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the YAML is invalid or missing required fields
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Graph config not found: {path}")

    with open(path) as f:
        config = yaml.safe_load(f)

    return GraphConfig(config)


def wrap_for_reducer(
    node_fn: Callable[[dict], dict],
    collect_key: str,
    state_key: str,
) -> Callable[[dict], dict]:
    """Wrap sub-node output for Annotated reducer aggregation.

    Args:
        node_fn: The original node function
        collect_key: State key where results are collected
        state_key: Key to extract from node result

    Returns:
        Wrapped function that outputs in reducer-compatible format
    """

    def wrapped(state: dict) -> dict:
        result = node_fn(state)
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
) -> tuple[Callable[[dict], list[Send]], str]:
    """Compile type: map node using LangGraph Send.

    Creates a sub-node and returns a map edge function that fans out
    to the sub-node for each item in the list.

    Args:
        name: Name of the map node
        config: Map node configuration with 'over', 'as', 'node', 'collect'
        builder: StateGraph builder to add sub-node to
        defaults: Default configuration for nodes

    Returns:
        Tuple of (map_edge_function, sub_node_name)
    """
    over_expr = config["over"]
    item_var = config["as"]
    sub_node_name = f"_map_{name}_sub"
    collect_key = config["collect"]
    sub_node_config = dict(config["node"])  # Copy to avoid mutating original
    state_key = sub_node_config.get("state_key", "result")

    # Auto-inject the 'as' variable into sub-node's variables
    # So the prompt can access it as {item_var}
    sub_variables = dict(sub_node_config.get("variables", {}))
    sub_variables[item_var] = f"{{state.{item_var}}}"
    sub_node_config["variables"] = sub_variables

    # Create sub-node from config
    sub_node = create_node_function(sub_node_name, sub_node_config, defaults)
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


def compile_graph(config: GraphConfig) -> StateGraph:
    """Compile a GraphConfig to a LangGraph StateGraph.

    Args:
        config: Parsed graph configuration

    Returns:
        StateGraph ready for compilation
    """
    # Build state class dynamically from config
    # If state_class is explicitly set, use it (with deprecation warning)
    if config.state_class and config.state_class != "showcase.models.GraphState":
        import warnings

        warnings.warn(
            f"state_class '{config.state_class}' is deprecated. "
            "State is now auto-generated from graph config.",
            DeprecationWarning,
            stacklevel=2,
        )
        state_class = resolve_class(config.state_class)
    else:
        # Dynamic state generation - no YAML coupling!
        state_class = build_state_class(config.raw_config)
    graph = StateGraph(state_class)

    # Parse tools if present
    tools = parse_tools(config.tools)
    python_tools = parse_python_tools(config.tools)
    if tools:
        logger.info(f"Parsed {len(tools)} shell tools: {', '.join(tools.keys())}")
    if python_tools:
        logger.info(
            f"Parsed {len(python_tools)} Python tools: {', '.join(python_tools.keys())}"
        )

    # Add nodes - inject loop_limits from graph config into node config
    # Track map nodes for special edge handling
    map_nodes: dict[str, tuple] = {}  # name -> (map_edge_fn, sub_node_name)

    for node_name, node_config in config.nodes.items():
        # Copy node config and add loop_limit if specified in graph's loop_limits
        enriched_config = dict(node_config)
        if node_name in config.loop_limits:
            enriched_config["loop_limit"] = config.loop_limits[node_name]

        node_type = node_config.get("type", NodeType.LLM)

        if node_type == NodeType.TOOL:
            node_fn = create_tool_node(node_name, enriched_config, tools)
            graph.add_node(node_name, node_fn)
        elif node_type == NodeType.PYTHON:
            node_fn = create_python_node(node_name, enriched_config, python_tools)
            graph.add_node(node_name, node_fn)
        elif node_type == NodeType.AGENT:
            node_fn = create_agent_node(node_name, enriched_config, tools)
            graph.add_node(node_name, node_fn)
        elif node_type == NodeType.MAP:
            # Map node - compile and track for edge wiring
            map_edge_fn, sub_node_name = compile_map_node(
                node_name, enriched_config, graph, config.defaults
            )
            map_nodes[node_name] = (map_edge_fn, sub_node_name)
            # Note: compile_map_node adds the sub_node to graph
        else:
            # LLM and router nodes
            node_fn = create_node_function(node_name, enriched_config, config.defaults)
            graph.add_node(node_name, node_fn)

        logger.info(f"Added node: {node_name} (type={node_type})")

    # Track which edges need conditional routing
    router_edges = {}  # For type: conditional edges with list targets
    expression_edges: dict[str, list[tuple[str, str]]] = {}  # For expression conditions

    # Process edges
    for edge in config.edges:
        from_node = edge["from"]
        to_node = edge["to"]
        condition = edge.get("condition")
        edge_type = edge.get("type")

        if from_node == "START":
            graph.set_entry_point(to_node)
        elif isinstance(to_node, str) and to_node in map_nodes:
            # Edge TO a map node: use conditional edge with Send function
            map_edge_fn, sub_node_name = map_nodes[to_node]
            graph.add_conditional_edges(from_node, map_edge_fn, [sub_node_name])
        elif from_node in map_nodes:
            # Edge FROM a map node: wire sub_node to next_node for fan-in
            _, sub_node_name = map_nodes[from_node]
            target = END if to_node == "END" else to_node
            graph.add_edge(sub_node_name, target)
        elif edge_type == "conditional" and isinstance(to_node, list):
            # Router-style conditional edge: routes to one of multiple targets
            # Store for later processing
            router_edges[from_node] = to_node
        elif condition:
            # Expression-based condition (e.g., "critique.score < 0.8")
            if from_node not in expression_edges:
                expression_edges[from_node] = []
            target = END if to_node == "END" else to_node
            expression_edges[from_node].append((condition, target))
        elif to_node == "END":
            graph.add_edge(from_node, END)
        else:
            graph.add_edge(from_node, to_node)

    # Add router conditional edges
    for source_node, target_nodes in router_edges.items():
        # Create mapping: target_name -> target_name (identity mapping)
        route_mapping = {target: target for target in target_nodes}

        graph.add_conditional_edges(
            source_node,
            make_router_fn(target_nodes),
            route_mapping,
        )

    # Add expression-based conditional edges
    for source_node, expr_edges in expression_edges.items():
        # Build mapping: all possible targets
        targets = {target for _, target in expr_edges}
        targets.add(END)  # Always include END as fallback
        route_mapping = {t: (END if t == END else t) for t in targets}

        graph.add_conditional_edges(
            source_node,
            make_expr_router_fn(expr_edges, source_node),
            route_mapping,
        )

    return graph


def load_and_compile(path: str | Path) -> StateGraph:
    """Load YAML and compile to StateGraph.

    Convenience function combining load_graph_config and compile_graph.

    Args:
        path: Path to YAML graph definition

    Returns:
        StateGraph ready for compilation
    """
    config = load_graph_config(path)
    logger.info(f"Loaded graph config: {config.name} v{config.version}")
    return compile_graph(config)
