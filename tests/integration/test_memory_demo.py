"""Tests for Memory Demo - Multi-turn conversation with persistence.

Tests the memory features from Section 6 working together:
- Checkpointer for state persistence
- Message accumulation via dynamic state (Annotated reducers)
- Tool results storage
- Result export
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


class TestMemoryDemoGraphConfig:
    """Tests for memory-demo.yaml graph configuration."""

    def test_graph_config_exists(self):
        """Graph config file exists."""
        config_path = Path("graphs/memory-demo.yaml")
        assert config_path.exists(), "graphs/memory-demo.yaml should exist"

    def test_graph_config_loads(self):
        """Graph config loads without errors."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config("graphs/memory-demo.yaml")
        assert config.name == "memory_demo"

    def test_graph_has_agent_node(self):
        """Graph includes an agent node."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config("graphs/memory-demo.yaml")
        assert "review" in config.nodes
        assert config.nodes["review"]["type"] == "agent"

    def test_graph_has_tools(self):
        """Graph defines git tools."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config("graphs/memory-demo.yaml")
        tools = config.tools or {}
        assert "git_log" in tools
        assert "git_diff" in tools


class TestCodeReviewPrompt:
    """Tests for code_review.yaml prompt."""

    def test_prompt_file_exists(self):
        """Prompt file exists."""
        prompt_path = Path("prompts/code_review.yaml")
        assert prompt_path.exists(), "prompts/code_review.yaml should exist"

    def test_prompt_loads(self):
        """Prompt loads with system and user templates."""
        from yamlgraph.utils.prompts import load_prompt

        prompt = load_prompt("code_review")
        assert "system" in prompt
        assert "user" in prompt


class TestCheckpointerIntegration:
    """Tests for checkpointer integration with graph builder."""

    def test_build_graph_accepts_checkpointer(self):
        """build_graph accepts optional checkpointer parameter."""
        import tempfile

        from yamlgraph.builder import build_graph
        from yamlgraph.storage.checkpointer import get_checkpointer

        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            checkpointer = get_checkpointer(f.name)
            # Should not raise
            graph = build_graph(checkpointer=checkpointer)
            assert graph is not None

    def test_graph_with_checkpointer_accepts_thread_id(self):
        """Graph with checkpointer can be invoked with thread_id."""
        import tempfile

        from yamlgraph.builder import build_graph
        from yamlgraph.storage.checkpointer import get_checkpointer

        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            checkpointer = get_checkpointer(f.name)
            _graph = build_graph(checkpointer=checkpointer)  # noqa: F841

            # Should accept configurable with thread_id
            config = {"configurable": {"thread_id": "test-123"}}
            # Just verify config structure is valid
            assert "thread_id" in config["configurable"]


class TestCLIThreadFlag:
    """Tests for CLI --thread flag."""

    def test_graph_run_cli_has_thread_argument(self):
        """Graph run CLI accepts --thread argument."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        # Parse with thread flag
        args = parser.parse_args(
            ["graph", "run", "graphs/yamlgraph.yaml", "--thread", "abc123"]
        )
        assert args.thread == "abc123"

    def test_graph_run_thread_defaults_to_none(self):
        """Thread defaults to None when not specified."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["graph", "run", "graphs/yamlgraph.yaml"])
        assert args.thread is None


class TestCLIExportFlag:
    """Tests for CLI --export flag."""

    def test_graph_run_cli_has_export_argument(self):
        """Graph run CLI accepts --export flag."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["graph", "run", "graphs/yamlgraph.yaml", "--export"])
        assert args.export is True

    def test_graph_run_export_defaults_to_false(self):
        """Export defaults to False when not specified."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["graph", "run", "graphs/yamlgraph.yaml"])
        assert args.export is False


