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

from yamlgraph.constants import NodeType
from yamlgraph.map_compiler import compile_map_node
from yamlgraph.models.state_builder import build_state_class
from yamlgraph.node_factory import (
    create_interrupt_node,
    create_node_function,
    create_passthrough_node,
    create_subgraph_node,
    create_tool_call_node,
    resolve_class,
)
from yamlgraph.routing import make_expr_router_fn, make_router_fn
from yamlgraph.storage.checkpointer_factory import get_checkpointer
from yamlgraph.tools.agent import create_agent_node
from yamlgraph.tools.nodes import create_tool_node
from yamlgraph.tools.python_tool import (
    create_python_node,
    load_python_function,
    parse_python_tools,
)
from yamlgraph.tools.shell import parse_tools
from yamlgraph.tools.websearch import parse_websearch_tools
from yamlgraph.utils.validators import validate_config

# Type alias for dynamic state
GraphState = dict[str, Any]

logger = logging.getLogger(__name__)


class GraphConfig:
    """Parsed graph configuration from YAML."""

    def __init__(self, config: dict, source_path: Path | None = None):
        """Initialize from parsed YAML dict.

        Args:
            config: Parsed YAML configuration dictionary
            source_path: Path to the source YAML file (for subgraph resolution)

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
        self.checkpointer = config.get("checkpointer")
        # Store raw config for dynamic state building
        self.raw_config = config
        # Store source path for subgraph resolution
        self.source_path = source_path


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

    return GraphConfig(config, source_path=path.resolve())


def _resolve_state_class(config: GraphConfig) -> type:
    """Resolve the state class for the graph.

    Uses dynamic state generation unless explicit state_class is set
    (deprecated).

    Args:
        config: Graph configuration

    Returns:
        TypedDict class for graph state
    """
    if config.state_class and config.state_class != "yamlgraph.models.GraphState":
        import warnings

        warnings.warn(
            f"state_class '{config.state_class}' is deprecated. "
            "State is now auto-generated from graph config.",
            DeprecationWarning,
            stacklevel=2,
        )
        return resolve_class(config.state_class)
    return build_state_class(config.raw_config)


def _parse_all_tools(
    config: GraphConfig,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Callable]]:
    """Parse shell, Python, and websearch tools from config.

    Args:
        config: Graph configuration

    Returns:
        Tuple of (shell_tools, python_tools, websearch_tools, callable_registry)
        callable_registry maps tool names to actual callable functions for tool_call nodes
    """
    tools = parse_tools(config.tools)
    python_tools = parse_python_tools(config.tools)
    websearch_tools = parse_websearch_tools(config.tools)

    # Build callable registry for tool_call nodes
    callable_registry: dict[str, Callable] = {}
    for name, tool_config in python_tools.items():
        try:
            callable_registry[name] = load_python_function(tool_config)
        except (ImportError, AttributeError) as e:
            logger.warning(f"Failed to load tool '{name}': {e}")

    if tools:
        logger.info(f"Parsed {len(tools)} shell tools: {', '.join(tools.keys())}")
    if python_tools:
        logger.info(
            f"Parsed {len(python_tools)} Python tools: {', '.join(python_tools.keys())}"
        )
    if websearch_tools:
        logger.info(
            f"Parsed {len(websearch_tools)} websearch tools: {', '.join(websearch_tools.keys())}"
        )

    return tools, python_tools, websearch_tools, callable_registry


def _compile_node(
    node_name: str,
    node_config: dict[str, Any],
    graph: StateGraph,
    config: GraphConfig,
    tools: dict[str, Any],
    python_tools: dict[str, Any],
    websearch_tools: dict[str, Any],
    callable_registry: dict[str, Callable],
) -> tuple[str, Any] | None:
    """Compile a single node and add to graph.

    Args:
        node_name: Name of the node
        node_config: Node configuration dict
        graph: StateGraph to add node to
        config: Full graph config for defaults
        tools: Shell tools registry
        python_tools: Python tools registry
        websearch_tools: Web search tools registry (LangChain StructuredTool)
        callable_registry: Loaded callable functions for tool_call nodes

    Returns:
        Tuple of (node_name, map_info) for map nodes, None otherwise
    """
    # Copy node config and add loop_limit if specified
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
        node_fn = create_agent_node(
            node_name, enriched_config, tools, websearch_tools, python_tools
        )
        graph.add_node(node_name, node_fn)
    elif node_type == NodeType.MAP:
        map_edge_fn, sub_node_name = compile_map_node(
            node_name, enriched_config, graph, config.defaults, callable_registry
        )
        logger.info(f"Added node: {node_name} (type={node_type})")
        return (node_name, (map_edge_fn, sub_node_name))
    elif node_type == NodeType.TOOL_CALL:
        # Dynamic tool call from state
        node_fn = create_tool_call_node(node_name, enriched_config, callable_registry)
        graph.add_node(node_name, node_fn)
    elif node_type == NodeType.INTERRUPT:
        # Human-in-the-loop interrupt node
        node_fn = create_interrupt_node(node_name, enriched_config)
        graph.add_node(node_name, node_fn)
    elif node_type == NodeType.PASSTHROUGH:
        # Simple state transformation node
        node_fn = create_passthrough_node(node_name, enriched_config)
        graph.add_node(node_name, node_fn)
    elif node_type == NodeType.SUBGRAPH:
        # Subgraph node - compose graphs from YAML
        if not config.source_path:
            raise ValueError(
                f"Cannot resolve subgraph path for node '{node_name}': "
                "parent graph has no source_path"
            )
        node_fn = create_subgraph_node(
            node_name,
            enriched_config,
            parent_graph_path=config.source_path,
        )
        graph.add_node(node_name, node_fn)
    else:
        # LLM and router nodes
        node_fn = create_node_function(node_name, enriched_config, config.defaults)
        graph.add_node(node_name, node_fn)

    logger.info(f"Added node: {node_name} (type={node_type})")
    return None


def _compile_nodes(
    config: GraphConfig,
    graph: StateGraph,
    tools: dict[str, Any],
    python_tools: dict[str, Any],
    websearch_tools: dict[str, Any],
    callable_registry: dict[str, Callable],
) -> dict[str, tuple]:
    """Compile all nodes and add to graph.

    Args:
        config: Graph configuration
        graph: StateGraph to add nodes to
        tools: Shell tools registry
        python_tools: Python tools registry
        websearch_tools: Web search tools registry
        callable_registry: Loaded callable functions for tool_call nodes

    Returns:
        Dict of map_nodes: name -> (map_edge_fn, sub_node_name)
    """
    map_nodes: dict[str, tuple] = {}

    for node_name, node_config in config.nodes.items():
        result = _compile_node(
            node_name,
            node_config,
            graph,
            config,
            tools,
            python_tools,
            websearch_tools,
            callable_registry,
        )
        if result:
            map_nodes[result[0]] = result[1]

    return map_nodes


def _process_edge(
    edge: dict[str, Any],
    graph: StateGraph,
    map_nodes: dict[str, tuple],
    router_edges: dict[str, list],
    expression_edges: dict[str, list[tuple[str, str]]],
) -> None:
    """Process a single edge and add to graph or edge tracking dicts.

    Args:
        edge: Edge configuration dict
        graph: StateGraph to add edges to
        map_nodes: Map node tracking dict
        router_edges: Dict to collect router edges
        expression_edges: Dict to collect expression-based edges
    """
    from_node = edge["from"]
    to_node = edge["to"]
    condition = edge.get("condition")
    edge_type = edge.get("type")

    if from_node == "START":
        graph.set_entry_point(to_node)
    elif from_node in map_nodes and to_node in map_nodes:
        # Edge from map node TO another map node: sub_node → map_edge_fn
        _, from_sub = map_nodes[from_node]
        to_map_edge_fn, to_sub = map_nodes[to_node]
        graph.add_conditional_edges(from_sub, to_map_edge_fn, [to_sub])
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
        # Router-style conditional edge: store for later processing
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


def _add_conditional_edges(
    graph: StateGraph,
    router_edges: dict[str, list],
    expression_edges: dict[str, list[tuple[str, str]]],
) -> None:
    """Add router and expression conditional edges to graph.

    Args:
        graph: StateGraph to add edges to
        router_edges: Router-style conditional edges
        expression_edges: Expression-based conditional edges
    """
    # Add router conditional edges
    for source_node, target_nodes in router_edges.items():
        route_mapping = {target: target for target in target_nodes}
        graph.add_conditional_edges(
            source_node,
            make_router_fn(target_nodes),
            route_mapping,
        )

    # Add expression-based conditional edges
    for source_node, expr_edges in expression_edges.items():
        targets = {target for _, target in expr_edges}
        targets.add(END)  # Always include END as fallback
        route_mapping = {t: (END if t == END else t) for t in targets}
        graph.add_conditional_edges(
            source_node,
            make_expr_router_fn(expr_edges, source_node),
            route_mapping,
        )


def compile_graph(config: GraphConfig) -> StateGraph:
    """Compile a GraphConfig to a LangGraph StateGraph.

    Args:
        config: Parsed graph configuration

    Returns:
        StateGraph ready for compilation
    """
    # Build state class and create graph
    state_class = _resolve_state_class(config)
    graph = StateGraph(state_class)

    # Parse all tools
    tools, python_tools, websearch_tools, callable_registry = _parse_all_tools(config)

    # Compile all nodes
    map_nodes = _compile_nodes(
        config, graph, tools, python_tools, websearch_tools, callable_registry
    )

    # Process edges
    router_edges: dict[str, list] = {}
    expression_edges: dict[str, list[tuple[str, str]]] = {}

    for edge in config.edges:
        _process_edge(edge, graph, map_nodes, router_edges, expression_edges)

    # Add conditional edges
    _add_conditional_edges(graph, router_edges, expression_edges)

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


def get_checkpointer_for_graph(config: GraphConfig, *, async_mode: bool = False):
    """Get checkpointer from graph config.

    Args:
        config: Graph configuration
        async_mode: If True, return async-compatible saver

    Returns:
        Configured checkpointer or None if not specified
    """
    return get_checkpointer(config.checkpointer, async_mode=async_mode)
