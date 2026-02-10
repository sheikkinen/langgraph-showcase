"""Tests for Jinja2 state context in interrupt nodes.

Bug: In control_nodes.py, execute_prompt is called with state as the
variables parameter but not as the Jinja2 state context, so {{ state.* }}
templates fail to render.
"""

from unittest.mock import patch

import pytest

from yamlgraph.node_factory.control_nodes import create_interrupt_node


class TestInterruptNodeJinja2State:
    """Tests for Jinja2 state context in interrupt nodes."""

    @pytest.mark.req("REQ-YG-013", "REQ-YG-021")
    def test_interrupt_node_passes_state_to_execute_prompt(self) -> None:
        """Interrupt node should pass state as Jinja2 context, not just variables."""
        captured_calls = []

        def capture_execute(*args, **kwargs):
            captured_calls.append({"args": args, "kwargs": kwargs})
            return "prompt result"

        with (
            patch("yamlgraph.executor.execute_prompt", side_effect=capture_execute),
            patch("langgraph.types.interrupt", return_value=None),
        ):
            node_fn = create_interrupt_node(
                node_name="ask_user",
                config={
                    "type": "interrupt",
                    "prompt": "clarify",
                },
            )

            state = {"question": "What color?", "context": "design review"}
            node_fn(state)  # Result unused, we check captured calls

            assert len(captured_calls) == 1
            call = captured_calls[0]

            # Check if state is passed as Jinja2 context (state= kwarg)
            has_state_kwarg = "state" in call["kwargs"]

            # Bug: state is passed as 2nd positional arg (variables), not state= kwarg
            assert has_state_kwarg, (
                f"execute_prompt should receive state= kwarg for Jinja2 templates. "
                f"Got args={call['args']}, kwargs={list(call['kwargs'].keys())}"
            )

    @pytest.mark.req("REQ-YG-013", "REQ-YG-021")
    def test_interrupt_node_jinja2_state_vs_variables(self) -> None:
        """Interrupt should support both simple vars and Jinja2 state templates."""
        captured_calls = []

        def capture_execute(*args, **kwargs):
            captured_calls.append({"args": args, "kwargs": kwargs})
            return "result"

        with (
            patch("yamlgraph.executor.execute_prompt", side_effect=capture_execute),
            patch("langgraph.types.interrupt", return_value=None),
        ):
            node_fn = create_interrupt_node(
                node_name="clarify",
                config={
                    "type": "interrupt",
                    "prompt": "ask",
                },
            )

            state = {"user_input": "test", "session_id": "abc123"}
            node_fn(state)

            call = captured_calls[0]

            # Variables should be passed for simple {var} templates
            # State should be passed for {{ state.var }} templates
            variables_arg = (
                call["args"][1]
                if len(call["args"]) > 1
                else call["kwargs"].get("variables")
            )
            state_kwarg = call["kwargs"].get("state")

            # Bug: state is used as variables but not as state= context
            assert state_kwarg is not None, (
                "Both variables and state should be available. "
                f"variables={variables_arg}, state={state_kwarg}"
            )
