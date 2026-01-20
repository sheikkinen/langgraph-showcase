"""Node function factory for YAML-defined graphs.

Creates LangGraph node functions from YAML configuration with support for:
- Resume (skip if output exists)
- Error handling (skip, retry, fail, fallback)
- Router nodes with dynamic routing
- Loop counting and limits
- Dynamic tool calls from state (type: tool_call)
- Streaming nodes (type: llm, stream: true)
- Subgraph nodes (type: subgraph) for composing workflows
"""

import logging
from collections.abc import AsyncIterator, Callable
from contextvars import ContextVar
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
from yamlgraph.utils.expressions import resolve_template
from yamlgraph.utils.prompts import resolve_prompt_path

# Type alias for dynamic state
GraphState = dict[str, Any]

logger = logging.getLogger(__name__)

# Thread-safe loading stack to detect circular subgraph references
# Note: Do NOT use default=[] as it shares the same list across contexts
_loading_stack: ContextVar[list[Path]] = ContextVar("loading_stack")


def create_tool_call_node(
    node_name: str,
    node_config: dict[str, Any],
    tools_registry: dict[str, Callable],
) -> Callable[[GraphState], dict]:
    """Create a node that dynamically calls a tool from state.

    This enables YAML-driven tool execution where tool name and args
    are resolved from state at runtime.

    Args:
        node_name: Name of the node
        node_config: Node configuration with 'tool', 'args', 'state_key'
        tools_registry: Dict mapping tool names to callable functions

    Returns:
        Node function compatible with LangGraph
    """
    tool_expr = node_config["tool"]  # e.g., "{state.task.tool}"
    args_expr = node_config["args"]  # e.g., "{state.task.args}"
    state_key = node_config.get("state_key", "result")

    def node_fn(state: dict) -> dict:
        # Resolve tool name and args from state
        tool_name = resolve_template(tool_expr, state)
        args = resolve_template(args_expr, state)

        # Extract task_id if available
        task = state.get("task", {})
        task_id = task.get("id") if isinstance(task, dict) else None

        # Look up tool in registry
        tool_func = tools_registry.get(tool_name)
        if tool_func is None:
            return {
                state_key: {
                    "task_id": task_id,
                    "tool": tool_name,
                    "success": False,
                    "result": None,
                    "error": f"Unknown tool: {tool_name}",
                },
                "current_step": node_name,
            }

        # Execute tool
        try:
            # Ensure args is a dict
            if not isinstance(args, dict):
                args = {}
            result = tool_func(**args)
            return {
                state_key: {
                    "task_id": task_id,
                    "tool": tool_name,
                    "success": True,
                    "result": result,
                    "error": None,
                },
                "current_step": node_name,
            }
        except Exception as e:
            return {
                state_key: {
                    "task_id": task_id,
                    "tool": tool_name,
                    "success": False,
                    "result": None,
                    "error": str(e),
                },
                "current_step": node_name,
            }

    node_fn.__name__ = f"{node_name}_tool_call"
    return node_fn


def resolve_class(class_path: str) -> type:
    """Dynamically import and return a class from a module path.

    Args:
        class_path: Full path like "yamlgraph.models.GenericReport" or short name

    Returns:
        The class object
    """
    import importlib

    parts = class_path.rsplit(".", 1)
    if len(parts) != 2:
        # Try to find in yamlgraph.models.schemas
        try:
            from yamlgraph.models import schemas

            if hasattr(schemas, class_path):
                return getattr(schemas, class_path)
        except ImportError:
            pass
        raise ValueError(f"Invalid class path: {class_path}")

    module_path, class_name = parts
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


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
            from yamlgraph.schema_loader import load_schema_from_yaml

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

    # Check for streaming mode
    if node_config.get("stream", False):
        return create_streaming_node(node_name, node_config)

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
        if check_loop_limit(node_name, loop_limit, current_count):
            return {"_loop_limit_reached": True, "current_step": node_name}

        loop_counts[node_name] = current_count + 1

        # Skip if output exists (resume support) - disabled for loop nodes
        if skip_if_exists and state.get(state_key) is not None:
            logger.info(f"Node {node_name} skipped - {state_key} already in state")
            return {"current_step": node_name, "_loop_counts": loop_counts}

        # Check requirements
        if error := check_requirements(requires, state, node_name):
            return {
                "errors": [error],
                "current_step": node_name,
                "_loop_counts": loop_counts,
            }

        # Resolve variables from templates OR use state directly
        if variable_templates:
            variables = {}
            for key, template in variable_templates.items():
                resolved = resolve_template(template, state)
                if isinstance(resolved, list):
                    resolved = ", ".join(str(item) for item in resolved)
                variables[key] = resolved
        else:
            # No explicit variable mapping - pass state as variables
            # Filter out internal keys and None values
            variables = {
                k: v
                for k, v in state.items()
                if not k.startswith("_") and v is not None
            }

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

        # Error handling - dispatch to strategy handlers
        if on_error == ErrorHandler.SKIP:
            handle_skip(node_name, error, loop_counts)
            return {"current_step": node_name, "_loop_counts": loop_counts}

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


