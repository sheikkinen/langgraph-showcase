"""Tests for Section 3: Self-Correction Loops (Reflexion).

TDD tests for expression conditions, loop tracking, and cyclic graphs.
"""

from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# Test: Expression Condition Parsing
# =============================================================================


class TestExpressionConditions:
    """Tests for condition expression evaluation."""

    @pytest.mark.req("REQ-YG-006")
    def test_evaluate_condition_exists(self):
        """evaluate_condition function should exist."""
        from yamlgraph.utils.conditions import evaluate_condition

        assert callable(evaluate_condition)

    @pytest.mark.req("REQ-YG-006")
    def test_less_than_comparison(self):
        """Evaluates 'score < 0.8' correctly."""
        from yamlgraph.utils.conditions import evaluate_condition

        state = {"score": 0.5}
        assert evaluate_condition("score < 0.8", state) is True

        state = {"score": 0.9}
        assert evaluate_condition("score < 0.8", state) is False

    @pytest.mark.req("REQ-YG-006")
    def test_greater_than_comparison(self):
        """Evaluates 'score > 0.5' correctly."""
        from yamlgraph.utils.conditions import evaluate_condition

        state = {"score": 0.7}
        assert evaluate_condition("score > 0.5", state) is True

        state = {"score": 0.3}
        assert evaluate_condition("score > 0.5", state) is False

    @pytest.mark.req("REQ-YG-006")
    def test_less_than_or_equal(self):
        """Evaluates 'score <= 0.8' correctly."""
        from yamlgraph.utils.conditions import evaluate_condition

        state = {"score": 0.8}
        assert evaluate_condition("score <= 0.8", state) is True

        state = {"score": 0.9}
        assert evaluate_condition("score <= 0.8", state) is False

    @pytest.mark.req("REQ-YG-006")
    def test_greater_than_or_equal(self):
        """Evaluates 'score >= 0.8' correctly."""
        from yamlgraph.utils.conditions import evaluate_condition

        state = {"score": 0.8}
        assert evaluate_condition("score >= 0.8", state) is True

        state = {"score": 0.7}
        assert evaluate_condition("score >= 0.8", state) is False

    @pytest.mark.req("REQ-YG-006")
    def test_equality_comparison(self):
        """Evaluates 'status == \"approved\"' correctly."""
        from yamlgraph.utils.conditions import evaluate_condition

        state = {"status": "approved"}
        assert evaluate_condition('status == "approved"', state) is True

        state = {"status": "pending"}
        assert evaluate_condition('status == "approved"', state) is False

    @pytest.mark.req("REQ-YG-006")
    def test_inequality_comparison(self):
        """Evaluates 'error != null' correctly."""
        from yamlgraph.utils.conditions import evaluate_condition

        state = {"error": "something"}
        assert evaluate_condition("error != null", state) is True

        state = {"error": None}
        assert evaluate_condition("error != null", state) is False

    @pytest.mark.req("REQ-YG-006")
    def test_nested_attribute_access(self):
        """Evaluates 'critique.score >= 0.8' from state."""
        from yamlgraph.utils.conditions import evaluate_condition

        # Using object with attribute
        critique = MagicMock()
        critique.score = 0.85
        state = {"critique": critique}
        assert evaluate_condition("critique.score >= 0.8", state) is True

        critique.score = 0.7
        assert evaluate_condition("critique.score >= 0.8", state) is False

    @pytest.mark.req("REQ-YG-006")
    def test_compound_and_condition(self):
        """Evaluates 'score < 0.8 and iteration < 3'."""
        from yamlgraph.utils.conditions import evaluate_condition

        state = {"score": 0.5, "iteration": 2}
        assert evaluate_condition("score < 0.8 and iteration < 3", state) is True

        state = {"score": 0.9, "iteration": 2}
        assert evaluate_condition("score < 0.8 and iteration < 3", state) is False

        state = {"score": 0.5, "iteration": 5}
        assert evaluate_condition("score < 0.8 and iteration < 3", state) is False

    @pytest.mark.req("REQ-YG-006")
    def test_compound_or_condition(self):
        """Evaluates 'approved == true or override == true'."""
        from yamlgraph.utils.conditions import evaluate_condition

        state = {"approved": True, "override": False}
        assert evaluate_condition("approved == true or override == true", state) is True

        state = {"approved": False, "override": True}
        assert evaluate_condition("approved == true or override == true", state) is True

        state = {"approved": False, "override": False}
        assert (
            evaluate_condition("approved == true or override == true", state) is False
        )

    @pytest.mark.req("REQ-YG-006")
    def test_invalid_expression_raises(self):
        """Malformed expression raises ValueError."""
        from yamlgraph.utils.conditions import evaluate_condition

        with pytest.raises(ValueError):
            evaluate_condition("score <<< 0.8", {})

    @pytest.mark.req("REQ-YG-006")
    def test_missing_attribute_returns_false(self):
        """Missing attribute in state returns False gracefully."""
        from yamlgraph.utils.conditions import evaluate_condition

        state = {}
        # Should not raise, should return False for missing attribute
        assert evaluate_condition("score < 0.8", state) is False


