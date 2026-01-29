"""Integration tests for CLI commands.

Tests actual command execution with real (but minimal) operations.
"""

import subprocess
import sys
from pathlib import Path


class TestGraphCommands:
    """Integration tests for graph subcommands."""

    def test_graph_validate_valid_graph(self):
        """'graph validate' succeeds for valid graph."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "yamlgraph.cli",
                "graph",
                "validate",
                "examples/demos/yamlgraph/graph.yaml",
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
            "examples/demos/yamlgraph/graph.yaml",
            "examples/demos/router/graph.yaml",
            "examples/demos/reflexion/graph.yaml",
            "examples/demos/git-report/graph.yaml",
            "examples/demos/memory/graph.yaml",
            "examples/demos/map/graph.yaml",
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
                "examples/demos/yamlgraph/graph.yaml",
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
                "examples/demos/yamlgraph/graph.yaml",
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
                "examples/demos/router/graph.yaml",
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
                "examples/demos/yamlgraph/graph.yaml",
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
        assert "schema" in result.stdout

    def test_graph_help(self):
        """'graph --help' shows subcommands."""
        result = subprocess.run(
            [sys.executable, "-m", "yamlgraph.cli", "graph", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "run" in result.stdout
        assert "validate" in result.stdout
        assert "codegen" in result.stdout
