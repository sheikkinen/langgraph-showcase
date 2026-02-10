"""Tests for subgraph pattern linter validations."""

from pathlib import Path

import pytest

from yamlgraph.linter.patterns.subgraph import (
    check_subgraph_node_requirements,
    check_subgraph_patterns,
)


class TestSubgraphNodeRequirements:
    """Test subgraph node validation."""

    @pytest.mark.req("REQ-YG-003")
    def test_valid_subgraph_with_all_fields(self, tmp_path):
        """Should pass when subgraph has all required fields and file exists."""
        # Create a mock subgraph file
        subgraph_file = tmp_path / "subgraphs" / "test_subgraph.yaml"
        subgraph_file.parent.mkdir(parents=True)
        subgraph_file.write_text("version: '1.0'\nnodes: {}")

        node_config = {
            "type": "subgraph",
            "graph": "subgraphs/test_subgraph.yaml",
            "input_mapping": {"input": "sub_input"},
            "output_mapping": {"sub_output": "output"},
        }
        graph_path = tmp_path / "test_graph.yaml"

        issues = check_subgraph_node_requirements(
            "test_node", node_config, graph_path, tmp_path
        )
        assert len(issues) == 0

    @pytest.mark.req("REQ-YG-003")
    def test_subgraph_missing_graph_field(self):
        """Should error when subgraph node missing 'graph' field."""
        node_config = {
            "type": "subgraph",
            "input_mapping": {"input": "sub_input"},
            # Missing graph field
        }
        graph_path = Path("/fake/path.yaml")

        issues = check_subgraph_node_requirements("test_node", node_config, graph_path)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].code == "E501"
        assert "missing required 'graph' field" in issues[0].message

    @pytest.mark.req("REQ-YG-003")
    def test_subgraph_file_not_found(self, tmp_path):
        """Should error when subgraph file doesn't exist."""
        node_config = {"type": "subgraph", "graph": "nonexistent.yaml"}
        graph_path = tmp_path / "test_graph.yaml"

        issues = check_subgraph_node_requirements(
            "test_node", node_config, graph_path, tmp_path
        )
        assert len(issues) == 3  # E502 + W501 + W502
        error_issues = [i for i in issues if i.severity == "error"]
        assert len(error_issues) == 1
        assert error_issues[0].code == "E502"
        assert "references non-existent graph file" in error_issues[0].message

    @pytest.mark.req("REQ-YG-003")
    def test_subgraph_file_found_relative_to_graph_dir(self, tmp_path):
        """Should find subgraph file relative to graph directory."""
        # Create graph in subdirectory
        graph_dir = tmp_path / "graphs"
        graph_dir.mkdir()
        graph_file = graph_dir / "main.yaml"

        # Create subgraph in same directory
        subgraph_file = graph_dir / "subgraph.yaml"
        subgraph_file.write_text("version: '1.0'\nnodes: {}")

        node_config = {
            "type": "subgraph",
            "graph": "subgraph.yaml",  # Relative to graph file
        }

        issues = check_subgraph_node_requirements(
            "test_node", node_config, graph_file, tmp_path
        )
        assert len(issues) == 2  # W501 + W502 (file exists, but no mappings)
        warning_codes = {i.code for i in issues}
        assert warning_codes == {"W501", "W502"}

    @pytest.mark.req("REQ-YG-003")
    def test_subgraph_missing_input_mapping_warning(self, tmp_path):
        """Should warn when subgraph node missing input_mapping."""
        # Create subgraph file
        subgraph_file = tmp_path / "subgraph.yaml"
        subgraph_file.write_text("version: '1.0'\nnodes: {}")

        node_config = {
            "type": "subgraph",
            "graph": "subgraph.yaml",
            "output_mapping": {"sub_output": "output"},
            # Missing input_mapping
        }
        graph_path = tmp_path / "test_graph.yaml"

        issues = check_subgraph_node_requirements(
            "test_node", node_config, graph_path, tmp_path
        )
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert issues[0].code == "W501"
        assert "missing input_mapping" in issues[0].message

    @pytest.mark.req("REQ-YG-003")
    def test_subgraph_missing_output_mapping_warning(self, tmp_path):
        """Should warn when subgraph node missing output_mapping."""
        # Create subgraph file
        subgraph_file = tmp_path / "subgraph.yaml"
        subgraph_file.write_text("version: '1.0'\nnodes: {}")

        node_config = {
            "type": "subgraph",
            "graph": "subgraph.yaml",
            "input_mapping": {"input": "sub_input"},
            # Missing output_mapping
        }
        graph_path = tmp_path / "test_graph.yaml"

        issues = check_subgraph_node_requirements(
            "test_node", node_config, graph_path, tmp_path
        )
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert issues[0].code == "W502"
        assert "missing output_mapping" in issues[0].message

    @pytest.mark.req("REQ-YG-003")
    def test_subgraph_missing_both_mappings_warnings(self, tmp_path):
        """Should warn for both missing mappings."""
        # Create subgraph file
        subgraph_file = tmp_path / "subgraph.yaml"
        subgraph_file.write_text("version: '1.0'\nnodes: {}")

        node_config = {
            "type": "subgraph",
            "graph": "subgraph.yaml",
            # Missing both mappings
        }
        graph_path = tmp_path / "test_graph.yaml"

        issues = check_subgraph_node_requirements(
            "test_node", node_config, graph_path, tmp_path
        )
        assert len(issues) == 2
        codes = {issue.code for issue in issues}
        assert codes == {"W501", "W502"}

    @pytest.mark.req("REQ-YG-003")
    def test_subgraph_minimal_valid_config(self, tmp_path):
        """Should pass with minimal valid config (just graph field)."""
        # Create subgraph file
        subgraph_file = tmp_path / "subgraph.yaml"
        subgraph_file.write_text("version: '1.0'\nnodes: {}")

        node_config = {
            "type": "subgraph",
            "graph": "subgraph.yaml",
            # No mappings - should warn
        }
        graph_path = tmp_path / "test_graph.yaml"

        issues = check_subgraph_node_requirements(
            "test_node", node_config, graph_path, tmp_path
        )
        # Should have warnings for missing mappings
        assert len(issues) == 2  # W501 + W502
        warning_codes = {i.code for i in issues}
        assert warning_codes == {"W501", "W502"}