# =============================================================================
# Test: Loop Tracking
# =============================================================================


class TestLoopTracking:
    """Tests for loop iteration tracking."""

    @pytest.mark.req("REQ-YG-006")
    def test_state_has_loop_counts_field(self):
        """Dynamic state should have _loop_counts field."""
        from yamlgraph.models.state_builder import build_state_class

        State = build_state_class({"nodes": {}})
        # Should have _loop_counts in annotations
        assert "_loop_counts" in State.__annotations__

        # And work at runtime
        state = {"_loop_counts": {"critique": 2}}
        assert state["_loop_counts"]["critique"] == 2

    @pytest.mark.req("REQ-YG-006")
    def test_node_increments_loop_counter(self):
        """Each node execution increments its counter in _loop_counts."""
        from yamlgraph.node_factory import create_node_function

        node_config = {
            "prompt": "test_prompt",
            "state_key": "result",
        }

        with patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute:
            mock_execute.return_value = "test result"

            node_fn = create_node_function("critique", node_config, {})

            # First call - should initialize counter
            state = {"message": "test"}
            result = node_fn(state)
            assert result.get("_loop_counts", {}).get("critique") == 1

            # Second call - should increment
            state = {"message": "test", "_loop_counts": {"critique": 1}}
            result = node_fn(state)
            assert result.get("_loop_counts", {}).get("critique") == 2


# =============================================================================
# Test: Loop Limits Configuration
# =============================================================================


class TestLoopLimits:
    """Tests for loop_limits configuration."""

    @pytest.mark.req("REQ-YG-006")
    def test_parses_loop_limits_from_yaml(self):
        """GraphConfig parses loop_limits section."""
        from yamlgraph.graph_loader import GraphConfig

        config_dict = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "draft": {"prompt": "draft"},
                "critique": {"prompt": "critique"},
            },
            "edges": [
                {"from": "START", "to": "draft"},
                {"from": "draft", "to": "critique"},
                {"from": "critique", "to": "END"},
            ],
            "loop_limits": {
                "critique": 3,
            },
        }
        config = GraphConfig(config_dict)
        assert config.loop_limits == {"critique": 3}

    @pytest.mark.req("REQ-YG-006")
    def test_loop_limits_defaults_to_empty(self):
        """Missing loop_limits defaults to empty dict."""
        from yamlgraph.graph_loader import GraphConfig

        config_dict = {
            "version": "1.0",
            "name": "test",
            "nodes": {"node1": {"prompt": "p1"}},
            "edges": [{"from": "START", "to": "node1"}, {"from": "node1", "to": "END"}],
        }
        config = GraphConfig(config_dict)
        assert config.loop_limits == {}

    @pytest.mark.req("REQ-YG-006")
    def test_node_checks_loop_limit(self):
        """Node execution checks loop limit before running."""
        from yamlgraph.node_factory import create_node_function

        node_config = {
            "prompt": "test_prompt",
            "state_key": "result",
            "loop_limit": 3,  # Node-level limit
        }

        with patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute:
            mock_execute.return_value = "test result"

            node_fn = create_node_function("critique", node_config, {})

            # Under limit - should execute
            state = {"_loop_counts": {"critique": 2}}
            result = node_fn(state)
            assert "result" in result

            # At limit - should skip/terminate
            state = {"_loop_counts": {"critique": 3}}
            result = node_fn(state)
            assert result.get("_loop_limit_reached") is True


# =============================================================================
# Test: Cyclic Edges
# =============================================================================


