"""Tests for YAML state configuration parsing.

Tests the parse_state_config function and state: section handling
in build_state_class.
"""

from typing import Any

from yamlgraph.models.state_builder import (
    TYPE_MAP,
    build_state_class,
    parse_state_config,
)


class TestParseStateConfig:
    """Tests for parse_state_config function."""

    def test_empty_config(self):
        """Empty state config returns empty dict."""
        result = parse_state_config({})
        assert result == {}

    def test_simple_str_type(self):
        """Parse 'str' type."""
        result = parse_state_config({"concept": "str"})
        assert result == {"concept": str}

    def test_simple_int_type(self):
        """Parse 'int' type."""
        result = parse_state_config({"count": "int"})
        assert result == {"count": int}

    def test_simple_float_type(self):
        """Parse 'float' type."""
        result = parse_state_config({"score": "float"})
        assert result == {"score": float}

    def test_simple_bool_type(self):
        """Parse 'bool' type."""
        result = parse_state_config({"enabled": "bool"})
        assert result == {"enabled": bool}

    def test_simple_list_type(self):
        """Parse 'list' type."""
        result = parse_state_config({"items": "list"})
        assert result == {"items": list}

    def test_simple_dict_type(self):
        """Parse 'dict' type."""
        result = parse_state_config({"metadata": "dict"})
        assert result == {"metadata": dict}

    def test_any_type(self):
        """Parse 'any' type."""
        result = parse_state_config({"data": "any"})
        assert result == {"data": Any}

    def test_type_aliases(self):
        """Type aliases like 'string', 'integer', 'boolean' work."""
        result = parse_state_config(
            {
                "name": "string",
                "age": "integer",
                "active": "boolean",
            }
        )
        assert result == {"name": str, "age": int, "active": bool}

    def test_case_insensitive(self):
        """Type names are case-insensitive."""
        result = parse_state_config(
            {
                "a": "STR",
                "b": "Int",
                "c": "FLOAT",
            }
        )
        assert result == {"a": str, "b": int, "c": float}

    def test_multiple_fields(self):
        """Parse multiple fields."""
        result = parse_state_config(
            {
                "concept": "str",
                "count": "int",
                "score": "float",
            }
        )
        assert result == {"concept": str, "count": int, "score": float}

    def test_unknown_type_defaults_to_any(self):
        """Unknown type strings default to Any."""
        result = parse_state_config({"custom": "unknown_type"})
        assert result == {"custom": Any}

    def test_non_string_value_defaults_to_any(self):
        """Non-string values default to Any."""
        result = parse_state_config(
            {
                "nested": {"type": "str"},  # Dict value, not string
                "number": 123,  # Int value, not string
            }
        )
        assert result == {"nested": Any, "number": Any}


class TestTypeMap:
    """Tests for TYPE_MAP constant."""

    def test_all_basic_types_present(self):
        """TYPE_MAP contains all basic Python types."""
        assert "str" in TYPE_MAP
        assert "int" in TYPE_MAP
        assert "float" in TYPE_MAP
        assert "bool" in TYPE_MAP
        assert "list" in TYPE_MAP
        assert "dict" in TYPE_MAP
        assert "any" in TYPE_MAP

    def test_aliases_present(self):
        """TYPE_MAP contains common aliases."""
        assert "string" in TYPE_MAP
        assert "integer" in TYPE_MAP
        assert "boolean" in TYPE_MAP


class TestBuildStateClassWithStateConfig:
    """Tests for build_state_class with state: section."""

    def test_state_section_adds_fields(self):
        """State section fields are included in generated class."""
        config = {
            "state": {"concept": "str", "count": "int"},
            "nodes": {},
            "edges": [],
        }
        state_class = build_state_class(config)
        annotations = state_class.__annotations__

        assert "concept" in annotations
        assert "count" in annotations

    def test_state_section_empty(self):
        """Empty state section doesn't break build."""
        config = {
            "state": {},
            "nodes": {},
            "edges": [],
        }
        state_class = build_state_class(config)
        # Should still have base fields
        assert "thread_id" in state_class.__annotations__

    def test_state_section_missing(self):
        """Missing state section is handled."""
        config = {
            "nodes": {},
            "edges": [],
        }
        state_class = build_state_class(config)
        # Should still have base fields
        assert "thread_id" in state_class.__annotations__

    def test_custom_field_overrides_common(self):
        """Custom state field can override common field type."""
        config = {
            "state": {"topic": "int"},  # Override str default
            "nodes": {},
            "edges": [],
        }
        state_class = build_state_class(config)
        # The custom field should be present
        assert "topic" in state_class.__annotations__

    def test_storyboard_example(self):
        """Test storyboard-style config with concept field."""
        config = {
            "state": {"concept": "str"},
            "nodes": {
                "expand_story": {
                    "type": "llm",
                    "state_key": "story",
                }
            },
            "edges": [],
        }
        state_class = build_state_class(config)
        annotations = state_class.__annotations__

        # Custom field from state section
        assert "concept" in annotations
        # Output field from node
        assert "story" in annotations
        # Base infrastructure fields
        assert "thread_id" in annotations
        assert "errors" in annotations
