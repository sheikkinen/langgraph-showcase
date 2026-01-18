"""Tests for type: tool_call node in node_factory.

TDD Phase 3: Dynamic tool execution from state.
"""

import pytest

from yamlgraph.constants import NodeType
from yamlgraph.node_factory import create_tool_call_node


# Sample tools for testing
def sample_tool(path: str, pattern: str = ".*") -> dict:
    """Sample tool that returns its args."""
    return {"path": path, "pattern": pattern, "found": ["line1", "line2"]}


def failing_tool(path: str) -> dict:
    """Tool that always raises."""
    raise ValueError(f"Cannot process: {path}")


def simple_tool() -> str:
    """Tool with no args."""
    return "simple result"


@pytest.fixture
def tools_registry() -> dict:
    """Sample tools registry."""
    return {
        "search_file": sample_tool,
        "failing_tool": failing_tool,
        "simple_tool": simple_tool,
    }


class TestNodeTypeConstant:
    """Verify TOOL_CALL is added to NodeType enum."""

    def test_tool_call_in_node_type(self):
        """TOOL_CALL should be a valid node type."""
        assert NodeType.TOOL_CALL == "tool_call"


class TestCreateToolCallNode:
    """Test create_tool_call_node factory function."""

    def test_creates_callable(self, tools_registry):
        """Should return a callable node function."""
        config = {
            "tool": "{state.task.tool}",
            "args": "{state.task.args}",
            "state_key": "result",
        }
        node_fn = create_tool_call_node("test_node", config, tools_registry)
        assert callable(node_fn)

    def test_resolves_tool_from_state(self, tools_registry):
        """Should resolve tool name dynamically from state."""
        config = {
            "tool": "{state.task.tool}",
            "args": "{state.task.args}",
            "state_key": "result",
        }
        node_fn = create_tool_call_node("test_node", config, tools_registry)

        state = {
            "task": {
                "id": 1,
                "tool": "search_file",
                "args": {"path": "foo.py", "pattern": "def"},
            }
        }
        result = node_fn(state)

        assert result["result"]["success"] is True
        assert result["result"]["tool"] == "search_file"

    def test_resolves_args_from_state(self, tools_registry):
        """Should resolve args dynamically and pass to tool."""
        config = {
            "tool": "{state.task.tool}",
            "args": "{state.task.args}",
            "state_key": "result",
        }
        node_fn = create_tool_call_node("test_node", config, tools_registry)

        state = {
            "task": {
                "id": 1,
                "tool": "search_file",
                "args": {"path": "bar.py", "pattern": "class"},
            }
        }
        result = node_fn(state)

        # Verify args were passed correctly
        assert result["result"]["result"]["path"] == "bar.py"
        assert result["result"]["result"]["pattern"] == "class"

    def test_successful_execution(self, tools_registry):
        """Should return success=True with result on success."""
        config = {
            "tool": "{state.task.tool}",
            "args": "{state.task.args}",
            "state_key": "result",
        }
        node_fn = create_tool_call_node("test_node", config, tools_registry)

        state = {"task": {"id": 42, "tool": "search_file", "args": {"path": "x.py"}}}
        result = node_fn(state)

        assert result["result"]["success"] is True
        assert result["result"]["task_id"] == 42
        assert result["result"]["error"] is None
        assert "found" in result["result"]["result"]

    def test_unknown_tool_handling(self, tools_registry):
        """Should return success=False for unknown tool."""
        config = {
            "tool": "{state.task.tool}",
            "args": "{state.task.args}",
            "state_key": "result",
        }
        node_fn = create_tool_call_node("test_node", config, tools_registry)

        state = {"task": {"id": 1, "tool": "nonexistent_tool", "args": {}}}
        result = node_fn(state)

        assert result["result"]["success"] is False
        assert "Unknown tool" in result["result"]["error"]
        assert result["result"]["tool"] == "nonexistent_tool"

    def test_tool_exception_handling(self, tools_registry):
        """Should catch exceptions and return success=False."""
        config = {
            "tool": "{state.task.tool}",
            "args": "{state.task.args}",
            "state_key": "result",
        }
        node_fn = create_tool_call_node("test_node", config, tools_registry)

        state = {"task": {"id": 5, "tool": "failing_tool", "args": {"path": "bad.py"}}}
        result = node_fn(state)

        assert result["result"]["success"] is False
        assert "Cannot process: bad.py" in result["result"]["error"]
        assert result["result"]["task_id"] == 5

    def test_includes_current_step(self, tools_registry):
        """Should include current_step in output for state tracking."""
        config = {
            "tool": "{state.task.tool}",
            "args": "{state.task.args}",
            "state_key": "result",
        }
        node_fn = create_tool_call_node("my_tool_call", config, tools_registry)

        state = {"task": {"id": 1, "tool": "simple_tool", "args": {}}}
        result = node_fn(state)

        assert result["current_step"] == "my_tool_call"

    def test_empty_args(self, tools_registry):
        """Should work with tools that take no arguments."""
        config = {
            "tool": "{state.task.tool}",
            "args": "{state.task.args}",
            "state_key": "result",
        }
        node_fn = create_tool_call_node("test_node", config, tools_registry)

        state = {"task": {"id": 1, "tool": "simple_tool", "args": {}}}
        result = node_fn(state)

        assert result["result"]["success"] is True
        assert result["result"]["result"] == "simple result"
