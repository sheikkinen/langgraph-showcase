"""YAML Prompt Executor - Unified interface for LLM calls.

This module provides a simple, reusable executor for YAML-defined prompts
with support for structured outputs via Pydantic models.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Type, TypeVar

import yaml
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from yamlgraph.config import (
    DEFAULT_TEMPERATURE,
    MAX_RETRIES,
    PROMPTS_DIR,
    RETRY_BASE_DELAY,
    RETRY_MAX_DELAY,
)
from yamlgraph.utils.llm_factory import create_llm
from yamlgraph.utils.template import validate_variables

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


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


def load_prompt(prompt_name: str) -> dict:
    """Load a YAML prompt template.

    Search order:
    1. prompts/{prompt_name}.yaml
    2. {parent}/prompts/{basename}.yaml (for external examples like examples/storyboard/...)

    Args:
        prompt_name: Name of the prompt file (without .yaml extension)

    Returns:
        Dictionary with 'system' and 'user' keys
    """
    # Try standard location first
    prompt_path = PROMPTS_DIR / f"{prompt_name}.yaml"
    if prompt_path.exists():
        with open(prompt_path) as f:
            return yaml.safe_load(f)

    # Try external example location: {parent}/prompts/{basename}.yaml
    parts = prompt_name.rsplit("/", 1)
    if len(parts) == 2:
        parent_dir, basename = parts
        alt_path = Path(parent_dir) / "prompts" / f"{basename}.yaml"
        if alt_path.exists():
            with open(alt_path) as f:
                return yaml.safe_load(f)

    raise FileNotFoundError(f"Prompt not found: {prompt_path}")


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


def execute_prompt(
    prompt_name: str,
    variables: dict | None = None,
    output_model: Type[T] | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    provider: str | None = None,
) -> T | str:
    """Execute a YAML prompt with optional structured output.

    Uses the singleton PromptExecutor for LLM caching.

    Args:
        prompt_name: Name of the prompt file (without .yaml)
        variables: Variables to substitute in the template
        output_model: Optional Pydantic model for structured output
        temperature: LLM temperature setting
        provider: LLM provider ("anthropic", "mistral", "openai").
                 Can also be set in YAML metadata or PROVIDER env var.

    Returns:
        Parsed Pydantic model if output_model provided, else raw string

    Example:
        >>> result = execute_prompt(
        ...     "greet",
        ...     variables={"name": "World", "style": "formal"},
        ...     output_model=GenericReport,
        ... )
        >>> print(result.summary)
    """
    return get_executor().execute(
        prompt_name=prompt_name,
        variables=variables,
        output_model=output_model,
        temperature=temperature,
        provider=provider,
    )


# Default executor instance for LLM caching
# Use get_executor() to access, or set_executor() for dependency injection
_executor: "PromptExecutor | None" = None
_executor_lock = threading.Lock()


def get_executor() -> "PromptExecutor":
    """Get the executor instance (thread-safe).

    Returns the default singleton or a custom instance set via set_executor().

    Returns:
        PromptExecutor instance with LLM caching
    """
    global _executor
    if _executor is None:
        with _executor_lock:
            # Double-check after acquiring lock
            if _executor is None:
                _executor = PromptExecutor()
    return _executor


def set_executor(executor: "PromptExecutor | None") -> None:
    """Set a custom executor instance for dependency injection (thread-safe).

    Useful for testing or when you need different executor configurations.

    Args:
        executor: Custom PromptExecutor instance, or None to reset to default
    """
    global _executor
    with _executor_lock:
        _executor = executor


class PromptExecutor:
    """Reusable executor with LLM caching and retry logic."""

    def __init__(self, max_retries: int = MAX_RETRIES):
        self._max_retries = max_retries

    def _get_llm(
        self,
        temperature: float = DEFAULT_TEMPERATURE,
        provider: str | None = None,
    ) -> BaseChatModel:
        """Get or create cached LLM instance.

        Uses llm_factory which handles caching internally.
        """
        return create_llm(temperature=temperature, provider=provider)

    def _invoke_with_retry(
        self, llm, messages, output_model: Type[T] | None = None
    ) -> T | str:
        """Invoke LLM with exponential backoff retry.

        Args:
            llm: The LLM instance to use
            messages: Messages to send
            output_model: Optional Pydantic model for structured output

        Returns:
            LLM response (parsed model or string)

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self._max_retries):
            try:
                if output_model:
                    structured_llm = llm.with_structured_output(output_model)
                    return structured_llm.invoke(messages)
                else:
                    response = llm.invoke(messages)
                    return response.content

            except Exception as e:
                last_exception = e

                if not is_retryable(e) or attempt == self._max_retries - 1:
                    raise

                # Exponential backoff with jitter
                delay = min(RETRY_BASE_DELAY * (2**attempt), RETRY_MAX_DELAY)
                logger.warning(
                    f"LLM call failed (attempt {attempt + 1}/{self._max_retries}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)

        raise last_exception

    def execute(
        self,
        prompt_name: str,
        variables: dict | None = None,
        output_model: Type[T] | None = None,
        temperature: float = DEFAULT_TEMPERATURE,
        provider: str | None = None,
    ) -> T | str:
        """Execute a prompt using cached LLM with retry logic.

        Same interface as execute_prompt() but with LLM caching and
        automatic retry for transient failures.

        Provider priority: parameter > YAML metadata > env var > default

        Raises:
            ValueError: If required template variables are missing
        """
        variables = variables or {}

        prompt_config = load_prompt(prompt_name)

        # Validate all required variables are provided (fail fast)
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

        llm = self._get_llm(temperature=temperature, provider=provider)

        return self._invoke_with_retry(llm, messages, output_model)
