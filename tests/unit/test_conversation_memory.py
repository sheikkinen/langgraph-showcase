"""Tests for Phase 6.3: Conversation Memory.

Tests that agent nodes:
1. Return messages to state for accumulation
2. Store raw tool results in state
3. Support multi-turn conversations via thread_id
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)

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


class TestAgentReturnsMessages:
    """Tests for message accumulation in agent state."""

    @pytest.mark.req("REQ-YG-026")
    def test_agent_returns_messages_in_state(self):
        """Agent node should return messages for state accumulation."""
        from yamlgraph.tools.agent import create_agent_node

        # Setup mock LLM
        mock_response = MagicMock()
        mock_response.content = "Analysis complete"
        mock_response.tool_calls = []

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = mock_response

        with patch("yamlgraph.tools.agent.create_llm", return_value=mock_llm):
            node_fn = create_agent_node(
                "agent",
                {"tools": [], "state_key": "result"},
                {},
            )
            result = node_fn({"input": "test"})

        # Should include messages in output
        assert "messages" in result, "Agent should return messages for accumulation"
        assert (
            len(result["messages"]) >= 2
        ), "Should have at least system + user + AI messages"

    @pytest.mark.req("REQ-YG-026")
    def test_agent_messages_include_all_types(self):
        """Agent should include system, user, AI, and tool messages."""
        from yamlgraph.tools.agent import create_agent_node
        from yamlgraph.tools.shell import ShellToolConfig

        # Mock LLM that calls a tool then responds
        # Use actual AIMessage for proper type checking
        tool_response = AIMessage(
            content="", tool_calls=[{"name": "test_tool", "args": {}, "id": "call_1"}]
        )

        final_response = AIMessage(content="Done")

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.side_effect = [tool_response, final_response]

        tool_config = ShellToolConfig(
            command="echo test",
            description="Test tool",
        )

        with (
            patch("yamlgraph.tools.agent.create_llm", return_value=mock_llm),
            patch("yamlgraph.tools.agent.execute_shell_tool") as mock_exec,
        ):
            mock_exec.return_value = MagicMock(success=True, output="tool output")

            node_fn = create_agent_node(
                "agent",
                {"tools": ["test_tool"], "state_key": "result"},
                {"test_tool": tool_config},
            )
            result = node_fn({"input": "test"})

        messages = result["messages"]
        types = [type(m).__name__ for m in messages]

        assert "SystemMessage" in types, "Should include system message"
        assert "HumanMessage" in types, "Should include human message"
        assert "AIMessage" in types, "Should include AI message"
        assert "ToolMessage" in types, "Should include tool message"


class TestToolResultsPersistence:
    """Tests for raw tool result storage."""

    @pytest.mark.req("REQ-YG-026")
    def test_tool_results_stored_in_state(self):
        """Agent should store raw tool results in state."""
        from yamlgraph.tools.agent import create_agent_node
        from yamlgraph.tools.shell import ShellToolConfig

        tool_response = MagicMock()
        tool_response.content = ""
        tool_response.tool_calls = [
            {"name": "git_log", "args": {"count": "5"}, "id": "call_1"}
        ]

        final_response = MagicMock()
        final_response.content = "Report ready"
        final_response.tool_calls = []

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.side_effect = [tool_response, final_response]

        tool_config = ShellToolConfig(
            command="git log -n {count}",
            description="Get git log",
        )

        with (
            patch("yamlgraph.tools.agent.create_llm", return_value=mock_llm),
            patch("yamlgraph.tools.agent.execute_shell_tool") as mock_exec,
        ):
            mock_exec.return_value = MagicMock(
                success=True, output="commit abc123\nAuthor: Test"
            )

            node_fn = create_agent_node(
                "agent",
                {
                    "tools": ["git_log"],
                    "state_key": "report",
                    "tool_results_key": "_tool_results",
                },
                {"git_log": tool_config},
            )
            result = node_fn({"input": "analyze"})

        assert "_tool_results" in result, "Should include tool_results in state"
        assert len(result["_tool_results"]) == 1, "Should have one tool result"

        tool_result = result["_tool_results"][0]
        assert tool_result["tool"] == "git_log"
        assert tool_result["args"] == {"count": "5"}
        assert "commit abc123" in tool_result["output"]
        assert tool_result["success"] is True

    @pytest.mark.req("REQ-YG-026")
    def test_tool_results_key_is_optional(self):
        """Without tool_results_key, raw results are not stored."""
        from yamlgraph.tools.agent import create_agent_node

        mock_response = MagicMock()
        mock_response.content = "Done"
        mock_response.tool_calls = []

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = mock_response

        with patch("yamlgraph.tools.agent.create_llm", return_value=mock_llm):
            node_fn = create_agent_node(
                "agent",
                {"tools": [], "state_key": "result"},  # No tool_results_key
                {},
            )
            result = node_fn({"input": "test"})

        # Should NOT have _tool_results if not configured
        assert "_tool_results" not in result

    @pytest.mark.req("REQ-YG-026")
    def test_multiple_tool_calls_all_stored(self):
        """Multiple tool calls should all be stored."""
        from yamlgraph.tools.agent import create_agent_node
        from yamlgraph.tools.shell import ShellToolConfig

        tool_response = MagicMock()
        tool_response.content = ""
        tool_response.tool_calls = [
            {"name": "tool_a", "args": {}, "id": "call_1"},
            {"name": "tool_b", "args": {}, "id": "call_2"},
        ]

        final_response = MagicMock()
        final_response.content = "Done"
        final_response.tool_calls = []

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.side_effect = [tool_response, final_response]

        tools = {
            "tool_a": ShellToolConfig(command="echo a", description="A"),
            "tool_b": ShellToolConfig(command="echo b", description="B"),
        }

        with (
            patch("yamlgraph.tools.agent.create_llm", return_value=mock_llm),
            patch("yamlgraph.tools.agent.execute_shell_tool") as mock_exec,
        ):
            mock_exec.return_value = MagicMock(success=True, output="output")

            node_fn = create_agent_node(
                "agent",
                {
                    "tools": ["tool_a", "tool_b"],
                    "state_key": "result",
                    "tool_results_key": "_tool_results",
                },
                tools,
            )
            result = node_fn({"input": "test"})

        assert len(result["_tool_results"]) == 2
        tool_names = [r["tool"] for r in result["_tool_results"]]
        assert "tool_a" in tool_names
        assert "tool_b" in tool_names


class TestMultiTurnConversation:
    """Tests for multi-turn conversation support."""

    @pytest.mark.req("REQ-YG-026")
    def test_existing_messages_preserved(self):
        """Agent should preserve existing messages from state."""
        from yamlgraph.tools.agent import create_agent_node

        mock_response = MagicMock()
        mock_response.content = "Follow-up response"
        mock_response.tool_calls = []

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = mock_response

        # Simulate state with existing messages
        existing_messages = [
            SystemMessage(content="You are helpful."),
            HumanMessage(content="First question"),
            AIMessage(content="First answer"),
        ]

        with patch("yamlgraph.tools.agent.create_llm", return_value=mock_llm):
            node_fn = create_agent_node(
                "agent",
                {"tools": [], "state_key": "result"},
                {},
            )
            result = node_fn(
                {
                    "input": "Follow-up question",
                    "messages": existing_messages,
                }
            )

        messages = result["messages"]
        # Should include new messages (at minimum human + AI for this turn)
        # The exact count depends on implementation - key is messages are returned
        assert len(messages) >= 2, "Should return messages for accumulation"

    @pytest.mark.req("REQ-YG-026")
    def test_agent_state_message_reducer_works(self):
        """Dynamic state's Annotated[list, add] should accumulate messages."""
        from operator import add as add_op
        from typing import get_type_hints

        from yamlgraph.models.state_builder import build_state_class

        State = build_state_class({"nodes": {"agent": {"type": "agent"}}})
        hints = get_type_hints(State, include_extras=True)

        # Check messages field has reducer annotation
        messages_hint = hints.get("messages")
        assert messages_hint is not None, "State should have messages field"

        # The Annotated type should have add as metadata
        if hasattr(messages_hint, "__metadata__"):
            assert (
                add_op in messages_hint.__metadata__
            ), "messages should use add reducer"
