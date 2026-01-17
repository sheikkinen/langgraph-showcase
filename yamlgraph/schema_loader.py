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


# =============================================================================
# YAML Loading
# =============================================================================


def load_schema_from_yaml(yaml_path: str) -> type | None:
    """Load a Pydantic model from a prompt YAML file's schema block.

    Args:
        yaml_path: Path to the YAML prompt file

    Returns:
        Dynamically created Pydantic model, or None if no schema defined
    """
    with open(yaml_path) as f:
        config = yaml.safe_load(f)

    if "schema" not in config:
        return None

    return build_pydantic_model(config["schema"])
