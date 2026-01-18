"""Tests for YAMLGraph meta-template tools."""

from pathlib import Path

from yamlgraph.tools.analysis.meta_tools import (
    extract_graph_template,
    extract_prompt_template,
)

# ============================================================================
# extract_graph_template tests
# ============================================================================


class TestExtractGraphTemplate:
    """Tests for extract_graph_template."""

    def test_extracts_node_types(self, tmp_path: Path):
        """Extract node type patterns from graph."""
        graph = tmp_path / "graph.yaml"
        graph.write_text("""
name: test-graph
version: "1.0"

nodes:
  step1:
    type: llm
    prompt: prompts/step1
    state_key: result1

  step2:
    type: agent
    prompt: prompts/step2
    tools: [tool1, tool2]
    max_iterations: 5

edges:
  - START -> step1
  - step1 -> step2
  - step2 -> END
""")
        result = extract_graph_template(str(graph))

        assert "node_types" in result
        assert "llm" in result["node_types"]
        assert "agent" in result["node_types"]

    def test_extracts_edge_patterns(self, tmp_path: Path):
        """Extract edge patterns (sequential, conditional)."""
        graph = tmp_path / "graph.yaml"
        graph.write_text("""
name: conditional-graph

nodes:
  check:
    type: llm
    prompt: check
  branch_a:
    type: llm
    prompt: a
  branch_b:
    type: llm
    prompt: b

edges:
  - START -> check
  - check -> branch_a:
      condition: state.result == "a"
  - check -> branch_b:
      condition: state.result == "b"
  - branch_a -> END
  - branch_b -> END
""")
        result = extract_graph_template(str(graph))

        assert "edge_patterns" in result
        patterns = result["edge_patterns"]
        assert "conditional" in patterns or any("condition" in str(p) for p in patterns)

    def test_extracts_state_fields(self, tmp_path: Path):
        """Extract state field patterns."""
        graph = tmp_path / "graph.yaml"
        graph.write_text("""
name: stateful-graph

state:
  input: str
  results: list
  errors: list[PipelineError]

nodes:
  process:
    type: llm
    prompt: process
    state_key: results
""")
        result = extract_graph_template(str(graph))

        assert "state_fields" in result
        fields = result["state_fields"]
        assert "input" in fields or any("input" in str(f) for f in fields)

    def test_extracts_tool_patterns(self, tmp_path: Path):
        """Extract tool declaration patterns."""
        graph = tmp_path / "graph.yaml"
        graph.write_text("""
name: tool-graph

tools:
  search:
    type: python
    module: mymodule
    function: search_func
    description: "Search for things"

  fetch:
    type: shell
    command: "curl {url}"

nodes:
  agent:
    type: agent
    tools: [search, fetch]
""")
        result = extract_graph_template(str(graph))

        assert "tool_patterns" in result
        patterns = result["tool_patterns"]
        assert "python" in patterns or any("python" in str(p) for p in patterns)

    def test_handles_missing_file(self):
        """Returns error for missing file."""
        result = extract_graph_template("/nonexistent/graph.yaml")
        assert "error" in result

    def test_handles_invalid_yaml(self, tmp_path: Path):
        """Returns error for invalid YAML."""
        graph = tmp_path / "bad.yaml"
        graph.write_text("{ invalid yaml: [")

        result = extract_graph_template(str(graph))
        assert "error" in result


# ============================================================================
# extract_prompt_template tests
# ============================================================================


class TestExtractPromptTemplate:
    """Tests for extract_prompt_template."""

    def test_extracts_system_structure(self, tmp_path: Path):
        """Extract system prompt structure."""
        prompt = tmp_path / "prompt.yaml"
        prompt.write_text("""
metadata:
  provider: anthropic
  model: claude-sonnet-4-20250514

system: |
  You are an expert assistant.

  ## Instructions
  - Be helpful
  - Be concise

  ## Output Format
  Respond in JSON.

user: "Process this: {input}"
""")
        result = extract_prompt_template(str(prompt))

        assert "system_structure" in result
        structure = result["system_structure"]
        assert "sections" in structure or len(structure) > 0

    def test_extracts_variable_patterns(self, tmp_path: Path):
        """Extract variable injection patterns."""
        prompt = tmp_path / "prompt.yaml"
        prompt.write_text("""
system: "You are a {role} assistant."
user: |
  Input: {input}
  Context: {context}
  Previous: {history}
""")
        result = extract_prompt_template(str(prompt))

        assert "variables" in result
        variables = result["variables"]
        assert "input" in variables
        assert "context" in variables

    def test_extracts_schema_patterns(self, tmp_path: Path):
        """Extract output schema patterns."""
        prompt = tmp_path / "prompt.yaml"
        prompt.write_text("""
system: "Analyze the input."
user: "{input}"

schema:
  type: object
  properties:
    result:
      type: string
    confidence:
      type: number
  required: [result]
""")
        result = extract_prompt_template(str(prompt))

        assert "schema_patterns" in result
        patterns = result["schema_patterns"]
        assert "result" in str(patterns) or len(patterns) > 0

    def test_extracts_jinja_patterns(self, tmp_path: Path):
        """Extract Jinja2 template patterns."""
        prompt = tmp_path / "prompt.yaml"
        prompt.write_text("""
system: |
  {% if context %}
  Context: {{ context }}
  {% endif %}

  {% for item in items %}
  - {{ item.name }}: {{ item.value }}
  {% endfor %}

user: "Process {{ input }}"
""")
        result = extract_prompt_template(str(prompt))

        assert "jinja_patterns" in result
        patterns = result["jinja_patterns"]
        assert "if" in patterns or "for" in patterns

    def test_handles_missing_file(self):
        """Returns error for missing file."""
        result = extract_prompt_template("/nonexistent/prompt.yaml")
        assert "error" in result

    def test_handles_invalid_yaml(self, tmp_path: Path):
        """Returns error for invalid YAML."""
        prompt = tmp_path / "bad.yaml"
        prompt.write_text("{ invalid yaml: [")

        result = extract_prompt_template(str(prompt))
        assert "error" in result
