"""Tests for type: map node functionality."""

from unittest.mock import MagicMock

import pytest

from yamlgraph.map_compiler import compile_map_node, wrap_for_reducer


class TestWrapForReducer:
    """Tests for wrap_for_reducer helper."""

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_wraps_result_in_list(self):
        """Wrap node output for reducer aggregation."""

        def simple_node(state: dict) -> dict:
            return {"result": state["item"] * 2}

        wrapped = wrap_for_reducer(simple_node, "collected", "result")
        result = wrapped({"item": 5})

        assert result == {"collected": [10]}

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_preserves_map_index(self):
        """Preserve _map_index in wrapped output."""

        def node_fn(state: dict) -> dict:
            return {"data": state["value"]}

        wrapped = wrap_for_reducer(node_fn, "results", "data")
        result = wrapped({"value": "test", "_map_index": 2})

        assert result == {"results": [{"_map_index": 2, "value": "test"}]}

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_extracts_state_key(self):
        """Extract specific state_key from node result."""

        def node_fn(state: dict) -> dict:
            return {"frame_data": {"before": "a", "after": "b"}, "other": "ignore"}

        wrapped = wrap_for_reducer(node_fn, "frames", "frame_data")
        result = wrapped({})

        assert result == {"frames": [{"before": "a", "after": "b"}]}


class TestCompileMapNode:
    """Tests for compile_map_node function."""

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_creates_map_edge_function(self):
        """compile_map_node returns a map edge function."""
        config = {
            "over": "{items}",
            "as": "item",
            "collect": "results",
            "node": {"type": "llm", "prompt": "test", "state_key": "result"},
        }
        builder = MagicMock()
        defaults = {}

        map_edge, sub_node_name = compile_map_node("expand", config, builder, defaults)

        # Should return callable and sub-node name
        assert callable(map_edge)
        assert sub_node_name == "_map_expand_sub"

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_map_edge_returns_send_list(self):
        """Map edge function returns list of Send objects."""
        from langgraph.types import Send

        config = {
            "over": "{items}",
            "as": "item",
            "collect": "results",
            "node": {"type": "llm", "prompt": "test", "state_key": "result"},
        }
        builder = MagicMock()
        defaults = {}

        map_edge, sub_node_name = compile_map_node("expand", config, builder, defaults)

        state = {"items": ["a", "b", "c"]}
        sends = map_edge(state)

        assert len(sends) == 3
        assert all(isinstance(s, Send) for s in sends)
        assert sends[0].node == sub_node_name
        assert sends[0].arg["item"] == "a"
        assert sends[0].arg["_map_index"] == 0
        assert sends[1].arg["item"] == "b"
        assert sends[1].arg["_map_index"] == 1

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_map_edge_empty_list(self):
        """Empty list returns empty Send list."""
        config = {
            "over": "{items}",
            "as": "item",
            "collect": "results",
            "node": {"type": "llm", "prompt": "test", "state_key": "result"},
        }
        builder = MagicMock()
        defaults = {}

        map_edge, _ = compile_map_node("expand", config, builder, defaults)

        state = {"items": []}
        sends = map_edge(state)

        assert sends == []

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_adds_wrapped_sub_node_to_builder(self):
        """compile_map_node adds wrapped sub-node to builder."""
        config = {
            "over": "{items}",
            "as": "item",
            "collect": "results",
            "node": {"type": "llm", "prompt": "test", "state_key": "result"},
        }
        builder = MagicMock()
        defaults = {}

        compile_map_node("expand", config, builder, defaults)

        # Should call builder.add_node
        builder.add_node.assert_called_once()
        call_args = builder.add_node.call_args
        assert call_args[0][0] == "_map_expand_sub"

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_validates_over_is_list(self):
        """Map edge validates that 'over' resolves to a list."""
        config = {
            "over": "{not_a_list}",
            "as": "item",
            "collect": "results",
            "node": {"type": "llm", "prompt": "test", "state_key": "result"},
        }
        builder = MagicMock()
        defaults = {}

        map_edge, _ = compile_map_node("expand", config, builder, defaults)

        state = {"not_a_list": "string"}
        with pytest.raises(TypeError, match="must resolve to list"):
            map_edge(state)


