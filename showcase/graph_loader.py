"""YAML Graph Loader - Compile YAML to LangGraph.

This module provides functionality to load graph definitions from YAML files
and compile them into LangGraph StateGraph instances.
"""

import importlib
import logging
from pathlib import Path
from typing import Any, Callable

import yaml
from langgraph.graph import END, StateGraph

from showcase.executor import execute_prompt
from showcase.models import ErrorType, PipelineError, ShowcaseState

logger = logging.getLogger(__name__)

# Constants for template parsing
STATE_TEMPLATE_PREFIX = "{state."
STATE_TEMPLATE_SUFFIX = "}"


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
        if not node_config.get("prompt"):
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
        self.state_class = config.get("state_class", "showcase.models.ShowcaseState")
        # Note: 'conditions' block intentionally not parsed
        # Routing is handled by _should_continue() function


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

    # Validation happens in GraphConfig.__init__
    return GraphConfig(config)


def resolve_class(class_path: str) -> type:
    """Import a class from its dotted path.
    
    Args:
        class_path: Dotted path like "showcase.models.GeneratedContent"
        
    Returns:
        The imported class
        
    Raises:
        ImportError: If module doesn't exist
        AttributeError: If class doesn't exist in module
    """
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def resolve_template(template: str, state: ShowcaseState) -> Any:
    """Resolve a template string against state.
    
    Supports simple path resolution like "{state.topic}" or 
    "{state.generated.content}" for nested access.
    
    Args:
        template: Template string with {state.path} syntax
        state: Pipeline state dictionary
        
    Returns:
        Resolved value, or None if path not found
        
    Examples:
        >>> resolve_template("{state.topic}", {"topic": "AI"})
        'AI'
        >>> resolve_template("literal", {})
        'literal'
    """
    if not isinstance(template, str):
        return template
    
    if not template.startswith(STATE_TEMPLATE_PREFIX):
        return template

    # Extract path: "{state.foo.bar}" -> ["foo", "bar"]
    prefix_len = len(STATE_TEMPLATE_PREFIX)
    suffix_len = len(STATE_TEMPLATE_SUFFIX)
    path_str = template[prefix_len:-suffix_len]
    path = path_str.split(".")

    value = state
    for part in path:
        if value is None:
            return None
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = getattr(value, part, None)

    return value


