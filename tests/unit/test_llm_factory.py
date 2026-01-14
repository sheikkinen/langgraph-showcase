"""Unit tests for LLM factory module."""

import os
from unittest.mock import patch

import pytest
from langchain_anthropic import ChatAnthropic

from showcase.utils.llm_factory import create_llm, clear_cache


class TestCreateLLM:
    """Test the create_llm factory function."""

    def setup_method(self):
        """Clear cache and environment before each test."""
        clear_cache()

    def test_default_provider_is_anthropic(self):
        """Should use Anthropic by default."""
        # Clear PROVIDER from environment to ensure default behavior
        with patch.dict(os.environ, {"PROVIDER": ""}, clear=False):
            llm = create_llm(temperature=0.7)
            assert isinstance(llm, ChatAnthropic)
            assert llm.temperature == 0.7

    def test_explicit_anthropic_provider(self):
        """Should create Anthropic LLM when provider='anthropic'."""
        llm = create_llm(provider="anthropic", temperature=0.5)
        assert isinstance(llm, ChatAnthropic)
        assert llm.temperature == 0.5

    def test_mistral_provider(self):
        """Should create Mistral LLM when provider='mistral'."""
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            llm = create_llm(provider="mistral", temperature=0.8)
            # Check it's the right class (will import on first call)
            assert llm.__class__.__name__ == "ChatMistralAI"
            assert llm.temperature == 0.8

    def test_openai_provider(self):
        """Should create OpenAI LLM when provider='openai'."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            llm = create_llm(provider="openai", temperature=0.6)
            assert llm.__class__.__name__ == "ChatOpenAI"
            assert llm.temperature == 0.6

    def test_provider_from_environment(self):
        """Should use PROVIDER env var when no provider specified."""
        with patch.dict(
            os.environ, {"PROVIDER": "mistral", "MISTRAL_API_KEY": "test-key"}
        ):
            llm = create_llm(temperature=0.7)
            assert llm.__class__.__name__ == "ChatMistralAI"

    def test_custom_model(self):
        """Should use custom model when specified."""
        with patch.dict(os.environ, {"PROVIDER": ""}, clear=False):
            llm = create_llm(model="claude-opus-4", temperature=0.5)
            assert isinstance(llm, ChatAnthropic)
            assert llm.model == "claude-opus-4"

    def test_model_from_environment(self):
        """Should use provider-specific model env var."""
        with patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-sonnet-4"}):
            llm = create_llm(provider="anthropic", temperature=0.7)
            assert llm.model == "claude-sonnet-4"

    def test_default_models(self):
        """Should use correct default models for each provider."""
        # Anthropic default
        llm_anthropic = create_llm(provider="anthropic", temperature=0.7)
        assert llm_anthropic.model == "claude-haiku-4-5"

        # Mistral default
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            llm_mistral = create_llm(provider="mistral", temperature=0.7)
            assert llm_mistral.model == "mistral-large-latest"

        # OpenAI default (uses model_name attribute)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            llm_openai = create_llm(provider="openai", temperature=0.7)
            assert llm_openai.model_name == "gpt-4o"

    def test_invalid_provider(self):
        """Should raise error for invalid provider."""
        with pytest.raises((ValueError, KeyError)):
            create_llm(provider="invalid-provider", temperature=0.7)

    def test_caching(self):
        """Should cache LLM instances for same parameters."""
        llm1 = create_llm(provider="anthropic", temperature=0.7)
        llm2 = create_llm(provider="anthropic", temperature=0.7)
        assert llm1 is llm2

        # Different temperature = different instance
        llm3 = create_llm(provider="anthropic", temperature=0.5)
        assert llm1 is not llm3

    def test_cache_key_includes_all_params(self):
        """Cache should differentiate on provider, model, temperature."""
        llm1 = create_llm(
            provider="anthropic", model="claude-haiku-4-5", temperature=0.7
        )
        llm2 = create_llm(provider="anthropic", model="claude-opus-4", temperature=0.7)
        assert llm1 is not llm2

        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            llm3 = create_llm(provider="mistral", temperature=0.7)
            assert llm1 is not llm3
