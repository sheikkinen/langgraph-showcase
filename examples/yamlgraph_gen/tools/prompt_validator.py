"""Prompt YAML structure validator for yamlgraph-generator."""

from pathlib import Path

import yaml

REQUIRED_KEYS = {"system", "user"}
OPTIONAL_KEYS = {"schema", "metadata", "examples", "description"}


def validate_prompt_file(path: str) -> dict:
    """Validate a single prompt YAML file.

    Returns dict: {valid: bool, errors: list[str], warnings: list[str]}
    """
    errors = []
    warnings = []

    try:
        content = Path(path).read_text()
    except FileNotFoundError:
        return {"valid": False, "errors": [f"File not found: {path}"], "warnings": []}

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        return {"valid": False, "errors": [f"Invalid YAML: {e}"], "warnings": []}

    if not isinstance(data, dict):
        return {
            "valid": False,
            "errors": ["Prompt must be a YAML mapping"],
            "warnings": [],
        }

    # Check required keys
    for key in REQUIRED_KEYS:
        if key not in data:
            errors.append(f"Missing required key: {key}")

    # Check for unknown keys
    all_keys = REQUIRED_KEYS | OPTIONAL_KEYS
    for key in data:
        if key not in all_keys:
            warnings.append(f"Unknown key: {key}")

    # Validate schema if present
    if "schema" in data:
        schema_result = _validate_schema(data["schema"])
        errors.extend(schema_result["errors"])
        warnings.extend(schema_result["warnings"])

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def _validate_schema(schema: dict) -> dict:
    """Validate schema block structure."""
    errors = []
    warnings = []

    if not isinstance(schema, dict):
        return {"errors": ["Schema must be a mapping"], "warnings": []}

    if "name" not in schema:
        errors.append("Schema missing 'name'")

    if "fields" not in schema:
        errors.append("Schema missing 'fields'")
    elif isinstance(schema["fields"], dict):
        for field_name, field_def in schema["fields"].items():
            if not isinstance(field_def, dict):
                errors.append(f"Field '{field_name}' must be a mapping")
            elif "type" not in field_def:
                warnings.append(f"Field '{field_name}' missing 'type'")

    return {"errors": errors, "warnings": warnings}


def validate_prompt_directory(directory: str) -> dict:
    """Validate all prompt files in a directory.

    Returns dict: {valid: bool, structure_valid: bool, structure_errors: list, results: dict}
    """
    results = {}
    all_valid = True
    all_errors = []

    dir_path = Path(directory)
    if not dir_path.exists():
        return {
            "valid": False,
            "structure_valid": False,
            "structure_errors": [f"Directory not found: {directory}"],
            "results": {},
        }

    for path in dir_path.glob("*.yaml"):
        result = validate_prompt_file(str(path))
        results[str(path)] = result
        if not result["valid"]:
            all_valid = False
            all_errors.extend([f"{path.name}: {e}" for e in result["errors"]])

    return {
        "valid": all_valid,
        "structure_valid": all_valid,
        "structure_errors": all_errors,
        "results": results,
    }


def validate_prompt_directory_node(state: dict) -> dict:
    """Yamlgraph node wrapper for validate_prompt_directory.

    Extracts output_dir from state and validates prompts subdirectory.
    """
    output_dir = state.get("output_dir", "")
    directory = str(Path(output_dir) / "prompts")
    return validate_prompt_directory(directory)
