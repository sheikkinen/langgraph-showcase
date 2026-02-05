"""Smoke tests for all demos.

Tests that each demo:
1. Has required files (graph.yaml, README.md)
2. Graph YAML is valid
3. Graph loads via yamlgraph
"""

from pathlib import Path

import pytest
import yaml

DEMOS_DIR = Path(__file__).parent.parent

# Demos with graph.yaml files
STANDARD_DEMOS = [
    "code-analysis",
    "data-files",
    "feature-brainstorm",
    "git-report",
    "hello",
    "interview",
    "map",
    "memory",
    "reflexion",
    "router",
    "run-analyzer",
    "soul",
    "subgraph",
    "system-status",
    "web-research",
    "yamlgraph",
]

# Demos with non-standard structure
INTERRUPT_YAMLS = [
    "interrupt-parent.yaml",
    "interrupt-parent-redis.yaml",
    "interrupt-parent-with-checkpointer-child.yaml",
]


class TestDemoStructure:
    """Test demo directory structure."""

    @pytest.mark.parametrize("demo", STANDARD_DEMOS)
    def test_has_readme(self, demo):
        """Each demo should have a README."""
        readme = DEMOS_DIR / demo / "README.md"
        assert readme.exists(), f"{demo} missing README.md"

    @pytest.mark.parametrize("demo", STANDARD_DEMOS)
    def test_has_graph_yaml(self, demo):
        """Each standard demo should have graph.yaml."""
        graph = DEMOS_DIR / demo / "graph.yaml"
        assert graph.exists(), f"{demo} missing graph.yaml"

    @pytest.mark.parametrize("demo", STANDARD_DEMOS)
    def test_graph_yaml_valid(self, demo):
        """Graph YAML should be valid."""
        graph = DEMOS_DIR / demo / "graph.yaml"
        config = yaml.safe_load(graph.read_text())
        assert config is not None
        # Should have either name or nodes
        assert "name" in config or "nodes" in config

    def test_interrupt_yamls_exist(self):
        """Interrupt demo should have its YAML files."""
        for yaml_file in INTERRUPT_YAMLS:
            path = DEMOS_DIR / "interrupt" / yaml_file
            assert path.exists(), f"Missing {yaml_file}"


class TestGraphLoader:
    """Test graphs load via yamlgraph."""

    @pytest.mark.parametrize("demo", STANDARD_DEMOS)
    def test_graph_loads(self, demo):
        """Graph should load without errors."""
        from yamlgraph.graph_loader import load_graph_config

        graph_path = DEMOS_DIR / demo / "graph.yaml"
        config = load_graph_config(str(graph_path))
        assert config is not None

    @pytest.mark.parametrize("yaml_file", INTERRUPT_YAMLS)
    def test_interrupt_graphs_load(self, yaml_file):
        """Interrupt graphs should load."""
        from yamlgraph.graph_loader import load_graph_config

        graph_path = DEMOS_DIR / "interrupt" / yaml_file
        config = load_graph_config(str(graph_path))
        assert config is not None


class TestPromptsExist:
    """Test that referenced prompts exist."""

    @pytest.mark.parametrize(
        "demo",
        [
            d
            for d in STANDARD_DEMOS
            if d
            not in ("interview", "run-analyzer")  # These have special prompt handling
        ],
    )
    def test_prompts_dir_exists(self, demo):
        """Demos with LLM nodes should have prompts directory."""
        demo_dir = DEMOS_DIR / demo
        graph = yaml.safe_load((demo_dir / "graph.yaml").read_text())

        # Check if any node uses prompts
        nodes = graph.get("nodes", {})
        has_llm_nodes = any(
            n.get("type") == "llm" or "prompt" in n for n in nodes.values()
        )

        if has_llm_nodes:
            prompts_dir = demo_dir / "prompts"
            assert prompts_dir.exists(), f"{demo} has LLM nodes but no prompts/"


class TestStreamingDemo:
    """Test streaming demo (Python-only, no graph.yaml)."""

    def test_has_readme(self):
        """Streaming demo should have README."""
        readme = DEMOS_DIR / "streaming" / "README.md"
        assert readme.exists()

    def test_has_demo_script(self):
        """Streaming demo should have Python script."""
        script = DEMOS_DIR / "streaming" / "demo_streaming.py"
        assert script.exists()

    def test_demo_script_importable(self):
        """Demo script should be syntactically valid."""
        script = DEMOS_DIR / "streaming" / "demo_streaming.py"
        code = script.read_text()
        compile(code, str(script), "exec")  # Raises SyntaxError if invalid
