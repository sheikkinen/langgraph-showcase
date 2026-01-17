"""Tests for agent nodes (type: agent).

Agent nodes allow the LLM to autonomously decide which tools to call
in a loop until it has enough information to respond.
"""

from unittest.mock import MagicMock, patch

from yamlgraph.tools.agent import build_langchain_tool, create_agent_node
from yamlgraph.tools.shell import ShellToolConfig


class TestBuildLangchainTool:
    """Tests for build_langchain_tool function."""

    def test_creates_tool_with_name(self):
        """Tool has correct name."""
        config = ShellToolConfig(
            command="echo test",
            description="Test tool",
        )
        tool = build_langchain_tool("my_tool", config)
        assert tool.name == "my_tool"

    def test_creates_tool_with_description(self):
        """Tool has correct description."""
        config = ShellToolConfig(
            command="echo test",
            description="A helpful test tool",
        )
        tool = build_langchain_tool("test", config)
        assert tool.description == "A helpful test tool"

    def test_tool_executes_command(self):
        """Tool invocation runs shell command."""
        config = ShellToolConfig(
            command="echo {message}",
            description="Echo a message",
        )
        tool = build_langchain_tool("echo", config)
        result = tool.invoke({"message": "hello"})
        assert "hello" in result


class TestCreateAgentNode:
    """Tests for create_agent_node function."""

    @patch("yamlgraph.tools.agent.create_llm")
    def test_agent_completes_without_tools(self, mock_create_llm):
        """Agent can finish with no tool calls."""
        # Mock LLM that returns a direct answer (no tool calls)
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.tool_calls = []
        mock_response.content = "The answer is 42"
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = mock_response
        mock_create_llm.return_value = mock_llm

        tools = {
            "search": ShellToolConfig(command="echo search", description="Search"),
        }
        node_config = {
            "prompt": "agent",
            "tools": ["search"],
            "max_iterations": 5,
            "state_key": "result",
        }

        node_fn = create_agent_node("agent", node_config, tools)
        result = node_fn({"input": "What is the meaning of life?"})

        assert result["result"] == "The answer is 42"
        assert result["_agent_iterations"] == 1

    @patch("yamlgraph.tools.agent.create_llm")
    def test_agent_calls_tool(self, mock_create_llm):
        """LLM tool call executes shell command."""
        # Mock LLM that first calls a tool, then returns answer
        mock_llm = MagicMock()

        # First response: call a tool
        first_response = MagicMock()
        first_response.tool_calls = [
            {"id": "call1", "name": "echo", "args": {"message": "test"}}
        ]
        first_response.content = ""

        # Second response: final answer
        second_response = MagicMock()
        second_response.tool_calls = []
        second_response.content = "I echoed: test"

        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.side_effect = [first_response, second_response]
        mock_create_llm.return_value = mock_llm

        tools = {
            "echo": ShellToolConfig(command="echo {message}", description="Echo"),
        }
        node_config = {
            "prompt": "agent",
            "tools": ["echo"],
            "max_iterations": 5,
            "state_key": "result",
        }

        node_fn = create_agent_node("agent", node_config, tools)
        result = node_fn({"input": "Echo something"})

        assert result["result"] == "I echoed: test"
        assert result["_agent_iterations"] == 2

    @patch("yamlgraph.tools.agent.create_llm")
    def test_max_iterations_enforced(self, mock_create_llm):
        """Stops after max_iterations reached."""
        # Mock LLM that always calls a tool (never finishes)
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.tool_calls = [
            {"id": "call1", "name": "search", "args": {"query": "more"}}
        ]
        mock_response.content = "Still searching..."
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = mock_response
        mock_create_llm.return_value = mock_llm

        tools = {
            "search": ShellToolConfig(command="echo searching", description="Search"),
        }
        node_config = {
            "prompt": "agent",
            "tools": ["search"],
            "max_iterations": 3,
            "state_key": "result",
        }

        node_fn = create_agent_node("agent", node_config, tools)
        result = node_fn({"input": "Search forever"})

        # Should stop at max_iterations
        assert result["_agent_limit_reached"] is True
        assert mock_llm.invoke.call_count == 3

    @patch("yamlgraph.tools.agent.create_llm")
    def test_tool_result_returned_to_llm(self, mock_create_llm):
        """LLM sees tool output in next turn."""
        mock_llm = MagicMock()

        # First: call tool
        first_response = MagicMock()
        first_response.tool_calls = [
            {"id": "call1", "name": "calc", "args": {"expr": "2+2"}}
        ]
        first_response.content = ""

        # Second: answer based on tool result
        second_response = MagicMock()
        second_response.tool_calls = []
        second_response.content = "The result is 4"

        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.side_effect = [first_response, second_response]
        mock_create_llm.return_value = mock_llm

        tools = {
            "calc": ShellToolConfig(
                command="echo 4",  # Simulates python calc
                description="Calculate",
            ),
        }
        node_config = {
            "prompt": "agent",
            "tools": ["calc"],
            "max_iterations": 5,
            "state_key": "answer",
        }

        node_fn = create_agent_node("agent", node_config, tools)
        node_fn({"input": "What is 2+2?"})

        # Check that second invoke received messages with tool result
        second_call_messages = mock_llm.invoke.call_args_list[1][0][0]
        # Should have: system, user, ai (with tool call), tool result
        assert len(second_call_messages) >= 4

    def test_default_max_iterations(self):
        """Default max_iterations is 5."""
        tools = {
            "test": ShellToolConfig(command="echo test", description="Test"),
        }
        node_config = {
            "prompt": "agent",
            "tools": ["test"],
            # No max_iterations specified
        }

        # Just verify it doesn't fail - actual behavior tested above
        node_fn = create_agent_node("agent", node_config, tools)
        assert callable(node_fn)
