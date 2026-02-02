"""Integration tests for data_files feature in graph_loader.

TDD: Tests written BEFORE integration implementation.
"""

from pathlib import Path

import pytest

from yamlgraph.graph_loader import load_graph_config


class TestDataFilesInGraphLoader:
    """Test data_files integration in graph_loader."""

    def test_graph_config_loads_data_files(self, tmp_path: Path) -> None:
        """GraphConfig.data property contains loaded data files."""
        # Create data file
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text("fields:\n  - name\n  - age")

        # Create graph file with data_files
        graph_file = tmp_path / "graph.yaml"
        graph_file.write_text("""
version: "1.0"
name: test-graph
data_files:
  schema: schema.yaml
nodes:
  start:
    type: passthrough
edges:
  - from: START
    to: start
  - from: start
    to: END
""")

        config = load_graph_config(graph_file)

        assert hasattr(config, "data")
        assert config.data == {"schema": {"fields": ["name", "age"]}}

    def test_graph_config_empty_data_files(self, tmp_path: Path) -> None:
        """Graph without data_files has empty data dict."""
        graph_file = tmp_path / "graph.yaml"
        graph_file.write_text("""
version: "1.0"
name: test-graph
nodes:
  start:
    type: passthrough
edges:
  - from: START
    to: start
  - from: start
    to: END
""")

        config = load_graph_config(graph_file)

        assert hasattr(config, "data")
        assert config.data == {}

    def test_data_files_path_relative_to_graph(self, tmp_path: Path) -> None:
        """Data files are resolved relative to graph file, not cwd."""
        # Create subdirectory for graph
        subdir = tmp_path / "graphs"
        subdir.mkdir()

        # Create data file next to graph
        schema_file = subdir / "schema.yaml"
        schema_file.write_text("version: 2")

        graph_file = subdir / "graph.yaml"
        graph_file.write_text("""
version: "1.0"
name: test-graph
data_files:
  schema: schema.yaml
nodes:
  start:
    type: passthrough
edges:
  - from: START
    to: start
  - from: start
    to: END
""")

        # Load from different cwd
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)  # Not in graphs/
            config = load_graph_config(subdir / "graph.yaml")
            assert config.data == {"schema": {"version": 2}}
        finally:
            os.chdir(original_cwd)

    def test_data_files_missing_raises_error(self, tmp_path: Path) -> None:
        """Missing data file raises error during graph load."""
        graph_file = tmp_path / "graph.yaml"
        graph_file.write_text("""
version: "1.0"
name: test-graph
data_files:
  schema: nonexistent.yaml
nodes:
  start:
    type: passthrough
edges:
  - from: START
    to: start
  - from: start
    to: END
""")

        from yamlgraph.data_loader import DataFileError

        with pytest.raises(DataFileError, match="not found"):
            load_graph_config(graph_file)

    def test_data_files_path_traversal_blocked(self, tmp_path: Path) -> None:
        """Path traversal attempts are blocked."""
        # Create a file outside the graph directory
        outside_file = tmp_path / "secret.yaml"
        outside_file.write_text("secret: value")

        # Create subdirectory for graph
        subdir = tmp_path / "graphs"
        subdir.mkdir()

        graph_file = subdir / "graph.yaml"
        graph_file.write_text("""
version: "1.0"
name: test-graph
data_files:
  secret: ../secret.yaml
nodes:
  start:
    type: passthrough
edges:
  - from: START
    to: start
  - from: start
    to: END
""")

        from yamlgraph.data_loader import DataFileError

        with pytest.raises(DataFileError, match="escapes graph directory"):
            load_graph_config(graph_file)


class TestDataFilesSchemaValidation:
    """Test data_files in GraphConfigSchema validation."""

    def test_schema_accepts_data_files(self) -> None:
        """GraphConfigSchema accepts data_files field."""
        from yamlgraph.models.graph_schema import GraphConfigSchema

        config = {
            "nodes": {"start": {"type": "passthrough"}},
            "edges": [{"from": "START", "to": "start"}, {"from": "start", "to": "END"}],
            "data_files": {"schema": "schema.yaml", "config": "config.yaml"},
        }

        # Should not raise
        schema = GraphConfigSchema.model_validate(config)
        assert schema.data_files == {"schema": "schema.yaml", "config": "config.yaml"}

    def test_schema_data_files_optional(self) -> None:
        """data_files is optional in schema."""
        from yamlgraph.models.graph_schema import GraphConfigSchema

        config = {
            "nodes": {"start": {"type": "passthrough"}},
            "edges": [{"from": "START", "to": "start"}, {"from": "start", "to": "END"}],
        }

        schema = GraphConfigSchema.model_validate(config)
        assert schema.data_files == {}

    def test_schema_rejects_invalid_data_files_type(self) -> None:
        """data_files must be a dict."""
        from pydantic import ValidationError

        from yamlgraph.models.graph_schema import GraphConfigSchema

        config = {
            "nodes": {"start": {"type": "passthrough"}},
            "edges": [{"from": "START", "to": "start"}, {"from": "start", "to": "END"}],
            "data_files": ["schema.yaml"],  # Should be dict
        }

        with pytest.raises(ValidationError):
            GraphConfigSchema.model_validate(config)
