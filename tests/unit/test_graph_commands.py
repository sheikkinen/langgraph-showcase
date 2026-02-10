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

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_graph_subparser_exists(self):
        """graph subparser should be configured."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        # Parse with graph command
        args = parser.parse_args(
            ["graph", "info", "examples/demos/yamlgraph/graph.yaml"]
        )
        assert args.command == "graph"

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_graph_run_subcommand_exists(self):
        """graph run subcommand should exist."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["graph", "run", "graphs/yamlgraph.yaml", "--var", "topic=AI"]
        )
        assert args.graph_command == "run"
        assert args.graph_path == "graphs/yamlgraph.yaml"

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
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

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_var_single_value(self):
        """--var key=value should parse correctly."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["graph", "run", "graphs/test.yaml", "--var", "topic=AI"]
        )
        assert args.var == ["topic=AI"]

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
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

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_thread_argument(self):
        """--thread should set thread ID."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["graph", "run", "graphs/test.yaml", "--thread", "abc123"]
        )
        assert args.thread == "abc123"

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_export_flag(self):
        """--export flag should enable export."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["graph", "run", "graphs/test.yaml", "--export"])
        assert args.export is True

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
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

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_parse_single_var(self):
        """Single var should parse to dict."""
        from yamlgraph.cli.graph_commands import parse_vars

        result = parse_vars(["topic=AI"])
        assert result == {"topic": "AI"}

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_parse_multiple_vars(self):
        """Multiple vars should parse to dict."""
        from yamlgraph.cli.graph_commands import parse_vars

        result = parse_vars(["topic=AI", "style=casual", "count=5"])
        assert result == {"topic": "AI", "style": "casual", "count": "5"}

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_parse_empty_list(self):
        """Empty list returns empty dict."""
        from yamlgraph.cli.graph_commands import parse_vars

        result = parse_vars([])
        assert result == {}

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_parse_none_returns_empty(self):
        """None returns empty dict."""
        from yamlgraph.cli.graph_commands import parse_vars

        result = parse_vars(None)
        assert result == {}

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_parse_value_with_equals(self):
        """Value containing = should preserve it."""
        from yamlgraph.cli.graph_commands import parse_vars

        result = parse_vars(["equation=a=b+c"])
        assert result == {"equation": "a=b+c"}

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
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

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_cmd_graph_run_exists(self):
        """cmd_graph_run function should exist."""
        from yamlgraph.cli.graph_commands import cmd_graph_run

        assert callable(cmd_graph_run)

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
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

    @patch("yamlgraph.graph_loader.get_checkpointer_for_graph")
    @patch("yamlgraph.graph_loader.compile_graph")
    @patch("yamlgraph.graph_loader.load_graph_config")
    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_invokes_graph_with_vars(self, mock_load_config, mock_compile, mock_get_cp):
        """Should invoke graph with parsed vars as initial state."""
        from yamlgraph.cli.graph_commands import cmd_graph_run

        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_graph = MagicMock()
        mock_compile.return_value = mock_graph

        mock_get_cp.return_value = None  # No checkpointer

        mock_app = MagicMock()
        mock_app.invoke.return_value = {"result": "success"}
        mock_graph.compile.return_value = mock_app

        args = argparse.Namespace(
            graph_path="examples/demos/yamlgraph/graph.yaml",
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

    @patch("yamlgraph.graph_loader.get_checkpointer_for_graph")
    @patch("yamlgraph.graph_loader.compile_graph")
    @patch("yamlgraph.graph_loader.load_graph_config")
    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_uses_checkpointer_from_graph(
        self, mock_load_config, mock_compile, mock_get_cp
    ):
        """Should use checkpointer from graph config when --thread provided."""
        from yamlgraph.cli.graph_commands import cmd_graph_run

        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_graph = MagicMock()
        mock_compile.return_value = mock_graph

        mock_checkpointer = MagicMock()
        mock_get_cp.return_value = mock_checkpointer

        mock_app = MagicMock()
        mock_app.invoke.return_value = {"result": "success"}
        mock_graph.compile.return_value = mock_app

        args = argparse.Namespace(
            graph_path="graphs/interview.yaml",
            var=["input=start"],
            thread="session-123",
            export=False,
        )

        with patch.object(Path, "exists", return_value=True):
            cmd_graph_run(args)

        # Verify checkpointer was retrieved and used
        mock_get_cp.assert_called_once_with(mock_config)
        mock_graph.compile.assert_called_once_with(checkpointer=mock_checkpointer)

        # Verify thread_id was passed in config
        call_kwargs = mock_app.invoke.call_args[1]
        assert call_kwargs["config"]["configurable"]["thread_id"] == "session-123"

    @patch("yamlgraph.graph_loader.get_checkpointer_for_graph")
    @patch("yamlgraph.graph_loader.compile_graph")
    @patch("yamlgraph.graph_loader.load_graph_config")
    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_uses_checkpointer_even_without_thread(
        self, mock_load_config, mock_compile, mock_get_cp
    ):
        """Should use checkpointer from graph config even without --thread."""
        from yamlgraph.cli.graph_commands import cmd_graph_run

        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_graph = MagicMock()
        mock_compile.return_value = mock_graph

        mock_checkpointer = MagicMock()
        mock_get_cp.return_value = mock_checkpointer

        mock_app = MagicMock()
        mock_app.invoke.return_value = {"result": "success"}
        mock_graph.compile.return_value = mock_app

        args = argparse.Namespace(
            graph_path="graphs/interview.yaml",
            var=["input=start"],
            thread=None,
            export=False,
        )

        with patch.object(Path, "exists", return_value=True):
            cmd_graph_run(args)

        # Verify checkpointer was retrieved and used
        mock_get_cp.assert_called_once_with(mock_config)
        mock_graph.compile.assert_called_once_with(checkpointer=mock_checkpointer)


# =============================================================================
# cmd_graph_info tests
# =============================================================================


class TestCmdGraphInfo:
    """Tests for cmd_graph_info function."""

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_cmd_graph_info_exists(self):
        """cmd_graph_info function should exist."""
        from yamlgraph.cli.graph_commands import cmd_graph_info

        assert callable(cmd_graph_info)

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
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

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_cmd_graph_validate_exists(self):
        """cmd_graph_validate function should exist."""
        from yamlgraph.cli.graph_commands import cmd_graph_validate

        assert callable(cmd_graph_validate)

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_validate_file_not_found(self):
        """Should error if graph file doesn't exist."""
        from yamlgraph.cli.graph_commands import cmd_graph_validate

        args = argparse.Namespace(graph_path="nonexistent.yaml")

        with pytest.raises(SystemExit):
            cmd_graph_validate(args)

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_validate_valid_graph(self):
        """Should validate a correct graph without errors."""
        from yamlgraph.cli.graph_commands import cmd_graph_validate

        args = argparse.Namespace(graph_path="examples/demos/yamlgraph/graph.yaml")

        # Should not raise
        cmd_graph_validate(args)

    @pytest.mark.req("REQ-YG-032", "REQ-YG-036")
    def test_validate_subparser_exists(self):
        """graph validate subcommand should exist."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["graph", "validate", "examples/demos/yamlgraph/graph.yaml"]
        )
        assert args.graph_command == "validate"
        assert args.graph_path == "examples/demos/yamlgraph/graph.yaml"


# =============================================================================
# --share-trace flag and _print_trace_url (FR-022)
# =============================================================================


class TestShareTraceFlag:
    """Tests for --share-trace CLI flag and trace URL printing."""

    @pytest.mark.req("REQ-YG-047")
    def test_share_trace_flag_parsed(self):
        """--share-trace flag should be recognized."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["graph", "run", "graphs/test.yaml", "--share-trace"])
        assert args.share_trace is True

    @pytest.mark.req("REQ-YG-047")
    def test_share_trace_flag_default_false(self):
        """--share-trace should default to False."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["graph", "run", "graphs/test.yaml"])
        assert args.share_trace is False

    @pytest.mark.req("REQ-YG-047")
    def test_print_trace_url_authenticated(self, capsys):
        """_print_trace_url should print authenticated URL when share=False."""
        from yamlgraph.cli.graph_commands import _print_trace_url

        tracer = MagicMock()
        with patch(
            "yamlgraph.utils.tracing.get_trace_url",
            return_value="https://smith.langchain.com/o/xxx/r/yyy",
        ):
            _print_trace_url(tracer, share=False)

        captured = capsys.readouterr()
        assert "🔗 Trace: https://smith.langchain.com/o/xxx/r/yyy" in captured.out

    @pytest.mark.req("REQ-YG-047")
    def test_print_trace_url_shared(self, capsys):
        """_print_trace_url should print public URL when share=True."""
        from yamlgraph.cli.graph_commands import _print_trace_url

        tracer = MagicMock()
        with patch(
            "yamlgraph.utils.tracing.share_trace",
            return_value="https://smith.langchain.com/public/xxx/r/yyy",
        ):
            _print_trace_url(tracer, share=True)

        captured = capsys.readouterr()
        assert (
            "🔗 Trace (public): https://smith.langchain.com/public/xxx/r/yyy"
            in captured.out
        )

    @pytest.mark.req("REQ-YG-047")
    def test_print_trace_url_no_tracer(self, capsys):
        """_print_trace_url should print nothing when tracer is None."""
        from yamlgraph.cli.graph_commands import _print_trace_url

        _print_trace_url(None, share=False)
        captured = capsys.readouterr()
        assert captured.out == ""

    @pytest.mark.req("REQ-YG-047")
    def test_print_trace_url_no_url(self, capsys):
        """_print_trace_url should print nothing when URL is None."""
        from yamlgraph.cli.graph_commands import _print_trace_url

        tracer = MagicMock()
        with patch("yamlgraph.utils.tracing.get_trace_url", return_value=None):
            _print_trace_url(tracer, share=False)

        captured = capsys.readouterr()
        assert captured.out == ""