class TestSubgraphPatternsIntegration:
    """Test subgraph pattern validation integration."""

    @pytest.mark.req("REQ-YG-003")
    def test_valid_subgraph_graph(self, tmp_path):
        """Should pass valid subgraph graph."""
        # Create subgraph file
        subgraph_dir = tmp_path / "subgraphs"
        subgraph_dir.mkdir()
        subgraph_file = subgraph_dir / "summarizer.yaml"
        subgraph_file.write_text("""
version: "1.0"
state:
  input_text: str
  output_summary: str
nodes:
  summarize:
    type: llm
    prompt: summarize/prompt
    state_key: output_summary
edges:
  - from: START
    to: summarize
  - from: summarize
    to: END
""")

        graph_content = """
version: "1.0"
state:
  raw_text: str
  summary: str
nodes:
  summarize:
    type: subgraph
    graph: subgraphs/summarizer.yaml
    input_mapping:
      raw_text: input_text
    output_mapping:
      summary: output_summary
edges:
  - from: START
    to: summarize
  - from: summarize
    to: END
"""
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text(graph_content)

        issues = check_subgraph_patterns(graph_file, tmp_path)
        assert len(issues) == 0

    @pytest.mark.req("REQ-YG-003")
    def test_invalid_subgraph_graph_missing_graph_field(self, tmp_path):
        """Should error when subgraph node missing graph field."""
        graph_content = """
version: "1.0"
nodes:
  summarize:
    type: subgraph
    input_mapping:
      raw_text: input_text
edges:
  - from: START
    to: summarize
"""
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text(graph_content)

        issues = check_subgraph_patterns(graph_file, tmp_path)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].code == "E501"

    @pytest.mark.req("REQ-YG-003")
    def test_invalid_subgraph_graph_file_not_found(self, tmp_path):
        """Should error when subgraph file doesn't exist."""
        graph_content = """
version: "1.0"
nodes:
  summarize:
    type: subgraph
    graph: nonexistent.yaml
edges:
  - from: START
    to: summarize
"""
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text(graph_content)

        issues = check_subgraph_patterns(graph_file, tmp_path)
        assert len(issues) == 3  # E502 + W501 + W502
        error_issues = [i for i in issues if i.severity == "error"]
        assert len(error_issues) == 1
        assert error_issues[0].code == "E502"

    @pytest.mark.req("REQ-YG-003")
    def test_subgraph_graph_missing_mappings_warnings(self, tmp_path):
        """Should warn when subgraph missing mappings."""
        # Create subgraph file
        subgraph_file = tmp_path / "subgraph.yaml"
        subgraph_file.write_text("version: '1.0'\nnodes: {}")

        graph_content = """
version: "1.0"
nodes:
  summarize:
    type: subgraph
    graph: subgraph.yaml
edges:
  - from: START
    to: summarize
"""
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text(graph_content)

        issues = check_subgraph_patterns(graph_file, tmp_path)
        assert len(issues) == 2
        codes = {issue.code for issue in issues}
        assert codes == {"W501", "W502"}

    @pytest.mark.req("REQ-YG-003")
    def test_mixed_nodes_validates_only_subgraphs(self, tmp_path):
        """Should only validate subgraph nodes, ignore others."""
        # Create subgraph file
        subgraph_file = tmp_path / "subgraph.yaml"
        subgraph_file.write_text("version: '1.0'\nnodes: {}")

        graph_content = """
version: "1.0"
nodes:
  prepare:
    type: llm
    prompt: prepare/prompt
  summarize:
    type: subgraph
    graph: subgraph.yaml
    input_mapping: {}
    output_mapping: {}
  finish:
    type: llm
    prompt: finish/prompt
edges:
  - from: START
    to: prepare
  - from: prepare
    to: summarize
  - from: summarize
    to: finish
  - from: finish
    to: END
"""
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text(graph_content)

        issues = check_subgraph_patterns(graph_file, tmp_path)
        # Empty mappings are still considered "present" but empty, so no warnings
        assert len(issues) == 0
