"""Unit tests for async LLM factory module."""

from unittest.mock import MagicMock, patch

import pytest

from yamlgraph.utils.llm_factory_async import (
    create_llm_async,
    get_executor,
    invoke_async,
    shutdown_executor,
)


class TestGetExecutor:
    """Tests for get_executor function."""

    def teardown_method(self):
        """Clean up executor after each test."""
        shutdown_executor()

    @pytest.mark.req("REQ-YG-010", "REQ-YG-011")
    def test_creates_executor(self):
        """Should create a ThreadPoolExecutor."""
        executor = get_executor()
        assert executor is not None

    @pytest.mark.req("REQ-YG-010", "REQ-YG-011")
    def test_returns_same_executor(self):
        """Should return the same executor on subsequent calls."""
        executor1 = get_executor()
        executor2 = get_executor()
        assert executor1 is executor2


class TestShutdownExecutor:
    """Tests for shutdown_executor function."""

    @pytest.mark.req("REQ-YG-010", "REQ-YG-011")
    def test_shutdown_cleans_up(self):
        """Shutdown should clean up executor."""
        # Create an executor
        executor1 = get_executor()
        assert executor1 is not None

        # Shutdown
        shutdown_executor()

        # Next call should create a new executor
        executor2 = get_executor()
        assert executor2 is not executor1

    @pytest.mark.req("REQ-YG-010", "REQ-YG-011")
    def test_shutdown_when_none(self):
        """Shutdown when no executor should not raise."""
        shutdown_executor()  # Ensure clean state
        shutdown_executor()  # Should not raise


class TestCreateLLMAsync:
    """Tests for create_llm_async function."""

    def teardown_method(self):
        """Clean up executor after each test."""
        shutdown_executor()

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-010", "REQ-YG-011")
    async def test_creates_llm(self):
        """Should create an LLM instance."""
        llm = await create_llm_async(provider="anthropic", temperature=0.5)
        assert llm is not None
        assert llm.temperature == 0.5

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-010", "REQ-YG-011")
    async def test_uses_default_provider(self):
        """Should use default provider when not specified."""
        with patch.dict("os.environ", {"PROVIDER": ""}, clear=False):
            llm = await create_llm_async(temperature=0.7)
            # Default is anthropic
            assert "anthropic" in llm.__class__.__name__.lower()


class TestInvokeAsync:
    """Tests for invoke_async function."""

    def teardown_method(self):
        """Clean up executor after each test."""
        shutdown_executor()

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-010", "REQ-YG-011")
    async def test_invoke_returns_string(self):
        """Should return string content when no output model."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Hello, world!"
        mock_llm.invoke.return_value = mock_response

        messages = [MagicMock()]
        result = await invoke_async(mock_llm, messages)

        assert result == "Hello, world!"
        mock_llm.invoke.assert_called_once_with(messages)

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-010", "REQ-YG-011")
    async def test_invoke_with_output_model(self):
        """Should use structured output when model provided."""
        from pydantic import BaseModel

        class TestOutput(BaseModel):
            value: str

        mock_llm = MagicMock()
        mock_structured_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_structured_llm.invoke.return_value = TestOutput(value="test")

        messages = [MagicMock()]
        result = await invoke_async(mock_llm, messages, output_model=TestOutput)

        assert isinstance(result, TestOutput)
        assert result.value == "test"
        mock_llm.with_structured_output.assert_called_once_with(TestOutput)
