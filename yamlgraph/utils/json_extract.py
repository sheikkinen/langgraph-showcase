"""Extract JSON from LLM output with various formats.

LLMs often wrap JSON responses in markdown code blocks or add
explanatory text. This module provides robust extraction.

FR-B: JSON Extraction feature.
"""

import json
import re


def find_balanced_json(text: str, start_char: str, end_char: str) -> str | None:
    """Find first valid balanced JSON structure with given delimiters.

    Scans for matching open/close brackets to extract nested JSON.
    Continues searching if a balanced candidate is syntactically invalid.

    Args:
        text: Text to search
        start_char: Opening bracket ('{' or '[')
        end_char: Closing bracket ('}' or ']')

    Returns:
        Extracted JSON string if found and valid, else None
    """
    search_start = 0

    while True:
        start_idx = text.find(start_char, search_start)
        if start_idx == -1:
            return None

        depth = 0
        for i, c in enumerate(text[start_idx:], start=start_idx):
            if c == start_char:
                depth += 1
            elif c == end_char:
                depth -= 1
                if depth == 0:
                    candidate = text[start_idx : i + 1]
                    try:
                        json.loads(candidate)  # Validate it's valid JSON
                        return candidate
                    except json.JSONDecodeError:
                        # Continue searching after this invalid candidate
                        search_start = i + 1
                        break
        else:
            # Unbalanced brackets - no closing found
            return None


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
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        candidate = find_balanced_json(text, start_char, end_char)
        if candidate:
            return json.loads(candidate)

    # 6. Return original text
    return text


__all__ = ["extract_json", "find_balanced_json"]
