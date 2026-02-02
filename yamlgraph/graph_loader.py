"""YAML Graph Loader - Compile YAML to LangGraph.

This module provides functionality to load graph definitions from YAML files
and compile them into LangGraph StateGraph instances.
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from yamlgraph.data_loader import load_data_files
from yamlgraph.models.state_builder import build_state_class
from yamlgraph.node_compiler import compile_nodes
from yamlgraph.routing import make_expr_router_fn, make_router_fn
from yamlgraph.storage.checkpointer_factory import get_checkpointer
from yamlgraph.tools.python_tool import load_python_function, parse_python_tools
from yamlgraph.tools.shell import parse_tools
from yamlgraph.utils.validators import validate_config

# Type alias for dynamic state
GraphState = dict[str, Any]

logger = logging.getLogger(__name__)


def detect_loop_nodes(edges: list[dict]) -> set[str]:
    """Detect nodes that participate in cycles (loops).

    Uses DFS with path tracking to find back edges indicating cycles.

    Args:
        edges: List of edge dicts with 'from' and 'to' keys

    Returns:
        Set of node names that are part of at least one cycle
    """
    from collections import defaultdict

    # Build adjacency list
    graph: dict[str, set[str]] = defaultdict(set)
    all_nodes: set[str] = set()

    for edge in edges:
        from_node = edge.get("from")
        to_nodes = edge.get("to")

        if from_node is None or to_nodes is None:
            continue

        if isinstance(to_nodes, str):
            to_nodes = [to_nodes]

        all_nodes.add(from_node)
        for to_node in to_nodes:
            graph[from_node].add(to_node)
            all_nodes.add(to_node)

    # Find nodes in cycles using DFS with ancestor tracking
    loop_nodes: set[str] = set()
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(all_nodes, WHITE)

    def dfs(node: str, ancestors: set[str]) -> None:
        """DFS that tracks ancestors to detect back edges."""
        color[node] = GRAY
        current_ancestors = ancestors | {node}

        for neighbor in graph.get(node, set()):
            if neighbor in current_ancestors:
                # Back edge found - mark all nodes from neighbor to current as in loop
                loop_nodes.update(current_ancestors)
            elif color[neighbor] == WHITE:
                dfs(neighbor, current_ancestors)

        color[node] = BLACK

    for node in all_nodes:
        if color[node] == WHITE:
            dfs(node, set())

    return loop_nodes


def apply_loop_node_defaults(config: dict[str, Any]) -> dict[str, Any]:
    """Auto-apply skip_if_exists=false to nodes detected in loops.

    This eliminates the common footgun where loop nodes need explicit
    skip_if_exists: false to re-run on each iteration.

    Args:
        config: Raw graph configuration dict

    Returns:
        Modified copy of config with skip_if_exists applied to loop nodes
    """
    import copy

    result = copy.deepcopy(config)
    edges = result.get("edges", [])
    nodes = result.get("nodes", {})

    loop_nodes = detect_loop_nodes(edges)

    if loop_nodes:
        logger.debug(f"Auto-detected loop nodes: {', '.join(sorted(loop_nodes))}")

    for node_name in loop_nodes:
        # Only set if node exists and not explicitly configured
        if node_name in nodes and "skip_if_exists" not in nodes[node_name]:
            nodes[node_name]["skip_if_exists"] = False

    return result


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
        self.loop_limits = config.get("loop_limits", {})
        self.checkpointer = config.get("checkpointer")
        # Store raw config for dynamic state building
        self.raw_config = config
        # Store source path for subgraph resolution
        self.source_path = source_path
        # Prompt resolution options (FR-A: graph-relative prompts)
        # Check top-level first, then defaults
        self.prompts_relative = config.get(
            "prompts_relative", self.defaults.get("prompts_relative", False)
        )
        self.prompts_dir = config.get("prompts_dir", self.defaults.get("prompts_dir"))

        # FR-021: Load external data files into state
        if source_path:
            self.data = load_data_files(config, source_path)
        else:
            self.data = {}


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

    # FR-010: Auto-apply skip_if_exists=false to loop nodes
    config = apply_loop_node_defaults(config)

    return GraphConfig(config, source_path=path.resolve())


def _resolve_state_class(config: GraphConfig) -> type:
    """Build state class dynamically from graph configuration.

    Args:
        config: Graph configuration

    Returns:
        TypedDict class for graph state
    """
    return build_state_class(config.raw_config)


def _parse_all_tools(
    config: GraphConfig,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Callable]]:
    """Parse shell and Python tools from config.

    Args:
        config: Graph configuration

    Returns:
        Tuple of (shell_tools, python_tools, callable_registry)
        callable_registry maps tool names to actual callable functions for tool_call nodes
    """
    tools = parse_tools(config.tools)
    python_tools = parse_python_tools(config.tools)

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

    return tools, python_tools, callable_registry


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
        if to_node in map_nodes:
            # START -> map node: use conditional entry point with Send function
            map_edge_fn, sub_node_name = map_nodes[to_node]
            graph.set_conditional_entry_point(map_edge_fn, [sub_node_name])
        else:
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
    tools, python_tools, callable_registry = _parse_all_tools(config)

    # Compile all nodes
    map_nodes = compile_nodes(config, graph, tools, python_tools, callable_registry)

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


def get_checkpointer_for_graph(
    config: GraphConfig,
) -> BaseCheckpointSaver | None:
    """Get checkpointer from graph config.

    Args:
        config: Graph configuration

    Returns:
        Configured checkpointer or None if not specified

    Note:
        For async usage, use get_checkpointer_async() directly.
    """
    return get_checkpointer(config.checkpointer)
