"""Tests for guardrail tool nodes - TDD: Red phase."""

import json


class TestEchoInput:
    """Test echo_input tool node."""

    def test_echo_returns_raw_input(self):
        """Should echo the raw input string."""
        from examples.openai_proxy.nodes.tools import echo_input

        state = {"input": '{"role": "user", "content": "Hello"}'}
        result = echo_input(state)

        assert result["echo"] == state["input"]

    def test_echo_empty_input(self):
        """Should handle empty input gracefully."""
        from examples.openai_proxy.nodes.tools import echo_input

        result = echo_input({"input": ""})
        assert result["echo"] == ""

    def test_echo_missing_input(self):
        """Should handle missing input key."""
        from examples.openai_proxy.nodes.tools import echo_input

        result = echo_input({})
        assert result["echo"] == ""


class TestValidateInput:
    """Test validate_input tool node."""

    def test_stamps_validation_missing(self):
        """Should stamp *validation missing* on each message."""
        from examples.openai_proxy.nodes.tools import validate_input

        messages = [{"role": "user", "content": "Hello world"}]
        state = {"input": json.dumps(messages)}
        result = validate_input(state)

        assert "*validation missing*" in result["validation"]
        assert "Hello world" in result["validation"]

    def test_multiple_messages(self):
        """Should process all messages and join with separator."""
        from examples.openai_proxy.nodes.tools import validate_input

        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Tell me a joke"},
        ]
        state = {"input": json.dumps(messages)}
        result = validate_input(state)

        assert "You are helpful" in result["validation"]
        assert "Tell me a joke" in result["validation"]
        assert result["validation"].count("*validation missing*") == 2
        assert "---" in result["validation"]

    def test_plain_text_fallback(self):
        """Should handle non-JSON input as plain text."""
        from examples.openai_proxy.nodes.tools import validate_input

        state = {"input": "just a plain string"}
        result = validate_input(state)

        assert "just a plain string" in result["validation"]
        assert "*validation missing*" in result["validation"]

    def test_empty_input(self):
        """Should handle empty input."""
        from examples.openai_proxy.nodes.tools import validate_input

        result = validate_input({"input": ""})
        assert "*validation missing*" in result["validation"]

    def test_returns_dict_with_validation_key(self):
        """Should return dict with 'validation' key."""
        from examples.openai_proxy.nodes.tools import validate_input

        result = validate_input({"input": "test"})
        assert "validation" in result
        assert isinstance(result["validation"], str)
