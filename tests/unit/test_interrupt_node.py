"""Unit tests for interrupt node functionality.

TDD tests for 001: Interrupt Node feature.
Tests create_interrupt_node() and interrupt YAML handling.
"""

from unittest.mock import patch

from yamlgraph.constants import NodeType
from yamlgraph.node_factory import create_interrupt_node


class TestNodeTypeInterrupt:
    """Test NodeType.INTERRUPT constant exists."""

    def test_interrupt_constant_exists(self):
        """NodeType should have INTERRUPT constant."""
        assert hasattr(NodeType, "INTERRUPT")
        assert NodeType.INTERRUPT == "interrupt"

    def test_interrupt_not_requires_prompt(self):
        """Interrupt nodes don't require prompt (can use message)."""
        assert not NodeType.requires_prompt("interrupt")


class TestCreateInterruptNode:
    """Test create_interrupt_node() factory function."""

    def test_create_interrupt_node_with_static_message(self):
        """Interrupt node with static message should work."""
        config = {
            "message": "What is your name?",
            "resume_key": "user_name",
        }
        node_fn = create_interrupt_node("ask_name", config)
        assert callable(node_fn)

    def test_create_interrupt_node_with_prompt(self):
        """Interrupt node with prompt should work."""
        config = {
            "prompt": "dialogue/generate_question",
            "state_key": "pending_question",
            "resume_key": "user_response",
        }
        node_fn = create_interrupt_node("ask_dynamic", config)
        assert callable(node_fn)

    @patch("langgraph.types.interrupt")
    def test_interrupt_node_calls_native_interrupt(self, mock_interrupt):
        """Node should call LangGraph's native interrupt()."""
        mock_interrupt.return_value = "Alice"  # Simulates resume value

        config = {"message": "What is your name?"}
        node_fn = create_interrupt_node("ask_name", config)

        state = {}
        result = node_fn(state)

        mock_interrupt.assert_called_once_with("What is your name?")
        assert result["user_input"] == "Alice"

    @patch("langgraph.types.interrupt")
    def test_interrupt_node_stores_payload_in_state_key(self, mock_interrupt):
        """Payload should be stored in state_key for idempotency."""
        mock_interrupt.return_value = "blue"

        config = {
            "message": "What is your favorite color?",
            "state_key": "pending_question",
            "resume_key": "color_choice",
        }
        node_fn = create_interrupt_node("ask_color", config)

        state = {}
        result = node_fn(state)

        assert result["pending_question"] == "What is your favorite color?"
        assert result["color_choice"] == "blue"

    @patch("langgraph.types.interrupt")
    def test_interrupt_node_idempotency_skips_prompt_on_resume(self, mock_interrupt):
        """When state_key exists, should not re-execute prompt."""
        mock_interrupt.return_value = "resumed_value"

        config = {
            "prompt": "expensive/llm_call",
            "state_key": "pending_question",
            "resume_key": "user_response",
        }
        node_fn = create_interrupt_node("ask_dynamic", config)

        # Simulate resume: state already has the payload
        state = {"pending_question": "Previously generated question"}

        with patch("yamlgraph.node_factory.execute_prompt") as mock_prompt:
            result = node_fn(state)

            # execute_prompt should NOT be called (idempotency)
            mock_prompt.assert_not_called()

            # Should use existing payload
            mock_interrupt.assert_called_once_with("Previously generated question")
            assert result["user_response"] == "resumed_value"

    @patch("langgraph.types.interrupt")
    @patch("yamlgraph.node_factory.execute_prompt")
    def test_interrupt_node_with_prompt_calls_execute_prompt(
        self, mock_execute_prompt, mock_interrupt
    ):
        """First execution with prompt should call execute_prompt."""
        mock_execute_prompt.return_value = "Generated question from LLM"
        mock_interrupt.return_value = "user answer"

        config = {
            "prompt": "dialogue/generate_question",
            "state_key": "pending_question",
            "resume_key": "user_response",
        }
        node_fn = create_interrupt_node("ask_dynamic", config)

        state = {"context": "some context"}
        result = node_fn(state)

        mock_execute_prompt.assert_called_once()
        mock_interrupt.assert_called_once_with("Generated question from LLM")
        assert result["pending_question"] == "Generated question from LLM"
        assert result["user_response"] == "user answer"

    @patch("langgraph.types.interrupt")
    def test_interrupt_node_sets_current_step(self, mock_interrupt):
        """Result should include current_step for tracking."""
        mock_interrupt.return_value = "answer"

        config = {"message": "Question?"}
        node_fn = create_interrupt_node("my_node", config)

        result = node_fn({})

        assert result["current_step"] == "my_node"

    def test_interrupt_node_default_keys(self):
        """Default state_key and resume_key should be used if not specified."""
        config = {"message": "Question?"}
        node_fn = create_interrupt_node("ask", config)

        # Just verify it creates without error
        assert callable(node_fn)


class TestInterruptNodeEdgeCases:
    """Edge cases for interrupt node handling."""

    @patch("langgraph.types.interrupt")
    def test_interrupt_with_dict_payload(self, mock_interrupt):
        """Interrupt should support dict payloads for structured questions."""
        mock_interrupt.return_value = {"choice": "A", "reason": "because"}

        config = {
            "message": {"question": "Pick A or B", "options": ["A", "B"]},
            "resume_key": "user_choice",
        }
        node_fn = create_interrupt_node("multi_choice", config)

        result = node_fn({})

        mock_interrupt.assert_called_once_with(
            {"question": "Pick A or B", "options": ["A", "B"]}
        )
        assert result["user_choice"] == {"choice": "A", "reason": "because"}

    @patch("langgraph.types.interrupt")
    def test_interrupt_node_no_message_uses_node_name(self, mock_interrupt):
        """If no message or prompt, use node name as fallback payload."""
        mock_interrupt.return_value = "answer"

        config = {}  # No message, no prompt
        node_fn = create_interrupt_node("approval_gate", config)

        _result = node_fn({})

        # Should use {"node": "approval_gate"} as fallback
        mock_interrupt.assert_called_once_with({"node": "approval_gate"})
