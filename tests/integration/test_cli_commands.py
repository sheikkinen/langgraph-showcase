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
            [sys.executable, "-m", "showcase.cli", "graph", "list"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        assert "showcase.yaml" in result.stdout
        assert "Available graphs" in result.stdout

    def test_graph_validate_valid_graph(self):
        """'graph validate' succeeds for valid graph."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "showcase.cli",
                "graph",
                "validate",
                "graphs/showcase.yaml",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        assert "VALID" in result.stdout

    def test_graph_validate_invalid_path(self):
        """'graph validate' fails for missing file."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "showcase.cli",
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
                "showcase.cli",
                "graph",
                "info",
                "graphs/showcase.yaml",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        assert "Nodes:" in result.stdout or "nodes" in result.stdout.lower()


class TestListRunsCommand:
    """Integration tests for list-runs command."""

    def test_list_runs_with_empty_db(self, tmp_path, monkeypatch):
        """'list-runs' handles empty database gracefully."""
        # Use temp db
        monkeypatch.setenv("SHOWCASE_DB_PATH", str(tmp_path / "test.db"))

        result = subprocess.run(
            [sys.executable, "-m", "showcase.cli", "list-runs"],
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


class TestMermaidCommand:
    """Integration tests for mermaid diagram generation."""

    def test_mermaid_generates_diagram(self):
        """'mermaid' command generates valid mermaid syntax."""
        result = subprocess.run(
            [sys.executable, "-m", "showcase.cli", "mermaid"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        # Mermaid diagrams start with graph or flowchart
        assert (
            "graph" in result.stdout.lower()
            or "flowchart" in result.stdout.lower()
            or "stateDiagram" in result.stdout
        )


class TestHelpOutput:
    """Test help messages work correctly."""

    def test_main_help(self):
        """Main --help shows available commands."""
        result = subprocess.run(
            [sys.executable, "-m", "showcase.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "graph" in result.stdout
        assert "list-runs" in result.stdout

    def test_graph_help(self):
        """'graph --help' shows subcommands."""
        result = subprocess.run(
            [sys.executable, "-m", "showcase.cli", "graph", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "run" in result.stdout
        assert "list" in result.stdout
        assert "validate" in result.stdout
