"""Tests for LM Studio provider integration."""

import os
from unittest.mock import MagicMock, patch

import pytest

from yamlgraph.utils.llm_factory import clear_cache, create_llm


class TestLMStudioProvider:
    """Tests for lmstudio provider in llm_factory."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    @pytest.mark.req("REQ-YG-010")
    def test_lmstudio_provider_is_valid(self):
        """lmstudio should be a valid provider option."""
        from yamlgraph.config import DEFAULT_MODELS

        assert "lmstudio" in DEFAULT_MODELS

    @pytest.mark.req("REQ-YG-010")
    def test_create_llm_with_lmstudio_provider(self):
        """create_llm should accept lmstudio provider."""
        with patch("langchain_openai.ChatOpenAI") as mock_chat:
            mock_chat.return_value = MagicMock()

            llm = create_llm(provider="lmstudio")

            assert llm is not None
            mock_chat.assert_called_once()

    @pytest.mark.req("REQ-YG-010")
    def test_lmstudio_uses_custom_base_url(self):
        """lmstudio should use LMSTUDIO_BASE_URL env var."""
        test_url = "http://localhost:1234/v1"

        with (
            patch.dict(os.environ, {"LMSTUDIO_BASE_URL": test_url}),
            patch("langchain_openai.ChatOpenAI") as mock_chat,
        ):
            mock_chat.return_value = MagicMock()
            clear_cache()  # Clear to force new creation with new env

            create_llm(provider="lmstudio")

            call_kwargs = mock_chat.call_args.kwargs
            assert call_kwargs["base_url"] == test_url

    @pytest.mark.req("REQ-YG-010")
    def test_lmstudio_default_base_url(self):
        """lmstudio should have sensible default base_url."""
        # Clear any existing LMSTUDIO_BASE_URL
        env = os.environ.copy()
        env.pop("LMSTUDIO_BASE_URL", None)

        with (
            patch.dict(os.environ, env, clear=True),
            patch("langchain_openai.ChatOpenAI") as mock_chat,
        ):
            mock_chat.return_value = MagicMock()
            clear_cache()

            create_llm(provider="lmstudio")

            call_kwargs = mock_chat.call_args.kwargs
            # Default should be localhost:1234
            assert "1234" in call_kwargs["base_url"]

    @pytest.mark.req("REQ-YG-010")
    def test_lmstudio_uses_model_from_config(self):
        """lmstudio should use configured model."""
        with patch("langchain_openai.ChatOpenAI") as mock_chat:
            mock_chat.return_value = MagicMock()
            clear_cache()

            create_llm(provider="lmstudio")

            call_kwargs = mock_chat.call_args.kwargs
            # Should have a model set
            assert "model" in call_kwargs
            assert call_kwargs["model"] is not None

    @pytest.mark.req("REQ-YG-010")
    def test_lmstudio_no_api_key_required(self):
        """lmstudio should work without API key (local server)."""
        with patch("langchain_openai.ChatOpenAI") as mock_chat:
            mock_chat.return_value = MagicMock()
            clear_cache()

            # Should not raise even without API key
            create_llm(provider="lmstudio")

            call_kwargs = mock_chat.call_args.kwargs
            # api_key should be "not-needed" or similar placeholder
            assert call_kwargs["api_key"] == "not-needed"

    @pytest.mark.req("REQ-YG-010")
    def test_lmstudio_respects_temperature(self):
        """lmstudio should pass temperature to ChatOpenAI."""
        with patch("langchain_openai.ChatOpenAI") as mock_chat:
            mock_chat.return_value = MagicMock()
            clear_cache()

            create_llm(provider="lmstudio", temperature=0.5)

            call_kwargs = mock_chat.call_args.kwargs
            assert call_kwargs["temperature"] == 0.5

    @pytest.mark.req("REQ-YG-010")
    def test_lmstudio_respects_model_override(self):
        """create_llm model parameter should override default."""
        custom_model = "custom-local-model"

        with patch("langchain_openai.ChatOpenAI") as mock_chat:
            mock_chat.return_value = MagicMock()
            clear_cache()

            create_llm(provider="lmstudio", model=custom_model)

            call_kwargs = mock_chat.call_args.kwargs
            assert call_kwargs["model"] == custom_model