def create_interrupt_node(
    node_name: str,
    config: dict[str, Any],
) -> Callable[[GraphState], dict]:
    """Create an interrupt node that pauses for human input.

    Uses LangGraph's native interrupt() function for human-in-the-loop.
    Handles idempotency by checking state_key before re-executing prompts.

    Args:
        node_name: Name of the node
        config: Node configuration with optional keys:
            - message: Static interrupt payload (string or dict)
            - prompt: Prompt name to generate dynamic payload
            - state_key: Where to store payload (default: "interrupt_message")
            - resume_key: Where to store resume value (default: "user_input")

    Returns:
        Node function compatible with LangGraph
    """
    from langgraph.types import interrupt

    message = config.get("message")
    prompt_name = config.get("prompt")
    state_key = config.get("state_key", "interrupt_message")
    resume_key = config.get("resume_key", "user_input")

    def interrupt_fn(state: dict) -> dict:
        # Check if we already have a payload (resuming) - idempotency
        existing_payload = state.get(state_key)

        if existing_payload is not None:
            # Resuming - use stored payload, don't re-execute prompt
            payload = existing_payload
        elif prompt_name:
            # First execution with prompt
            payload = execute_prompt(prompt_name, state)
        elif message is not None:
            # Static message
            payload = message
        else:
            # Fallback: use node name as payload
            payload = {"node": node_name}

        # Native LangGraph interrupt - pauses here on first run
        # On resume, returns the Command(resume=...) value
        response = interrupt(payload)

        return {
            state_key: payload,  # Store for idempotency check
            resume_key: response,  # User's response
            "current_step": node_name,
        }

    interrupt_fn.__name__ = f"{node_name}_interrupt"
    return interrupt_fn


def create_passthrough_node(
    node_name: str,
    config: dict[str, Any],
) -> Callable[[GraphState], dict]:
    """Create a passthrough node that transforms state without external calls.

    Useful for:
    - Loop counters (increment values)
    - State accumulation (append to lists)
    - Simple data transformations
    - Clean transition points in graphs

    Args:
        node_name: Name of the node
        config: Node configuration with:
            - output: Dict of state_key -> expression mappings
                      Expressions use {state.field} syntax
                      Supports arithmetic: {state.count + 1}
                      Supports list append: {state.history + [state.current]}

    Returns:
        Node function compatible with LangGraph

    Example:
        ```yaml
        next_turn:
          type: passthrough
          output:
            turn_number: "{state.turn_number + 1}"
            history: "{state.history + [state.narration]}"
        ```
    """
    from yamlgraph.utils.expressions import resolve_template

    output_templates = config.get("output", {})

    def passthrough_fn(state: dict) -> dict:
        result = {"current_step": node_name}

        for key, template in output_templates.items():
            try:
                resolved = resolve_template(template, state)
                # If resolution failed (None) and key exists in state, keep original
                if resolved is None and key in state:
                    result[key] = state[key]
                else:
                    result[key] = resolved
            except Exception as e:
                logger.warning(
                    f"Passthrough node {node_name}: failed to resolve {key}: {e}"
                )
                # Keep original value on error
                if key in state:
                    result[key] = state[key]

        logger.info(f"Node {node_name} completed successfully")
        return result

    passthrough_fn.__name__ = f"{node_name}_passthrough"
    return passthrough_fn


def create_streaming_node(
    node_name: str,
    node_config: dict[str, Any],
) -> Callable[[GraphState], AsyncIterator[str]]:
    """Create a streaming node that yields tokens.

    Streaming nodes are async generators that yield tokens as they
    are produced by the LLM. They do not support structured output.

    Args:
        node_name: Name of the node
        node_config: Node configuration with:
            - prompt: Prompt name to execute
            - state_key: Where to store final result (optional)
            - on_token: Optional callback function for each token
            - provider: LLM provider
            - temperature: LLM temperature

    Returns:
        Async generator function compatible with streaming execution
    """
    from yamlgraph.executor_async import execute_prompt_streaming
    from yamlgraph.utils.expressions import resolve_template

    prompt_name = node_config.get("prompt")
    variable_templates = node_config.get("variables", {})
    provider = node_config.get("provider")
    temperature = node_config.get("temperature", 0.7)
    on_token = node_config.get("on_token")

    async def streaming_node(state: dict) -> AsyncIterator[str]:
        # Resolve variables from templates OR use state directly
        if variable_templates:
            variables = {}
            for key, template in variable_templates.items():
                resolved = resolve_template(template, state)
                if isinstance(resolved, list):
                    resolved = ", ".join(str(item) for item in resolved)
                variables[key] = resolved
        else:
            # No explicit variable mapping - pass state as variables
            variables = {
                k: v
                for k, v in state.items()
                if not k.startswith("_") and v is not None
            }

        async for token in execute_prompt_streaming(
            prompt_name,
            variables=variables,
            provider=provider,
            temperature=temperature,
        ):
            if on_token:
                on_token(token)
            yield token

    streaming_node.__name__ = f"{node_name}_streaming"
    return streaming_node


