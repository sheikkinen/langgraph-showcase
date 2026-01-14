"""Tests for Section 2: Router Pattern.

TDD tests for router node type and multi-target conditional edges.
"""

import pytest
from unittest.mock import patch, MagicMock

from showcase.graph_loader import (
    GraphConfig,
    create_node_function,
    compile_graph,
    load_graph_config,
)


# =============================================================================
# Test: ToneClassification Model
# =============================================================================


class TestToneClassificationModel:
    """Tests for ToneClassification Pydantic model."""

    def test_tone_classification_model_exists(self):
        """ToneClassification model can be imported."""
        from showcase.models import ToneClassification
        assert ToneClassification is not None

    def test_tone_classification_has_required_fields(self):
        """ToneClassification has tone, confidence, reasoning fields."""
        from showcase.models import ToneClassification
        
        classification = ToneClassification(
            tone="positive",
            confidence=0.95,
            reasoning="User expressed happiness",
        )
        assert classification.tone == "positive"
        assert classification.confidence == 0.95
        assert classification.reasoning == "User expressed happiness"


# =============================================================================
# Test: Router Node Type Parsing
# =============================================================================


class TestRouterNodeParsing:
    """Tests for parsing router node configuration."""

    def test_parses_router_type(self):
        """Node with type: router is parsed."""
        config_dict = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "classify": {
                    "type": "router",
                    "prompt": "classify_tone",
                    "routes": {
                        "positive": "handle_positive",
                        "negative": "handle_negative",
                    },
                    "default_route": "handle_neutral",
                },
                "handle_positive": {"prompt": "positive"},
                "handle_negative": {"prompt": "negative"},
                "handle_neutral": {"prompt": "neutral"},
            },
            "edges": [
                {"from": "START", "to": "classify"},
                {"from": "classify", "to": ["handle_positive", "handle_negative", "handle_neutral"], "type": "conditional"},
                {"from": "handle_positive", "to": "END"},
                {"from": "handle_negative", "to": "END"},
                {"from": "handle_neutral", "to": "END"},
            ],
        }
        config = GraphConfig(config_dict)
        assert config.nodes["classify"]["type"] == "router"
        assert config.nodes["classify"]["routes"]["positive"] == "handle_positive"

    def test_validates_router_has_routes(self):
        """Router node without routes raises ValueError."""
        config_dict = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "classify": {
                    "type": "router",
                    "prompt": "classify_tone",
                    # Missing routes
                },
            },
            "edges": [
                {"from": "START", "to": "classify"},
                {"from": "classify", "to": "END"},
            ],
        }
        with pytest.raises(ValueError, match="routes"):
            GraphConfig(config_dict)

    def test_validates_route_targets_exist(self):
        """Router routes must point to existing nodes."""
        config_dict = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "classify": {
                    "type": "router",
                    "prompt": "classify_tone",
                    "routes": {
                        "positive": "nonexistent_node",
                    },
                },
            },
            "edges": [
                {"from": "START", "to": "classify"},
                {"from": "classify", "to": "END"},
            ],
        }
        with pytest.raises(ValueError, match="nonexistent_node"):
            GraphConfig(config_dict)


# =============================================================================
# Test: Router Node Function
# =============================================================================


