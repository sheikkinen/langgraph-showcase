"""Integration tests for yamlgraph-generator."""

from pathlib import Path

import yaml

from examples.yamlgraph_gen.tools.file_ops import write_generated_files
from examples.yamlgraph_gen.tools.prompt_validator import validate_prompt_directory
from examples.yamlgraph_gen.tools.snippet_loader import (
    load_snippet,
    load_snippets_for_patterns,
)


class TestSnippetToGeneratedFlow:
    """Integration tests for snippet loading to file generation."""

    def test_load_pattern_and_write(self, tmp_path: Path) -> None:
        """Load a pattern snippet and write generated files."""
        # Load router pattern snippets
        result = load_snippets_for_patterns(["router"])
        snippets = result["snippet_contents"]

        # Verify we got snippets
        assert len(snippets) > 0

        # Create a minimal graph and prompts
        graph_content = """
version: "1.0"
name: test-router
description: Test router pipeline

nodes:
  classify:
    type: router
    prompt: prompts/classify.yaml

edges:
  - from: START
    to: classify
  - from: classify
    to: END
"""

        prompts = [
            {
                "filename": "classify.yaml",
                "content": "system: Classify input.\nuser: Classify {input}",
            }
        ]

        # Write files
        write_result = write_generated_files(str(tmp_path), graph_content, prompts)

        assert write_result["status"] == "success"
        assert (tmp_path / "graph.yaml").exists()
        assert (tmp_path / "prompts" / "classify.yaml").exists()

    def test_generated_prompts_validate(self, tmp_path: Path) -> None:
        """Generated prompt files should pass validation."""
        prompts = [
            {
                "filename": "node1.yaml",
                "content": "system: You are helpful.\nuser: Do {task}",
            },
            {
                "filename": "node2.yaml",
                "content": """
system: Process items.
user: Process {item}
schema:
  name: Result
  fields:
    output:
      type: str
      description: The result
""",
            },
        ]

        write_generated_files(str(tmp_path), "version: '1.0'", prompts)

        result = validate_prompt_directory(str(tmp_path / "prompts"))

        assert result["valid"] is True


class TestSnippetStructure:
    """Tests verifying snippet YAML structure."""

    def test_pattern_snippets_have_nodes_and_edges(self) -> None:
        """Pattern snippets should have both nodes and edges."""
        pattern = load_snippet("patterns/classify-then-process")
        data = pattern["data"]

        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) > 0
        assert len(data["edges"]) > 0

    def test_node_snippets_have_node_key(self) -> None:
        """Node snippets should have node definition."""
        node = load_snippet("nodes/llm-basic")
        data = node["data"]

        assert "node" in data or "description" in data

    def test_scaffold_snippets_valid_yaml(self) -> None:
        """Scaffold snippets should be valid YAML."""
        scaffold = load_snippet("scaffolds/graph-header")
        data = scaffold["data"]

        assert "version" in data
        assert "name" in data or "{graph_name}" in scaffold["content"]


class TestGeneratedGraphStructure:
    """Tests for generated graph YAML structure."""

    def test_generated_graph_is_valid_yaml(self, tmp_path: Path) -> None:
        """Generated graph should be valid YAML."""
        graph_content = """
version: "1.0"
name: test
description: A test graph

defaults:
  provider: anthropic

state:
  input: str
  output: any

nodes:
  process:
    type: llm
    prompt: prompts/process.yaml
    state_key: output

edges:
  - from: START
    to: process
  - from: process
    to: END
"""

        write_generated_files(str(tmp_path), graph_content, [])

        # Parse the written file
        parsed = yaml.safe_load((tmp_path / "graph.yaml").read_text())

        assert parsed["version"] == "1.0"
        assert parsed["name"] == "test"
        assert "nodes" in parsed
        assert "edges" in parsed