# =============================================================================
# Subgraph Node Support
# =============================================================================


def _map_input_state(
    parent_state: dict[str, Any],
    input_mapping: dict[str, str] | str,
) -> dict[str, Any]:
    """Map parent state to child input based on mapping config.

    Args:
        parent_state: Current state from parent graph
        input_mapping: Mapping configuration:
            - dict: explicit {parent_key: child_key} mapping
            - "auto": copy all fields
            - "*": pass state reference directly

    Returns:
        Input state for child graph
    """
    if input_mapping == "auto":
        return parent_state.copy()
    elif input_mapping == "*":
        return parent_state
    else:
        return {
            child_key: parent_state.get(parent_key)
            for parent_key, child_key in input_mapping.items()
        }


def _map_output_state(
    child_output: dict[str, Any],
    output_mapping: dict[str, str] | str,
) -> dict[str, Any]:
    """Map child output to parent state updates based on mapping config.

    Args:
        child_output: Output state from child graph
        output_mapping: Mapping configuration:
            - dict: explicit {parent_key: child_key} mapping
            - "auto": pass all fields
            - "*": pass output directly

    Returns:
        Updates to apply to parent state
    """
    if output_mapping in ("auto", "*"):
        return child_output
    else:
        return {
            parent_key: child_output.get(child_key)
            for parent_key, child_key in output_mapping.items()
        }


def _build_child_config(
    parent_config: dict[str, Any],
    node_name: str,
) -> dict[str, Any]:
    """Build child graph config with propagated thread ID.

    Args:
        parent_config: RunnableConfig from parent graph
        node_name: Name of the subgraph node

    Returns:
        Config for child graph with thread_id: parent_thread:node_name
    """
    configurable = parent_config.get("configurable", {})
    parent_thread_id = configurable.get("thread_id")

    child_thread_id = (
        f"{parent_thread_id}:{node_name}" if parent_thread_id else node_name
    )

    return {
        **parent_config,
        "configurable": {
            **configurable,
            "thread_id": child_thread_id,
        },
    }


def create_subgraph_node(
    node_name: str,
    node_config: dict[str, Any],
    parent_graph_path: Path,
    parent_checkpointer: Any | None = None,
) -> Callable[[dict, dict], dict] | Any:
    """Create a node that invokes a compiled subgraph.

    Args:
        node_name: Name of this node in parent graph
        node_config: Subgraph configuration from YAML
        parent_graph_path: Path to parent graph (for relative resolution)
        parent_checkpointer: Checkpointer to inherit (if any)

    Returns:
        Node function that invokes subgraph (or CompiledGraph for mode=direct)

    Raises:
        FileNotFoundError: If subgraph YAML doesn't exist
        ValueError: If circular reference detected
    """
    from yamlgraph.graph_loader import compile_graph, load_graph_config

    # Resolve path relative to parent graph file
    graph_rel_path = node_config["graph"]
    graph_path = (parent_graph_path.parent / graph_rel_path).resolve()

    mode = node_config.get("mode", "invoke")
    input_mapping = node_config.get("input_mapping", {})
    output_mapping = node_config.get("output_mapping", {})

    # Validate graph exists
    if not graph_path.exists():
        raise FileNotFoundError(f"Subgraph not found: {graph_path}")

    # Circular reference detection (thread-safe)
    # Use .get([]) to provide default without sharing mutable state
    stack = _loading_stack.get([])
    if graph_path in stack:
        cycle = " -> ".join(str(p) for p in [*stack, graph_path])
        raise ValueError(f"Circular subgraph reference: {cycle}")

    # Push onto loading stack for this context
    token = _loading_stack.set([*stack, graph_path])
    try:
        subgraph_config = load_graph_config(graph_path)
        state_graph = compile_graph(subgraph_config)
        # Compile with checkpointer (if provided)
        compiled = state_graph.compile(checkpointer=parent_checkpointer)
    finally:
        _loading_stack.reset(token)

    if mode == "direct":
        # Mode: Direct - shared schema, LangGraph handles state mapping
        # Return compiled graph directly - LangGraph's add_node() accepts
        # CompiledStateGraph objects and handles them natively
        return compiled

    # Mode: Invoke - explicit state mapping
    from langchain_core.runnables import RunnableConfig

    def subgraph_node(state: dict, config: RunnableConfig | None = None) -> dict:
        """Execute the subgraph with mapped state."""
        config = config or {}

        # Build child input from parent state
        child_input = _map_input_state(state, input_mapping)

        # Build child config with propagated thread ID
        child_config = _build_child_config(config, node_name)

        # Invoke subgraph
        child_output = compiled.invoke(child_input, child_config)

        # Map child output back to parent state
        parent_updates = _map_output_state(child_output, output_mapping)
        parent_updates["current_step"] = node_name

        return parent_updates

    subgraph_node.__name__ = f"{node_name}_subgraph"
    return subgraph_node
