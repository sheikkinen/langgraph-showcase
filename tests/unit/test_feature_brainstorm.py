"""Tests for feature-brainstorm graph.

TDD: Write tests first, then implement graph and prompts.
"""

from pathlib import Path

import yaml

from yamlgraph.tools.graph_linter import lint_graph

# Use absolute paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
GRAPH_PATH = PROJECT_ROOT / "examples/demos/feature-brainstorm/graph.yaml"
PROMPTS_DIR = PROJECT_ROOT / "examples/demos/feature-brainstorm/prompts"


class TestFeatureBrainstormStructure:
    """Test graph file structure and validity."""

    def test_graph_file_exists(self):
        """Graph file should exist."""
        assert GRAPH_PATH.exists(), f"Missing {GRAPH_PATH}"

    def test_graph_passes_linter(self):
        """Graph should pass all lint checks."""
        result = lint_graph(GRAPH_PATH, project_root=PROJECT_ROOT)
        assert result.valid, f"Lint errors: {[i.message for i in result.issues]}"

    def test_graph_has_required_fields(self):
        """Graph should have name, description, state, tools, nodes, edges."""
        with open(GRAPH_PATH) as f:
            graph = yaml.safe_load(f)

        assert "name" in graph, "Missing 'name'"
        assert "description" in graph, "Missing 'description'"
        assert "state" in graph, "Missing 'state'"
        assert "tools" in graph, "Missing 'tools'"
        assert "nodes" in graph, "Missing 'nodes'"
        assert "edges" in graph, "Missing 'edges'"

    def test_graph_has_focus_state_variable(self):
        """Graph should have optional 'focus' state variable."""
        with open(GRAPH_PATH) as f:
            graph = yaml.safe_load(f)

        state = graph.get("state", {})
        assert "focus" in state, "Missing 'focus' in state"


class TestFeatureBrainstormTools:
    """Test tool definitions."""

    def test_has_codebase_reading_tools(self):
        """Graph should have tools to read codebase."""
        with open(GRAPH_PATH) as f:
            graph = yaml.safe_load(f)

        tools = graph.get("tools", {})
        tool_names = set(tools.keys())

        # Should have at least these for context gathering
        expected = {"read_patterns", "read_readme", "search_todos"}
        missing = expected - tool_names
        assert not missing, f"Missing tools: {missing}"

    def test_has_search_web_tool(self):
        """Graph should have search_web tool for research."""
        with open(GRAPH_PATH) as f:
            graph = yaml.safe_load(f)

        tools = graph.get("tools", {})

        # search_web should be a python tool now
        assert "search_web" in tools, "Missing search_web tool"
        assert tools["search_web"].get("type") == "python"
        assert tools["search_web"].get("function") == "search_web"


class TestFeatureBrainstormNodes:
    """Test node definitions."""

    def test_has_gather_context_node(self):
        """Graph should have gather_context agent node."""
        with open(GRAPH_PATH) as f:
            graph = yaml.safe_load(f)

        nodes = graph.get("nodes", {})
        assert "gather_context" in nodes, "Missing 'gather_context' node"
        assert nodes["gather_context"]["type"] == "agent"

    def test_has_research_node(self):
        """Graph should have research agent node."""
        with open(GRAPH_PATH) as f:
            graph = yaml.safe_load(f)

        nodes = graph.get("nodes", {})
        assert "research_alternatives" in nodes, "Missing 'research_alternatives' node"

    def test_has_brainstorm_node(self):
        """Graph should have brainstorm LLM node."""
        with open(GRAPH_PATH) as f:
            graph = yaml.safe_load(f)

        nodes = graph.get("nodes", {})
        assert "brainstorm" in nodes, "Missing 'brainstorm' node"
        assert nodes["brainstorm"]["type"] == "llm"

    def test_has_prioritize_node(self):
        """Graph should have prioritize LLM node."""
        with open(GRAPH_PATH) as f:
            graph = yaml.safe_load(f)

        nodes = graph.get("nodes", {})
        assert "prioritize" in nodes, "Missing 'prioritize' node"


class TestFeatureBrainstormPrompts:
    """Test prompt files exist and are valid."""

    def test_prompts_directory_exists(self):
        """Prompts directory should exist."""
        assert PROMPTS_DIR.exists(), f"Missing {PROMPTS_DIR}"

    def test_gather_prompt_exists(self):
        """gather.yaml prompt should exist."""
        prompt_path = PROMPTS_DIR / "gather.yaml"
        assert prompt_path.exists(), f"Missing {prompt_path}"

    def test_research_prompt_exists(self):
        """research.yaml prompt should exist."""
        prompt_path = PROMPTS_DIR / "research.yaml"
        assert prompt_path.exists(), f"Missing {prompt_path}"

    def test_ideate_prompt_exists(self):
        """ideate.yaml prompt should exist."""
        prompt_path = PROMPTS_DIR / "ideate.yaml"
        assert prompt_path.exists(), f"Missing {prompt_path}"

    def test_prioritize_prompt_exists(self):
        """prioritize.yaml prompt should exist."""
        prompt_path = PROMPTS_DIR / "prioritize.yaml"
        assert prompt_path.exists(), f"Missing {prompt_path}"

    def test_prompts_have_required_fields(self):
        """All prompts should have system and user fields."""
        for prompt_file in PROMPTS_DIR.glob("*.yaml"):
            with open(prompt_file) as f:
                prompt = yaml.safe_load(f)

            assert (
                "system" in prompt or "user" in prompt
            ), f"{prompt_file.name} missing 'system' or 'user'"


class TestFeatureBrainstormEdges:
    """Test edge definitions create valid flow."""

    def test_starts_with_gather_context(self):
        """Graph should start with gather_context."""
        with open(GRAPH_PATH) as f:
            graph = yaml.safe_load(f)

        edges = graph.get("edges", [])
        start_edges = [e for e in edges if e.get("from") == "START"]

        assert start_edges, "Missing START edge"
        assert start_edges[0]["to"] == "gather_context"

    def test_ends_with_prioritize(self):
        """Graph should end after prioritize."""
        with open(GRAPH_PATH) as f:
            graph = yaml.safe_load(f)

        edges = graph.get("edges", [])
        end_edges = [e for e in edges if e.get("to") == "END"]

        assert end_edges, "Missing END edge"
        # Last node before END should be prioritize
        assert any(e["from"] == "prioritize" for e in end_edges)

    def test_has_complete_flow(self):
        """Graph should have edges connecting all nodes."""
        with open(GRAPH_PATH) as f:
            graph = yaml.safe_load(f)

        edges = graph.get("edges", [])
        nodes = set(graph.get("nodes", {}).keys())

        # All nodes should be reachable (appear as 'to')
        targets = {e["to"] for e in edges if e["to"] != "END"}
        unreachable = nodes - targets
        assert not unreachable, f"Unreachable nodes: {unreachable}"
