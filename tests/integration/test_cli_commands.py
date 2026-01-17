"""Integration tests for CLI commands.

Tests actual command execution with real (but minimal) operations.
"""

import subprocess
import sys
from pathlib import Path


class TestGraphCommands:
    """Integration tests for graph subcommands."""

    def test_graph_list_returns_graphs(self):
        """'graph list' shows available graphs."""
        result = subprocess.run(
            [sys.executable, "-m", "yamlgraph.cli", "graph", "list"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        assert "yamlgraph.yaml" in result.stdout
        assert "Available graphs" in result.stdout

    def test_graph_list_shows_all_demos(self):
        """'graph list' shows all demo graphs."""
        result = subprocess.run(
            [sys.executable, "-m", "yamlgraph.cli", "graph", "list"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        # Should list all main demo graphs
        assert "router-demo.yaml" in result.stdout
        assert "reflexion-demo.yaml" in result.stdout
        assert "git-report.yaml" in result.stdout

    def test_graph_validate_valid_graph(self):
        """'graph validate' succeeds for valid graph."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "yamlgraph.cli",
                "graph",
                "validate",
                "graphs/yamlgraph.yaml",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        assert "VALID" in result.stdout

    def test_graph_validate_all_demos(self):
        """'graph validate' succeeds for all demo graphs."""
        demos = [
            "graphs/yamlgraph.yaml",
            "graphs/router-demo.yaml",
            "graphs/reflexion-demo.yaml",
            "graphs/git-report.yaml",
            "graphs/memory-demo.yaml",
            "graphs/map-demo.yaml",
        ]
        for demo in demos:
            result = subprocess.run(
                [sys.executable, "-m", "yamlgraph.cli", "graph", "validate", demo],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent,
            )
            assert result.returncode == 0, f"Failed to validate {demo}: {result.stderr}"

    def test_graph_validate_invalid_path(self):
        """'graph validate' fails for missing file."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "yamlgraph.cli",
                "graph",
                "validate",
                "nonexistent.yaml",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode != 0

    def test_graph_info_shows_nodes(self):
        """'graph info' shows node details."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "yamlgraph.cli",
                "graph",
                "info",
                "graphs/yamlgraph.yaml",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        assert "Nodes:" in result.stdout or "nodes" in result.stdout.lower()

    def test_graph_info_shows_edges(self):
        """'graph info' shows edge details."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "yamlgraph.cli",
                "graph",
                "info",
                "graphs/yamlgraph.yaml",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        assert "Edges:" in result.stdout or "edges" in result.stdout.lower()

    def test_graph_info_router_demo(self):
        """'graph info' shows router-demo structure."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "yamlgraph.cli",
                "graph",
                "info",
                "graphs/router-demo.yaml",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        assert "classify" in result.stdout
        assert "router" in result.stdout.lower()

    def test_graph_run_nonexistent_file_shows_error(self):
        """'graph run' with nonexistent file shows error."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "yamlgraph.cli",
                "graph",
                "run",
                "graphs/does-not-exist.yaml",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        # Should fail with file not found
        assert result.returncode != 0
        assert (
            "not found" in result.stdout.lower() + result.stderr.lower()
            or "Error" in result.stdout + result.stderr
        )

    def test_graph_run_invalid_var_format(self):
        """'graph run' with invalid --var format shows error."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "yamlgraph.cli",
                "graph",
                "run",
                "graphs/yamlgraph.yaml",
                "--var",
                "invalid_no_equals",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode != 0
        assert (
            "Invalid" in result.stdout + result.stderr
            or "key=value" in result.stdout + result.stderr
        )


class TestListRunsCommand:
    """Integration tests for list-runs command."""

    def test_list_runs_with_empty_db(self, tmp_path, monkeypatch):
        """'list-runs' handles empty database gracefully."""
        # Use temp db
        monkeypatch.setenv("SHOWCASE_DB_PATH", str(tmp_path / "test.db"))

        result = subprocess.run(
            [sys.executable, "-m", "yamlgraph.cli", "list-runs"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
            env={
                **subprocess.os.environ,
                "SHOWCASE_DB_PATH": str(tmp_path / "test.db"),
            },
        )
        # Should succeed even with no runs
        assert result.returncode == 0
        assert "No runs found" in result.stdout or "runs" in result.stdout.lower()


class TestHelpOutput:
    """Test help messages work correctly."""

    def test_main_help(self):
        """Main --help shows available commands."""
        result = subprocess.run(
            [sys.executable, "-m", "yamlgraph.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "graph" in result.stdout
        assert "list-runs" in result.stdout

    def test_graph_help(self):
        """'graph --help' shows subcommands."""
        result = subprocess.run(
            [sys.executable, "-m", "yamlgraph.cli", "graph", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "run" in result.stdout
        assert "list" in result.stdout
        assert "validate" in result.stdout
