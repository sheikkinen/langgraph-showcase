"""Tests for router pattern linter validations."""

import pytest
import yaml

from yamlgraph.linter.patterns.router import (
    check_router_edge_targets,
    check_router_node_structure,
    check_router_patterns,
    check_router_schema_fields,
)


class TestRouterNodeStructure:
    """Test router node structural validation."""

    @pytest.mark.req("REQ-YG-003")
    def test_valid_router_structure(self):
        """Should pass valid router structure."""
        node_config = {
            "type": "router",
            "routes": {"positive": "handle_positive", "negative": "handle_negative"},
            "default_route": "handle_neutral",
        }

        issues = check_router_node_structure("test_router", node_config)
        assert len(issues) == 0

    @pytest.mark.req("REQ-YG-003")
    def test_routes_as_list_error(self):
        """Should error when routes is a list instead of dict."""
        node_config = {
            "type": "router",
            "routes": ["positive", "negative"],  # Wrong: should be dict
        }

        issues = check_router_node_structure("test_router", node_config)
        # Should have E101 error + W101 warning for missing default_route
        assert len(issues) == 2
        error_issues = [i for i in issues if i.severity == "error"]
        assert len(error_issues) == 1
        assert error_issues[0].code == "E101"
        assert "routes as list" in error_issues[0].message
        assert "dict mapping" in error_issues[0].fix

    @pytest.mark.req("REQ-YG-003")
    def test_missing_default_route_warning(self):
        """Should warn when default_route is missing."""
        node_config = {"type": "router", "routes": {"positive": "handle_positive"}}

        issues = check_router_node_structure("test_router", node_config)
        assert len(issues) == 1
        assert issues[0].code == "W101"
        assert "missing default_route" in issues[0].message

    @pytest.mark.req("REQ-YG-003")
    def test_routes_wrong_type_error(self):
        """Should error when routes is neither dict nor list."""
        node_config = {
            "type": "router",
            "routes": "invalid_string",  # Wrong type
        }

        issues = check_router_node_structure("test_router", node_config)
        # Should have E101 error + W101 warning for missing default_route
        assert len(issues) == 2
        error_issues = [i for i in issues if i.severity == "error"]
        assert len(error_issues) == 1
        assert error_issues[0].code == "E101"
        assert "must be dict" in error_issues[0].message


class TestRouterSchemaFields:
    """Test router schema field validation."""

    @pytest.mark.req("REQ-YG-003")
    def test_valid_intent_field(self, tmp_path):
        """Should pass with 'intent' field in schema."""
        # Create test graph
        graph_path = tmp_path / "test.yaml"
        with open(graph_path, "w") as f:
            yaml.dump(
                {
                    "nodes": {"router1": {"type": "router", "prompt": "classify"}},
                    "defaults": {"prompts_dir": "prompts"},
                },
                f,
            )

        # Create prompts directory and file
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "classify.yaml"
        with open(prompt_file, "w") as f:
            yaml.dump(
                {
                    "schema": {
                        "fields": {
                            "intent": {"type": "str", "description": "Classification"}
                        }
                    }
                },
                f,
            )

        issues = check_router_schema_fields(
            "router1", {"type": "router", "prompt": "classify"}, graph_path, tmp_path
        )
        assert len(issues) == 0

    @pytest.mark.req("REQ-YG-003")
    def test_valid_tone_field(self, tmp_path):
        """Should pass with 'tone' field in schema."""
        # Create test graph
        graph_path = tmp_path / "test.yaml"
        with open(graph_path, "w") as f:
            yaml.dump(
                {
                    "nodes": {"router1": {"type": "router", "prompt": "classify"}},
                    "defaults": {"prompts_dir": "prompts"},
                },
                f,
            )

        # Create prompts directory and file
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "classify.yaml"
        with open(prompt_file, "w") as f:
            yaml.dump(
                {
                    "schema": {
                        "fields": {
                            "tone": {
                                "type": "str",
                                "description": "Tone classification",
                            }
                        }
                    }
                },
                f,
            )

        issues = check_router_schema_fields(
            "router1", {"type": "router", "prompt": "classify"}, graph_path, tmp_path
        )
        assert len(issues) == 0

    @pytest.mark.req("REQ-YG-003")
    def test_missing_intent_tone_field_error(self, tmp_path):
        """Should error when schema lacks 'intent' or 'tone' field."""
        # Create test graph
        graph_path = tmp_path / "test.yaml"
        with open(graph_path, "w") as f:
            yaml.dump(
                {
                    "nodes": {"router1": {"type": "router", "prompt": "classify"}},
                    "defaults": {"prompts_dir": "prompts"},
                },
                f,
            )

        # Create prompts directory and file with wrong field name
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "classify.yaml"
        with open(prompt_file, "w") as f:
            yaml.dump(
                {
                    "schema": {
                        "fields": {
                            "category": {
                                "type": "str",
                                "description": "Wrong field name",
                            }
                        }
                    }
                },
                f,
            )

        issues = check_router_schema_fields(
            "router1", {"type": "router", "prompt": "classify"}, graph_path, tmp_path
        )
        assert len(issues) == 1
        assert issues[0].code == "E102"
        assert "missing 'intent' or 'tone' field" in issues[0].message
        assert "Framework requires" in issues[0].fix

    @pytest.mark.req("REQ-YG-003")
    def test_no_prompt_no_check(self, tmp_path):
        """Should not check schema when no prompt specified."""
        graph_path = tmp_path / "test.yaml"
        issues = check_router_schema_fields(
            "router1", {"type": "router"}, graph_path, tmp_path
        )
        assert len(issues) == 0


