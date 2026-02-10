"""Guardrail tool nodes: echo + validate."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def echo_input(state: dict[str, Any]) -> dict[str, Any]:
    """Echo the input for audit trail. Tool node handler."""
    raw = state.get("input", "")
    logger.info(f"[echo] {raw[:200]}")
    return {"echo": raw}


def validate_input(state: dict[str, Any]) -> dict[str, Any]:
    """Validate input content. Stamps *validation missing* on unvalidated content.

    This is the guardrail — any content that hasn't been through
    a proper validation pipeline gets flagged.
    """
    raw = state.get("input", "")

    # Parse messages if JSON
    try:
        messages = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        messages = [{"role": "user", "content": raw}]

    # Stamp validation status
    validated_content = []
    for msg in messages:
        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
        validated_content.append(f"{content}\n\n*validation missing*")

    return {"validation": "\n---\n".join(validated_content)}
