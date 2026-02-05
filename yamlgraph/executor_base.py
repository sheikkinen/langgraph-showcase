"""Executor Base - Shared utilities for sync and async prompt execution.

Provides common functions for prompt loading, formatting, and message building.
"""

import logging
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from yamlgraph.utils.prompts import load_prompt
from yamlgraph.utils.template import validate_variables

logger = logging.getLogger(__name__)

# Exceptions that are retryable
RETRYABLE_EXCEPTIONS = (
    "RateLimitError",
    "APIConnectionError",
    "APITimeoutError",
    "InternalServerError",
    "ServiceUnavailableError",
)


def is_retryable(exception: Exception) -> bool:
    """Check if an exception is retryable.

    Args:
        exception: The exception to check

    Returns:
        True if the exception should be retried
    """
    exc_name = type(exception).__name__
    return exc_name in RETRYABLE_EXCEPTIONS or "rate" in exc_name.lower()


def format_prompt(
    template: str,
    variables: dict,
    state: dict | None = None,
) -> str:
    """Format a prompt template with variables.

    Supports both simple {variable} placeholders and Jinja2 templates.
    If the template contains Jinja2 syntax ({%, {{), uses Jinja2 rendering.

    Args:
        template: Template string with {variable} or Jinja2 placeholders
        variables: Dictionary of variable values
        state: Optional state dict for Jinja2 templates (accessible as {{ state.field }})

    Returns:
        Formatted string

    Examples:
        Simple format:
            format_prompt("Hello {name}", {"name": "World"})

        Jinja2 with variables:
            format_prompt("{% for item in items %}{{ item }}{% endfor %}", {"items": [1, 2]})

        Jinja2 with state:
            format_prompt("Topic: {{ state.topic }}", {}, state={"topic": "AI"})
    """
    # Check for Jinja2 syntax
    if "{%" in template or "{{" in template:
        from jinja2 import Template

        jinja_template = Template(template)
        # Pass both variables and state to Jinja2
        context = {"state": state or {}, **variables}
        return jinja_template.render(**context)

    # Fall back to simple format - stringify lists for compatibility
    safe_vars = {
        k: (", ".join(map(str, v)) if isinstance(v, list) else v)
        for k, v in variables.items()
    }
    return template.format(**safe_vars)


def prepare_messages(
    prompt_name: str,
    variables: dict | None = None,
    provider: str | None = None,
    model: str | None = None,
    graph_path: Path | None = None,
    prompts_dir: Path | None = None,
    prompts_relative: bool = False,
) -> tuple[list, str | None, str | None]:
    """Load prompt, validate, format, and build messages.

    Shared logic for sync and async executors.

    Args:
        prompt_name: Name of the prompt file (without .yaml)
        variables: Variables to substitute in the template
        provider: LLM provider override (None to use YAML/env default)
        model: LLM model override (None to use YAML/env default)
        graph_path: Path to graph file for relative prompt resolution
        prompts_dir: Explicit prompts directory override
        prompts_relative: If True, resolve prompts relative to graph_path

    Returns:
        Tuple of (messages list, resolved provider, resolved model)

    Raises:
        ValueError: If required template variables are missing
    """
    variables = variables or {}

    prompt_config = load_prompt(
        prompt_name,
        prompts_dir=prompts_dir,
        graph_path=graph_path,
        prompts_relative=prompts_relative,
    )

    # Validate all required variables are provided (fail fast)
    full_template = prompt_config.get("system", "") + prompt_config.get("user", "")
    validate_variables(full_template, variables, prompt_name)

    # Extract provider and model from YAML if not provided via parameter
    resolved_provider = provider
    if resolved_provider is None:
        resolved_provider = prompt_config.get("provider")
        if resolved_provider:
            logger.debug(f"Using provider from YAML: {resolved_provider}")

    resolved_model = model
    if resolved_model is None:
        resolved_model = prompt_config.get("model")
        if resolved_model:
            logger.debug(f"Using model from YAML: {resolved_model}")

    system_text = format_prompt(prompt_config.get("system", ""), variables)
    user_text = format_prompt(prompt_config["user"], variables)

    messages = []
    if system_text:
        messages.append(SystemMessage(content=system_text))
    messages.append(HumanMessage(content=user_text))

    return messages, resolved_provider, resolved_model
