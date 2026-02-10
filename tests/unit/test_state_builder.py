"""Unit tests for dynamic state builder.

TDD: Red phase - these tests define the expected behavior.
"""

from operator import add
from typing import Annotated, get_args, get_origin

import pytest

from yamlgraph.models.state_builder import sorted_add


class TestSortedAdd:
    """Test the sorted_add reducer for map node fan-in."""

    @pytest.mark.req("REQ-YG-024")
    def test_concatenates_lists(self):
        """Should concatenate two lists."""
        result = sorted_add([1, 2], [3, 4])
        assert result == [1, 2, 3, 4]

    @pytest.mark.req("REQ-YG-024")
    def test_handles_empty_existing(self):
        """Should handle empty existing list."""
        result = sorted_add([], [1, 2])
        assert result == [1, 2]

    @pytest.mark.req("REQ-YG-024")
    def test_handles_none_existing(self):
        """Should handle None as existing list."""
        result = sorted_add(None, [1, 2])
        assert result == [1, 2]

    @pytest.mark.req("REQ-YG-024")
    def test_handles_empty_new(self):
        """Should handle empty new list."""
        result = sorted_add([1, 2], [])
        assert result == [1, 2]

    @pytest.mark.req("REQ-YG-024")
    def test_handles_none_new(self):
        """Should handle None as new list."""
        result = sorted_add([1, 2], None)
        assert result == [1, 2]

    @pytest.mark.req("REQ-YG-024")
    def test_sorts_by_map_index(self):
        """Should sort results by _map_index for map fan-in."""
        # Simulate out-of-order parallel results
        existing = [{"_map_index": 2, "value": "third"}]
        new = [{"_map_index": 0, "value": "first"}]
        result = sorted_add(existing, new)

        assert result[0]["_map_index"] == 0
        assert result[0]["value"] == "first"
        assert result[1]["_map_index"] == 2
        assert result[1]["value"] == "third"

    @pytest.mark.req("REQ-YG-024")
    def test_sorts_multiple_out_of_order(self):
        """Should sort many out-of-order items correctly."""
        # Simulate 5 items arriving in random order
        items = [
            {"_map_index": 3, "data": "d"},
            {"_map_index": 0, "data": "a"},
            {"_map_index": 4, "data": "e"},
            {"_map_index": 1, "data": "b"},
            {"_map_index": 2, "data": "c"},
        ]
        result = sorted_add([], items)

        assert [r["data"] for r in result] == ["a", "b", "c", "d", "e"]

    @pytest.mark.req("REQ-YG-024")
    def test_no_sort_for_non_dict_items(self):
        """Should not sort if items are not dicts."""
        result = sorted_add([3, 1], [2])
        assert result == [3, 1, 2]  # Preserved insertion order

    @pytest.mark.req("REQ-YG-024")
    def test_no_sort_for_dicts_without_map_index(self):
        """Should not sort if dicts lack _map_index."""
        result = sorted_add([{"a": 1}], [{"b": 2}])
        assert result == [{"a": 1}, {"b": 2}]


