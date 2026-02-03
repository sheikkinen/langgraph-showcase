"""Python handlers for questionnaire state management.

These functions are used as Python tools in the graph to manage
conversation state, detect gaps, apply corrections, and save output.
"""

from datetime import date
from pathlib import Path


def append_user_message(state: dict) -> dict:
    """Add user message to conversation history.

    Args:
        state: Must contain 'user_message' and optionally 'messages'

    Returns:
        Dict with updated 'messages' list
    """
    messages = list(state.get("messages") or [])
    messages.append({"role": "user", "content": state["user_message"]})
    return {"messages": messages}


def append_assistant_message(state: dict) -> dict:
    """Add assistant response to conversation history.

    Args:
        state: Must contain 'response' and optionally 'messages'

    Returns:
        Dict with updated 'messages' list
    """
    messages = list(state.get("messages") or [])
    messages.append({"role": "assistant", "content": state["response"]})
    return {"messages": messages}


def prune_messages(state: dict, max_messages: int = 20) -> dict:
    """Keep conversation within context limits.

    Preserves first 2 messages (opening context) and most recent messages.

    Args:
        state: Must contain 'messages'
        max_messages: Maximum messages to keep (default 20)

    Returns:
        Dict with pruned 'messages' list
    """
    messages = list(state.get("messages") or [])
    if len(messages) > max_messages:
        # Keep first 2 (opening) + most recent
        keep_recent = max_messages - 2
        messages = messages[:2] + messages[-keep_recent:]
    return {"messages": messages}


def store_recap_summary(state: dict) -> dict:
    """Store recap summary for external use (email, SMS, etc).

    Args:
        state: Must contain 'response'

    Returns:
        Dict with 'recap_summary' set to response
    """
    response = state.get("response", "")
    return {"recap_summary": response}


def detect_gaps(state: dict) -> dict:
    """Find missing required fields. Increments probe_count.

    Args:
        state: Must contain 'schema', 'extracted', 'probe_count'

    Returns:
        Dict with 'gaps' (list), 'has_gaps' (bool), 'probe_count' (int)
    """
    schema = state.get("schema", {})
    extracted = state.get("extracted") or {}
    probe_count = state.get("probe_count", 0) + 1

    gaps = []
    for field in schema.get("fields", []):
        if field.get("required"):
            value = extracted.get(field["id"])
            if value is None or value == "":
                gaps.append(field["id"])

    return {"gaps": gaps, "has_gaps": len(gaps) > 0, "probe_count": probe_count}


def apply_corrections(state: dict) -> dict:
    """Merge corrections from recap into extracted data.

    Args:
        state: Must contain 'extracted', 'recap_action', 'correction_count'

    Returns:
        Dict with updated 'extracted' and incremented 'correction_count'
    """
    extracted = dict(state.get("extracted") or {})
    recap_action = state.get("recap_action", {})
    corrections = recap_action.get("corrections", {})
    correction_count = state.get("correction_count", 0) + 1

    for field_id, value in corrections.items():
        if value is not None:
            extracted[field_id] = value

    return {"extracted": extracted, "correction_count": correction_count}


def save_to_file(state: dict) -> dict:
    """Save feature request to markdown file.

    Args:
        state: Must contain 'extracted' and 'analysis'

    Returns:
        Dict with 'output_path' and 'complete' = True
    """
    extracted = _to_dict(state.get("extracted", {}))
    analysis = _to_dict(state.get("analysis", {}))

    # Generate filename from title
    title = extracted.get("title", "untitled")
    slug = "".join(c if c.isalnum() or c == "-" else "-" for c in title.lower())[:50]
    filename = f"{date.today().isoformat()}-{slug}.md"

    # Use CWD/outputs (works with yamlgraph graph run)
    output_dir = Path.cwd() / "outputs"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / filename

    # Format as markdown
    content = _format_feature_request(extracted, analysis)
    output_path.write_text(content, encoding="utf-8")

    return {"output_path": str(output_path), "complete": True}


def _to_dict(obj) -> dict:
    """Convert object to dict (handles Pydantic models)."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, dict):
        return obj
    return {}


def _format_feature_request(extracted: dict, analysis: dict) -> str:
    """Format collected data as feature request markdown."""
    return f"""# Feature Request: {extracted.get("title", "Untitled")}

**Priority:** {extracted.get("priority", "MEDIUM").upper()}
**Type:** Feature
**Status:** Proposed
**Requested:** {date.today().isoformat()}

## Summary

{extracted.get("summary", "")}

## Problem

{extracted.get("problem", "")}

## Proposed Solution

{extracted.get("proposed_solution", "")}

## Acceptance Criteria

{_format_list(extracted.get("acceptance_criteria", []))}

## Alternatives Considered

{extracted.get("alternatives", "None documented.")}

## Critical Analysis

{analysis.get("analysis", "")}

### Strengths
{_format_list(analysis.get("strengths", []))}

### Concerns
{_format_list(analysis.get("concerns", []))}

### Recommendation
{analysis.get("recommendation", "")}
"""


def _format_list(items: list | None) -> str:
    """Format list as markdown bullet points."""
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)
