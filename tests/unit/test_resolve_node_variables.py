"""Tests for resolve_node_variables shared utility."""

from yamlgraph.utils.expressions import resolve_node_variables


class TestResolveNodeVariables:
    """Test resolve_node_variables function."""

    def test_with_templates_resolves_state_expressions(self):
        """Variables with templates should resolve state expressions."""
        state = {"name": "Alice", "age": 30}
        templates = {"user": "{state.name}", "years": "{state.age}"}

        result = resolve_node_variables(templates, state)

        assert result == {"user": "Alice", "years": 30}

    def test_with_templates_preserves_types(self):
        """Templates should preserve original types (lists, dicts)."""
        state = {"items": [1, 2, 3], "config": {"key": "value"}}
        templates = {"list_var": "{state.items}", "dict_var": "{state.config}"}

        result = resolve_node_variables(templates, state)

        assert result == {"list_var": [1, 2, 3], "dict_var": {"key": "value"}}

    def test_with_templates_supports_nested_state(self):
        """Templates should resolve nested state paths."""
        state = {"user": {"profile": {"name": "Bob"}}}
        templates = {"username": "{state.user.profile.name}"}

        result = resolve_node_variables(templates, state)

        assert result == {"username": "Bob"}

    def test_without_templates_returns_filtered_state(self):
        """Empty templates should return filtered state (no _ keys, no None)."""
        state = {
            "name": "Alice",
            "age": 30,
            "_internal": "hidden",
            "empty": None,
            "valid": "value",
        }

        result = resolve_node_variables({}, state)

        assert result == {"name": "Alice", "age": 30, "valid": "value"}
        assert "_internal" not in result
        assert "empty" not in result

    def test_without_templates_none_returns_filtered_state(self):
        """None templates should behave like empty templates."""
        state = {"name": "Alice", "_secret": "hidden"}

        result = resolve_node_variables(None, state)

        assert result == {"name": "Alice"}

    def test_with_templates_keeps_static_values(self):
        """Non-expression values in templates should be kept as-is."""
        state = {"name": "Alice"}
        templates = {"greeting": "Hello", "user": "{state.name}"}

        result = resolve_node_variables(templates, state)

        assert result == {"greeting": "Hello", "user": "Alice"}

    def test_with_missing_state_key_returns_none(self):
        """Missing state keys should return None."""
        state = {}
        templates = {"missing": "{state.nonexistent}"}

        result = resolve_node_variables(templates, state)

        # resolve_template returns None for missing keys
        assert result == {"missing": None}

    def test_empty_state_without_templates(self):
        """Empty state without templates should return empty dict."""
        result = resolve_node_variables({}, {})

        assert result == {}
