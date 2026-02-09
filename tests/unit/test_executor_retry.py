"""Tests for PromptExecutor._invoke_with_retry (REQ-YG-014/031).

Covers the retry loop with exponential backoff, retryable vs non-retryable
exceptions, and structured output path.
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel, Field

from yamlgraph.executor import PromptExecutor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeRateLimitError(Exception):
    """Simulates a provider RateLimitError (retryable by name)."""

    pass


# Rename class so is_retryable detects it
_FakeRateLimitError.__name__ = "RateLimitError"
_FakeRateLimitError.__qualname__ = "RateLimitError"


class _FakeAPIConnectionError(Exception):
    pass


_FakeAPIConnectionError.__name__ = "APIConnectionError"
_FakeAPIConnectionError.__qualname__ = "APIConnectionError"


class _OutputModel(BaseModel):
    answer: str = Field(description="The answer")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestInvokeWithRetrySuccess:
    """Happy path for _invoke_with_retry."""

    def test_returns_string_on_first_attempt(self):
        """Successful first call returns content string."""
        executor = PromptExecutor(max_retries=3)
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="hello world")

        result = executor._invoke_with_retry(mock_llm, ["msg"])

        assert result == "hello world"
        assert mock_llm.invoke.call_count == 1

    def test_returns_structured_output_on_first_attempt(self):
        """Successful first call with output_model returns parsed model."""
        executor = PromptExecutor(max_retries=3)

        expected = _OutputModel(answer="42")
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = expected
        mock_llm.with_structured_output.return_value = mock_structured

        result = executor._invoke_with_retry(
            mock_llm, ["msg"], output_model=_OutputModel
        )

        assert result == expected
        mock_llm.with_structured_output.assert_called_once_with(_OutputModel)
        mock_structured.invoke.assert_called_once_with(["msg"])


class TestInvokeWithRetryRetries:
    """Retry behaviour for transient failures."""

    @patch("yamlgraph.executor.time.sleep")
    def test_retries_on_retryable_error_then_succeeds(self, mock_sleep):
        """Retryable error triggers retry; second attempt succeeds."""
        executor = PromptExecutor(max_retries=3)
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            _FakeRateLimitError("rate limited"),
            MagicMock(content="success after retry"),
        ]

        result = executor._invoke_with_retry(mock_llm, ["msg"])

        assert result == "success after retry"
        assert mock_llm.invoke.call_count == 2
        mock_sleep.assert_called_once()  # backoff delay applied

    @patch("yamlgraph.executor.time.sleep")
    def test_exponential_backoff_delays(self, mock_sleep):
        """Each retry doubles the delay (capped at RETRY_MAX_DELAY)."""
        executor = PromptExecutor(max_retries=4)
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            _FakeRateLimitError("1st"),
            _FakeRateLimitError("2nd"),
            _FakeRateLimitError("3rd"),
            MagicMock(content="ok"),
        ]

        result = executor._invoke_with_retry(mock_llm, ["msg"])

        assert result == "ok"
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert len(delays) == 3
        # Delays should be monotonically non-decreasing
        assert delays[0] <= delays[1] <= delays[2]

    @patch("yamlgraph.executor.time.sleep")
    def test_raises_after_all_retries_exhausted(self, mock_sleep):
        """All retries fail → raises the last exception."""
        executor = PromptExecutor(max_retries=3)
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = _FakeRateLimitError("always failing")

        with pytest.raises(Exception, match="always failing"):
            executor._invoke_with_retry(mock_llm, ["msg"])

        assert mock_llm.invoke.call_count == 3
        assert mock_sleep.call_count == 2  # no sleep after final attempt

    @patch("yamlgraph.executor.time.sleep")
    def test_structured_output_retries(self, mock_sleep):
        """Retries also work through the structured-output path."""
        executor = PromptExecutor(max_retries=3)

        expected = _OutputModel(answer="retried")
        mock_structured = MagicMock()
        mock_structured.invoke.side_effect = [
            _FakeRateLimitError("rate limited"),
            expected,
        ]
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured

        result = executor._invoke_with_retry(
            mock_llm, ["msg"], output_model=_OutputModel
        )

        assert result == expected
        assert mock_structured.invoke.call_count == 2


class TestInvokeWithRetryNonRetryable:
    """Non-retryable errors raise immediately."""

    def test_value_error_not_retried(self):
        """ValueError raises immediately without retry."""
        executor = PromptExecutor(max_retries=3)
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = ValueError("bad input")

        with pytest.raises(ValueError, match="bad input"):
            executor._invoke_with_retry(mock_llm, ["msg"])

        assert mock_llm.invoke.call_count == 1

    def test_type_error_not_retried(self):
        """TypeError raises immediately without retry."""
        executor = PromptExecutor(max_retries=3)
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = TypeError("wrong type")

        with pytest.raises(TypeError, match="wrong type"):
            executor._invoke_with_retry(mock_llm, ["msg"])

        assert mock_llm.invoke.call_count == 1

    def test_generic_exception_not_retried(self):
        """Unrecognised exception raises immediately."""
        executor = PromptExecutor(max_retries=3)
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = RuntimeError("unexpected")

        with pytest.raises(RuntimeError, match="unexpected"):
            executor._invoke_with_retry(mock_llm, ["msg"])

        assert mock_llm.invoke.call_count == 1


class TestInvokeWithRetryMaxRetriesConfig:
    """max_retries parameter respected."""

    @patch("yamlgraph.executor.time.sleep")
    def test_max_retries_one_means_no_retries(self, mock_sleep):
        """max_retries=1 means single attempt, no retries."""
        executor = PromptExecutor(max_retries=1)
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = _FakeRateLimitError("once")

        with pytest.raises(Exception, match="once"):
            executor._invoke_with_retry(mock_llm, ["msg"])

        assert mock_llm.invoke.call_count == 1
        mock_sleep.assert_not_called()

    @patch("yamlgraph.executor.time.sleep")
    def test_api_connection_error_is_retried(self, mock_sleep):
        """APIConnectionError is retryable by name."""
        executor = PromptExecutor(max_retries=2)
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            _FakeAPIConnectionError("conn refused"),
            MagicMock(content="ok"),
        ]

        result = executor._invoke_with_retry(mock_llm, ["msg"])

        assert result == "ok"
        assert mock_llm.invoke.call_count == 2


class TestGetExecutorSingleton:
    """Thread-safe singleton access."""

    def test_get_executor_returns_instance(self):
        """get_executor() returns a PromptExecutor."""
        import yamlgraph.executor as mod

        # Reset singleton
        mod._executor = None
        try:
            executor = mod.get_executor()
            assert isinstance(executor, PromptExecutor)
        finally:
            mod._executor = None

    def test_get_executor_returns_same_instance(self):
        """Repeated calls return the same object."""
        import yamlgraph.executor as mod

        mod._executor = None
        try:
            a = mod.get_executor()
            b = mod.get_executor()
            assert a is b
        finally:
            mod._executor = None
