"""Tests for universal graph runner (Phase 7.2).

TDD tests for `yamlgraph graph run <path>` command.
"""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# graph subcommand tests
# =============================================================================


class TestGraphSubcommand:
    """Tests for graph subcommand group."""

    def test_graph_subparser_exists(self):
        """graph subparser should be configured."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        # Parse with graph command
        args = parser.parse_args(["graph", "list"])
        assert args.command == "graph"

    def test_graph_run_subcommand_exists(self):
        """graph run subcommand should exist."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["graph", "run", "graphs/yamlgraph.yaml", "--var", "topic=AI"]
        )
        assert args.graph_command == "run"
        assert args.graph_path == "graphs/yamlgraph.yaml"

    def test_graph_list_subcommand_exists(self):
        """graph list subcommand should exist."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["graph", "list"])
        assert args.graph_command == "list"

    def test_graph_info_subcommand_exists(self):
        """graph info subcommand should exist."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["graph", "info", "graphs/yamlgraph.yaml"])
        assert args.graph_command == "info"
        assert args.graph_path == "graphs/yamlgraph.yaml"


# =============================================================================
# graph run argument parsing tests
# =============================================================================


class TestGraphRunArgs:
    """Tests for graph run argument parsing."""

    def test_var_single_value(self):
        """--var key=value should parse correctly."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["graph", "run", "graphs/test.yaml", "--var", "topic=AI"]
        )
        assert args.var == ["topic=AI"]

    def test_var_multiple_values(self):
        """Multiple --var flags should accumulate."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            [
                "graph",
                "run",
                "graphs/test.yaml",
                "--var",
                "topic=AI",
                "--var",
                "style=casual",
            ]
        )
        assert args.var == ["topic=AI", "style=casual"]

    def test_thread_argument(self):
        """--thread should set thread ID."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["graph", "run", "graphs/test.yaml", "--thread", "abc123"]
        )
        assert args.thread == "abc123"

    def test_export_flag(self):
        """--export flag should enable export."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["graph", "run", "graphs/test.yaml", "--export"])
        assert args.export is True

    def test_graph_path_required(self):
        """graph run requires a path argument."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["graph", "run"])


# =============================================================================
# parse_vars helper tests
# =============================================================================


class TestParseVars:
    """Tests for --var parsing helper."""

    def test_parse_single_var(self):
        """Single var should parse to dict."""
        from yamlgraph.cli.graph_commands import parse_vars

        result = parse_vars(["topic=AI"])
        assert result == {"topic": "AI"}

    def test_parse_multiple_vars(self):
        """Multiple vars should parse to dict."""
        from yamlgraph.cli.graph_commands import parse_vars

        result = parse_vars(["topic=AI", "style=casual", "count=5"])
        assert result == {"topic": "AI", "style": "casual", "count": "5"}

    def test_parse_empty_list(self):
        """Empty list returns empty dict."""
        from yamlgraph.cli.graph_commands import parse_vars

        result = parse_vars([])
        assert result == {}

    def test_parse_none_returns_empty(self):
        """None returns empty dict."""
        from yamlgraph.cli.graph_commands import parse_vars

        result = parse_vars(None)
        assert result == {}

    def test_parse_value_with_equals(self):
        """Value containing = should preserve it."""
        from yamlgraph.cli.graph_commands import parse_vars

        result = parse_vars(["equation=a=b+c"])
        assert result == {"equation": "a=b+c"}

    def test_parse_invalid_format_raises(self):
        """Invalid format (no =) should raise ValueError."""
        from yamlgraph.cli.graph_commands import parse_vars

        with pytest.raises(ValueError, match="Invalid"):
            parse_vars(["invalid"])


# =============================================================================
# cmd_graph_run tests
# =============================================================================


class TestCmdGraphRun:
    """Tests for cmd_graph_run function."""

    def test_cmd_graph_run_exists(self):
        """cmd_graph_run function should exist."""
        from yamlgraph.cli.graph_commands import cmd_graph_run

        assert callable(cmd_graph_run)

    def test_graph_not_found_error(self):
        """Should error if graph file doesn't exist."""
        from yamlgraph.cli.graph_commands import cmd_graph_run

        args = argparse.Namespace(
            graph_path="nonexistent.yaml",
            var=[],
            thread=None,
            export=False,
        )

        with pytest.raises(SystemExit):
            cmd_graph_run(args)

    @patch("yamlgraph.graph_loader.load_and_compile")
    def test_invokes_graph_with_vars(self, mock_load):
        """Should invoke graph with parsed vars as initial state."""
        from yamlgraph.cli.graph_commands import cmd_graph_run

        mock_graph = MagicMock()
        mock_app = MagicMock()
        mock_app.invoke.return_value = {"result": "success"}
        mock_graph.compile.return_value = mock_app
        mock_load.return_value = mock_graph

        args = argparse.Namespace(
            graph_path="graphs/yamlgraph.yaml",
            var=["topic=AI", "style=casual"],
            thread=None,
            export=False,
        )

        # Mock Path.exists
        with patch.object(Path, "exists", return_value=True):
            cmd_graph_run(args)

        mock_app.invoke.assert_called_once()
        call_args = mock_app.invoke.call_args[0][0]
        assert call_args["topic"] == "AI"
        assert call_args["style"] == "casual"


