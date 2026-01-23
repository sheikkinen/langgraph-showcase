"""Glossary management for consistent terminology."""

import json


def merge_terms(state: dict) -> dict:
    """Merge extracted terms into unified glossary.

    Combines existing glossary with newly extracted terms from LLM.
    Existing terms take priority (not overwritten).
    Keys are normalized to lowercase for case-insensitive matching.

    Args:
        state: Must contain optional 'glossary' (dict or JSON string) and 'term_extractions' (list)

    Returns:
        dict with 'glossary' key containing merged term dictionary
    """
    existing = state.get("glossary", {}) or {}

    # Handle string glossary input (e.g., from CLI --var glossary='{}')
    if isinstance(existing, str):
        try:
            existing = json.loads(existing)
        except json.JSONDecodeError:
            existing = {}

    extractions = state.get("term_extractions", []) or []

    # Start with existing glossary (preserve existing translations)
    merged: dict[str, str] = dict(existing)

    for extraction in extractions:
        # Skip None or malformed extractions
        if not extraction or not isinstance(extraction, dict):
            continue

        terms = extraction.get("terms", [])
        if not terms or not isinstance(terms, list):
            continue

        for term in terms:
            if not isinstance(term, dict):
                continue

            source = term.get("source_term", "")
            translation = term.get("translation", "")

            # Skip empty source terms
            if not source or not isinstance(source, str):
                continue

            # Normalize key to lowercase
            key = source.lower()

            # Only add if not already in glossary (existing takes priority)
            if key not in merged:
                merged[key] = translation

    return {"glossary": merged}
