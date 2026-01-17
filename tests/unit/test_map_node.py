"""Tests for type: map node functionality."""

from unittest.mock import MagicMock

import pytest

from yamlgraph.map_compiler import compile_map_node, wrap_for_reducer


class TestWrapForReducer:
    """Tests for wrap_for_reducer helper."""

    def test_wraps_result_in_list(self):
        """Wrap node output for reducer aggregation."""

        def simple_node(state: dict) -> dict:
            return {"result": state["item"] * 2}

        wrapped = wrap_for_reducer(simple_node, "collected", "result")
        result = wrapped({"item": 5})

        assert result == {"collected": [10]}

    def test_preserves_map_index(self):
        """Preserve _map_index in wrapped output."""

        def node_fn(state: dict) -> dict:
            return {"data": state["value"]}

        wrapped = wrap_for_reducer(node_fn, "results", "data")
        result = wrapped({"value": "test", "_map_index": 2})

        assert result == {"results": [{"_map_index": 2, "value": "test"}]}

    def test_extracts_state_key(self):
        """Extract specific state_key from node result."""

        def node_fn(state: dict) -> dict:
            return {"frame_data": {"before": "a", "after": "b"}, "other": "ignore"}

        wrapped = wrap_for_reducer(node_fn, "frames", "frame_data")
        result = wrapped({})

        assert result == {"frames": [{"before": "a", "after": "b"}]}


class TestCompileMapNode:
    """Tests for compile_map_node function."""

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
