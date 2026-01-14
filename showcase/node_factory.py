"""Node function factory for YAML-defined graphs.

Creates LangGraph node functions from YAML configuration with support for:
- Resume (skip if output exists)
- Error handling (skip, retry, fail, fallback)
- Router nodes with dynamic routing
- Loop counting and limits
"""

import logging
from typing import Any, Callable

from showcase.executor import execute_prompt
from showcase.models import ErrorType, PipelineError, ShowcaseState

logger = logging.getLogger(__name__)


def resolve_template(template: str, state: ShowcaseState) -> Any:
    """Resolve a template string to a value from state.
    
    Args:
        template: Template string like "{state.field}" or "{state.obj.attr}"
        state: Current pipeline state
        
    Returns:
        Resolved value or None if not found
    """
    STATE_PREFIX = "{state."
    STATE_SUFFIX = "}"
    
    if not isinstance(template, str):
        return template
    
    if not (template.startswith(STATE_PREFIX) and template.endswith(STATE_SUFFIX)):
        return template
    
    # Extract path: "{state.foo.bar}" -> "foo.bar"
    path = template[len(STATE_PREFIX):-len(STATE_SUFFIX)]
    parts = path.split(".")
    
    value = state
    for part in parts:
        if value is None:
            return None
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = getattr(value, part, None)
    
    return value


def resolve_class(class_path: str) -> type:
    """Dynamically import and return a class from a module path.
    
    Args:
        class_path: Full path like "showcase.models.Analysis"
        
    Returns:
        The class object
    """
    import importlib
    
    parts = class_path.rsplit(".", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid class path: {class_path}")
    
    module_path, class_name = parts
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def create_node_function(
    node_name: str,
    node_config: dict,
    defaults: dict,
) -> Callable[[ShowcaseState], dict]:
    """Create a node function from YAML config.
    
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

    # Get config values (node > defaults)
    temperature = node_config.get("temperature", defaults.get("temperature", 0.7))
    provider = node_config.get("provider", defaults.get("provider"))
    state_key = node_config.get("state_key", node_name)
    variable_templates = node_config.get("variables", {})
    requires = node_config.get("requires", [])
    
    # Error handling
    on_error = node_config.get("on_error")
    max_retries = node_config.get("max_retries", 3)
    fallback_config = node_config.get("fallback", {})
    fallback_provider = fallback_config.get("provider") if fallback_config else None
    
    # Router config
    routes = node_config.get("routes", {})
    default_route = node_config.get("default_route")
    
    # Loop limit
    loop_limit = node_config.get("loop_limit")

    def node_fn(state: ShowcaseState) -> dict:
        """Generated node function."""
        loop_counts = dict(state.get("_loop_counts") or {})
        current_count = loop_counts.get(node_name, 0)
        
        # Check loop limit
        if loop_limit is not None and current_count >= loop_limit:
            logger.warning(f"Node {node_name} hit loop limit ({loop_limit})")
            return {"_loop_limit_reached": True, "current_step": node_name}
        
        loop_counts[node_name] = current_count + 1
        
        # Skip if output exists (resume support)
        if state.get(state_key) is not None:
            logger.info(f"Node {node_name} skipped - {state_key} already in state")
            return {"current_step": node_name, "_loop_counts": loop_counts}

        # Check requirements
        for req in requires:
            if state.get(req) is None:
                error = PipelineError(
                    type=ErrorType.STATE_ERROR,
                    message=f"Missing required state: {req}",
                    node=node_name,
                    retryable=False,
                )
                return {"error": error, "current_step": node_name, "_loop_counts": loop_counts}

        # Resolve variables
        variables = {}
        for key, template in variable_templates.items():
            resolved = resolve_template(template, state)
            if isinstance(resolved, list):
                resolved = ", ".join(str(item) for item in resolved)
            variables[key] = resolved

        def attempt_execute(use_provider: str | None) -> tuple[Any, Exception | None]:
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

        result, error = attempt_execute(provider)
        
        if error is None:
            logger.info(f"Node {node_name} completed successfully")
            update = {state_key: result, "current_step": node_name, "_loop_counts": loop_counts}
            
            # Router: add _route to state
            if node_type == "router" and routes:
                route_key = getattr(result, "tone", None) or getattr(result, "intent", None)
                if route_key and route_key in routes:
                    update["_route"] = routes[route_key]
                elif default_route:
                    update["_route"] = default_route
                else:
                    update["_route"] = list(routes.values())[0]
                logger.info(f"Router {node_name} routing to: {update['_route']}")
            return update

        # Error handling
        if on_error == "skip":
            logger.warning(f"Node {node_name} failed, skipping: {error}")
            return {"current_step": node_name, "_loop_counts": loop_counts}
        
        elif on_error == "fail":
            logger.error(f"Node {node_name} failed (on_error=fail): {error}")
            raise error
        
        elif on_error == "retry":
            for attempt in range(1, max_retries):
                logger.info(f"Node {node_name} retry {attempt}/{max_retries - 1}")
                result, error = attempt_execute(provider)
                if error is None:
                    return {state_key: result, "current_step": node_name, "_loop_counts": loop_counts}
            logger.error(f"Node {node_name} failed after {max_retries} attempts")
            pipeline_error = PipelineError.from_exception(error, node=node_name)
            return {"error": pipeline_error, "current_step": node_name, "_loop_counts": loop_counts}
        
        elif on_error == "fallback" and fallback_provider:
            logger.info(f"Node {node_name} trying fallback: {fallback_provider}")
            result, fallback_error = attempt_execute(fallback_provider)
            if fallback_error is None:
                return {state_key: result, "current_step": node_name, "_loop_counts": loop_counts}
            logger.error(f"Node {node_name} failed with primary and fallback")
            pipeline_error = PipelineError.from_exception(fallback_error, node=node_name)
            return {"error": pipeline_error, "current_step": node_name, "_loop_counts": loop_counts}
        
        else:
            logger.error(f"Node {node_name} failed: {error}")
            pipeline_error = PipelineError.from_exception(error, node=node_name)
            return {"error": pipeline_error, "current_step": node_name, "_loop_counts": loop_counts}

    node_fn.__name__ = f"{node_name}_node"
    return node_fn
