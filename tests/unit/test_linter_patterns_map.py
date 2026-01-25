"""Tests for map pattern linter validations."""

from yamlgraph.tools.linter_patterns.map import (
    check_map_node_structure,
    check_map_node_types,
    check_map_patterns,
)


class TestMapNodeStructure:
    """Test map node structural validation."""

    def test_valid_map_structure(self):
        """Should pass valid map structure."""
        node_config = {
            "type": "map",
            "over": "{state.items}",
            "as": "item",
            "node": {"prompt": "process_item", "state_key": "result"},
            "collect": "results",
        }

        issues = check_map_node_structure("test_map", node_config)
        assert len(issues) == 0

    def test_missing_over_field(self):
        """Should error when 'over' field is missing."""
        node_config = {
            "type": "map",
            "as": "item",
            "node": {"prompt": "process_item", "state_key": "result"},
            "collect": "results",
        }

        issues = check_map_node_structure("test_map", node_config)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].code == "E201"
        assert "missing required field 'over'" in issues[0].message

    def test_missing_as_field(self):
        """Should error when 'as' field is missing."""
        node_config = {
            "type": "map",
            "over": "{state.items}",
            "node": {"prompt": "process_item", "state_key": "result"},
            "collect": "results",
        }

        issues = check_map_node_structure("test_map", node_config)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].code == "E202"
        assert "missing required field 'as'" in issues[0].message

    def test_missing_node_field(self):
        """Should error when 'node' field is missing."""
        node_config = {
            "type": "map",
            "over": "{state.items}",
            "as": "item",
            "collect": "results",
        }

        issues = check_map_node_structure("test_map", node_config)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].code == "E203"
        assert "missing required field 'node'" in issues[0].message

    def test_missing_collect_field(self):
        """Should error when 'collect' field is missing."""
        node_config = {
            "type": "map",
            "over": "{state.items}",
            "as": "item",
            "node": {"prompt": "process_item", "state_key": "result"},
        }

        issues = check_map_node_structure("test_map", node_config)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].code == "E204"
        assert "missing required field 'collect'" in issues[0].message

    def test_top_level_prompt_error(self):
        """Should error when 'prompt' exists at top level."""
        node_config = {
            "type": "map",
            "over": "{state.items}",
            "as": "item",
            "prompt": "should_not_be_here",  # Wrong: should be in nested node
            "node": {"prompt": "process_item", "state_key": "result"},
            "collect": "results",
        }

        issues = check_map_node_structure("test_map", node_config)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].code == "E205"
        assert "should not have top-level 'prompt' field" in issues[0].message

    def test_multiple_missing_fields(self):
        """Should report all missing required fields."""
        node_config = {
            "type": "map"
            # Missing: over, as, node, collect
        }

        issues = check_map_node_structure("test_map", node_config)
        error_codes = {issue.code for issue in issues if issue.severity == "error"}
        assert "E201" in error_codes  # missing over
        assert "E202" in error_codes  # missing as
        assert "E203" in error_codes  # missing node
        assert "E204" in error_codes  # missing collect


class TestMapNodeTypes:
    """Test map node field type validation."""

    def test_valid_over_field(self):
        """Should pass valid 'over' field format."""
        node_config = {
            "type": "map",
            "over": "{state.items}",
            "as": "item",
            "node": {"prompt": "process_item"},
            "collect": "results",
        }

        issues = check_map_node_types("test_map", node_config)
        assert len(issues) == 0

    def test_invalid_over_field_warning(self):
        """Should warn when 'over' field doesn't look like state reference."""
        node_config = {
            "type": "map",
            "over": "not_a_state_ref",  # Should be {state.something}
            "as": "item",
            "node": {"prompt": "process_item"},
            "collect": "results",
        }

        issues = check_map_node_types("test_map", node_config)
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert issues[0].code == "W201"
        assert "should reference state list" in issues[0].message

    def test_nested_node_missing_prompt_warning(self):
        """Should warn when nested node lacks prompt or type."""
        node_config = {
            "type": "map",
            "over": "{state.items}",
            "as": "item",
            "node": {
                "state_key": "result"
                # Missing prompt or type
            },
            "collect": "results",
        }

        issues = check_map_node_types("test_map", node_config)
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert issues[0].code == "W202"
        assert "missing prompt or type" in issues[0].message


class TestMapPatternsIntegration:
    """Test map pattern validation integration."""

    def test_valid_map_graph(self, tmp_path):
        """Should pass valid map graph."""
        graph_content = """
nodes:
  process_items:
    type: map
    over: "{state.items}"
    as: item
    node:
      prompt: process_item
      state_key: result
    collect: results
"""
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text(graph_content)

        issues = check_map_patterns(graph_file)
        assert len(issues) == 0

    def test_invalid_map_graph(self, tmp_path):
        """Should catch invalid map graph."""
        graph_content = """
nodes:
  bad_map:
    type: map
    # Missing all required fields
"""
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text(graph_content)

        issues = check_map_patterns(graph_file)
        # Should have 4 errors: E201, E202, E203, E204
        error_issues = [i for i in issues if i.severity == "error"]
        assert len(error_issues) == 4
        error_codes = {issue.code for issue in error_issues}
        assert error_codes == {"E201", "E202", "E203", "E204"}

    def test_mixed_nodes_only_validates_maps(self, tmp_path):
        """Should only validate map nodes, ignore others."""
        graph_content = """
nodes:
  llm_node:
    type: llm
    prompt: hello
  router_node:
    type: router
    routes: {"pos": "handle_pos"}
  map_node:
    type: map
    # Missing required fields
"""
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text(graph_content)

        issues = check_map_patterns(graph_file)
        # Should only validate the map_node
        assert len(issues) > 0
        for issue in issues:
            assert "map_node" in issue.message
