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


class GraphConfig:
    """Parsed graph configuration from YAML."""

    def __init__(self, config: dict):
        """Initialize from parsed YAML dict.
        
        Args:
            config: Parsed YAML configuration dictionary
        """
        self.version = config.get("version", "1.0")
        self.name = config.get("name", "unnamed")
        self.description = config.get("description", "")
        self.defaults = config.get("defaults", {})
        self.nodes = config.get("nodes", {})
        self.edges = config.get("edges", [])
        self.state_class = config.get("state_class", "showcase.models.ShowcaseState")
        self.conditions = config.get("conditions", {})


def load_graph_config(path: str | Path) -> GraphConfig:
    """Load and parse a YAML graph definition.
    
    Args:
        path: Path to the YAML file
        
    Returns:
        GraphConfig instance
        
    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Graph config not found: {path}")

    with open(path) as f:
        config = yaml.safe_load(f)

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
    
    if not template.startswith("{state."):
        return template

    # Extract path: "{state.foo.bar}" -> ["foo", "bar"]
    path_str = template[7:-1]  # Remove "{state." and "}"
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

    def node_fn(state: ShowcaseState) -> dict:
        """Generated node function."""
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

        try:
            result = execute_prompt(
                prompt_name=prompt_name,
                variables=variables,
                output_model=output_model,
                temperature=temperature,
                provider=provider,
            )
            
            logger.info(f"Node {node_name} completed successfully")
            return {state_key: result, "current_step": node_name}
            
        except Exception as e:
            logger.error(f"Node {node_name} failed: {e}")
            error = PipelineError.from_exception(e, node=node_name)
            return {"error": error, "current_step": node_name}

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

    # Process edges
    for edge in config.edges:
        from_node = edge["from"]
        to_node = edge["to"]
        condition = edge.get("condition")

        if from_node == "START":
            graph.set_entry_point(to_node)
            graph._entry_point = to_node  # Store for testing
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

    # Add conditional edges if any
    if conditional_source and conditional_targets:
        graph.add_conditional_edges(
            conditional_source,
            _should_continue,
            conditional_targets,
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
