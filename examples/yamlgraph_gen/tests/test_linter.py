"""Tests for linter module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from examples.yamlgraph_gen.tools.linter import lint_graph


class TestLintGraph:
    """Tests for lint_graph function."""

    def test_missing_graph_file(self, tmp_path: Path) -> None:
        """Missing graph file returns error."""
        result = lint_graph(str(tmp_path / "missing.yaml"))

        assert result["valid"] is False
        assert any("not found" in e for e in result["errors"])

    @patch("examples.yamlgraph_gen.tools.linter.subprocess.run")
    def test_lint_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Successful lint returns valid."""
        graph_file = tmp_path / "graph.yaml"
        graph_file.write_text("version: '1.0'")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="OK",
            stderr="",
        )

        result = lint_graph(str(graph_file))

        assert result["valid"] is True
        assert result["errors"] == []
        assert result["output"] == "OK"

    @patch("examples.yamlgraph_gen.tools.linter.subprocess.run")
    def test_lint_failure(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Failed lint returns errors."""
        graph_file = tmp_path / "graph.yaml"
        graph_file.write_text("invalid: graph")

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: missing required field 'version'",
        )

        result = lint_graph(str(graph_file))

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert result["lint_result"]["valid"] is False

    @patch("examples.yamlgraph_gen.tools.linter.subprocess.run")
    def test_lint_command_format(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Lint calls yamlgraph with correct args."""
        graph_file = tmp_path / "graph.yaml"
        graph_file.write_text("version: '1.0'")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        lint_graph(str(graph_file))

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "yamlgraph"
        assert args[1] == "graph"
        assert args[2] == "lint"
        assert str(graph_file) in args[3]
