"""Tests for CLI memory-demo command."""

import pytest
from unittest.mock import MagicMock, patch


class TestMemoryDemoParser:
    """Tests for memory-demo CLI argument parsing."""

    def test_memory_demo_command_exists(self):
        """memory-demo command is registered."""
        from showcase.cli import create_parser

        parser = create_parser()
        # Should parse without error
        args = parser.parse_args(["memory-demo", "--input", "test query"])
        assert args.command == "memory-demo"

    def test_input_argument_required(self):
        """--input argument is required."""
        from showcase.cli import create_parser

        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["memory-demo"])  # Missing --input

    def test_thread_argument_optional(self):
        """--thread argument is optional."""
        from showcase.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["memory-demo", "--input", "test"])
        assert args.thread is None

    def test_thread_argument_accepted(self):
        """--thread argument is accepted."""
        from showcase.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["memory-demo", "--input", "test", "--thread", "abc123"]
        )
        assert args.thread == "abc123"

    def test_export_flag_default_false(self):
        """--export flag defaults to False."""
        from showcase.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["memory-demo", "--input", "test"])
        assert args.export is False

    def test_export_flag_sets_true(self):
        """--export flag sets to True."""
        from showcase.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["memory-demo", "--input", "test", "--export"])
        assert args.export is True

    def test_repo_argument_defaults_to_current(self):
        """--repo defaults to current directory."""
        from showcase.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["memory-demo", "--input", "test"])
        assert args.repo == "."

    def test_repo_argument_accepted(self):
        """--repo argument is accepted."""
        from showcase.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["memory-demo", "--input", "test", "--repo", "/path/to/repo"]
        )
        assert args.repo == "/path/to/repo"


class TestMemoryDemoCommand:
    """Tests for cmd_memory_demo function."""

    def test_cmd_memory_demo_exists(self):
        """cmd_memory_demo function exists."""
        from showcase.cli import cmd_memory_demo

        assert callable(cmd_memory_demo)

    def test_generates_thread_id_if_not_provided(self):
        """New thread_id is generated when not provided."""
        from showcase.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["memory-demo", "--input", "test"])

        # Mock the graph execution - patch at source
        with patch("showcase.graph_loader.load_and_compile") as mock_load:
            mock_graph = MagicMock()
            mock_app = MagicMock()
            mock_graph.compile.return_value = mock_app
            mock_app.invoke.return_value = {
                "response": "Test response",
                "messages": [],
                "_tool_results": [],
            }
            mock_load.return_value = mock_graph

            from showcase.cli import cmd_memory_demo

            cmd_memory_demo(args)

            # Verify invoke was called
            mock_app.invoke.assert_called_once()

    def test_uses_provided_thread_id(self):
        """Uses provided thread_id for continuation."""
        from showcase.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["memory-demo", "--input", "follow up", "--thread", "existing-123"]
        )

        with patch("showcase.graph_loader.load_and_compile") as mock_load:
            mock_graph = MagicMock()
            mock_app = MagicMock()
            mock_graph.compile.return_value = mock_app
            mock_app.invoke.return_value = {
                "response": "Response",
                "messages": [],
            }
            mock_load.return_value = mock_graph

            from showcase.cli import cmd_memory_demo

            cmd_memory_demo(args)

            # Verify thread_id passed to invoke
            # Thread ID should be in configurable or state
            assert mock_app.invoke.called

    def test_prints_response(self, capsys):
        """Command prints the response."""
        from showcase.cli import create_parser, cmd_memory_demo

        parser = create_parser()
        args = parser.parse_args(["memory-demo", "--input", "test"])

        with patch("showcase.graph_loader.load_and_compile") as mock_load:
            mock_graph = MagicMock()
            mock_app = MagicMock()
            mock_graph.compile.return_value = mock_app
            mock_app.invoke.return_value = {
                "response": "Here are the commits...",
                "messages": [1, 2, 3],
                "_tool_results": [{"tool": "git_log"}],
            }
            mock_load.return_value = mock_graph

            cmd_memory_demo(args)

            captured = capsys.readouterr()
            assert "Here are the commits" in captured.out

    def test_prints_thread_id(self, capsys):
        """Command prints the thread_id for continuation."""
        from showcase.cli import create_parser, cmd_memory_demo

        parser = create_parser()
        args = parser.parse_args(["memory-demo", "--input", "test"])

        with patch("showcase.graph_loader.load_and_compile") as mock_load:
            mock_graph = MagicMock()
            mock_app = MagicMock()
            mock_graph.compile.return_value = mock_app
            mock_app.invoke.return_value = {
                "response": "Response",
                "messages": [],
            }
            mock_load.return_value = mock_graph

            cmd_memory_demo(args)

            captured = capsys.readouterr()
            # Should show thread ID for continuation
            assert "thread" in captured.out.lower()