class TestCyclicEdges:
    """Tests for cyclic graph support."""

    @pytest.mark.req("REQ-YG-006")
    def test_allows_backward_edges(self):
        """Graph config allows edges pointing to earlier nodes."""
        from yamlgraph.graph_loader import GraphConfig

        config_dict = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "draft": {"prompt": "draft"},
                "critique": {"prompt": "critique"},
                "refine": {"prompt": "refine"},
            },
            "edges": [
                {"from": "START", "to": "draft"},
                {"from": "draft", "to": "critique"},
                {
                    "from": "critique",
                    "to": "refine",
                    "condition": "critique.score < 0.8",
                },
                {"from": "critique", "to": "END", "condition": "critique.score >= 0.8"},
                {"from": "refine", "to": "critique"},  # Backward edge (cycle)
            ],
            "loop_limits": {"critique": 3},
        }
        # Should not raise
        config = GraphConfig(config_dict)
        assert config is not None

    @pytest.mark.req("REQ-YG-006")
    def test_compiles_cyclic_graph(self):
        """Cyclic graph compiles to StateGraph."""
        from yamlgraph.graph_loader import GraphConfig, compile_graph

        config_dict = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "draft": {"prompt": "draft", "state_key": "current_draft"},
                "critique": {"prompt": "critique", "state_key": "critique"},
                "refine": {"prompt": "refine", "state_key": "current_draft"},
            },
            "edges": [
                {"from": "START", "to": "draft"},
                {"from": "draft", "to": "critique"},
                {
                    "from": "critique",
                    "to": "refine",
                    "condition": "critique.score < 0.8",
                },
                {"from": "critique", "to": "END", "condition": "critique.score >= 0.8"},
                {"from": "refine", "to": "critique"},  # Cycle
            ],
            "loop_limits": {"critique": 3},
        }
        config = GraphConfig(config_dict)
        graph = compile_graph(config)
        assert graph is not None


# =============================================================================
# Test: Pydantic Models
# =============================================================================


class TestReflexionModels:
    """Tests for DraftContent and Critique-like fixture models.

    Note: Demo models were removed from yamlgraph.models in Section 10.
    These tests use fixture models to prove the pattern still works.
    """

    @pytest.mark.req("REQ-YG-006")
    def test_draft_content_model_exists(self):
        """DraftContent-like fixture model can be created."""
        from tests.conftest import FixtureDraftContent

        assert FixtureDraftContent is not None

    @pytest.mark.req("REQ-YG-006")
    def test_draft_content_fields(self):
        """DraftContent-like model has content and version fields."""
        from tests.conftest import FixtureDraftContent

        draft = FixtureDraftContent(content="Test essay", version=1)
        assert draft.content == "Test essay"
        assert draft.version == 1

    @pytest.mark.req("REQ-YG-006")
    def test_critique_model_exists(self):
        """Critique-like fixture model can be created."""
        from tests.conftest import FixtureCritique

        assert FixtureCritique is not None

    @pytest.mark.req("REQ-YG-006")
    def test_critique_fields(self):
        """Critique-like model has score, feedback, issues, should_refine fields."""
        from tests.conftest import FixtureCritique

        critique = FixtureCritique(
            score=0.75,
            feedback="Improve transitions",
            issues=["Weak intro", "No conclusion"],
            should_refine=True,
        )
        assert critique.score == 0.75
        assert critique.feedback == "Improve transitions"
        assert len(critique.issues) == 2
        assert critique.should_refine is True


# =============================================================================
# Test: Reflexion Demo Graph
# =============================================================================


class TestReflexionDemoGraph:
    """Tests for the reflexion-demo.yaml graph."""

    @pytest.mark.req("REQ-YG-006")
    def test_demo_graph_loads(self):
        """reflexion-demo.yaml loads without error."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config("examples/demos/reflexion/graph.yaml")
        assert config.name == "reflexion-demo"
        assert "draft" in config.nodes
        assert "critique" in config.nodes
        assert "refine" in config.nodes

    @pytest.mark.req("REQ-YG-006")
    def test_demo_graph_has_loop_limits(self):
        """reflexion-demo.yaml has loop_limits configured."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config("examples/demos/reflexion/graph.yaml")
        assert "critique" in config.loop_limits
        assert config.loop_limits["critique"] >= 3

    @pytest.mark.req("REQ-YG-006")
    def test_demo_graph_compiles(self):
        """reflexion-demo.yaml compiles to StateGraph."""
        from yamlgraph.graph_loader import compile_graph, load_graph_config

        config = load_graph_config("examples/demos/reflexion/graph.yaml")
        graph = compile_graph(config)
        assert graph is not None
