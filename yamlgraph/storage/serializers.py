"""Serialization utilities for Redis checkpointer.

Extracted from simple_redis.py to keep modules under 400 lines.
"""

from __future__ import annotations

import base64
from collections import ChainMap
from datetime import datetime
from typing import Any
from uuid import UUID

import orjson


def serialize_key(key: Any) -> str:
    """Serialize a dict key to a JSON-safe string.

    Handles tuple keys from LangGraph's channel_versions and versions_seen.
    """
    if isinstance(key, str):
        return key
    if isinstance(key, tuple):
        # Mark as tuple for deserialization
        return f"__tuple__:{orjson.dumps(key).decode()}"
    # Fallback: convert to string
    return str(key)


def deserialize_key(key: str) -> Any:
    """Deserialize a stringified key back to its original type."""
    if key.startswith("__tuple__:"):
        json_part = key[len("__tuple__:") :]
        return tuple(orjson.loads(json_part))
    return key


def stringify_keys(obj: Any) -> Any:
    """Recursively convert non-string dict keys to JSON-safe strings."""
    if isinstance(obj, dict):
        return {serialize_key(k): stringify_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [stringify_keys(item) for item in obj]
    return obj


def unstringify_keys(obj: Any) -> Any:
    """Recursively convert stringified keys back to original types."""
    if isinstance(obj, dict):
        return {deserialize_key(k): unstringify_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [unstringify_keys(item) for item in obj]
    return obj


def serialize_value(obj: Any) -> Any:
    """Serialize non-JSON types for orjson."""
    if isinstance(obj, UUID):
        return {"__type__": "uuid", "value": str(obj)}
    if isinstance(obj, datetime):
        return {"__type__": "datetime", "value": obj.isoformat()}
    if isinstance(obj, bytes):
        return {"__type__": "bytes", "value": base64.b64encode(obj).decode()}
    if isinstance(obj, ChainMap):
        return {"__type__": "chainmap", "value": dict(obj)}
    # Skip functions/callables - LangGraph internals may include these
    if callable(obj) and not isinstance(obj, type):
        return {"__type__": "function", "value": None}
    raise TypeError(f"Cannot serialize {type(obj)}")


def deserialize_value(obj: dict) -> Any:
    """Deserialize custom types from JSON."""
    if isinstance(obj, dict) and "__type__" in obj:
        type_name = obj["__type__"]
        value = obj["value"]
        if type_name == "uuid":
            return UUID(value)
        if type_name == "datetime":
            return datetime.fromisoformat(value)
        if type_name == "bytes":
            return base64.b64decode(value)
        if type_name == "chainmap":
            return ChainMap(value)
    return obj


def deep_deserialize(obj: Any) -> Any:
    """Recursively deserialize custom types."""
    if isinstance(obj, dict):
        if "__type__" in obj:
            return deserialize_value(obj)
        return {k: deep_deserialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [deep_deserialize(item) for item in obj]
    return obj


__all__ = [
    "serialize_key",
    "deserialize_key",
    "stringify_keys",
    "unstringify_keys",
    "serialize_value",
    "deserialize_value",
    "deep_deserialize",
]