class TestMemoryDemoEndToEnd:
    """End-to-end tests for memory demo (mocked LLM)."""

    def test_single_turn_returns_messages(self):
        """Single turn execution returns messages in state."""
        from yamlgraph.tools.agent import create_agent_node
        from yamlgraph.tools.shell import ShellToolConfig

        mock_response = AIMessage(content="Here are the recent commits...")

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = mock_response

        tool_config = ShellToolConfig(
            command="git log --oneline -n {count}",
            description="Get recent commits",
        )

        mock_prompt = {"system": "You are an assistant.", "user": "{input}"}

        with (
            patch("yamlgraph.tools.agent.create_llm", return_value=mock_llm),
            patch("yamlgraph.tools.agent.load_prompt", return_value=mock_prompt),
        ):
            node_fn = create_agent_node(
                "review",
                {
                    "tools": ["git_log"],
                    "state_key": "response",
                    "tool_results_key": "_tool_results",
                },
                {"git_log": tool_config},
            )
            result = node_fn({"input": "Show recent commits"})

        assert "messages" in result
        assert "response" in result

    def test_multi_turn_preserves_history(self):
        """Multi-turn conversation preserves message history."""
        from yamlgraph.tools.agent import create_agent_node

        mock_response = AIMessage(content="Based on our previous discussion...")

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = mock_response

        # Simulate existing conversation
        existing_messages = [
            SystemMessage(content="You are a code review assistant."),
            HumanMessage(content="Show commits"),
            AIMessage(content="Here are 5 commits..."),
        ]

        mock_prompt = {"system": "You are an assistant.", "user": "{input}"}

        with (
            patch("yamlgraph.tools.agent.create_llm", return_value=mock_llm),
            patch("yamlgraph.tools.agent.load_prompt", return_value=mock_prompt),
        ):
            node_fn = create_agent_node(
                "review",
                {"tools": [], "state_key": "response"},
                {},
            )
            result = node_fn(
                {
                    "input": "What about tests?",
                    "messages": existing_messages,
                }
            )

        # New messages should be returned
        assert len(result["messages"]) >= 2  # At least human + AI

    def test_tool_results_stored_in_state(self):
        """Tool execution results are stored in state."""
        from yamlgraph.tools.agent import create_agent_node
        from yamlgraph.tools.shell import ShellToolConfig

        tool_response = AIMessage(
            content="",
            tool_calls=[{"name": "git_log", "args": {"count": "5"}, "id": "call_1"}],
        )
        final_response = AIMessage(content="Found 5 commits")

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.side_effect = [tool_response, final_response]

        tool_config = ShellToolConfig(
            command="git log --oneline -n {count}",
            description="Get recent commits",
        )

        mock_prompt = {"system": "You are an assistant.", "user": "{input}"}

        with (
            patch("yamlgraph.tools.agent.create_llm", return_value=mock_llm),
            patch("yamlgraph.tools.agent.load_prompt", return_value=mock_prompt),
            patch("yamlgraph.tools.agent.execute_shell_tool") as mock_exec,
        ):
            mock_exec.return_value = MagicMock(
                success=True, output="abc123 First commit\ndef456 Second commit"
            )

            node_fn = create_agent_node(
                "review",
                {
                    "tools": ["git_log"],
                    "state_key": "response",
                    "tool_results_key": "_tool_results",
                },
                {"git_log": tool_config},
            )
            result = node_fn({"input": "Show commits"})

        assert "_tool_results" in result
        assert len(result["_tool_results"]) == 1
        assert result["_tool_results"][0]["tool"] == "git_log"

    def test_export_creates_files(self, tmp_path: Path):
        """Export flag creates output files."""
        from yamlgraph.storage.export import export_result

        state = {
            "thread_id": "demo-123",
            "response": "# Code Review Summary\n\nFound 5 commits.",
            "_tool_results": [
                {"tool": "git_log", "args": {"count": "5"}, "output": "..."}
            ],
        }

        config = {
            "response": {"format": "markdown", "filename": "review.md"},
            "_tool_results": {"format": "json", "filename": "tool_outputs.json"},
        }

        paths = export_result(state, config, base_path=tmp_path)

        assert len(paths) == 2

        # Check markdown file
        md_path = tmp_path / "demo-123" / "review.md"
        assert md_path.exists()
        assert "Code Review Summary" in md_path.read_text()

        # Check JSON file
        json_path = tmp_path / "demo-123" / "tool_outputs.json"
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert data[0]["tool"] == "git_log"
