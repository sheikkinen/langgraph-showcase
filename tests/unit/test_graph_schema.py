"""Tests for graph configuration Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from yamlgraph.models.graph_schema import (
    EdgeConfig,
    NodeConfig,
    validate_graph_schema,
)


class TestNodeConfig:
    """Tests for NodeConfig validation."""

    def test_default_node_type_is_llm(self):
        """Default node type is llm."""
        node = NodeConfig(prompt="test")
        assert node.type == "llm"

    def test_llm_node_requires_prompt(self):
        """LLM node must have prompt."""
        with pytest.raises(ValidationError, match="requires 'prompt'"):
            NodeConfig(type="llm")

    def test_router_requires_routes(self):
        """Router node must have routes."""
        with pytest.raises(ValidationError, match="requires 'routes'"):
            NodeConfig(type="router", prompt="classify")

    def test_router_with_routes_valid(self):
        """Router with routes is valid."""
        node = NodeConfig(
            type="router",
            prompt="classify",
            routes={"positive": "happy", "negative": "sad"},
        )
        assert node.routes == {"positive": "happy", "negative": "sad"}

    def test_map_requires_all_fields(self):
        """Map node requires over, as, node, collect."""
        # Missing 'as'
        with pytest.raises(ValidationError, match="requires 'as'"):
            NodeConfig(
                type="map",
                over="{state.items}",
                node={"prompt": "process"},
                collect="results",
            )

    def test_map_with_all_fields_valid(self):
        """Map node with all fields is valid."""
        node = NodeConfig.model_validate(
            {
                "type": "map",
                "over": "{state.items}",
                "as": "item",
                "node": {"prompt": "process"},
                "collect": "results",
            }
        )
        assert node.item_var == "item"
        assert node.collect == "results"

    def test_invalid_on_error_rejected(self):
        """Invalid on_error value is rejected."""
        with pytest.raises(ValidationError, match="Invalid on_error"):
            NodeConfig(prompt="test", on_error="invalid_handler")

    def test_valid_on_error_accepted(self):
        """Valid on_error values accepted."""
        for handler in ["skip", "retry", "fail", "fallback"]:
            node = NodeConfig(prompt="test", on_error=handler)
            assert node.on_error == handler

    def test_temperature_range(self):
        """Temperature must be 0-2."""
        NodeConfig(prompt="test", temperature=0.5)  # Valid

        with pytest.raises(ValidationError):
            NodeConfig(prompt="test", temperature=-0.1)

        with pytest.raises(ValidationError):
            NodeConfig(prompt="test", temperature=2.5)


class TestEdgeConfig:
    """Tests for EdgeConfig validation."""

    def test_simple_edge(self):
        """Simple from/to edge."""
        edge = EdgeConfig.model_validate({"from": "a", "to": "b"})
        assert edge.from_node == "a"
        assert edge.to == "b"

    def test_edge_with_condition(self):
        """Edge with condition expression."""
        edge = EdgeConfig.model_validate(
            {
                "from": "critique",
                "to": "refine",
                "condition": "score < 0.8",
            }
        )
        assert edge.condition == "score < 0.8"

    def test_edge_to_multiple_targets(self):
        """Edge can have list of targets."""
        edge = EdgeConfig.model_validate(
            {
                "from": "a",
                "to": ["b", "c"],
            }
        )
        assert edge.to == ["b", "c"]


class TestGraphConfigSchema:
    """Tests for full graph schema validation."""

    def test_minimal_valid_graph(self):
        """Minimal valid graph configuration."""
        config = {
            "nodes": {
                "greet": {"prompt": "greet"},
            },
            "edges": [
                {"from": "START", "to": "greet"},
                {"from": "greet", "to": "END"},
            ],
        }
        schema = validate_graph_schema(config)
        assert schema.name == "unnamed"
        assert "greet" in schema.nodes

    def test_full_graph_config(self):
        """Full graph with all optional fields."""
        config = {
            "version": "1.0",
            "name": "test-graph",
            "description": "A test graph",
            "defaults": {"provider": "anthropic"},
            "nodes": {
                "generate": {"prompt": "generate", "temperature": 0.8},
            },
            "edges": [
                {"from": "START", "to": "generate"},
                {"from": "generate", "to": "END"},
            ],
            "loop_limits": {"refine": 3},
        }
        schema = validate_graph_schema(config)
        assert schema.name == "test-graph"
        assert schema.defaults == {"provider": "anthropic"}

    def test_router_targets_validated(self):
        """Router targets must exist as nodes."""
        config = {
            "nodes": {
                "classify": {
                    "type": "router",
                    "prompt": "classify",
                    "routes": {"a": "nonexistent"},
                },
            },
            "edges": [{"from": "START", "to": "classify"}],
        }
        with pytest.raises(ValidationError, match="nonexistent"):
            validate_graph_schema(config)

    def test_edge_nodes_validated(self):
        """Edge nodes must exist."""
        config = {
            "nodes": {"a": {"prompt": "test"}},
            "edges": [
                {"from": "START", "to": "a"},
                {"from": "a", "to": "missing"},
            ],
        }
        with pytest.raises(ValidationError, match="missing"):
            validate_graph_schema(config)

    def test_start_end_always_valid(self):
        """START and END are always valid node references."""
        config = {
            "nodes": {"middle": {"prompt": "test"}},
            "edges": [
                {"from": "START", "to": "middle"},
                {"from": "middle", "to": "END"},
            ],
        }
        schema = validate_graph_schema(config)
        assert len(schema.edges) == 2
