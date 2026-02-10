"""YAML Prompt Executor - Unified interface for LLM calls.

This module provides a simple, reusable executor for YAML-defined prompts
with support for structured outputs via Pydantic models.
"""

import logging
import threading
import time
from pathlib import Path
from typing import TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

from yamlgraph.config import (
    DEFAULT_TEMPERATURE,
    MAX_RETRIES,
    RETRY_BASE_DELAY,
    RETRY_MAX_DELAY,
)
from yamlgraph.executor_base import format_prompt, is_retryable, prepare_messages
from yamlgraph.utils.llm_factory import create_llm

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

__all__ = ["execute_prompt", "format_prompt", "get_executor", "PromptExecutor"]


def execute_prompt(
    prompt_name: str,
    variables: dict | None = None,
    output_model: type[T] | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    provider: str | None = None,
    model: str | None = None,
    graph_path: "Path | None" = None,
    prompts_dir: "Path | None" = None,
    prompts_relative: bool = False,
    state: dict | None = None,
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
        model: LLM model override (e.g. "claude-haiku-4-5", "mistral-small-latest").
               Priority: parameter > prompt YAML metadata > provider default.
        graph_path: Path to graph file for relative prompt resolution
        prompts_dir: Explicit prompts directory override
        prompts_relative: If True, resolve prompts relative to graph_path
        state: Optional state dict for Jinja2 templates (accessible as {{ state.field }})

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
        model=model,
        graph_path=graph_path,
        prompts_dir=prompts_dir,
        prompts_relative=prompts_relative,
        state=state,
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


class PromptExecutor:
    """Reusable executor with LLM caching and retry logic."""

    def __init__(self, max_retries: int = MAX_RETRIES):
        self._max_retries = max_retries

    def _get_llm(
        self,
        temperature: float = DEFAULT_TEMPERATURE,
        provider: str | None = None,
        model: str | None = None,
    ) -> BaseChatModel:
        """Get or create cached LLM instance.

        Uses llm_factory which handles caching internally.
        """
        return create_llm(temperature=temperature, provider=provider, model=model)

    def _invoke_with_retry(
        self, llm, messages, output_model: type[T] | None = None
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
        output_model: type[T] | None = None,
        temperature: float = DEFAULT_TEMPERATURE,
        provider: str | None = None,
        model: str | None = None,
        graph_path: "Path | None" = None,
        prompts_dir: "Path | None" = None,
        prompts_relative: bool = False,
        state: dict | None = None,
    ) -> T | str:
        """Execute a prompt using cached LLM with retry logic.

        Same interface as execute_prompt() but with LLM caching and
        automatic retry for transient failures.

        Model/provider priority: parameter > prompt YAML metadata > env var > default

        Args:
            prompt_name: Name of the prompt file (without .yaml)
            variables: Variables to substitute in the template
            output_model: Optional Pydantic model for structured output
            temperature: LLM temperature setting
            provider: LLM provider ("anthropic", "mistral", "openai")
            model: LLM model override (None to use prompt YAML/provider default)
            graph_path: Path to graph file for relative prompt resolution
            prompts_dir: Explicit prompts directory override
            prompts_relative: If True, resolve prompts relative to graph_path
            state: Optional state dict for Jinja2 templates (accessible as {{ state.field }})

        Raises:
            ValueError: If required template variables are missing
        """
        messages, resolved_provider, resolved_model = prepare_messages(
            prompt_name=prompt_name,
            variables=variables,
            provider=provider,
            model=model,
            graph_path=graph_path,
            prompts_dir=prompts_dir,
            prompts_relative=prompts_relative,
            state=state,
        )

        llm = self._get_llm(
            temperature=temperature, provider=resolved_provider, model=resolved_model
        )

        return self._invoke_with_retry(llm, messages, output_model)
