"""Node function factory for YAML-defined graphs.

Creates LangGraph node functions from YAML configuration with support for:
- Resume (skip if output exists)
- Error handling (skip, retry, fail, fallback)
- Router nodes with dynamic routing
- Loop counting and limits
"""

import logging
from typing import Any, Callable

from showcase.constants import ErrorHandler, NodeType
from showcase.executor import execute_prompt
from showcase.models import ErrorType, PipelineError
from showcase.utils.expressions import resolve_template

# Type alias for dynamic state
GraphState = dict[str, Any]

logger = logging.getLogger(__name__)


def resolve_class(class_path: str) -> type:
    """Dynamically import and return a class from a module path.

    Args:
        class_path: Full path like "showcase.models.GenericReport" or short name

    Returns:
        The class object
    """
    import importlib

    parts = class_path.rsplit(".", 1)
    if len(parts) != 2:
        # Try to find in showcase.models.schemas
        try:
            from showcase.models import schemas

            if hasattr(schemas, class_path):
                return getattr(schemas, class_path)
        except ImportError:
            pass
        raise ValueError(f"Invalid class path: {class_path}")

    module_path, class_name = parts
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def resolve_prompt_path(prompt_name: str, prompts_dir: str | None = None) -> str:
    """Resolve a prompt name to its full YAML file path.

    Search order:
    1. prompts_dir/{prompt_name}.yaml (default: prompts/)
    2. {prompt_name}/prompts/{basename}.yaml (for external examples)

    Args:
        prompt_name: Prompt name like "greet" or "examples/storyboard/expand_story"
        prompts_dir: Base prompts directory (defaults to "prompts/")

    Returns:
        Full path to the YAML file

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    import os

    if prompts_dir is None:
        prompts_dir = os.environ.get("PROMPTS_DIR", "prompts")

    # Try standard location first: prompts/{prompt_name}.yaml
    yaml_path = os.path.join(prompts_dir, f"{prompt_name}.yaml")
    if os.path.exists(yaml_path):
        return yaml_path

    # Try external example location: {parent}/prompts/{basename}.yaml
    # e.g., "examples/storyboard/expand_story" -> "examples/storyboard/prompts/expand_story.yaml"
    parts = prompt_name.rsplit("/", 1)
    if len(parts) == 2:
        parent_dir, basename = parts
        alt_path = os.path.join(parent_dir, "prompts", f"{basename}.yaml")
        if os.path.exists(alt_path):
            return alt_path

    raise FileNotFoundError(f"Prompt not found: {yaml_path}")


def get_output_model_for_node(
    node_config: dict[str, Any], prompts_dir: str | None = None
) -> type | None:
    """Get output model for a node, checking inline schema if no explicit model.

    Priority:
    1. Explicit output_model in node config (class path)
    2. Inline schema in prompt YAML file
    3. None (raw string output)

    Args:
        node_config: Node configuration from YAML
        prompts_dir: Base prompts directory

    Returns:
        Pydantic model class or None
    """
    # 1. Check for explicit output_model
    if model_path := node_config.get("output_model"):
        return resolve_class(model_path)

    # 2. Check for inline schema in prompt YAML
    prompt_name = node_config.get("prompt")
    if prompt_name:
        try:
            from showcase.schema_loader import load_schema_from_yaml

            yaml_path = resolve_prompt_path(prompt_name, prompts_dir)
            return load_schema_from_yaml(yaml_path)
        except FileNotFoundError:
            # Prompt file doesn't exist yet - will fail later
            pass

    # 3. No output model
    return None


def create_node_function(
    node_name: str,
    node_config: dict,
    defaults: dict,
) -> Callable[[GraphState], dict]:
    """Create a node function from YAML config.

    Args:
        node_name: Name of the node
        node_config: Node configuration from YAML
        defaults: Default configuration values

    Returns:
        Node function compatible with LangGraph
    """
    node_type = node_config.get("type", NodeType.LLM)
    prompt_name = node_config.get("prompt")

    # Resolve output model (explicit > inline schema > None)
    output_model = get_output_model_for_node(node_config)

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

    # Skip if exists (default true for resume support, false for loop nodes)
    skip_if_exists = node_config.get("skip_if_exists", True)

    def node_fn(state: dict) -> dict:
        """Generated node function."""
        loop_counts = dict(state.get("_loop_counts") or {})
        current_count = loop_counts.get(node_name, 0)

        # Check loop limit
        if loop_limit is not None and current_count >= loop_limit:
            logger.warning(f"Node {node_name} hit loop limit ({loop_limit})")
            return {"_loop_limit_reached": True, "current_step": node_name}

        loop_counts[node_name] = current_count + 1

        # Skip if output exists (resume support) - disabled for loop nodes
        if skip_if_exists and state.get(state_key) is not None:
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
                return {
                    "error": error,
                    "current_step": node_name,
                    "_loop_counts": loop_counts,
                }

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
            update = {
                state_key: result,
                "current_step": node_name,
                "_loop_counts": loop_counts,
            }

            # Router: add _route to state
            if node_type == NodeType.ROUTER and routes:
                route_key = getattr(result, "tone", None) or getattr(
                    result, "intent", None
                )
                if route_key and route_key in routes:
                    update["_route"] = routes[route_key]
                elif default_route:
                    update["_route"] = default_route
                else:
                    update["_route"] = list(routes.values())[0]
                logger.info(f"Router {node_name} routing to: {update['_route']}")
            return update

        # Error handling
        if on_error == ErrorHandler.SKIP:
            logger.warning(f"Node {node_name} failed, skipping: {error}")
            return {"current_step": node_name, "_loop_counts": loop_counts}

        elif on_error == ErrorHandler.FAIL:
            logger.error(f"Node {node_name} failed (on_error=fail): {error}")
            raise error

        elif on_error == ErrorHandler.RETRY:
            last_exception: Exception | None = None
            for attempt in range(1, max_retries):
                logger.info(f"Node {node_name} retry {attempt}/{max_retries - 1}")
                result, error = attempt_execute(provider)
                if error is None:
                    return {
                        state_key: result,
                        "current_step": node_name,
                        "_loop_counts": loop_counts,
                    }
                last_exception = error
            logger.error(f"Node {node_name} failed after {max_retries} attempts")
            pipeline_error = PipelineError.from_exception(
                last_exception or Exception("Unknown error"), node=node_name
            )
            return {
                "error": pipeline_error,
                "current_step": node_name,
                "_loop_counts": loop_counts,
            }

        elif on_error == ErrorHandler.FALLBACK and fallback_provider:
            logger.info(f"Node {node_name} trying fallback: {fallback_provider}")
            result, fallback_error = attempt_execute(fallback_provider)
            if fallback_error is None:
                return {
                    state_key: result,
                    "current_step": node_name,
                    "_loop_counts": loop_counts,
                }
            logger.error(f"Node {node_name} failed with primary and fallback")
            pipeline_error = PipelineError.from_exception(
                fallback_error, node=node_name
            )
            return {
                "error": pipeline_error,
                "current_step": node_name,
                "_loop_counts": loop_counts,
            }

        else:
            logger.error(f"Node {node_name} failed: {error}")
            pipeline_error = PipelineError.from_exception(error, node=node_name)
            return {
                "error": pipeline_error,
                "current_step": node_name,
                "_loop_counts": loop_counts,
            }

    node_fn.__name__ = f"{node_name}_node"
    return node_fn
