"""Tests for type: tool_call integration in graph_loader.

TDD Phase 3b: Wire tool_call node into graph compilation.
"""

import pytest
from langgraph.graph import StateGraph

from yamlgraph.graph_loader import GraphConfig, _compile_node
from yamlgraph.map_compiler import compile_map_node


# Sample tools for testing
def sample_search(path: str) -> dict:
    """Sample search tool."""
    return {"path": path, "matches": ["line1", "line2"]}


def sample_read(file: str, start: int = 1, end: int = 10) -> dict:
    """Sample read tool."""
    return {"file": file, "lines": list(range(start, end + 1))}


@pytest.fixture
def tools_registry() -> dict:
    """Combined tools registry for tool_call nodes."""
    return {
        "search_file": sample_search,
        "read_lines": sample_read,
    }


@pytest.fixture
def minimal_config() -> GraphConfig:
    """Minimal graph config with tools."""
    config_dict = {
        "version": "1.0",
        "name": "test",
        "nodes": {
            "dummy": {
                "prompt": "test",
                "state_key": "result",
            }
        },
        "edges": [
            {"from": "START", "to": "dummy"},
            {"from": "dummy", "to": "END"},
        ],
        "tools": {
            "search_file": {
                "type": "python",
                "module": "tests.unit.test_tool_call_integration",
                "function": "sample_search",
            },
            "read_lines": {
                "type": "python",
                "module": "tests.unit.test_tool_call_integration",
                "function": "sample_read",
            },
        },
    }
    return GraphConfig(config_dict)


class TestCompileToolCallNode:
    """Test _compile_node with type: tool_call."""

    def test_compiles_tool_call_node(self, minimal_config, tools_registry):
        """Should compile tool_call node and add to graph."""
        from operator import add
        from typing import Annotated

        # Create state class with reducer for discovery_findings
        class TestState:
            discovery_findings: Annotated[list, add] = []

        graph = StateGraph(TestState)

        node_config = {
            "type": "tool_call",
            "tool": "{state.task.tool}",
            "args": "{state.task.args}",
            "state_key": "result",
        }

        result = _compile_node(
            "test_tool_call",
            node_config,
            graph,
            minimal_config,
            tools={},
            python_tools={},
            websearch_tools={},
            callable_registry=tools_registry,  # tool_call uses callable_registry
        )

        # Should not return map info
        assert result is None
        # Node should be in graph
        assert "test_tool_call" in graph.nodes

    def test_tool_call_node_executes(self, tools_registry):
        """Tool call node should execute tool from state."""
        from yamlgraph.node_factory import create_tool_call_node

        node_config = {
            "tool": "{state.task.tool}",
            "args": "{state.task.args}",
            "state_key": "result",
        }
        node_fn = create_tool_call_node("exec_tool", node_config, tools_registry)

        state = {
            "task": {
                "id": 1,
                "tool": "search_file",
                "args": {"path": "foo.py"},
            }
        }
        result = node_fn(state)

        assert result["result"]["success"] is True
        assert result["result"]["result"]["path"] == "foo.py"


class TestMapWithToolCall:
    """Test map node with tool_call sub-node."""

    def test_map_with_tool_call_sub_node(self, tools_registry):
        """Map node should support type: tool_call in sub-node."""
        from operator import add
        from typing import Annotated

        class TestState:
            discovery_plan: dict = {}
            discovery_findings: Annotated[list, add] = []

        graph = StateGraph(TestState)

        map_config = {
            "type": "map",
            "over": "{state.discovery_plan.tasks}",
            "as": "task",
            "node": {
                "type": "tool_call",
                "tool": "{state.task.tool}",
                "args": "{state.task.args}",
                "state_key": "discovery_result",
            },
            "collect": "discovery_findings",
        }

        # This should work - map_compiler needs to handle tool_call sub-nodes
        map_edge_fn, sub_node_name = compile_map_node(
            "execute_discovery",
            map_config,
            graph,
            defaults={},
            tools_registry=tools_registry,  # New parameter for tool_call
        )

        assert callable(map_edge_fn)
        assert sub_node_name == "_map_execute_discovery_sub"
        assert sub_node_name in graph.nodes