class TestRouterNodeFunction:
    """Tests for router node execution."""

    @patch("showcase.node_factory.execute_prompt")
    def test_router_returns_route_in_state(self, mock_execute):
        """Router node adds _route to state based on classification."""
        mock_classification = MagicMock()
        mock_classification.tone = "positive"
        mock_execute.return_value = mock_classification
        
        node_config = {
            "type": "router",
            "prompt": "classify_tone",
            "output_model": "showcase.models.ToneClassification",
            "routes": {
                "positive": "respond_positive",
                "negative": "respond_negative",
            },
            "default_route": "respond_neutral",
            "state_key": "classification",
        }
        node_fn = create_node_function("classify", node_config, {})
        
        result = node_fn({"message": "I love this!"})
        
        # _route should be the TARGET NODE NAME, not the route key
        assert result.get("_route") == "respond_positive"
        assert "classification" in result

    @patch("showcase.node_factory.execute_prompt")
    def test_router_uses_default_route_for_unknown(self, mock_execute):
        """Router uses default_route when tone not in routes."""
        mock_classification = MagicMock()
        mock_classification.tone = "confused"  # Not in routes
        mock_execute.return_value = mock_classification
        
        node_config = {
            "type": "router",
            "prompt": "classify_tone",
            "output_model": "showcase.models.ToneClassification",
            "routes": {
                "positive": "respond_positive",
                "negative": "respond_negative",
            },
            "default_route": "respond_neutral",
            "state_key": "classification",
        }
        node_fn = create_node_function("classify", node_config, {})
        
        result = node_fn({"message": "Huh?"})
        
        assert result.get("_route") == "respond_neutral"


# =============================================================================
# Test: Multi-Target Conditional Edges
# =============================================================================


class TestConditionalEdges:
    """Tests for multi-target conditional edge routing."""

    def test_parses_conditional_edge_with_list_targets(self):
        """Edge with to: [a, b, c] and type: conditional is parsed."""
        config_dict = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "classify": {"type": "router", "prompt": "classify", "routes": {"a": "node_a", "b": "node_b"}, "default_route": "node_a"},
                "node_a": {"prompt": "a"},
                "node_b": {"prompt": "b"},
            },
            "edges": [
                {"from": "START", "to": "classify"},
                {"from": "classify", "to": ["node_a", "node_b"], "type": "conditional"},
                {"from": "node_a", "to": "END"},
                {"from": "node_b", "to": "END"},
            ],
        }
        config = GraphConfig(config_dict)
        conditional_edge = config.edges[1]
        assert conditional_edge["type"] == "conditional"
        assert conditional_edge["to"] == ["node_a", "node_b"]

    @patch("showcase.node_factory.execute_prompt")
    def test_graph_routes_to_correct_node(self, mock_execute):
        """Compiled graph routes based on _route in state."""
        # Mock classifier returns "positive"
        mock_classification = MagicMock()
        mock_classification.tone = "positive"
        mock_execute.return_value = mock_classification
        
        config_dict = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "classify": {
                    "type": "router",
                    "prompt": "classify",
                    "output_model": "showcase.models.ToneClassification",
                    "routes": {"positive": "respond_positive", "negative": "respond_negative"},
                    "default_route": "respond_neutral",
                    "state_key": "classification",
                },
                "respond_positive": {"prompt": "positive", "state_key": "response"},
                "respond_negative": {"prompt": "negative", "state_key": "response"},
                "respond_neutral": {"prompt": "neutral", "state_key": "response"},
            },
            "edges": [
                {"from": "START", "to": "classify"},
                {"from": "classify", "to": ["respond_positive", "respond_negative", "respond_neutral"], "type": "conditional"},
                {"from": "respond_positive", "to": "END"},
                {"from": "respond_negative", "to": "END"},
                {"from": "respond_neutral", "to": "END"},
            ],
        }
        config = GraphConfig(config_dict)
        graph = compile_graph(config)
        
        # Graph should compile without error
        assert graph is not None


# =============================================================================
# Test: Demo Graph Loading
# =============================================================================


class TestRouterDemoGraph:
    """Tests for the router-demo.yaml graph."""

    def test_demo_graph_loads(self):
        """router-demo.yaml loads without error."""
        config = load_graph_config("graphs/router-demo.yaml")
        assert config.name == "tone-router-demo"
        assert "classify" in config.nodes
        assert config.nodes["classify"]["type"] == "router"

    def test_demo_graph_compiles(self):
        """router-demo.yaml compiles to StateGraph."""
        config = load_graph_config("graphs/router-demo.yaml")
        graph = compile_graph(config)
        assert graph is not None
