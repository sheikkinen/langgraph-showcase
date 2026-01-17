"""Async Prompt Executor - Async interface for LLM calls.

This module provides async versions of execute_prompt for use in
async contexts like web servers or concurrent pipelines.

Note: This is a foundation module. The underlying LLM calls still
use sync HTTP clients wrapped with run_in_executor.
"""

import asyncio
import logging
from typing import Type, TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from yamlgraph.config import DEFAULT_TEMPERATURE
from yamlgraph.executor import format_prompt, load_prompt
from yamlgraph.utils.llm_factory import create_llm
from yamlgraph.utils.llm_factory_async import invoke_async
from yamlgraph.utils.template import validate_variables

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


async def execute_prompt_async(
    prompt_name: str,
    variables: dict | None = None,
    output_model: Type[T] | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    provider: str | None = None,
) -> T | str:
    """Execute a YAML prompt asynchronously.

    Async version of execute_prompt for use in async contexts.

    Args:
        prompt_name: Name of the prompt file (without .yaml)
        variables: Variables to substitute in the template
        output_model: Optional Pydantic model for structured output
        temperature: LLM temperature setting
        provider: LLM provider ("anthropic", "mistral", "openai")

    Returns:
        Parsed Pydantic model if output_model provided, else raw string

    Example:
        >>> result = await execute_prompt_async(
        ...     "greet",
        ...     variables={"name": "World"},
        ...     output_model=GenericReport,
        ... )
    """
    variables = variables or {}

    # Load and validate prompt (sync - file I/O is fast)
    prompt_config = load_prompt(prompt_name)

    full_template = prompt_config.get("system", "") + prompt_config.get("user", "")
    validate_variables(full_template, variables, prompt_name)

    # Extract provider from YAML metadata if not provided
    if provider is None and "provider" in prompt_config:
        provider = prompt_config["provider"]
        logger.debug(f"Using provider from YAML metadata: {provider}")

    system_text = format_prompt(prompt_config.get("system", ""), variables)
    user_text = format_prompt(prompt_config["user"], variables)

    messages = []
    if system_text:
        messages.append(SystemMessage(content=system_text))
    messages.append(HumanMessage(content=user_text))

    # Create LLM (cached via factory)
    llm = create_llm(temperature=temperature, provider=provider)

    # Invoke asynchronously
    return await invoke_async(llm, messages, output_model)


async def execute_prompts_concurrent(
    prompts: list[dict],
) -> list[BaseModel | str]:
    """Execute multiple prompts concurrently.

    Useful for parallel LLM calls in pipelines.

    Args:
        prompts: List of dicts with keys:
            - prompt_name: str (required)
            - variables: dict (optional)
            - output_model: Type[BaseModel] (optional)
            - temperature: float (optional)
            - provider: str (optional)

    Returns:
        List of results in same order as input prompts

    Example:
        >>> results = await execute_prompts_concurrent([
        ...     {"prompt_name": "summarize", "variables": {"text": "..."}},
        ...     {"prompt_name": "analyze", "variables": {"text": "..."}},
        ... ])
    """
    tasks = []
    for prompt_config in prompts:
        task = execute_prompt_async(
            prompt_name=prompt_config["prompt_name"],
            variables=prompt_config.get("variables"),
            output_model=prompt_config.get("output_model"),
            temperature=prompt_config.get("temperature", DEFAULT_TEMPERATURE),
            provider=prompt_config.get("provider"),
        )
        tasks.append(task)

    return await asyncio.gather(*tasks)


__all__ = ["execute_prompt_async", "execute_prompts_concurrent"]
