"""Extract JSON from LLM output with various formats.

LLMs often wrap JSON responses in markdown code blocks or add
explanatory text. This module provides robust extraction.

FR-B: JSON Extraction feature.
"""

import json
import re


def extract_json(text: str) -> dict | list | str:
    """Extract JSON from LLM response.

    Extraction order:
    1. Parse as raw JSON (handles both objects and arrays)
    2. Extract from ```json ... ``` code block
    3. Extract from ``` ... ``` code block (any language)
    4. Extract first {...} or [...] pattern
    5. Return original text if no JSON found

    Args:
        text: Raw LLM response

    Returns:
        Parsed JSON (dict/list) or original string if extraction fails

    Examples:
        >>> extract_json('{"key": "value"}')
        {'key': 'value'}

        >>> extract_json('```json\\n{"key": "value"}\\n```')
        {'key': 'value'}

        >>> extract_json('Result: {"x": 1} found')
        {'x': 1}
    """
    if not text:
        return text

    text = text.strip()

    # 1. Try raw JSON first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Try ```json ... ``` block
    match = re.search(r"```json\s*\n?(.*?)\n?```", text, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Try ``` ... ``` block (any language)
    match = re.search(r"```\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 4. Try {...} or [...] pattern
    # Find all potential JSON objects/arrays and try parsing each
    # Use non-greedy matching to find smallest valid JSON structures
    for pattern in [
        r"\{[^{}]*\}",  # Simple object: {key: value}
        r"\[[^\[\]]*\]",  # Simple array: [1, 2, 3]
    ]:
        for match in re.finditer(pattern, text):
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue

    # 5. Try nested structures (greedy, last resort)
    # Find balanced braces manually
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start_idx = text.find(start_char)
        if start_idx == -1:
            continue

        # Find matching closing bracket
        depth = 0
        for i, c in enumerate(text[start_idx:], start=start_idx):
            if c == start_char:
                depth += 1
            elif c == end_char:
                depth -= 1
                if depth == 0:
                    candidate = text[start_idx : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break  # Try next start position

    # 6. Return original text
    return text


__all__ = ["extract_json"]
