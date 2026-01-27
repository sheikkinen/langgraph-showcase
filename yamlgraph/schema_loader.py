"""Dynamic Pydantic model generation from YAML schema definitions.

This module enables defining output schemas in YAML prompt files,
making prompts fully self-contained with their expected output structure.

Example YAML schema:
    schema:
      name: MyOutputModel
      fields:
        title:
          type: str
          description: "The output title"
        confidence:
          type: float
          constraints: {ge: 0.0, le: 1.0}
"""

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, create_model

# =============================================================================
# Type Resolution
# =============================================================================

# Mapping from type strings to Python types
TYPE_MAP: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "Any": Any,
}


def normalize_coding_keys(field: dict) -> None:
    """Normalize coding dict keys to strings for JSON serialization safety.

    JSON only supports string keys, so integer keys like {0: "A", 1: "B"}
    become {"0": "A", "1": "B"} after serialization. This function normalizes
    upfront to ensure consistent behavior before and after checkpointer
    round-trips (e.g., Redis).

    Args:
        field: Field definition dict, modified in-place if 'coding' exists

    Example:
        >>> field = {"coding": {0: "Zero", 1: "One"}}
        >>> normalize_coding_keys(field)
        >>> field["coding"]
        {"0": "Zero", "1": "One"}
    """
    coding = field.get("coding")
    if coding is not None and isinstance(coding, dict):
        field["coding"] = {str(k): v for k, v in coding.items()}


def resolve_type(type_str: str, field_name: str | None = None) -> type:
    """Resolve a type string to a Python type.

    Supports:
        - Basic types: str, int, float, bool, Any
        - Generic types: list[str], list[int], dict[str, str]

    Args:
        type_str: Type string like "str", "list[str]", "dict[str, Any]"
        field_name: Optional field name for better error messages

    Returns:
        Python type annotation

    Raises:
        ValueError: If type string is not recognized
    """
    # Check basic types first
    if type_str in TYPE_MAP:
        return TYPE_MAP[type_str]

    # Handle list[T] pattern
    list_match = re.match(r"list\[(\w+)\]", type_str)
    if list_match:
        inner_type = resolve_type(list_match.group(1), field_name)
        return list[inner_type]

    # Handle dict[K, V] pattern
    dict_match = re.match(r"dict\[(\w+),\s*(\w+)\]", type_str)
    if dict_match:
        key_type = resolve_type(dict_match.group(1), field_name)
        value_type = resolve_type(dict_match.group(2), field_name)
        return dict[key_type, value_type]

    # Provide helpful error with supported types
    supported = ", ".join(TYPE_MAP.keys())
    context = f" for field '{field_name}'" if field_name else ""
    raise ValueError(
        f"Unknown type: '{type_str}'{context}. "
        f"Supported types: {supported}, list[T], dict[K, V]"
    )


# =============================================================================
# Model Building
# =============================================================================


def build_pydantic_model(schema: dict) -> type:
    """Build a Pydantic model dynamically from a schema dict.

    Args:
        schema: Schema definition with 'name' and 'fields' keys
            Example:
                {
                    "name": "MyOutputModel",
                    "fields": {
                        "title": {"type": "str", "description": "..."},
                        "score": {"type": "float", "constraints": {"ge": 0}},
                    }
                }

    Returns:
        Dynamically created Pydantic model class
    """
    model_name = schema["name"]
    field_definitions = {}

    for field_name, field_def in schema["fields"].items():
        # Normalize coding keys for JSON serialization safety (FR-007)
        normalize_coding_keys(field_def)

        # Resolve the type - pass field_name for better error messages
        field_type = resolve_type(field_def["type"], field_name)

        # Handle optional fields
        is_optional = field_def.get("optional", False)
        if is_optional:
            field_type = field_type | None

        # Build Field kwargs
        field_kwargs: dict[str, Any] = {}

        if "description" in field_def:
            field_kwargs["description"] = field_def["description"]

        if "default" in field_def:
            field_kwargs["default"] = field_def["default"]
        elif is_optional:
            field_kwargs["default"] = None

        # Add constraints (ge, le, min_length, max_length, etc.)
        if constraints := field_def.get("constraints"):
            field_kwargs.update(constraints)

        # Create field tuple: (type, Field(...))
        if field_kwargs:
            field_definitions[field_name] = (field_type, Field(**field_kwargs))
        else:
            field_definitions[field_name] = (field_type, ...)

    return create_model(model_name, **field_definitions)


# JSON Schema type mapping
JSON_SCHEMA_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def build_pydantic_model_from_json_schema(
    schema: dict, model_name: str = "DynamicOutput"
) -> type:
    """Build a Pydantic model from a JSON Schema-style definition.

    Args:
        schema: JSON Schema with 'type: object' and 'properties'
        model_name: Name for the generated model

    Returns:
        Dynamically created Pydantic model class
    """
    if schema.get("type") != "object":
        raise ValueError("output_schema must have type: object")

    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    field_definitions = {}

    for field_name, field_def in properties.items():
        # Normalize coding keys for JSON serialization safety (FR-007)
        normalize_coding_keys(field_def)

        json_type = field_def.get("type", "string")
        description = field_def.get("description", "")

        # Handle array types
        if json_type == "array":
            items = field_def.get("items", {})
            item_type = JSON_SCHEMA_TYPE_MAP.get(items.get("type", "string"), str)
            field_type = list[item_type]
        # Handle enum types
        elif "enum" in field_def:
            field_type = str  # Enums become str in Pydantic
        else:
            field_type = JSON_SCHEMA_TYPE_MAP.get(json_type, str)

        # Check if required
        is_optional = field_name not in required
        if is_optional:
            field_type = field_type | None

        # Build Field
        field_kwargs: dict[str, Any] = {}
        if description:
            field_kwargs["description"] = description
        if is_optional:
            field_kwargs["default"] = None

        if field_kwargs:
            field_definitions[field_name] = (field_type, Field(**field_kwargs))
        else:
            field_definitions[field_name] = (field_type, ...)

    return create_model(model_name, **field_definitions)


# =============================================================================
# YAML Loading
# =============================================================================


def load_schema_from_yaml(yaml_path: str | Path) -> type | None:
    """Load a Pydantic model from a prompt YAML file's schema block.

    Supports two formats:
    1. Native format (schema: with name/fields)
    2. JSON Schema format (output_schema: with type/properties)

    Args:
        yaml_path: Path to the YAML prompt file

    Returns:
        Dynamically created Pydantic model, or None if no schema defined
    """
    with open(yaml_path) as f:
        config = yaml.safe_load(f)

    # Check for native format first
    if "schema" in config:
        return build_pydantic_model(config["schema"])

    # Check for JSON Schema format (output_schema)
    if "output_schema" in config:
        # Generate model name from file name
        path = Path(yaml_path)
        model_name = "".join(word.title() for word in path.stem.split("_")) + "Output"
        return build_pydantic_model_from_json_schema(
            config["output_schema"], model_name
        )

    return None
