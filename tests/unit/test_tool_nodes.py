"""Tests for tool nodes (type: tool)."""


import pytest

from showcase.tools.shell import ShellToolConfig
from showcase.tools.nodes import create_tool_node


class TestCreateToolNode:
    """Tests for create_tool_node function."""

    def test_executes_named_tool(self):
        """Node runs correct tool from registry."""
        tools = {
            "echo_tool": ShellToolConfig(command="echo hello"),
            "other_tool": ShellToolConfig(command="echo other"),
        }
        node_config = {"tool": "echo_tool"}

        node_fn = create_tool_node("test_node", node_config, tools)
        result = node_fn({})

        assert result["test_node"].strip() == "hello"
        assert result["current_step"] == "test_node"

    def test_resolves_variables_from_state(self):
        """State values passed to tool."""
        tools = {
            "greet": ShellToolConfig(command="echo Hello {name}"),
        }
        node_config = {
            "tool": "greet",
            "variables": {"name": "{state.user_name}"},
        }

        node_fn = create_tool_node("greet_node", node_config, tools)
        result = node_fn({"user_name": "Alice"})

        assert "Alice" in result["greet_node"]

    def test_stores_result_in_state_key(self):
        """Tool output saved to custom state_key."""
        tools = {
            "data_tool": ShellToolConfig(command="echo data_value"),
        }
        node_config = {
            "tool": "data_tool",
            "state_key": "my_data",
        }

        node_fn = create_tool_node("fetch_node", node_config, tools)
        result = node_fn({})

        assert "my_data" in result
        assert result["my_data"].strip() == "data_value"

    def test_on_error_skip(self):
        """Failed tool skipped when on_error: skip."""
        tools = {
            "fail_tool": ShellToolConfig(command="exit 1"),
        }
        node_config = {
            "tool": "fail_tool",
            "on_error": "skip",
        }

        node_fn = create_tool_node("fail_node", node_config, tools)
        result = node_fn({})

        # Should not raise, should return with error info
        assert result["current_step"] == "fail_node"
        assert "errors" in result or result.get("fail_node") is None

    def test_on_error_fail_raises(self):
        """Failed tool raises when on_error: fail."""
        tools = {
            "fail_tool": ShellToolConfig(command="exit 1"),
        }
        node_config = {
            "tool": "fail_tool",
            "on_error": "fail",
        }

        node_fn = create_tool_node("fail_node", node_config, tools)

        with pytest.raises(RuntimeError):
            node_fn({})

    def test_nested_state_variable(self):
        """Nested state values like {state.location.lat} resolved."""
        tools = {
            "geo": ShellToolConfig(command="echo {lat},{lon}"),
        }
        node_config = {
            "tool": "geo",
            "variables": {
                "lat": "{state.location.lat}",
                "lon": "{state.location.lon}",
            },
        }

        node_fn = create_tool_node("geo_node", node_config, tools)
        result = node_fn({"location": {"lat": "37.7749", "lon": "-122.4194"}})

        assert "37.7749" in result["geo_node"]
        assert "-122.4194" in result["geo_node"]

    def test_missing_tool_raises(self):
        """Unknown tool name raises error."""
        tools = {}
        node_config = {"tool": "nonexistent"}

        with pytest.raises(KeyError):
            create_tool_node("bad_node", node_config, tools)

    def test_json_parse_tool(self):
        """Tool with parse: json returns dict."""
        tools = {
            "json_tool": ShellToolConfig(
                command="echo '{{\"count\": 42}}'",
                parse="json",
            ),
        }
        node_config = {"tool": "json_tool"}

        node_fn = create_tool_node("json_node", node_config, tools)
        result = node_fn({})

        assert result["json_node"] == {"count": 42}
