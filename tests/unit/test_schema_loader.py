"""Tests for YAML schema loader - dynamic Pydantic model generation.

TDD: RED phase - write tests first for schema_loader module.
"""

import pytest
from pydantic import ValidationError


class TestBuildPydanticModel:
    """Tests for build_pydantic_model function."""

    @pytest.mark.req("REQ-YG-044")
    def test_simple_string_field(self):
        """Build model with single string field."""
        from yamlgraph.schema_loader import build_pydantic_model

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

    @pytest.mark.req("REQ-YG-044")
    def test_multiple_fields(self):
        """Build model with multiple field types."""
        from yamlgraph.schema_loader import build_pydantic_model

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

    @pytest.mark.req("REQ-YG-044")
    def test_list_field(self):
        """Build model with list field."""
        from yamlgraph.schema_loader import build_pydantic_model

        schema = {
            "name": "ListModel",
            "fields": {
                "items": {"type": "list[str]", "description": "List of items"},
            },
        }

        Model = build_pydantic_model(schema)

        instance = Model(items=["a", "b", "c"])
        assert instance.items == ["a", "b", "c"]

    @pytest.mark.req("REQ-YG-044")
    def test_optional_field(self):
        """Build model with optional field."""
        from yamlgraph.schema_loader import build_pydantic_model

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

    @pytest.mark.req("REQ-YG-044")
    def test_field_with_default(self):
        """Build model with default value."""
        from yamlgraph.schema_loader import build_pydantic_model

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

    @pytest.mark.req("REQ-YG-044")
    def test_constraints_ge_le(self):
        """Build model with ge/le constraints."""
        from yamlgraph.schema_loader import build_pydantic_model

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

    @pytest.mark.req("REQ-YG-044")
    def test_field_description_in_schema(self):
        """Field descriptions should be accessible."""
        from yamlgraph.schema_loader import build_pydantic_model

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

    @pytest.mark.req("REQ-YG-044")
    def test_tone_classification_schema(self):
        """Build ToneClassification equivalent from schema."""
        from yamlgraph.schema_loader import build_pydantic_model

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

    @pytest.mark.req("REQ-YG-044")
    def test_load_schema_returns_none_if_no_schema(self, tmp_path):
        """Return None if prompt has no schema block."""
        from yamlgraph.schema_loader import load_schema_from_yaml

        prompt_file = tmp_path / "simple.yaml"
        prompt_file.write_text("""
name: simple_prompt
system: You are helpful.
user: "{input}"
""")

        result = load_schema_from_yaml(str(prompt_file))
        assert result is None

    @pytest.mark.req("REQ-YG-044")
    def test_load_schema_builds_model(self, tmp_path):
        """Load and build model from prompt with schema."""
        from yamlgraph.schema_loader import load_schema_from_yaml

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

    @pytest.mark.req("REQ-YG-044")
    def test_resolve_basic_types(self):
        """Resolve basic type strings."""
        from yamlgraph.schema_loader import resolve_type

        assert resolve_type("str") is str
        assert resolve_type("int") is int
        assert resolve_type("float") is float
        assert resolve_type("bool") is bool

    @pytest.mark.req("REQ-YG-044")
    def test_resolve_list_types(self):
        """Resolve list type strings."""
        from yamlgraph.schema_loader import resolve_type

        result = resolve_type("list[str]")
        assert result == list[str]

        result = resolve_type("list[int]")
        assert result == list[int]

    @pytest.mark.req("REQ-YG-044")
    def test_resolve_dict_types(self):
        """Resolve dict type strings."""
        from yamlgraph.schema_loader import resolve_type

        result = resolve_type("dict[str, str]")
        assert result == dict[str, str]

    @pytest.mark.req("REQ-YG-044")
    def test_resolve_any_type(self):
        """Resolve Any type."""
        from typing import Any

        from yamlgraph.schema_loader import resolve_type

        result = resolve_type("Any")
        assert result is Any

    @pytest.mark.req("REQ-YG-044")
    def test_invalid_type_raises(self):
        """Invalid type string raises ValueError."""
        from yamlgraph.schema_loader import resolve_type

        with pytest.raises(ValueError, match="Unknown type"):
            resolve_type("InvalidType")


