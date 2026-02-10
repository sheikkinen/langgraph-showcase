"""LLM node factories.

Creates LangGraph nodes that invoke LLM prompts.
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from yamlgraph.constants import ErrorHandler, NodeType
from yamlgraph.error_handlers import (
    check_loop_limit,
    check_requirements,
    handle_default,
    handle_fail,
    handle_fallback,
    handle_retry,
    handle_skip,
)
from yamlgraph.executor import execute_prompt
from yamlgraph.node_factory.base import GraphState, get_output_model_for_node
from yamlgraph.utils.expressions import resolve_node_variables
from yamlgraph.utils.json_extract import extract_json

logger = logging.getLogger(__name__)


def create_node_function(
    node_name: str,
    node_config: dict,
    defaults: dict,
    graph_path: Path | None = None,
) -> Callable[[GraphState], dict]:
    """Create a node function from YAML config.

    Args:
        node_name: Name of the node
        node_config: Node configuration from YAML
        defaults: Default configuration values
        graph_path: Path to graph YAML file (for relative prompt resolution)

    Returns:
        Node function compatible with LangGraph
    """
    from yamlgraph.node_factory.streaming import create_streaming_node

    node_type = node_config.get("type", NodeType.LLM)
    prompt_name = node_config.get("prompt")

    # Prompt resolution options from defaults (FR-A)
    prompts_relative = defaults.get("prompts_relative", False)
    prompts_dir = defaults.get("prompts_dir")
    if prompts_dir:
        prompts_dir = Path(prompts_dir)

    # Check for streaming mode
    if node_config.get("stream", False):
        return create_streaming_node(
            node_name,
            node_config,
            graph_path=graph_path,
            prompts_dir=prompts_dir,
            prompts_relative=prompts_relative,
        )

    # Resolve output model (explicit > inline schema > None)
    # When parse_json is true, skip output_model (provider doesn't support structured output)
    parse_json = node_config.get("parse_json", False)
    if parse_json:
        output_model = None  # Use manual JSON parsing instead
    else:
        output_model = get_output_model_for_node(
            node_config,
            prompts_dir=prompts_dir,
            graph_path=graph_path,
            prompts_relative=prompts_relative,
        )

    # Get config values (node > defaults)
    temperature = node_config.get("temperature", defaults.get("temperature", 0.7))
    provider = node_config.get("provider", defaults.get("provider"))
    model = node_config.get("model", defaults.get("model"))
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
        if check_loop_limit(node_name, loop_limit, current_count):
            return {"_loop_limit_reached": True, "current_step": node_name}

        loop_counts[node_name] = current_count + 1

        # Skip if output exists (resume support) - disabled for loop nodes
        if skip_if_exists and state.get(state_key) is not None:
            logger.info(f"Node {node_name} skipped - {state_key} already in state")
            return {"current_step": node_name, "_loop_counts": loop_counts}

        # Check requirements
        if error := check_requirements(requires, state, node_name):
            # State-level "errors" list accumulates via add reducer
            return {
                "errors": [error],
                "current_step": node_name,
                "_loop_counts": loop_counts,
            }

        # Resolve variables from templates OR use state directly
        variables = resolve_node_variables(variable_templates, state)

        def attempt_execute(use_provider: str | None) -> tuple[Any, Exception | None]:
            try:
                result = execute_prompt(
                    prompt_name=prompt_name,
                    variables=variables,
                    output_model=output_model,
                    temperature=temperature,
                    provider=use_provider,
                    model=model,
                    graph_path=graph_path,
                    prompts_dir=prompts_dir,
                    prompts_relative=prompts_relative,
                    state=state,
                )
                return result, None
            except Exception as e:
                return None, e

        result, error = attempt_execute(provider)

        if error is None:
            # Post-process: JSON extraction if enabled (FR-B)
            if parse_json and isinstance(result, str):
                result = extract_json(result)

            logger.info(f"Node {node_name} completed successfully")
            update = {
                state_key: result,
                "current_step": node_name,
                "_loop_counts": loop_counts,
            }

            # Router: add _route to state
            if node_type == NodeType.ROUTER and routes:
                # Support both Pydantic models (getattr) and dicts (.get)
                if isinstance(result, dict):
                    route_key = result.get("tone") or result.get("intent")
                else:
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

        # Error handling - dispatch to strategy handlers
        if on_error == ErrorHandler.SKIP:
            handle_skip(node_name, error, loop_counts)
            return {
                state_key: None,  # Clear to prevent stale data
                "current_step": node_name,
                "_loop_counts": loop_counts,
                "_skipped": True,
                "_skip_reason": "error",
            }

        elif on_error == ErrorHandler.FAIL:
            handle_fail(node_name, error)

        elif on_error == ErrorHandler.RETRY:
            result = handle_retry(
                node_name,
                lambda: attempt_execute(provider),
                max_retries,
            )
            return result.to_state_update(state_key, node_name, loop_counts)

        elif on_error == ErrorHandler.FALLBACK and fallback_provider:
            result = handle_fallback(
                node_name,
                attempt_execute,
                fallback_provider,
            )
            return result.to_state_update(state_key, node_name, loop_counts)

        else:
            result = handle_default(node_name, error)
            return result.to_state_update(state_key, node_name, loop_counts)

    node_fn.__name__ = f"{node_name}_node"
    return node_fn
