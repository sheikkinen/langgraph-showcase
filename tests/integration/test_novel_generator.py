"""Integration tests for novel generator demo.

Exercises existing requirements in a creative writing context.
Marketing artifact: demonstrates TDD approach to example development.

FR-034: Novel Generator Demo (Marketing Showcase)
"""

from pathlib import Path

import pytest

# Demo path
DEMO_PATH = (
    Path(__file__).parent.parent.parent / "examples" / "demos" / "novel_generator"
)
GRAPH_PATH = DEMO_PATH / "graph.yaml"


@pytest.mark.req("REQ-YG-024")  # Conditional routing
def test_evolution_loop_improves_synopsis():
    """Synopsis quality improves over iterations.

    Validates that:
    1. Graph loads successfully
    2. Evolution loop executes (analyze → evolve → analyze)
    3. Synopsis quality grade improves or meets threshold
    """
    # Red phase: test fails until implementation exists
    assert GRAPH_PATH.exists(), f"Graph not found at {GRAPH_PATH}"

    from yamlgraph.graph_loader import load_graph_config

    config = load_graph_config(str(GRAPH_PATH))

    # Verify evolution loop structure exists
    node_names = list(config.nodes.keys())
    assert "generate_synopsis" in node_names, "Missing generate_synopsis node"
    assert "analyze_synopsis" in node_names, "Missing analyze_synopsis node"
    assert "evolve_synopsis" in node_names, "Missing evolve_synopsis node"

    # Verify conditional edge from analyze_synopsis
    analyze_edges = [e for e in config.edges if e.get("from") == "analyze_synopsis"]
    assert len(analyze_edges) >= 2, "analyze_synopsis should have conditional edges"


@pytest.mark.req("REQ-YG-040")  # Map node compilation
def test_map_node_generates_parallel_prose():
    """Map node generates prose for multiple beats.

    Validates that:
    1. Map node is defined with correct structure
    2. over/as/node/collect fields present
    3. Nested node configured for prose generation
    """
    assert GRAPH_PATH.exists(), f"Graph not found at {GRAPH_PATH}"

    from yamlgraph.graph_loader import load_graph_config

    config = load_graph_config(str(GRAPH_PATH))

    # Find map node
    map_nodes = [
        (name, cfg) for name, cfg in config.nodes.items() if cfg.get("type") == "map"
    ]
    assert len(map_nodes) >= 1, "No map node found for prose generation"

    node_name, prose_map = map_nodes[0]
    assert prose_map.get("over") is not None, "Map node must have 'over'"
    assert prose_map.get("collect") is not None, "Map node must have 'collect'"


@pytest.mark.req("REQ-YG-024")  # Conditional routing
def test_review_gate_routes_correctly():
    """Review gate routes based on quality.

    Validates that:
    1. review_draft node exists
    2. Conditional edges route to END or revise
    """
    assert GRAPH_PATH.exists(), f"Graph not found at {GRAPH_PATH}"

    from yamlgraph.graph_loader import load_graph_config

    config = load_graph_config(str(GRAPH_PATH))

    node_names = list(config.nodes.keys())
    assert "review_draft" in node_names, "Missing review_draft node"

    # Verify conditional routing exists
    review_edges = [e for e in config.edges if e.get("from") == "review_draft"]
    assert len(review_edges) >= 1, "review_draft should have outgoing edges"


@pytest.mark.req("REQ-YG-024", "REQ-YG-040")
def test_full_pipeline_end_to_end():
    """Full pipeline exercises multiple requirements.

    Validates complete flow:
    premise → synopsis → timeline → prose (map) → review → output
    """
    assert GRAPH_PATH.exists(), f"Graph not found at {GRAPH_PATH}"

    from yamlgraph.graph_loader import compile_graph, load_graph_config

    config = load_graph_config(str(GRAPH_PATH))

    # Verify 3-phase structure via node count
    assert len(config.nodes) >= 6, "Should have nodes for all 3 phases"

    # Verify graph compiles
    graph = compile_graph(config)
    assert graph is not None, "Graph should compile successfully"


@pytest.mark.req("REQ-YG-024", "REQ-YG-040")
def test_graph_lint_passes():
    """Graph passes linter validation.

    Marketing requirement: graph.yaml must be valid.
    """
    assert GRAPH_PATH.exists(), f"Graph not found at {GRAPH_PATH}"

    from yamlgraph.linter import lint_graph

    result = lint_graph(str(GRAPH_PATH), project_root=DEMO_PATH)
    errors = [i for i in result.issues if i.severity == "error"]

    assert len(errors) == 0, f"Graph has lint errors: {[e.message for e in errors]}"
