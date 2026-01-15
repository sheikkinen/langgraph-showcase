"""Tests for YAML schema loader - dynamic Pydantic model generation.

TDD: RED phase - write tests first for schema_loader module.
"""

import pytest
from pydantic import ValidationError


class TestBuildPydanticModel:
    """Tests for build_pydantic_model function."""

    def test_simple_string_field(self):
        """Build model with single string field."""
        from showcase.schema_loader import build_pydantic_model

        schema = {
            "name": "SimpleModel",
            "fields": {
                "message": {
                    "type": "str",
                    "description": "A simple message",
                }
            },
        }

        Model = build_pydantic_model(schema)

        assert Model.__name__ == "SimpleModel"
        instance = Model(message="hello")
        assert instance.message == "hello"

    def test_multiple_fields(self):
        """Build model with multiple field types."""
        from showcase.schema_loader import build_pydantic_model

        schema = {
            "name": "MultiFieldModel",
            "fields": {
                "name": {"type": "str", "description": "Name"},
                "count": {"type": "int", "description": "Count"},
                "score": {"type": "float", "description": "Score"},
                "active": {"type": "bool", "description": "Is active"},
            },
        }

        Model = build_pydantic_model(schema)

        instance = Model(name="test", count=5, score=0.9, active=True)
        assert instance.name == "test"
        assert instance.count == 5
        assert instance.score == 0.9
        assert instance.active is True

    def test_list_field(self):
        """Build model with list field."""
        from showcase.schema_loader import build_pydantic_model

        schema = {
            "name": "ListModel",
            "fields": {
                "items": {"type": "list[str]", "description": "List of items"},
            },
        }

        Model = build_pydantic_model(schema)

        instance = Model(items=["a", "b", "c"])
        assert instance.items == ["a", "b", "c"]

    def test_optional_field(self):
        """Build model with optional field."""
        from showcase.schema_loader import build_pydantic_model

        schema = {
            "name": "OptionalModel",
            "fields": {
                "required_field": {"type": "str", "description": "Required"},
                "optional_field": {
                    "type": "str",
                    "description": "Optional",
                    "optional": True,
                },
            },
        }

        Model = build_pydantic_model(schema)

        # Should work without optional field
        instance = Model(required_field="hello")
        assert instance.required_field == "hello"
        assert instance.optional_field is None

    def test_field_with_default(self):
        """Build model with default value."""
        from showcase.schema_loader import build_pydantic_model

        schema = {
            "name": "DefaultModel",
            "fields": {
                "name": {"type": "str", "description": "Name"},
                "count": {"type": "int", "description": "Count", "default": 10},
            },
        }

        Model = build_pydantic_model(schema)

        instance = Model(name="test")
        assert instance.count == 10

    def test_constraints_ge_le(self):
        """Build model with ge/le constraints."""
        from showcase.schema_loader import build_pydantic_model

        schema = {
            "name": "ConstrainedModel",
            "fields": {
                "score": {
                    "type": "float",
                    "description": "Score between 0 and 1",
                    "constraints": {"ge": 0.0, "le": 1.0},
                },
            },
        }

        Model = build_pydantic_model(schema)

        # Valid value
        instance = Model(score=0.5)
        assert instance.score == 0.5

        # Invalid - below minimum
        with pytest.raises(ValidationError):
            Model(score=-0.1)

        # Invalid - above maximum
        with pytest.raises(ValidationError):
            Model(score=1.5)

    def test_field_description_in_schema(self):
        """Field descriptions should be accessible."""
        from showcase.schema_loader import build_pydantic_model

        schema = {
            "name": "DescribedModel",
            "fields": {
                "message": {
                    "type": "str",
                    "description": "The greeting message",
                },
            },
        }

        Model = build_pydantic_model(schema)

        # Check field info contains description
        field_info = Model.model_fields["message"]
        assert field_info.description == "The greeting message"


class TestToneClassificationSchema:
    """Test building ToneClassification model from YAML schema."""

    def test_tone_classification_schema(self):
        """Build ToneClassification equivalent from schema."""
        from showcase.schema_loader import build_pydantic_model

        schema = {
            "name": "ToneClassification",
            "fields": {
                "tone": {
                    "type": "str",
                    "description": "Detected tone: positive, negative, or neutral",
                },
                "confidence": {
                    "type": "float",
                    "description": "Confidence score 0-1",
                    "constraints": {"ge": 0.0, "le": 1.0},
                },
                "reasoning": {
                    "type": "str",
                    "description": "Explanation for the classification",
                },
            },
        }

        Model = build_pydantic_model(schema)

        instance = Model(
            tone="positive",
            confidence=0.95,
            reasoning="The message expresses enthusiasm",
        )

        assert instance.tone == "positive"
        assert instance.confidence == 0.95
        assert instance.reasoning == "The message expresses enthusiasm"


class TestLoadSchemaFromYaml:
    """Tests for loading schema from prompt YAML files."""

    def test_load_schema_returns_none_if_no_schema(self, tmp_path):
        """Return None if prompt has no schema block."""
        from showcase.schema_loader import load_schema_from_yaml

        prompt_file = tmp_path / "simple.yaml"
        prompt_file.write_text("""
name: simple_prompt
system: You are helpful.
user: "{input}"
""")

        result = load_schema_from_yaml(str(prompt_file))
        assert result is None

    def test_load_schema_builds_model(self, tmp_path):
        """Load and build model from prompt with schema."""
        from showcase.schema_loader import load_schema_from_yaml

        prompt_file = tmp_path / "with_schema.yaml"
        prompt_file.write_text("""
name: classify_tone
version: "1.0"

schema:
  name: ToneClassification
  fields:
    tone:
      type: str
      description: "Detected tone"
    confidence:
      type: float
      description: "Confidence score"
      constraints:
        ge: 0.0
        le: 1.0

system: You are a tone classifier.
user: "Classify: {message}"
""")

        Model = load_schema_from_yaml(str(prompt_file))

        assert Model is not None
        assert Model.__name__ == "ToneClassification"

        instance = Model(tone="positive", confidence=0.9)
        assert instance.tone == "positive"


class TestTypeResolution:
    """Tests for resolving type strings to Python types."""

    def test_resolve_basic_types(self):
        """Resolve basic type strings."""
        from showcase.schema_loader import resolve_type

        assert resolve_type("str") is str
        assert resolve_type("int") is int
        assert resolve_type("float") is float
        assert resolve_type("bool") is bool

    def test_resolve_list_types(self):
        """Resolve list type strings."""
        from showcase.schema_loader import resolve_type

        result = resolve_type("list[str]")
        assert result == list[str]

        result = resolve_type("list[int]")
        assert result == list[int]

    def test_resolve_dict_types(self):
        """Resolve dict type strings."""
        from showcase.schema_loader import resolve_type

        result = resolve_type("dict[str, str]")
        assert result == dict[str, str]

    def test_resolve_any_type(self):
        """Resolve Any type."""
        from typing import Any

        from showcase.schema_loader import resolve_type

        result = resolve_type("Any")
        assert result is Any

    def test_invalid_type_raises(self):
        """Invalid type string raises ValueError."""
        from showcase.schema_loader import resolve_type

        with pytest.raises(ValueError, match="Unknown type"):
            resolve_type("InvalidType")
