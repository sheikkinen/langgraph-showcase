"""Streaming node factory.

Creates LangGraph nodes that stream LLM output.
"""

import logging
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

from yamlgraph.node_factory.base import GraphState
from yamlgraph.utils.expressions import resolve_node_variables

logger = logging.getLogger(__name__)


def create_streaming_node(
    node_name: str,
    node_config: dict[str, Any],
    graph_path: Path | None = None,
    prompts_dir: Path | None = None,
    prompts_relative: bool = False,
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
        graph_path: Path to graph YAML file (for relative prompt resolution)
        prompts_dir: Explicit prompts directory override
        prompts_relative: If True, resolve prompts relative to graph_path

    Returns:
        Async generator function compatible with streaming execution
    """
    from yamlgraph.executor_async import execute_prompt_streaming

    prompt_name = node_config.get("prompt")
    variable_templates = node_config.get("variables", {})
    provider = node_config.get("provider")
    temperature = node_config.get("temperature", 0.7)
    on_token = node_config.get("on_token")

    async def streaming_node(state: dict) -> AsyncIterator[str]:
        # Resolve variables from templates OR use state directly
        variables = resolve_node_variables(variable_templates, state)

        async for token in execute_prompt_streaming(
            prompt_name,
            variables=variables,
            provider=provider,
            temperature=temperature,
            graph_path=graph_path,
            prompts_dir=prompts_dir,
            prompts_relative=prompts_relative,
            state=state,
        ):
            if on_token:
                on_token(token)
            yield token

    streaming_node.__name__ = f"{node_name}_streaming"
    return streaming_node
