"""Tests for Jinja2 state support in prompts.

Bug: format_prompt advertises Jinja2 state support, but prepare_messages
never passes state, so {{ state.* }} renders empty without validation.

This is a silent prompt corruption risk.
"""

from unittest.mock import patch


class TestFormatPromptState:
    """Tests for format_prompt state parameter."""

    def test_format_prompt_with_state_works_directly(self) -> None:
        """format_prompt correctly handles state when passed directly."""
        from yamlgraph.executor_base import format_prompt

        template = "Topic: {{ state.topic }}"
        result = format_prompt(template, variables={}, state={"topic": "AI"})

        assert result == "Topic: AI", "format_prompt should render state correctly"

    def test_format_prompt_without_state_renders_empty(self) -> None:
        """format_prompt renders empty when state not provided."""
        from yamlgraph.executor_base import format_prompt

        template = "Topic: {{ state.topic }}"
        # Without state, {{ state.topic }} renders empty
        result = format_prompt(template, variables={})

        # This should render "Topic: " (empty state.topic)
        assert result == "Topic: ", "Without state, Jinja2 renders empty"


class TestPrepareMessagesState:
    """Tests for prepare_messages state handling."""

    def test_prepare_messages_passes_state_to_format_prompt(self) -> None:
        """prepare_messages should pass state to format_prompt for Jinja2."""
        from yamlgraph.executor_base import prepare_messages

        with patch("yamlgraph.executor_base.load_prompt") as mock_load:
            mock_load.return_value = {
                "system": "You analyze {{ state.topic }}",
                "user": "Analyze {{ state.topic }} for patterns",
            }

            # Call prepare_messages with state as a parameter
            messages, _, _ = prepare_messages(
                "test_prompt",
                variables={},
                state={"topic": "machine learning"},
            )

            # Extract message contents
            system_content = messages[0].content if messages else ""
            user_content = messages[1].content if len(messages) > 1 else ""

            # These assertions should now PASS
            assert (
                "machine learning" in system_content
            ), f"System message should contain state.topic, got: {system_content}"
            assert (
                "machine learning" in user_content
            ), f"User message should contain state.topic, got: {user_content}"

    def test_prepare_messages_should_accept_state_parameter(self) -> None:
        """prepare_messages should have explicit state parameter."""
        import inspect

        from yamlgraph.executor_base import prepare_messages

        sig = inspect.signature(prepare_messages)
        params = list(sig.parameters.keys())

        # BUG: prepare_messages does not have a state parameter
        assert "state" in params, (
            f"prepare_messages should accept state parameter. "
            f"Current params: {params}"
        )


class TestExecutorStateIntegration:
    """Integration tests for state in execute_prompt."""

    def test_execute_prompt_passes_state(self) -> None:
        """execute_prompt should pass state to prepare_messages."""
        import inspect

        from yamlgraph.executor import execute_prompt

        sig = inspect.signature(execute_prompt)
        params = list(sig.parameters.keys())

        # BUG: execute_prompt does not have a state parameter
        assert "state" in params, (
            f"execute_prompt should accept state parameter. "
            f"Current params: {params}"
        )

    def test_execute_prompt_async_passes_state(self) -> None:
        """execute_prompt_async should pass state to prepare_messages."""
        import inspect

        from yamlgraph.executor_async import execute_prompt_async

        sig = inspect.signature(execute_prompt_async)
        params = list(sig.parameters.keys())

        # BUG: execute_prompt_async does not have a state parameter
        assert "state" in params, (
            f"execute_prompt_async should accept state parameter. "
            f"Current params: {params}"
        )
