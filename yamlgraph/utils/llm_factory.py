"""LLM Factory - Multi-provider abstraction for language models.

This module provides a simple factory pattern for creating LLM instances
across different providers (Anthropic, Mistral, OpenAI).
"""

import logging
import os
import threading
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel

from yamlgraph.config import DEFAULT_MODELS

logger = logging.getLogger(__name__)

# Type alias for supported providers
ProviderType = Literal["anthropic", "mistral", "openai"]

# Thread-safe cache for LLM instances
_llm_cache: dict[tuple, BaseChatModel] = {}
_cache_lock = threading.Lock()


def create_llm(
    provider: ProviderType | None = None,
    model: str | None = None,
    temperature: float = 0.7,
) -> BaseChatModel:
    """Create an LLM instance with multi-provider support.

    Supports Anthropic (default), Mistral, and OpenAI providers.
    Provider can be specified via parameter or PROVIDER environment variable.
    Model can be specified via parameter or {PROVIDER}_MODEL environment variable.

    LLM instances are cached by (provider, model, temperature) to improve performance.

    Args:
        provider: LLM provider ("anthropic", "mistral", "openai").
                 Defaults to PROVIDER env var or "anthropic".
        model: Model name. Defaults to {PROVIDER}_MODEL env var or provider default.
        temperature: Temperature for generation (0.0-1.0).

    Returns:
        Configured LLM instance.

    Raises:
        ValueError: If provider is invalid.

    Examples:
        >>> # Use default Anthropic
        >>> llm = create_llm(temperature=0.7)

        >>> # Override provider
        >>> llm = create_llm(provider="mistral", temperature=0.8)

        >>> # Custom model
        >>> llm = create_llm(provider="openai", model="gpt-4o-mini")
    """
    # Determine provider (parameter > env var > default)
    selected_provider = provider or os.getenv("PROVIDER") or "anthropic"

    # Validate provider
    if selected_provider not in DEFAULT_MODELS:
        raise ValueError(
            f"Invalid provider: {selected_provider}. "
            f"Must be one of: {', '.join(DEFAULT_MODELS.keys())}"
        )

    # Determine model (parameter > env var > default)
    # Note: DEFAULT_MODELS already handles env var via config.py
    selected_model = model or DEFAULT_MODELS[selected_provider]

    # Create cache key
    cache_key = (selected_provider, selected_model, temperature)

    # Thread-safe cache access
    with _cache_lock:
        # Return cached instance if available
        if cache_key in _llm_cache:
            logger.debug(
                f"Using cached LLM: {selected_provider}/{selected_model} (temp={temperature})"
            )
            return _llm_cache[cache_key]

        # Create new LLM instance
        logger.info(
            f"Creating LLM: {selected_provider}/{selected_model} (temp={temperature})"
        )

        if selected_provider == "mistral":
            from langchain_mistralai import ChatMistralAI

            llm = ChatMistralAI(model=selected_model, temperature=temperature)
        elif selected_provider == "openai":
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(model=selected_model, temperature=temperature)
        else:  # anthropic (default)
            from langchain_anthropic import ChatAnthropic

            llm = ChatAnthropic(model=selected_model, temperature=temperature)

        # Cache the instance
        _llm_cache[cache_key] = llm

        return llm


def clear_cache() -> None:
    """Clear the LLM instance cache.

    Useful for testing or when you want to force recreation of LLM instances.
    """
    with _cache_lock:
        _llm_cache.clear()
    logger.debug("LLM cache cleared")