class TestRouterEdgeTargets:
    """Test router edge target validation."""

    @pytest.mark.req("REQ-YG-003")
    def test_valid_conditional_edge_to_list(self):
        """Should pass when conditional edge targets router as list."""
        graph = {
            "edges": [
                {
                    "from": "input",
                    "to": ["router1"],  # Correct: list format
                    "condition": "state.score > 0.5",
                }
            ]
        }

        issues = check_router_edge_targets("router1", graph)
        assert len(issues) == 0

    @pytest.mark.req("REQ-YG-003")
    def test_invalid_conditional_edge_to_single(self):
        """Should error when conditional edge targets router as single node."""
        graph = {
            "edges": [
                {
                    "from": "input",
                    "to": "router1",  # Wrong: should be list for conditional
                    "condition": "state.score > 0.5",
                }
            ]
        }

        issues = check_router_edge_targets("router1", graph)
        assert len(issues) == 1
        assert issues[0].code == "E103"
        assert "Conditional edge" in issues[0].message
        assert "list" in issues[0].fix


class TestRouterPatternsIntegration:
    """Test full router pattern validation integration."""

    @pytest.mark.req("REQ-YG-003")
    def test_valid_router_graph(self, tmp_path):
        """Should pass completely valid router graph."""
        # Create test graph
        graph_path = tmp_path / "valid_router.yaml"
        with open(graph_path, "w") as f:
            yaml.dump(
                {
                    "nodes": {
                        "classify": {
                            "type": "router",
                            "prompt": "classify",
                            "routes": {
                                "positive": "handle_positive",
                                "negative": "handle_negative",
                            },
                            "default_route": "handle_neutral",
                        }
                    },
                    "defaults": {"prompts_dir": "prompts"},
                },
                f,
            )

        # Create valid prompt
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "classify.yaml"
        with open(prompt_file, "w") as f:
            yaml.dump(
                {
                    "schema": {
                        "fields": {
                            "intent": {"type": "str", "description": "Classification"}
                        }
                    }
                },
                f,
            )

        issues = check_router_patterns(graph_path, tmp_path)
        assert len(issues) == 0

    @pytest.mark.req("REQ-YG-003")
    def test_invalid_router_graph_multiple_errors(self, tmp_path):
        """Should catch multiple router validation errors."""
        # Create test graph with multiple issues
        graph_path = tmp_path / "invalid_router.yaml"
        with open(graph_path, "w") as f:
            yaml.dump(
                {
                    "nodes": {
                        "classify": {
                            "type": "router",
                            "prompt": "classify",
                            "routes": [
                                "positive",
                                "negative",
                            ],  # Wrong: list instead of dict
                            # Missing default_route
                        }
                    },
                    "edges": [
                        {
                            "from": "input",
                            "to": "classify",  # Wrong: should be list for conditional
                            "condition": "true",
                        }
                    ],
                    "defaults": {"prompts_dir": "prompts"},
                },
                f,
            )

        # Create invalid prompt (wrong field name)
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "classify.yaml"
        with open(prompt_file, "w") as f:
            yaml.dump(
                {
                    "schema": {
                        "fields": {
                            "category": {"type": "str", "description": "Wrong field"}
                        }
                    }
                },
                f,
            )

        issues = check_router_patterns(graph_path, tmp_path)

        # Should have 3 errors: E101 (routes), E102 (schema), E103 (edge)
        error_codes = {issue.code for issue in issues}
        assert "E101" in error_codes  # routes as list
        assert "E102" in error_codes  # wrong schema field
        assert "E103" in error_codes  # conditional edge to single node

        # Should have 1 warning: W101 (missing default_route)
        warning_codes = {issue.code for issue in issues if issue.severity == "warning"}
        assert "W101" in warning_codes
