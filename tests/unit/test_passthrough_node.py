"""Unit tests for passthrough node functionality."""

import pytest

from yamlgraph.node_factory import create_passthrough_node


class TestPassthroughNode:
    """Tests for create_passthrough_node."""

    @pytest.mark.req("REQ-YG-021")
    def test_increment_counter(self):
        """Test basic counter increment."""
        config = {
            "output": {
                "counter": "{state.counter + 1}",
            }
        }
        node_fn = create_passthrough_node("next_turn", config)

        state = {"counter": 5}
        result = node_fn(state)

        assert result["counter"] == 6
        assert result["current_step"] == "next_turn"

    @pytest.mark.req("REQ-YG-021")
    def test_append_to_list(self):
        """Test appending item to list."""
        config = {
            "output": {
                "history": "{state.history + [state.current]}",
            }
        }
        node_fn = create_passthrough_node("save_history", config)

        state = {"history": ["a", "b"], "current": "c"}
        result = node_fn(state)

        assert result["history"] == ["a", "b", "c"]

    @pytest.mark.req("REQ-YG-021")
    def test_append_dict_to_list(self):
        """Test appending dict to list using simple syntax."""
        # Note: Complex dict literals not yet supported
        # Use Python node for complex transformations
        config = {
            "output": {
                "log": "{state.log + [state.entry]}",
            }
        }
        node_fn = create_passthrough_node("log_action", config)

        state = {"log": [], "entry": {"turn": 1, "action": "attack"}}
        result = node_fn(state)

        assert result["log"] == [{"turn": 1, "action": "attack"}]

    @pytest.mark.req("REQ-YG-021")
    def test_multiple_outputs(self):
        """Test multiple output fields."""
        config = {
            "output": {
                "counter": "{state.counter + 1}",
                "doubled": "{state.value * 2}",
                "message": "{state.prefix + ': done'}",
            }
        }
        node_fn = create_passthrough_node("transform", config)

        state = {"counter": 0, "value": 5, "prefix": "Status"}
        result = node_fn(state)

        assert result["counter"] == 1
        assert result["doubled"] == 10
        assert result["message"] == "Status: done"

    @pytest.mark.req("REQ-YG-021")
    def test_empty_output(self):
        """Test passthrough with no output (just sets current_step)."""
        config = {"output": {}}
        node_fn = create_passthrough_node("noop", config)

        state = {"x": 1}
        result = node_fn(state)

        assert result["current_step"] == "noop"
        assert "x" not in result  # Doesn't copy state

    @pytest.mark.req("REQ-YG-021")
    def test_no_output_key(self):
        """Test passthrough with missing output key."""
        config = {}  # No output defined
        node_fn = create_passthrough_node("minimal", config)

        state = {"x": 1}
        result = node_fn(state)

        assert result["current_step"] == "minimal"

    @pytest.mark.req("REQ-YG-021")
    def test_error_keeps_original_value(self):
        """Test that errors preserve original state values."""
        config = {
            "output": {
                "result": "{state.undefined_field + 1}",  # Will fail
            }
        }
        node_fn = create_passthrough_node("error_test", config)

        state = {"result": 42}  # Has existing value, but undefined_field missing
        result = node_fn(state)

        # Should keep original value on error (undefined_field resolves to None)
        # When left operand is None, we keep original
        assert result["result"] == 42

    @pytest.mark.req("REQ-YG-021")
    def test_function_name(self):
        """Test that function has descriptive name."""
        config = {"output": {}}
        node_fn = create_passthrough_node("my_node", config)

        assert node_fn.__name__ == "my_node_passthrough"

    @pytest.mark.req("REQ-YG-021")
    def test_string_concatenation(self):
        """Test string concatenation with + operator."""
        config = {
            "output": {
                "message": "{state.prefix + state.suffix}",
            }
        }
        node_fn = create_passthrough_node("concat", config)

        result = node_fn({"prefix": "Hello, ", "suffix": "World!"})
        assert result["message"] == "Hello, World!"