class TestBuildPydanticModelFromJsonSchema:
    """Tests for build_pydantic_model_from_json_schema function."""

    @pytest.mark.req("REQ-YG-044")
    def test_simple_object_schema(self):
        """Build model from basic JSON Schema."""
        from yamlgraph.schema_loader import build_pydantic_model_from_json_schema

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name"},
                "count": {"type": "integer", "description": "The count"},
            },
            "required": ["name", "count"],
        }

        Model = build_pydantic_model_from_json_schema(schema, "TestModel")

        assert Model.__name__ == "TestModel"
        instance = Model(name="test", count=5)
        assert instance.name == "test"
        assert instance.count == 5

    @pytest.mark.req("REQ-YG-044")
    def test_optional_fields_from_required(self):
        """Fields not in required list should be optional."""
        from yamlgraph.schema_loader import build_pydantic_model_from_json_schema

        schema = {
            "type": "object",
            "properties": {
                "required_field": {"type": "string"},
                "optional_field": {"type": "string"},
            },
            "required": ["required_field"],
        }

        Model = build_pydantic_model_from_json_schema(schema)

        # Should work without optional field
        instance = Model(required_field="hello")
        assert instance.required_field == "hello"
        assert instance.optional_field is None

    @pytest.mark.req("REQ-YG-044")
    def test_array_type(self):
        """Handle array type with items."""
        from yamlgraph.schema_loader import build_pydantic_model_from_json_schema

        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tags",
                },
            },
            "required": ["tags"],
        }

        Model = build_pydantic_model_from_json_schema(schema)

        instance = Model(tags=["a", "b", "c"])
        assert instance.tags == ["a", "b", "c"]

    @pytest.mark.req("REQ-YG-044")
    def test_enum_type_becomes_string(self):
        """Enum fields should become string type."""
        from yamlgraph.schema_loader import build_pydantic_model_from_json_schema

        schema = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "active", "completed"],
                    "description": "Status",
                },
            },
            "required": ["status"],
        }

        Model = build_pydantic_model_from_json_schema(schema)

        instance = Model(status="active")
        assert instance.status == "active"

    @pytest.mark.req("REQ-YG-044")
    def test_all_json_schema_types(self):
        """Handle all JSON Schema basic types."""
        from yamlgraph.schema_loader import build_pydantic_model_from_json_schema

        schema = {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "count": {"type": "integer"},
                "score": {"type": "number"},
                "active": {"type": "boolean"},
            },
            "required": ["text", "count", "score", "active"],
        }

        Model = build_pydantic_model_from_json_schema(schema)

        instance = Model(text="hello", count=5, score=0.9, active=True)
        assert instance.text == "hello"
        assert instance.count == 5
        assert instance.score == 0.9
        assert instance.active is True

    @pytest.mark.req("REQ-YG-044")
    def test_non_object_schema_raises(self):
        """Schema must have type: object."""
        from yamlgraph.schema_loader import build_pydantic_model_from_json_schema

        schema = {"type": "array", "items": {"type": "string"}}

        with pytest.raises(ValueError, match="must have type: object"):
            build_pydantic_model_from_json_schema(schema)

    @pytest.mark.req("REQ-YG-044")
    def test_empty_properties(self):
        """Handle schema with no properties."""
        from yamlgraph.schema_loader import build_pydantic_model_from_json_schema

        schema = {"type": "object"}

        Model = build_pydantic_model_from_json_schema(schema)
        instance = Model()
        assert instance is not None

    @pytest.mark.req("REQ-YG-044")
    def test_description_preserved(self):
        """Field descriptions should be accessible."""
        from yamlgraph.schema_loader import build_pydantic_model_from_json_schema

        schema = {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The greeting"},
            },
            "required": ["message"],
        }

        Model = build_pydantic_model_from_json_schema(schema)
        field_info = Model.model_fields["message"]
        assert field_info.description == "The greeting"


class TestLoadSchemaFromYamlOutputSchema:
    """Tests for loading output_schema (JSON Schema format) from YAML."""

    @pytest.mark.req("REQ-YG-044")
    def test_load_output_schema_builds_model(self, tmp_path):
        """Load and build model from prompt with output_schema."""
        from yamlgraph.schema_loader import load_schema_from_yaml

        prompt_file = tmp_path / "json_schema_prompt.yaml"
        prompt_file.write_text("""
name: analyze_text
version: "1.0"

output_schema:
  type: object
  properties:
    sentiment:
      type: string
      description: "Detected sentiment"
    confidence:
      type: number
      description: "Confidence score"
  required:
    - sentiment
    - confidence

system: You are a sentiment analyzer.
user: "Analyze: {text}"
""")

        Model = load_schema_from_yaml(str(prompt_file))

        assert Model is not None
        # Model name derived from filename: json_schema_prompt -> JsonSchemaPromptOutput
        assert Model.__name__ == "JsonSchemaPromptOutput"

        instance = Model(sentiment="positive", confidence=0.9)
        assert instance.sentiment == "positive"

    @pytest.mark.req("REQ-YG-044")
    def test_native_schema_takes_precedence(self, tmp_path):
        """If both schema and output_schema exist, native schema wins."""
        from yamlgraph.schema_loader import load_schema_from_yaml

        prompt_file = tmp_path / "both_schemas.yaml"
        prompt_file.write_text("""
name: test_prompt

schema:
  name: NativeModel
  fields:
    native_field:
      type: str
      description: "From native schema"

output_schema:
  type: object
  properties:
    json_field:
      type: string
  required:
    - json_field

system: Test
user: "{input}"
""")

        Model = load_schema_from_yaml(str(prompt_file))

        assert Model.__name__ == "NativeModel"
        assert "native_field" in Model.model_fields
        assert "json_field" not in Model.model_fields
