"""YAML Graph Loader - Compile YAML to LangGraph.

This module provides functionality to load graph definitions from YAML files
and compile them into LangGraph StateGraph instances.
"""

import logging
from collections.abc import Callable
from pathlib import Path

import yaml
from langgraph.graph import END, StateGraph

from showcase.models import ShowcaseState
from showcase.node_factory import create_node_function, resolve_class
from showcase.tools.agent import create_agent_node
from showcase.tools.nodes import create_tool_node
from showcase.tools.shell import parse_tools
from showcase.utils.conditions import evaluate_condition

logger = logging.getLogger(__name__)


def _validate_config(config: dict) -> None:
    """Validate YAML configuration structure.
    
    Args:
        config: Parsed YAML dictionary
        
    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Check required top-level keys
    if not config.get("nodes"):
        raise ValueError("Graph config missing required 'nodes' section")
    
    if not config.get("edges"):
        raise ValueError("Graph config missing required 'edges' section")
    
    nodes = config["nodes"]
    
    # Validate each node
    for node_name, node_config in nodes.items():
        node_type = node_config.get("type", "llm")
        # Only LLM and router nodes require prompt
        if node_type in ("llm", "router") and not node_config.get("prompt"):
            raise ValueError(f"Node '{node_name}' missing required 'prompt' field")
        
        # Validate router nodes
        if node_config.get("type") == "router":
            if not node_config.get("routes"):
                raise ValueError(f"Router node '{node_name}' missing required 'routes' field")
            
            # Validate route targets exist
            for route_key, target_node in node_config["routes"].items():
                if target_node not in nodes:
                    raise ValueError(
                        f"Router node '{node_name}' route '{route_key}' points to "
                        f"nonexistent node '{target_node}'"
                    )
    
    # Validate each edge
    for i, edge in enumerate(config["edges"]):
        if "from" not in edge:
            raise ValueError(f"Edge {i} missing required 'from' field")
        if "to" not in edge:
            raise ValueError(f"Edge {i} missing required 'to' field")

    # Validate on_error values
    valid_on_error = {"skip", "retry", "fail", "fallback"}
    for node_name, node_config in nodes.items():
        on_error = node_config.get("on_error")
        if on_error and on_error not in valid_on_error:
            raise ValueError(
                f"Node '{node_name}' has invalid on_error value '{on_error}'. "
                f"Valid values: {', '.join(valid_on_error)}"
            )


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
        _validate_config(config)
        
        self.version = config.get("version", "1.0")
        self.name = config.get("name", "unnamed")
        self.description = config.get("description", "")
        self.defaults = config.get("defaults", {})
        self.nodes = config.get("nodes", {})
        self.edges = config.get("edges", [])
        self.tools = config.get("tools", {})
        self.state_class = config.get("state_class", "showcase.models.ShowcaseState")
        self.loop_limits = config.get("loop_limits", {})


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


def _should_continue(state: ShowcaseState) -> str:
    """Default routing condition: continue or end.
    
    Args:
        state: Current pipeline state
        
    Returns:
        'continue' if should proceed, 'end' if should stop
    """
    if state.get("error") is not None:
        return "end"
    if state.get("generated") is None:
        return "end"
    return "continue"


def compile_graph(config: GraphConfig) -> StateGraph:
    """Compile a GraphConfig to a LangGraph StateGraph.
    
    Args:
        config: Parsed graph configuration
        
    Returns:
        StateGraph ready for compilation
    """
    # Get state class
    state_class = resolve_class(config.state_class)
    graph = StateGraph(state_class)
    
    # Parse tools if present
    tools = parse_tools(config.tools)
    if tools:
        logger.info(f"Parsed {len(tools)} tools: {', '.join(tools.keys())}")

    # Add nodes - inject loop_limits from graph config into node config
    for node_name, node_config in config.nodes.items():
        # Copy node config and add loop_limit if specified in graph's loop_limits
        enriched_config = dict(node_config)
        if node_name in config.loop_limits:
            enriched_config["loop_limit"] = config.loop_limits[node_name]
        
        node_type = node_config.get("type", "llm")
        
        if node_type == "tool":
            node_fn = create_tool_node(node_name, enriched_config, tools)
        elif node_type == "agent":
            node_fn = create_agent_node(node_name, enriched_config, tools)
        else:
            # LLM and router nodes
            node_fn = create_node_function(node_name, enriched_config, config.defaults)
        
        graph.add_node(node_name, node_fn)
        logger.info(f"Added node: {node_name} (type={node_type})")

    # Track which edges need conditional routing
    conditional_source = None
    conditional_targets = {}
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
        elif edge_type == "conditional" and isinstance(to_node, list):
            # Router-style conditional edge: routes to one of multiple targets
            # Store for later processing
            router_edges[from_node] = to_node
        elif condition and condition not in ("continue", "end"):
            # Expression-based condition (e.g., "critique.score < 0.8")
            if from_node not in expression_edges:
                expression_edges[from_node] = []
            target = END if to_node == "END" else to_node
            expression_edges[from_node].append((condition, target))
        elif condition:
            # Legacy continue/end style conditions
            if conditional_source is None:
                conditional_source = from_node
            if from_node == conditional_source:
                conditional_targets[condition] = to_node if to_node != "END" else END
        elif to_node == "END":
            graph.add_edge(from_node, END)
        else:
            graph.add_edge(from_node, to_node)

    # Add conditional edges if any (continue/end style - legacy)
    if conditional_source and conditional_targets:
        graph.add_conditional_edges(
            conditional_source,
            _should_continue,
            conditional_targets,
        )
    
    # Add router conditional edges
    for source_node, target_nodes in router_edges.items():
        # Create routing function that reads _route from state
        def make_router_fn(targets: list[str]) -> Callable:
            def router_fn(state: ShowcaseState) -> str:
                route = state.get("_route")
                if route and route in targets:
                    return route
                # Default to first target
                return targets[0]
            return router_fn
        
        # Create mapping: target_name -> target_name (identity mapping)
        route_mapping = {target: target for target in target_nodes}
        
        graph.add_conditional_edges(
            source_node,
            make_router_fn(target_nodes),
            route_mapping,
        )
    
    # Add expression-based conditional edges
    for source_node, expr_edges in expression_edges.items():
        def make_expr_router_fn(edges: list[tuple[str, str]]) -> Callable:
            """Create router that evaluates expression conditions."""
            def expr_router_fn(state: ShowcaseState) -> str:
                # Check loop limit first
                if state.get("_loop_limit_reached"):
                    return END
                    
                for condition, target in edges:
                    try:
                        if evaluate_condition(condition, state):
                            logger.debug(f"Condition '{condition}' matched, routing to {target}")
                            return target
                    except ValueError as e:
                        logger.warning(f"Failed to evaluate condition '{condition}': {e}")
                # No condition matched - this shouldn't happen with well-formed graphs
                logger.warning(f"No condition matched for {source_node}, defaulting to END")
                return END
            return expr_router_fn
        
        # Build mapping: all possible targets
        targets = {target for _, target in expr_edges}
        targets.add(END)  # Always include END as fallback
        route_mapping = {t: (END if t == END else t) for t in targets}
        
        graph.add_conditional_edges(
            source_node,
            make_expr_router_fn(expr_edges),
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
