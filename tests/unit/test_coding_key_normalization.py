"""Tests for FR-007: JSON Key Type Coercion.

Ensures coding dict keys are normalized to strings to survive
JSON serialization (e.g., Redis checkpointer round-trips).
"""

from yamlgraph.schema_loader import (
    build_pydantic_model,
    build_pydantic_model_from_json_schema,
    normalize_coding_keys,
)


class TestNormalizeCodingKeys:
    """Tests for normalize_coding_keys function."""

    def test_normalizes_integer_keys_to_strings(self):
        """Integer keys become string keys."""
        field = {"coding": {0: "Zero", 1: "One", 2: "Two"}}
        normalize_coding_keys(field)
        assert field["coding"] == {"0": "Zero", "1": "One", "2": "Two"}

    def test_preserves_string_keys(self):
        """String keys remain unchanged."""
        field = {"coding": {"a": "Alpha", "b": "Beta"}}
        normalize_coding_keys(field)
        assert field["coding"] == {"a": "Alpha", "b": "Beta"}

    def test_handles_mixed_keys(self):
        """Mixed integer and string keys all become strings."""
        field = {"coding": {0: "Zero", "one": "One", 2: "Two"}}
        normalize_coding_keys(field)
        assert field["coding"] == {"0": "Zero", "one": "One", "2": "Two"}

    def test_no_op_when_no_coding(self):
        """Field without coding is unchanged."""
        field = {"type": "str", "description": "test"}
        original = field.copy()
        normalize_coding_keys(field)
        assert field == original

    def test_no_op_when_coding_is_none(self):
        """Field with coding=None is unchanged."""
        field = {"type": "int", "coding": None}
        normalize_coding_keys(field)
        assert field["coding"] is None

    def test_handles_empty_coding(self):
        """Empty coding dict stays empty."""
        field = {"coding": {}}
        normalize_coding_keys(field)
        assert field["coding"] == {}

    def test_survives_json_roundtrip(self):
        """After normalization, JSON round-trip preserves lookup capability."""
        import json

        field = {"coding": {0: "Erinomainen", 1: "Hyvä", 2: "Tyydyttävä"}}
        normalize_coding_keys(field)

        # Simulate JSON serialization (Redis checkpointer)
        serialized = json.dumps(field)
        restored = json.loads(serialized)

        # Lookup should work with string keys
        assert restored["coding"]["0"] == "Erinomainen"
        assert restored["coding"]["1"] == "Hyvä"
        assert restored["coding"]["2"] == "Tyydyttävä"

        # Same as original (after normalization)
        assert restored["coding"] == field["coding"]


class TestBuildPydanticModelNormalization:
    """Integration tests: normalization during model building."""

    def test_build_pydantic_model_normalizes_coding(self):
        """build_pydantic_model normalizes coding keys."""
        schema = {
            "name": "TestModel",
            "fields": {
                "score": {
                    "type": "int",
                    "description": "Rating score",
                    "coding": {0: "Poor", 1: "Fair", 2: "Good"},
                }
            },
        }

        # Build the model - should normalize coding keys in schema
        _model = build_pydantic_model(schema)

        # Verify the schema was modified (coding keys normalized)
        assert schema["fields"]["score"]["coding"] == {
            "0": "Poor",
            "1": "Fair",
            "2": "Good",
        }

    def test_build_json_schema_model_normalizes_coding(self):
        """build_pydantic_model_from_json_schema normalizes coding keys."""
        schema = {
            "type": "object",
            "properties": {
                "rating": {
                    "type": "integer",
                    "description": "User rating",
                    "coding": {1: "Bad", 2: "OK", 3: "Great"},
                }
            },
            "required": ["rating"],
        }

        # Build the model - should normalize coding keys
        _model = build_pydantic_model_from_json_schema(schema, "RatingModel")

        # Verify the schema was modified
        assert schema["properties"]["rating"]["coding"] == {
            "1": "Bad",
            "2": "OK",
            "3": "Great",
        }