# =============================================================================
# cmd_graph_list tests
# =============================================================================


class TestCmdGraphList:
    """Tests for cmd_graph_list function."""

    def test_cmd_graph_list_exists(self):
        """cmd_graph_list function should exist."""
        from yamlgraph.cli.graph_commands import cmd_graph_list

        assert callable(cmd_graph_list)

    @patch("yamlgraph.cli.graph_commands.Path")
    def test_lists_yaml_files(self, mock_path):
        """Should list all .yaml files in graphs/."""
        from yamlgraph.cli.graph_commands import cmd_graph_list

        mock_graphs_dir = MagicMock()
        mock_path.return_value = mock_graphs_dir
        mock_graphs_dir.exists.return_value = True
        mock_graphs_dir.glob.return_value = [
            Path("graphs/yamlgraph.yaml"),
            Path("graphs/router-demo.yaml"),
        ]

        args = argparse.Namespace()

        with patch("builtins.print") as mock_print:
            cmd_graph_list(args)
            # Check it printed something about the graphs
            calls = [str(c) for c in mock_print.call_args_list]
            assert any("yamlgraph" in c for c in calls)


# =============================================================================
# cmd_graph_info tests
# =============================================================================


class TestCmdGraphInfo:
    """Tests for cmd_graph_info function."""

    def test_cmd_graph_info_exists(self):
        """cmd_graph_info function should exist."""
        from yamlgraph.cli.graph_commands import cmd_graph_info

        assert callable(cmd_graph_info)

    def test_info_file_not_found(self):
        """Should error if graph file doesn't exist."""
        from yamlgraph.cli.graph_commands import cmd_graph_info

        args = argparse.Namespace(graph_path="nonexistent.yaml")

        with pytest.raises(SystemExit):
            cmd_graph_info(args)


# =============================================================================
# cmd_graph_validate tests
# =============================================================================


class TestCmdGraphValidate:
    """Tests for cmd_graph_validate function."""

    def test_cmd_graph_validate_exists(self):
        """cmd_graph_validate function should exist."""
        from yamlgraph.cli.graph_commands import cmd_graph_validate

        assert callable(cmd_graph_validate)

    def test_validate_file_not_found(self):
        """Should error if graph file doesn't exist."""
        from yamlgraph.cli.graph_commands import cmd_graph_validate

        args = argparse.Namespace(graph_path="nonexistent.yaml")

        with pytest.raises(SystemExit):
            cmd_graph_validate(args)

    def test_validate_valid_graph(self):
        """Should validate a correct graph without errors."""
        from yamlgraph.cli.graph_commands import cmd_graph_validate

        args = argparse.Namespace(graph_path="graphs/yamlgraph.yaml")

        # Should not raise
        cmd_graph_validate(args)

    def test_validate_subparser_exists(self):
        """graph validate subcommand should exist."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["graph", "validate", "graphs/yamlgraph.yaml"])
        assert args.graph_command == "validate"
        assert args.graph_path == "graphs/yamlgraph.yaml"
