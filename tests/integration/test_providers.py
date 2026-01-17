"""Integration tests for multi-provider LLM support."""

import os
from unittest.mock import patch

import pytest
from pydantic import BaseModel, Field

from yamlgraph.executor import execute_prompt, load_prompt
from yamlgraph.utils.llm_factory import clear_cache


class ProviderTestContent(BaseModel):
    """Test model for provider tests - replaces demo model dependency."""

    title: str = Field(description="Title of the generated content")
    content: str = Field(description="The main generated text")
    word_count: int = Field(description="Approximate word count")
    tags: list[str] = Field(default_factory=list, description="Relevant tags")


class TestProviderIntegration:
    """Test multi-provider functionality end-to-end."""

    def setup_method(self):
        """Clear LLM cache before each test."""
        clear_cache()

    def test_execute_prompt_with_anthropic_provider(self):
        """Should execute prompt with explicit Anthropic provider."""
        result = execute_prompt(
            prompt_name="greet",
            variables={"name": "Alice", "style": "formal"},
            provider="anthropic",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.skipif(
        not os.getenv("MISTRAL_API_KEY"), reason="MISTRAL_API_KEY not set"
    )
    def test_execute_prompt_with_mistral_provider(self):
        """Should execute prompt with Mistral provider."""
        result = execute_prompt(
            prompt_name="greet",
            variables={"name": "Bob", "style": "casual"},
            provider="mistral",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set"
    )
    def test_execute_prompt_with_openai_provider(self):
        """Should execute prompt with OpenAI provider."""
        result = execute_prompt(
            prompt_name="greet",
            variables={"name": "Charlie", "style": "friendly"},
            provider="openai",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_provider_from_environment_variable(self):
        """Should use provider from PROVIDER env var."""
        with patch.dict(os.environ, {"PROVIDER": "anthropic"}):
            result = execute_prompt(
                prompt_name="greet",
                variables={"name": "Dave", "style": "formal"},
            )
            assert isinstance(result, str)
            assert len(result) > 0

    def test_provider_in_yaml_metadata(self):
        """Should extract provider from YAML metadata."""
        # greet.yaml doesn't have provider metadata,
        # so this just verifies the load works
        _ = load_prompt("greet")

        # Even though greet.yaml doesn't have provider,
        # the executor should handle it gracefully
        result = execute_prompt(
            prompt_name="greet",
            variables={"name": "Eve", "style": "casual"},
        )
        assert isinstance(result, str)

    def test_structured_output_with_different_providers(self):
        """Should work with structured outputs across providers."""
        result = execute_prompt(
            prompt_name="generate",
            variables={
                "topic": "Python testing",
                "style": "technical",
                "word_count": 50,
            },
            output_model=ProviderTestContent,
            provider="anthropic",
        )
        assert isinstance(result, ProviderTestContent)
        assert result.content
        assert isinstance(result.tags, list)

    def test_temperature_and_provider_together(self):
        """Should handle both temperature and provider parameters."""
        result = execute_prompt(
            prompt_name="greet",
            variables={"name": "Frank", "style": "formal"},
            temperature=0.3,
            provider="anthropic",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_invalid_provider_raises_error(self):
        """Should raise error for invalid provider."""
        with pytest.raises(ValueError, match="Invalid provider"):
            execute_prompt(
                prompt_name="greet",
                variables={"name": "Greg", "style": "casual"},
                provider="invalid-provider",
            )

    def test_caching_across_calls_with_same_provider(self):
        """Should reuse LLM instances for same provider/temperature."""
        # First call
        result1 = execute_prompt(
            prompt_name="greet",
            variables={"name": "Harry", "style": "formal"},
            temperature=0.7,
            provider="anthropic",
        )

        # Second call with same params should use cached LLM
        result2 = execute_prompt(
            prompt_name="greet",
            variables={"name": "Ivy", "style": "casual"},
            temperature=0.7,
            provider="anthropic",
        )

        # Both should succeed (testing cache doesn't break functionality)
        assert isinstance(result1, str)
        assert isinstance(result2, str)


class TestJinja2WithProviders:
    """Test Jinja2 templates work with different providers."""

    def setup_method(self):
        """Clear LLM cache before each test."""
        clear_cache()

    def test_simple_prompt_template_format(self):
        """Should work with simple {variable} templates on any provider."""
        result = execute_prompt(
            prompt_name="greet",
            variables={"name": "TestUser", "style": "formal"},
            provider="anthropic",
        )
        assert isinstance(result, str)
        assert len(result) > 0
