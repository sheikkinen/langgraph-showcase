"""Tests for runner module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from examples.yamlgraph_gen.tools.runner import (
    run_graph,
    run_graph_with_test_inputs,
)


class TestRunGraph:
    """Tests for run_graph function."""

    def test_missing_graph_file(self, tmp_path: Path) -> None:
        """Missing graph file returns error."""
        result = run_graph(str(tmp_path / "missing.yaml"))

        assert result["valid"] is False
        assert any("not found" in e for e in result["errors"])

    @patch("examples.yamlgraph_gen.tools.runner.subprocess.run")
    def test_run_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Successful run returns valid."""
        graph_file = tmp_path / "graph.yaml"
        graph_file.write_text("version: '1.0'")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Output: success",
            stderr="",
        )

        result = run_graph(str(graph_file))

        assert result["valid"] is True
        assert result["errors"] == []
        assert "success" in result["stdout"]

    @patch("examples.yamlgraph_gen.tools.runner.subprocess.run")
    def test_run_with_variables(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Run with variables passes them to command."""
        graph_file = tmp_path / "graph.yaml"
        graph_file.write_text("version: '1.0'")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        run_graph(str(graph_file), {"topic": "test", "count": "5"})

        args = mock_run.call_args[0][0]
        assert "--var" in args
        assert "topic=test" in args
        assert "count=5" in args

    @patch("examples.yamlgraph_gen.tools.runner.subprocess.run")
    def test_run_failure(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Failed run returns errors."""
        graph_file = tmp_path / "graph.yaml"
        graph_file.write_text("version: '1.0'")

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="KeyError: 'missing_key'",
        )

        result = run_graph(str(graph_file))

        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestRunGraphWithTestInputs:
    """Tests for run_graph_with_test_inputs function."""

    @patch("examples.yamlgraph_gen.tools.runner.run_graph")
    def test_router_pattern_inputs(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Router pattern uses message input."""
        graph_file = tmp_path / "graph.yaml"
        graph_file.write_text("version: '1.0'")

        mock_run.return_value = {"valid": True}

        run_graph_with_test_inputs(str(graph_file), "router")

        mock_run.assert_called_once()
        variables = mock_run.call_args[0][1]
        assert "message" in variables

    @patch("examples.yamlgraph_gen.tools.runner.run_graph")
    def test_map_pattern_inputs(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Map pattern uses items input."""
        graph_file = tmp_path / "graph.yaml"
        graph_file.write_text("version: '1.0'")

        mock_run.return_value = {"valid": True}

        run_graph_with_test_inputs(str(graph_file), "map")

        variables = mock_run.call_args[0][1]
        assert "items" in variables

    @patch("examples.yamlgraph_gen.tools.runner.run_graph")
    def test_unknown_pattern_empty_inputs(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Unknown pattern uses empty inputs."""
        graph_file = tmp_path / "graph.yaml"
        graph_file.write_text("version: '1.0'")

        mock_run.return_value = {"valid": True}

        run_graph_with_test_inputs(str(graph_file), "unknown")

        variables = mock_run.call_args[0][1]
        assert variables == {}
