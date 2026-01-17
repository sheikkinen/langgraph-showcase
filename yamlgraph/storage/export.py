"""JSON Export - Serialize pipeline results.

Provides functions to export pipeline state and results
to JSON format for sharing and archival.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from yamlgraph.config import OUTPUTS_DIR


def export_state(
    state: dict,
    output_dir: str | Path | None = None,
    prefix: str = "export",
) -> Path:
    """Export pipeline state to JSON file.

    Args:
        state: State dictionary to export
        output_dir: Directory for output files (default: outputs/)
        prefix: Filename prefix

    Returns:
        Path to the created file
    """
    if output_dir is None:
        output_dir = OUTPUTS_DIR
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    thread_id = state.get("thread_id", "unknown")
    filename = f"{prefix}_{thread_id}_{timestamp}.json"

    filepath = output_path / filename

    # Convert state to JSON-serializable format
    export_data = _serialize_state(state)

    with open(filepath, "w") as f:
        json.dump(export_data, f, indent=2, default=str)

    return filepath


def _serialize_state(state: dict) -> dict:
    """Convert state to JSON-serializable format.

    Handles Pydantic models and other complex types.

    Args:
        state: State dictionary

    Returns:
        JSON-serializable dictionary
    """
    result = {}

    for key, value in state.items():
        if isinstance(value, BaseModel):
            result[key] = value.model_dump()
        elif hasattr(value, "__dict__"):
            result[key] = _serialize_object(value)
        else:
            result[key] = value

    return result


def _serialize_object(obj: Any) -> Any:
    """Recursively serialize an object.

    Args:
        obj: Object to serialize

    Returns:
        JSON-serializable representation
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    elif isinstance(obj, dict):
        return {k: _serialize_object(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_serialize_object(item) for item in obj]
    elif hasattr(obj, "isoformat"):
        return obj.isoformat()
    else:
        return obj


def load_export(filepath: str | Path) -> dict:
    """Load an exported JSON file.

    Args:
        filepath: Path to JSON file

    Returns:
        Loaded dictionary
    """
    with open(filepath) as f:
        return json.load(f)


def list_exports(
    output_dir: str | Path = "outputs", prefix: str = "export"
) -> list[Path]:
    """List all export files in a directory.

    Args:
        output_dir: Directory to search
        prefix: Filename prefix filter

    Returns:
        List of matching file paths, sorted by modification time
    """
    output_path = Path(output_dir)
    if not output_path.exists():
        return []

    files = list(output_path.glob(f"{prefix}_*.json"))
    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)


def export_summary(state: dict) -> dict:
    """Create a summary export (without full content).

    Useful for quick review of pipeline results.
    Works generically with any Pydantic models in state.

    Args:
        state: Full state dictionary

    Returns:
        Summary dictionary with key information only
    """
    # Internal keys to skip
    internal_keys = frozenset(
        {"_route", "_loop_counts", "thread_id", "topic", "current_step", "error"}
    )

    summary = {
        "thread_id": state.get("thread_id"),
        "topic": state.get("topic"),
        "current_step": state.get("current_step"),
        "error": state.get("error"),
    }

    # Process all non-internal fields generically
    for key, value in state.items():
        if key in internal_keys or value is None:
            continue

        if isinstance(value, BaseModel):
            # Extract scalar fields from any Pydantic model
            summary[key] = _extract_scalar_summary(value)
        elif isinstance(value, str):
            # For strings, include presence only
            summary[f"has_{key}"] = bool(value)

    return summary


def _extract_scalar_summary(model: BaseModel) -> dict[str, Any]:
    """Extract scalar fields from a Pydantic model for summary.

    Args:
        model: Any Pydantic model

    Returns:
        Dict with scalar field names and values (strings truncated)
    """
    result = {}
    for field_name, field_value in model.model_dump().items():
        if isinstance(field_value, str):
            # Truncate long strings
            result[field_name] = (
                field_value[:100] + "..." if len(field_value) > 100 else field_value
            )
        elif isinstance(field_value, (int, float, bool)):
            result[field_name] = field_value
        elif isinstance(field_value, list):
            result[f"{field_name}_count"] = len(field_value)
    return result


def export_result(
    state: dict,
    export_config: dict,
    base_path: str | Path = "outputs",
) -> list[Path]:
    """Export state fields to files.

    Args:
        state: Final graph state
        export_config: Mapping of field -> export settings
        base_path: Base directory for exports

    Returns:
        List of paths to exported files

    Example config:
        {
            "final_summary": {"format": "markdown", "filename": "summary.md"},
            "generated": {"format": "json", "filename": "content.json"},
        }
    """
    base_path = Path(base_path)
    thread_id = state.get("thread_id", "unknown")
    output_dir = base_path / thread_id
    output_dir.mkdir(parents=True, exist_ok=True)

    exported = []

    for field, settings in export_config.items():
        if field not in state or state[field] is None:
            continue

        value = state[field]
        filename = settings.get("filename", f"{field}.txt")
        format_type = settings.get("format", "text")

        file_path = output_dir / filename

        if format_type == "json":
            content = _serialize_to_json(value)
            file_path.write_text(content)
        elif format_type == "markdown":
            content = _serialize_to_markdown(value)
            file_path.write_text(content)
        else:
            file_path.write_text(str(value))

        exported.append(file_path)

    return exported


def _serialize_to_json(value: Any) -> str:
    """Serialize value to JSON string."""
    if isinstance(value, BaseModel):
        return value.model_dump_json(indent=2)
    return json.dumps(value, default=str, indent=2)


def _serialize_to_markdown(value: Any) -> str:
    """Serialize value to Markdown string."""
    if isinstance(value, BaseModel):
        return _pydantic_to_markdown(value)
    return str(value)


def _pydantic_to_markdown(model: BaseModel) -> str:
    """Convert Pydantic model to Markdown."""
    lines = [f"# {model.__class__.__name__}", ""]
    for field, value in model.model_dump().items():
        if isinstance(value, list):
            lines.append(f"## {field.replace('_', ' ').title()}")
            for item in value:
                lines.append(f"- {item}")
            lines.append("")
        else:
            lines.append(f"**{field.replace('_', ' ').title()}**: {value}")
    return "\n".join(lines)