class TestBuildStateClass:
    """Test dynamic TypedDict generation from graph config."""

    @pytest.mark.req("REQ-YG-024")
    def test_includes_base_infrastructure_fields(self):
        """State always has infrastructure fields."""
        from yamlgraph.models.state_builder import build_state_class

        config = {"nodes": {}, "edges": []}
        State = build_state_class(config)

        annotations = State.__annotations__
        assert "thread_id" in annotations
        assert "current_step" in annotations
        assert "errors" in annotations
        assert "messages" in annotations

    @pytest.mark.req("REQ-YG-024")
    def test_errors_has_reducer(self):
        """errors field uses Annotated[list, add] reducer."""
        from yamlgraph.models.state_builder import build_state_class

        config = {"nodes": {}, "edges": []}
        State = build_state_class(config)

        errors_type = State.__annotations__["errors"]
        assert get_origin(errors_type) is Annotated
        args = get_args(errors_type)
        assert args[0] is list
        assert args[1] is add

    @pytest.mark.req("REQ-YG-024")
    def test_messages_has_reducer(self):
        """messages field uses Annotated[list, add] reducer."""
        from yamlgraph.models.state_builder import build_state_class

        config = {"nodes": {}, "edges": []}
        State = build_state_class(config)

        messages_type = State.__annotations__["messages"]
        assert get_origin(messages_type) is Annotated
        args = get_args(messages_type)
        assert args[0] is list
        assert args[1] is add

    @pytest.mark.req("REQ-YG-024")
    def test_extracts_state_key_from_nodes(self):
        """state_key in node config becomes state field."""
        from yamlgraph.models.state_builder import build_state_class

        config = {
            "nodes": {
                "generate": {"prompt": "generate", "state_key": "generated"},
                "analyze": {"prompt": "analyze", "state_key": "analysis"},
            },
            "edges": [],
        }
        State = build_state_class(config)

        assert "generated" in State.__annotations__
        assert "analysis" in State.__annotations__

    @pytest.mark.req("REQ-YG-024")
    def test_agent_node_adds_input_field(self):
        """Agent nodes automatically add 'input' field."""
        from yamlgraph.models.state_builder import build_state_class

        config = {
            "nodes": {
                "agent": {"type": "agent", "prompt": "agent"},
            },
            "edges": [],
        }
        State = build_state_class(config)

        assert "input" in State.__annotations__

    @pytest.mark.req("REQ-YG-024")
    def test_agent_node_adds_tool_results_field(self):
        """Agent nodes add _tool_results field."""
        from yamlgraph.models.state_builder import build_state_class

        config = {
            "nodes": {
                "agent": {"type": "agent", "prompt": "agent"},
            },
            "edges": [],
        }
        State = build_state_class(config)

        assert "_tool_results" in State.__annotations__

    @pytest.mark.req("REQ-YG-024")
    def test_router_node_adds_route_field(self):
        """Router nodes add _route field."""
        from yamlgraph.models.state_builder import build_state_class

        config = {
            "nodes": {
                "router": {
                    "type": "router",
                    "prompt": "router",
                    "routes": {"a": "node_a", "b": "node_b"},
                },
            },
            "edges": [],
        }
        State = build_state_class(config)

        assert "_route" in State.__annotations__

    @pytest.mark.req("REQ-YG-024")
    def test_loop_tracking_fields_included(self):
        """Loop tracking fields are always included."""
        from yamlgraph.models.state_builder import build_state_class

        config = {"nodes": {}, "edges": []}
        State = build_state_class(config)

        assert "_loop_counts" in State.__annotations__
        assert "_loop_limit_reached" in State.__annotations__
        assert "_agent_iterations" in State.__annotations__
        assert "_agent_limit_reached" in State.__annotations__

    @pytest.mark.req("REQ-YG-024")
    def test_state_is_typeddict_total_false(self):
        """Generated state is TypedDict with total=False (all optional)."""
        from yamlgraph.models.state_builder import build_state_class

        config = {"nodes": {}, "edges": []}
        State = build_state_class(config)

        # TypedDict with total=False has __total__ = False
        assert State.__total__ is False

    @pytest.mark.req("REQ-YG-024")
    def test_state_works_with_langgraph(self):
        """Generated state class works with LangGraph StateGraph."""
        from langgraph.graph import StateGraph

        from yamlgraph.models.state_builder import build_state_class

        config = {
            "nodes": {
                "test": {"prompt": "test", "state_key": "result"},
            },
            "edges": [],
        }
        State = build_state_class(config)

        # Should not raise
        graph = StateGraph(State)
        graph.add_node("test", lambda s: {"result": "done"})
        graph.set_entry_point("test")
        graph.set_finish_point("test")
        compiled = graph.compile()

        # Verify fields are preserved
        result = compiled.invoke({"input": "hello"})
        assert "result" in result

    @pytest.mark.req("REQ-YG-024")
    def test_reducer_accumulates_messages(self):
        """Messages reducer accumulates across nodes."""
        from langgraph.graph import StateGraph

        from yamlgraph.models.state_builder import build_state_class

        config = {"nodes": {}, "edges": []}
        State = build_state_class(config)

        graph = StateGraph(State)
        graph.add_node("n1", lambda s: {"messages": [{"content": "a"}]})
        graph.add_node("n2", lambda s: {"messages": [{"content": "b"}]})
        graph.add_edge("n1", "n2")
        graph.set_entry_point("n1")
        graph.set_finish_point("n2")
        compiled = graph.compile()

        result = compiled.invoke({})
        assert len(result["messages"]) == 2


class TestExtractNodeFields:
    """Test field extraction from node configurations."""

    @pytest.mark.req("REQ-YG-024")
    def test_extracts_state_key(self):
        """Extracts state_key from nodes."""
        from yamlgraph.models.state_builder import extract_node_fields

        nodes = {
            "gen": {"state_key": "generated"},
            "analyze": {"state_key": "analysis"},
        }
        fields = extract_node_fields(nodes)

        assert "generated" in fields
        assert "analysis" in fields

    @pytest.mark.req("REQ-YG-024")
    def test_agent_adds_special_fields(self):
        """Agent nodes add input and _tool_results."""
        from yamlgraph.models.state_builder import extract_node_fields

        nodes = {"agent": {"type": "agent"}}
        fields = extract_node_fields(nodes)

        assert "input" in fields
        assert "_tool_results" in fields

    @pytest.mark.req("REQ-YG-024")
    def test_router_adds_route_field(self):
        """Router nodes add _route."""
        from yamlgraph.models.state_builder import extract_node_fields

        nodes = {"router": {"type": "router", "routes": {}}}
        fields = extract_node_fields(nodes)

        assert "_route" in fields


class TestCommonInputFields:
    """Test that common input fields are included."""

    @pytest.mark.req("REQ-YG-024")
    def test_includes_topic_field(self):
        """topic field included for content generation."""
        from yamlgraph.models.state_builder import build_state_class

        config = {"nodes": {}, "edges": []}
        State = build_state_class(config)

        assert "topic" in State.__annotations__

    @pytest.mark.req("REQ-YG-024")
    def test_includes_style_field(self):
        """style field included for content generation."""
        from yamlgraph.models.state_builder import build_state_class

        config = {"nodes": {}, "edges": []}
        State = build_state_class(config)

        assert "style" in State.__annotations__

    @pytest.mark.req("REQ-YG-024")
    def test_includes_word_count_field(self):
        """word_count field included for content generation."""
        from yamlgraph.models.state_builder import build_state_class

        config = {"nodes": {}, "edges": []}
        State = build_state_class(config)

        assert "word_count" in State.__annotations__

    @pytest.mark.req("REQ-YG-024")
    def test_includes_message_field(self):
        """message field included for router."""
        from yamlgraph.models.state_builder import build_state_class

        config = {"nodes": {}, "edges": []}
        State = build_state_class(config)

        assert "message" in State.__annotations__

    @pytest.mark.req("REQ-YG-024")
    def test_includes_input_field(self):
        """input field included for agents."""
        from yamlgraph.models.state_builder import build_state_class

        config = {"nodes": {}, "edges": []}
        State = build_state_class(config)

        assert "input" in State.__annotations__
