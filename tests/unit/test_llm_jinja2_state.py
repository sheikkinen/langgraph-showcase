"""Tests for Jinja2 state context in LLM nodes.

Bug: execute_prompt is called without state= parameter, so templates
like {{ state.foo }} render empty even though the feature is documented.
"""

from unittest.mock import patch

from yamlgraph.node_factory import create_node_function


class TestLLMNodeJinja2State:
    """Tests for Jinja2 state context in LLM nodes."""

    def test_llm_node_passes_state_to_execute_prompt(self) -> None:
        """LLM node should pass state to execute_prompt for Jinja2 templates."""
        captured_calls = []

        def capture_execute(*args, **kwargs):
            captured_calls.append(kwargs)
            return "test result"

        with (
            patch(
                "yamlgraph.node_factory.llm_nodes.execute_prompt",
                side_effect=capture_execute,
            ),
            patch(
                "yamlgraph.node_factory.llm_nodes.get_output_model_for_node"
            ) as mock_get_model,
        ):
            mock_get_model.return_value = None

            node_fn = create_node_function(
                "analyzer",
                {
                    "type": "llm",
                    "prompt": "analyze",
                },
                {},
            )

            state = {"topic": "machine learning", "context": "research paper"}
            node_fn(state)

            assert len(captured_calls) == 1
            call_kwargs = captured_calls[0]

            # Bug: state= parameter is not passed to execute_prompt
            assert "state" in call_kwargs, (
                f"execute_prompt should receive state= parameter for Jinja2 templates. "
                f"Got kwargs: {list(call_kwargs.keys())}"
            )
            assert (
                call_kwargs["state"] == state
            ), f"state should contain full graph state. Got: {call_kwargs.get('state')}"

    def test_jinja2_state_template_renders_correctly(self) -> None:
        """Jinja2 {{ state.field }} should render with actual state values."""
        from yamlgraph.executor_base import format_prompt

        # This is what should happen inside execute_prompt
        template = "Analyze {{ state.topic }} in the context of {{ state.context }}"
        state = {"topic": "AI safety", "context": "healthcare"}

        formatted = format_prompt(template, {}, state=state)

        assert (
            "AI safety" in formatted
        ), f"Jinja2 state.topic should render. Got: {formatted}"
        assert (
            "healthcare" in formatted
        ), f"Jinja2 state.context should render. Got: {formatted}"

    def test_llm_node_jinja2_template_not_passed_through(self) -> None:
        """Without state= param, Jinja2 state templates pass through unrendered."""
        # Simulate current behavior - state not passed
        from yamlgraph.executor_base import format_prompt

        template = "Analyze {{ state.topic }}"

        # Current bug: state is not passed
        formatted = format_prompt(
            template, {}
        )  # No state= param, so {{state.topic}} not available

        # Template should NOT render correctly without state
        assert (
            "{{ state.topic }}" in formatted or "AI" not in formatted
        ), "Without state= parameter, Jinja2 state templates should not render"