class TestWrapForReducerErrorHandling:
    """Tests for error handling in wrap_for_reducer."""

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_exception_captured_with_map_index(self):
        """Exceptions should be captured with _map_index."""

        def failing_node(state: dict) -> dict:
            raise ValueError("Processing failed")

        wrapped = wrap_for_reducer(failing_node, "results", "data")
        result = wrapped({"_map_index": 3})

        # Should contain error info
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["_map_index"] == 3
        assert "_error" in result["results"][0]
        assert "Processing failed" in result["results"][0]["_error"]
        assert result["results"][0]["_error_type"] == "ValueError"
        # Should also propagate to errors list
        assert "errors" in result

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_error_in_result_handled(self):
        """Nodes returning 'error' in result should be handled."""

        def node_with_error(state: dict) -> dict:
            return {"error": "Something went wrong"}

        wrapped = wrap_for_reducer(node_with_error, "results", "data")
        result = wrapped({"_map_index": 2})

        assert "results" in result
        assert result["results"][0]["_map_index"] == 2
        assert "_error" in result["results"][0]

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_errors_list_in_result_handled(self):
        """Nodes returning 'errors' list should be handled."""

        def node_with_errors(state: dict) -> dict:
            return {"errors": ["Error 1", "Error 2"]}

        wrapped = wrap_for_reducer(node_with_errors, "results", "data")
        result = wrapped({"_map_index": 1})

        assert "results" in result
        assert "errors" in result
        assert result["results"][0]["_map_index"] == 1

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_pydantic_model_converted(self):
        """Pydantic models should be converted to dicts."""
        from pydantic import BaseModel

        class ItemResult(BaseModel):
            name: str
            value: int

        def node_returning_pydantic(state: dict) -> dict:
            return {"data": ItemResult(name="test", value=42)}

        wrapped = wrap_for_reducer(node_returning_pydantic, "results", "data")
        result = wrapped({})

        assert result["results"][0]["name"] == "test"
        assert result["results"][0]["value"] == 42


class TestCompileMapNodeToolCall:
    """Tests for tool_call sub-nodes in map nodes."""

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_tool_call_subnode_requires_registry(self):
        """Tool call sub-node requires tools_registry."""
        config = {
            "over": "{items}",
            "as": "item",
            "collect": "results",
            "node": {"type": "tool_call", "tool": "my_tool", "state_key": "result"},
        }
        builder = MagicMock()
        defaults = {}

        with pytest.raises(ValueError, match="no tools_registry"):
            compile_map_node("expand", config, builder, defaults)


class TestCompileMapNodePython:
    """Tests for python sub-nodes in map nodes (FR-021)."""

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_python_subnode_requires_registry(self):
        """Python sub-node requires python_tools registry."""
        config = {
            "over": "{items}",
            "as": "item",
            "collect": "results",
            "node": {"type": "python", "tool": "process_item", "state_key": "result"},
        }
        builder = MagicMock()
        defaults = {}

        with pytest.raises(ValueError, match="no python_tools"):
            compile_map_node("expand", config, builder, defaults)

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_python_subnode_unknown_tool_error(self):
        """Unknown python tool in map sub-node raises error."""
        from yamlgraph.tools.python_tool import PythonToolConfig

        config = {
            "over": "{items}",
            "as": "item",
            "collect": "results",
            "node": {"type": "python", "tool": "unknown_tool", "state_key": "result"},
        }
        builder = MagicMock()
        defaults = {}
        tool_config = PythonToolConfig(module="test", function="other")
        python_tools = {"other_tool": tool_config}

        with pytest.raises(ValueError, match="Unknown python tool 'unknown_tool'"):
            compile_map_node(
                "expand", config, builder, defaults, python_tools=python_tools
            )

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_python_subnode_creates_wrapped_node(self):
        """Python sub-node is wrapped and added to builder."""
        from unittest.mock import patch

        from yamlgraph.tools.python_tool import PythonToolConfig

        def process_item(state: dict) -> dict:
            return {"result": state["item"] * 2}

        config = {
            "over": "{items}",
            "as": "item",
            "collect": "results",
            "node": {"type": "python", "tool": "process_item", "state_key": "result"},
        }
        builder = MagicMock()
        defaults = {}
        tool_config = PythonToolConfig(module="test", function="process_item")
        python_tools = {"process_item": tool_config}

        with patch(
            "yamlgraph.map_compiler.load_python_function", return_value=process_item
        ):
            map_edge, sub_node_name = compile_map_node(
                "process", config, builder, defaults, python_tools=python_tools
            )

        assert sub_node_name == "_map_process_sub"
        builder.add_node.assert_called_once()

    @pytest.mark.req("REQ-YG-040", "REQ-YG-041")
    def test_python_subnode_returns_correct_result(self):
        """Python sub-node result is collected correctly."""
        from unittest.mock import patch

        from yamlgraph.tools.python_tool import PythonToolConfig

        def process_item(state: dict) -> dict:
            return {"result": f"processed_{state['item']}"}

        config = {
            "over": "{items}",
            "as": "item",
            "collect": "results",
            "node": {"type": "python", "tool": "process_item", "state_key": "result"},
        }
        builder = MagicMock()
        defaults = {}
        tool_config = PythonToolConfig(module="test", function="process_item")
        python_tools = {"process_item": tool_config}

        with patch(
            "yamlgraph.map_compiler.load_python_function", return_value=process_item
        ):
            compile_map_node(
                "process", config, builder, defaults, python_tools=python_tools
            )

        # Get the wrapped node that was added
        wrapped_node = builder.add_node.call_args[0][1]

        # Call it with a test state
        result = wrapped_node({"item": "test", "_map_index": 0})

        assert "results" in result
        assert result["results"][0]["_map_index"] == 0
        # The result should be "processed_test"
        assert result["results"][0]["value"] == "processed_test"
