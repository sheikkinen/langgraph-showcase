"""Tests for yamlgraph.executor_base module.

Covers:
- Format prompt functionality
- Retry logic (is_retryable)
"""

import pytest

from yamlgraph.executor_base import (
    RETRYABLE_EXCEPTIONS,
    format_prompt,
    is_retryable,
)


class TestIsRetryable:
    """Tests for is_retryable function."""

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_rate_limit_error_is_retryable(self) -> None:
        """Test RateLimitError is retryable."""

        class RateLimitError(Exception):
            pass

        assert is_retryable(RateLimitError("Rate limited"))

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_api_connection_error_is_retryable(self) -> None:
        """Test APIConnectionError is retryable."""

        class APIConnectionError(Exception):
            pass

        assert is_retryable(APIConnectionError("Connection failed"))

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_api_timeout_error_is_retryable(self) -> None:
        """Test APITimeoutError is retryable."""

        class APITimeoutError(Exception):
            pass

        assert is_retryable(APITimeoutError("Timeout"))

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_internal_server_error_is_retryable(self) -> None:
        """Test InternalServerError is retryable."""

        class InternalServerError(Exception):
            pass

        assert is_retryable(InternalServerError("500"))

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_service_unavailable_error_is_retryable(self) -> None:
        """Test ServiceUnavailableError is retryable."""

        class ServiceUnavailableError(Exception):
            pass

        assert is_retryable(ServiceUnavailableError("503"))

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_value_error_not_retryable(self) -> None:
        """Test ValueError is not retryable."""
        assert is_retryable(ValueError("Bad value")) is False

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_type_error_not_retryable(self) -> None:
        """Test TypeError is not retryable."""
        assert is_retryable(TypeError("Bad type")) is False

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_generic_exception_not_retryable(self) -> None:
        """Test generic Exception is not retryable."""
        assert is_retryable(Exception("Generic error")) is False

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_rate_in_name_is_retryable(self) -> None:
        """Test exception with 'rate' in name is retryable."""

        class CustomRateLimitException(Exception):
            pass

        assert is_retryable(CustomRateLimitException("hit rate limit"))

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_retryable_exceptions_constant(self) -> None:
        """Test RETRYABLE_EXCEPTIONS contains expected errors."""
        expected = {
            "RateLimitError",
            "APIConnectionError",
            "APITimeoutError",
            "InternalServerError",
            "ServiceUnavailableError",
        }
        assert set(RETRYABLE_EXCEPTIONS) == expected


class TestFormatPrompt:
    """Tests for format_prompt function."""

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_simple_variable_substitution(self) -> None:
        """Test basic {variable} substitution."""
        result = format_prompt("Hello {name}", {"name": "World"}, state=None)
        assert result == "Hello World"

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_multiple_variables(self) -> None:
        """Test multiple variable substitution."""
        result = format_prompt(
            "{greeting} {name}!", {"greeting": "Hi", "name": "Alice"}, state=None
        )
        assert result == "Hi Alice!"

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_jinja2_variable(self) -> None:
        """Test Jinja2 {{ variable }} syntax."""
        result = format_prompt("Hello {{ name }}", {"name": "Jinja"}, state=None)
        assert result == "Hello Jinja"

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_jinja2_loop(self) -> None:
        """Test Jinja2 for loop."""
        template = "{% for item in items %}{{ item }} {% endfor %}"
        result = format_prompt(template, {"items": ["a", "b", "c"]}, state=None)
        assert result == "a b c "

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_jinja2_conditional(self) -> None:
        """Test Jinja2 if conditional."""
        template = "{% if show %}visible{% endif %}"
        result = format_prompt(template, {"show": True}, state=None)
        assert result == "visible"

        result = format_prompt(template, {"show": False}, state=None)
        assert result == ""

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_state_access_in_jinja2(self) -> None:
        """Test state access via {{ state.field }}."""
        template = "Topic: {{ state.topic }}"
        result = format_prompt(template, {}, state={"topic": "AI"})
        assert result == "Topic: AI"

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_list_auto_join(self) -> None:
        """Test lists are auto-joined for simple format."""
        result = format_prompt("Tags: {tags}", {"tags": ["a", "b", "c"]}, state=None)
        assert result == "Tags: a, b, c"

    @pytest.mark.req("REQ-YG-013", "REQ-YG-031")
    def test_nested_state_access(self) -> None:
        """Test nested state access in Jinja2."""
        template = "{{ state.user.name }}"
        result = format_prompt(template, {}, state={"user": {"name": "Bob"}})
        assert result == "Bob"
