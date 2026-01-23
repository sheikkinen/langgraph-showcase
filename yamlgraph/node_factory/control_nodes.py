"""Control flow node factories.

Creates interrupt and passthrough nodes for flow control.
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from yamlgraph.executor_base import format_prompt
from yamlgraph.node_factory.base import GraphState

logger = logging.getLogger(__name__)


def create_interrupt_node(
    node_name: str,
    config: dict[str, Any],
    graph_path: Path | None = None,
    prompts_dir: Path | None = None,
    prompts_relative: bool = False,
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
        graph_path: Path to graph file for relative prompt resolution
        prompts_dir: Explicit prompts directory override
        prompts_relative: If True, resolve prompts relative to graph_path

    Returns:
        Node function compatible with LangGraph
    """
    from langgraph.types import interrupt

    from yamlgraph.executor import execute_prompt

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
            payload = execute_prompt(
                prompt_name,
                state,
                graph_path=graph_path,
                prompts_dir=prompts_dir,
                prompts_relative=prompts_relative,
            )
        elif message is not None:
            # Static message - check for template syntax and interpolate
            # Jinja2: {{ or {% | Simple: {word}
            has_template = "{{" in message or "{%" in message or (
                "{" in message and "}" in message
            )
            if has_template:
                payload = format_prompt(message, state, state)
            else:
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
