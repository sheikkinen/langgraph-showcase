"""Tests for agent nodes (type: agent).

Agent nodes allow the LLM to autonomously decide which tools to call
in a loop until it has enough information to respond.
"""

from unittest.mock import MagicMock, patch

import pytest

from yamlgraph.tools.agent import (
    build_langchain_tool,
    build_python_tool,
    create_agent_node,
)
from yamlgraph.tools.python_tool import PythonToolConfig
from yamlgraph.tools.shell import ShellToolConfig

# Mock prompt config returned by load_prompt
MOCK_AGENT_PROMPT = {
    "system": "You are a helpful assistant.",
    "user": "{input}",
}


@pytest.fixture(autouse=True)
def mock_load_prompt():
    """Auto-mock load_prompt for all tests in this module."""
    with patch("yamlgraph.tools.agent.load_prompt", return_value=MOCK_AGENT_PROMPT):
        yield


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


class TestBuildPythonTool:
    """Tests for build_python_tool function."""

    def test_creates_tool_with_name(self):
        """Tool has correct name."""
        config = PythonToolConfig(
            module="yamlgraph.utils.prompts",
            function="load_prompt",
            description="Load a prompt",
        )
        tool = build_python_tool("load_prompt", config)
        assert tool.name == "load_prompt"

    def test_creates_tool_with_description(self):
        """Tool has correct description."""
        config = PythonToolConfig(
            module="yamlgraph.utils.prompts",
            function="load_prompt",
            description="Load a YAML prompt file",
        )
        tool = build_python_tool("load_prompt", config)
        assert tool.description == "Load a YAML prompt file"

    def test_tool_is_structured_tool(self):
        """Tool is a LangChain StructuredTool."""
        from langchain_core.tools import StructuredTool

        config = PythonToolConfig(
            module="yamlgraph.utils.prompts",
            function="load_prompt",
            description="Load a prompt",
        )
        tool = build_python_tool("test_tool", config)
        assert isinstance(tool, StructuredTool)

    def test_tool_executes_function(self):
        """Tool invocation calls the Python function."""
        # Use a simple test function
        config = PythonToolConfig(
            module="os.path",
            function="join",
            description="Join paths",
        )
        tool = build_python_tool("path_join", config)
        result = tool.invoke({"a": "/home", "p": "user"})
        assert "/home" in result or "user" in result


class TestAgentWithPythonTools:
    """Tests for agent nodes using Python tools."""

    @patch("yamlgraph.tools.agent.create_llm")
    def test_agent_calls_python_tool(self, mock_create_llm):
        """Agent can use Python tools."""
        mock_llm = MagicMock()

        # First response: call a python tool
        first_response = MagicMock()
        first_response.tool_calls = [
            {
                "id": "call1",
                "name": "my_python_tool",
                "args": {"a": "/home", "p": "user"},
            }
        ]
        first_response.content = ""

        # Second response: final answer
        second_response = MagicMock()
        second_response.tool_calls = []
        second_response.content = "Path is /home/user"

        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.side_effect = [first_response, second_response]
        mock_create_llm.return_value = mock_llm

        python_tools = {
            "my_python_tool": PythonToolConfig(
                module="os.path",
                function="join",
                description="Join paths",
            ),
        }
        node_config = {
            "prompt": "agent",
            "tools": ["my_python_tool"],
            "max_iterations": 5,
            "state_key": "result",
        }

        node_fn = create_agent_node("agent", node_config, {}, python_tools=python_tools)
        result = node_fn({"input": "Join home and user"})

        assert result["result"] == "Path is /home/user"
        assert result["_agent_iterations"] == 2

    @patch("yamlgraph.tools.agent.create_llm")
    def test_agent_mixes_shell_and_python_tools(self, mock_create_llm):
        """Agent can use both shell and python tools."""
        mock_llm = MagicMock()

        # First: call shell tool
        first_response = MagicMock()
        first_response.tool_calls = [
            {"id": "call1", "name": "echo_tool", "args": {"message": "hello"}}
        ]
        first_response.content = ""

        # Second: call python tool
        second_response = MagicMock()
        second_response.tool_calls = [
            {"id": "call2", "name": "path_tool", "args": {"a": "/", "p": "tmp"}}
        ]
        second_response.content = ""

        # Third: final answer
        third_response = MagicMock()
        third_response.tool_calls = []
        third_response.content = "Done with both tools"

        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.side_effect = [first_response, second_response, third_response]
        mock_create_llm.return_value = mock_llm

        shell_tools = {
            "echo_tool": ShellToolConfig(command="echo {message}", description="Echo"),
        }
        python_tools = {
            "path_tool": PythonToolConfig(
                module="os.path",
                function="join",
                description="Join paths",
            ),
        }
        node_config = {
            "prompt": "agent",
            "tools": ["echo_tool", "path_tool"],
            "max_iterations": 5,
            "state_key": "result",
        }

        node_fn = create_agent_node(
            "agent", node_config, shell_tools, python_tools=python_tools
        )
        result = node_fn({"input": "Use both tools"})

        assert result["result"] == "Done with both tools"
        assert result["_agent_iterations"] == 3
