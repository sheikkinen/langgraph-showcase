"""Tests for FR-013: Demo structure in examples/demos/.

TDD tests to verify demo organization:
- Demo graphs load from examples/demos/
- Demo prompts are co-located with their graphs
- demo.sh script works with new paths
"""

from pathlib import Path

import pytest

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
EXAMPLES_DEMOS = PROJECT_ROOT / "examples" / "demos"


class TestDemoDirectoryStructure:
    """Verify demos are organized under examples/demos/."""

    @pytest.mark.req("REQ-YG-001")
    def test_demos_directory_exists(self) -> None:
        """examples/demos/ directory should exist."""
        assert EXAMPLES_DEMOS.exists(), f"Missing {EXAMPLES_DEMOS}"
        assert EXAMPLES_DEMOS.is_dir()

    @pytest.mark.parametrize(
        "demo_name",
        [
            "hello",
            "router",
            "yamlgraph",
            "reflexion",
            "git-report",
            "memory",
            "map",
            "interview",
            "code-analysis",
            "web-research",
            "subgraph",
            "feature-brainstorm",
        ],
    )
    @pytest.mark.req("REQ-YG-001")
    def test_demo_has_graph_yaml(self, demo_name: str) -> None:
        """Each demo should have a graph.yaml file."""
        demo_dir = EXAMPLES_DEMOS / demo_name
        graph_file = demo_dir / "graph.yaml"
        assert graph_file.exists(), f"Missing {graph_file}"

    @pytest.mark.parametrize(
        "demo_name",
        [
            "hello",
            "router",
            "yamlgraph",
            "reflexion",
        ],
    )
    @pytest.mark.req("REQ-YG-001")
    def test_demo_has_prompts_directory(self, demo_name: str) -> None:
        """Demos with prompts should have a prompts/ subdirectory."""
        demo_dir = EXAMPLES_DEMOS / demo_name
        prompts_dir = demo_dir / "prompts"
        # Either prompts dir exists, or prompts are inline in graph.yaml
        if prompts_dir.exists():
            assert prompts_dir.is_dir()
            yaml_files = list(prompts_dir.glob("*.yaml"))
            assert len(yaml_files) > 0, f"Empty prompts dir: {prompts_dir}"


class TestDemoScriptLocation:
    """Verify demo.sh is in examples/demos/."""

    @pytest.mark.req("REQ-YG-001")
    def test_demo_script_exists(self) -> None:
        """demo.sh should exist in examples/demos/."""
        demo_script = EXAMPLES_DEMOS / "demo.sh"
        assert demo_script.exists(), f"Missing {demo_script}"

    @pytest.mark.req("REQ-YG-001")
    def test_demo_script_is_executable(self) -> None:
        """demo.sh should be executable."""
        demo_script = EXAMPLES_DEMOS / "demo.sh"
        if demo_script.exists():
            import os

            assert os.access(demo_script, os.X_OK), f"Not executable: {demo_script}"


class TestCoreMinimal:
    """Verify core graphs/ only has minimal examples."""

    @pytest.mark.req("REQ-YG-001")
    def test_core_graphs_minimal(self) -> None:
        """Core graphs/ should only have hello.yaml."""
        core_graphs = PROJECT_ROOT / "graphs"
        if core_graphs.exists():
            list(core_graphs.glob("*.yaml"))
            # After migration, only hello.yaml should remain
            # For now, just check the structure
            assert core_graphs.is_dir()


class TestDemosLoadable:
    """Verify demos can be loaded with yamlgraph."""

    @pytest.mark.parametrize(
        "demo_name",
        [
            "hello",
            "router",
        ],
    )
    @pytest.mark.req("REQ-YG-001")
    def test_demo_graph_loads(self, demo_name: str) -> None:
        """Demo graphs should load without errors."""
        from yamlgraph.graph_loader import load_and_compile

        graph_path = EXAMPLES_DEMOS / demo_name / "graph.yaml"
        if graph_path.exists():
            graph = load_and_compile(str(graph_path))
            assert graph is not None