def create_node_function(
    node_name: str,
    node_config: dict,
    defaults: dict,
) -> Callable[[ShowcaseState], dict]:
    """Create a node function from YAML config.
    
    Factory function that generates node functions dynamically
    based on YAML configuration.
    
    Args:
        node_name: Name of the node
        node_config: Node configuration from YAML
        defaults: Default configuration values
        
    Returns:
        Node function compatible with LangGraph
    """
    node_type = node_config.get("type", "llm")
    prompt_name = node_config.get("prompt")
    
    # Resolve output model class
    output_model = None
    if model_path := node_config.get("output_model"):
        output_model = resolve_class(model_path)

    # Get temperature (node config > defaults)
    temperature = node_config.get("temperature", defaults.get("temperature", 0.7))
    provider = node_config.get("provider", defaults.get("provider"))
    state_key = node_config.get("state_key", node_name)
    variable_templates = node_config.get("variables", {})
    requires = node_config.get("requires", [])
    
    # Error handling config
    on_error = node_config.get("on_error")  # skip | retry | fail | fallback | None
    max_retries = node_config.get("max_retries", 3)
    fallback_config = node_config.get("fallback", {})
    fallback_provider = fallback_config.get("provider") if fallback_config else None
    
    # Router config
    routes = node_config.get("routes", {})
    default_route = node_config.get("default_route")

    def node_fn(state: ShowcaseState) -> dict:
        """Generated node function."""
        # Skip if output already exists (enables resume)
        existing = state.get(state_key)
        if existing is not None:
            logger.info(f"Node {node_name} skipped - {state_key} already in state")
            return {"current_step": node_name}

        # Check requirements
        for req in requires:
            if state.get(req) is None:
                error = PipelineError(
                    type=ErrorType.STATE_ERROR,
                    message=f"Missing required state: {req}",
                    node=node_name,
                    retryable=False,
                )
                return {"error": error, "current_step": node_name}

        # Resolve variables from state
        variables = {}
        for key, template in variable_templates.items():
            resolved = resolve_template(template, state)
            # Convert list to string for key_points
            if isinstance(resolved, list):
                resolved = ", ".join(str(item) for item in resolved)
            variables[key] = resolved

        def attempt_execute(use_provider: str | None) -> tuple[Any, Exception | None]:
            """Attempt to execute prompt with given provider."""
            try:
                result = execute_prompt(
                    prompt_name=prompt_name,
                    variables=variables,
                    output_model=output_model,
                    temperature=temperature,
                    provider=use_provider,
                )
                return result, None
            except Exception as e:
                return None, e

        # Execute with error handling based on on_error setting
        result, error = attempt_execute(provider)
        
        if error is None:
            logger.info(f"Node {node_name} completed successfully")
            update = {state_key: result, "current_step": node_name}
            
            # For router nodes, add _route to state
            if node_type == "router" and routes:
                # Get the route key from the classification result
                route_key = getattr(result, "tone", None) or getattr(result, "intent", None)
                if route_key and route_key in routes:
                    # Map the classification key to target node name
                    update["_route"] = routes[route_key]
                elif default_route:
                    update["_route"] = default_route
                else:
                    update["_route"] = list(routes.values())[0]  # First route as fallback
                logger.info(f"Router {node_name} routing to: {update['_route']}")
            
            return update

        # Handle error based on on_error setting
        if on_error == "skip":
            logger.warning(f"Node {node_name} failed, skipping: {error}")
            return {"current_step": node_name}
        
        elif on_error == "fail":
            logger.error(f"Node {node_name} failed (on_error=fail): {error}")
            raise error
        
        elif on_error == "retry":
            # Retry with configured max_retries
            for attempt in range(1, max_retries):
                logger.info(f"Node {node_name} retry {attempt}/{max_retries - 1}")
                result, error = attempt_execute(provider)
                if error is None:
                    logger.info(f"Node {node_name} completed on retry {attempt}")
                    return {state_key: result, "current_step": node_name}
            # All retries exhausted
            logger.error(f"Node {node_name} failed after {max_retries} attempts")
            pipeline_error = PipelineError.from_exception(error, node=node_name)
            return {"error": pipeline_error, "current_step": node_name}
        
        elif on_error == "fallback" and fallback_provider:
            # Try fallback provider
            logger.info(f"Node {node_name} trying fallback provider: {fallback_provider}")
            result, fallback_error = attempt_execute(fallback_provider)
            if fallback_error is None:
                logger.info(f"Node {node_name} completed with fallback provider")
                return {state_key: result, "current_step": node_name}
            # Both providers failed
            logger.error(f"Node {node_name} failed with primary and fallback providers")
            pipeline_error = PipelineError.from_exception(fallback_error, node=node_name)
            return {"error": pipeline_error, "current_step": node_name}
        
        else:
            # Default behavior: return error in state
            logger.error(f"Node {node_name} failed: {error}")
            pipeline_error = PipelineError.from_exception(error, node=node_name)
            return {"error": pipeline_error, "current_step": node_name}

    node_fn.__name__ = f"{node_name}_node"
    return node_fn


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

    # Add nodes
    for node_name, node_config in config.nodes.items():
        node_fn = create_node_function(node_name, node_config, config.defaults)
        graph.add_node(node_name, node_fn)
        logger.info(f"Added node: {node_name}")

    # Track which edges need conditional routing
    conditional_source = None
    conditional_targets = {}
    router_edges = {}  # For type: conditional edges with list targets

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
        elif condition:
            # Collect conditional edges from same source
            if conditional_source is None:
                conditional_source = from_node
            if from_node == conditional_source:
                conditional_targets[condition] = to_node if to_node != "END" else END
        elif to_node == "END":
            graph.add_edge(from_node, END)
        else:
            graph.add_edge(from_node, to_node)

    # Add conditional edges if any (continue/end style)
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
