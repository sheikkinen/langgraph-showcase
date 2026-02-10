"""LLM Factory - Multi-provider abstraction for language models.

This module provides a simple factory pattern for creating LLM instances
across different providers (Anthropic, Mistral, OpenAI, Replicate).
"""

import logging
import os
import threading
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel

from yamlgraph.config import DEFAULT_MODELS

logger = logging.getLogger(__name__)

# Type alias for supported providers
ProviderType = Literal[
    "anthropic", "google", "lmstudio", "mistral", "openai", "replicate", "xai"
]

# Thread-safe cache for LLM instances
_llm_cache: dict[tuple, BaseChatModel] = {}
_cache_lock = threading.Lock()


def create_llm(
    provider: ProviderType | None = None,
    model: str | None = None,
    temperature: float = 0.7,
) -> BaseChatModel:
    """Create an LLM instance with multi-provider support.

    Supports Anthropic (default), Google, Mistral, OpenAI, Replicate, and xAI providers.
    Provider can be specified via parameter or PROVIDER environment variable.
    Model can be specified via parameter or {PROVIDER}_MODEL environment variable.

    LLM instances are cached by (provider, model, temperature) to improve performance.

    Args:
        provider: LLM provider ("anthropic", "mistral", "openai", "replicate", "xai").
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

        >>> # Use xAI Grok
        >>> llm = create_llm(provider="xai", model="grok-beta")
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

        if selected_provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=selected_model,
                temperature=temperature,
                google_api_key=os.getenv("GOOGLE_API_KEY"),
            )
        elif selected_provider == "mistral":
            from langchain_mistralai import ChatMistralAI

            llm = ChatMistralAI(model=selected_model, temperature=temperature)
        elif selected_provider == "openai":
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(model=selected_model, temperature=temperature)
        elif selected_provider == "replicate":
            llm = _create_replicate_llm(selected_model, temperature)
        elif selected_provider == "xai":
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=selected_model,
                temperature=temperature,
                base_url="https://api.x.ai/v1",
                api_key=os.getenv("XAI_API_KEY"),
            )
        elif selected_provider == "lmstudio":
            from langchain_openai import ChatOpenAI

            base_url = os.getenv("LMSTUDIO_BASE_URL") or "http://localhost:1234/v1"
            llm = ChatOpenAI(
                model=selected_model,
                temperature=temperature,
                base_url=base_url,
                api_key="not-needed",  # Local server, no API key required
            )
        else:  # anthropic (default)
            from langchain_anthropic import ChatAnthropic

            llm = ChatAnthropic(model=selected_model, temperature=temperature)

        # Cache the instance
        _llm_cache[cache_key] = llm

        return llm


def _create_replicate_llm(model: str, temperature: float) -> BaseChatModel:
    """Create a Replicate-hosted model via LangChain wrapper.

    Uses langchain-litellm for unified interface. Requires REPLICATE_API_TOKEN
    environment variable (loaded from .env via config.py).

    Note: Replicate doesn't support structured output (response_format).
    Use parse_json: true in node config instead of output_schema in prompts.

    Args:
        model: Model name (e.g., "ibm-granite/granite-4.0-h-small")
        temperature: Temperature for generation

    Returns:
        LangChain-compatible chat model

    Raises:
        ValueError: If REPLICATE_API_TOKEN is not set
    """
    import warnings

    import litellm
    from langchain_litellm import ChatLiteLLM

    # Suppress Pydantic serialization warnings from langchain-litellm
    # (type mismatch between LiteLLM and LangChain response types - harmless)
    warnings.filterwarnings("ignore", message="Pydantic serializer warnings")

    # Validate API token is set
    if not os.getenv("REPLICATE_API_TOKEN"):
        raise ValueError(
            "REPLICATE_API_TOKEN environment variable is required. "
            "Get your token at https://replicate.com/account/api-tokens"
        )

    # Drop unsupported params (like response_format) for Replicate
    litellm.drop_params = True

    # LiteLLM format: replicate/owner/model
    litellm_model = f"replicate/{model}"

    return ChatLiteLLM(
        model=litellm_model,
        temperature=temperature,
    )


def clear_cache() -> None:
    """Clear the LLM instance cache.

    Useful for testing or when you want to force recreation of LLM instances.
    """
    with _cache_lock:
        _llm_cache.clear()
    logger.debug("LLM cache cleared")
