"""Tests for JSON extraction from LLM output (FR-B)."""

import pytest

from yamlgraph.utils.json_extract import extract_json, find_balanced_json


class TestExtractJson:
    """Tests for extract_json utility."""

    @pytest.mark.req("REQ-YG-016")
    def test_extract_raw_json_object(self):
        """Should parse raw JSON object."""
        text = '{"name": "test", "value": 42}'
        result = extract_json(text)

        assert result == {"name": "test", "value": 42}

    @pytest.mark.req("REQ-YG-016")
    def test_extract_raw_json_array(self):
        """Should parse raw JSON array."""
        text = "[1, 2, 3]"
        result = extract_json(text)

        assert result == [1, 2, 3]

    @pytest.mark.req("REQ-YG-016")
    def test_extract_json_codeblock(self):
        """Should extract JSON from ```json ... ``` block."""
        text = """Here is the result:

```json
{"frequency": 3, "amount": null}
```

Reasoning: The user mentioned drinking 2-3 times per week.
"""
        result = extract_json(text)

        assert result == {"frequency": 3, "amount": None}

    @pytest.mark.req("REQ-YG-016")
    def test_extract_any_codeblock(self):
        """Should extract JSON from ``` ... ``` block without language."""
        text = """```
{"status": "ok"}
```"""
        result = extract_json(text)

        assert result == {"status": "ok"}

    @pytest.mark.req("REQ-YG-016")
    def test_extract_curly_pattern(self):
        """Should extract JSON from {...} pattern in text."""
        text = 'The extracted data is {"key": "value"} from the input.'
        result = extract_json(text)

        assert result == {"key": "value"}

    @pytest.mark.req("REQ-YG-016")
    def test_extract_array_pattern(self):
        """Should extract JSON from [...] pattern in text."""
        text = 'Items: ["a", "b", "c"] found.'
        result = extract_json(text)

        assert result == ["a", "b", "c"]

    @pytest.mark.req("REQ-YG-016")
    def test_returns_original_on_failure(self):
        """Should return original text if no JSON found."""
        text = "This is just plain text with no JSON."
        result = extract_json(text)

        assert result == text

    @pytest.mark.req("REQ-YG-016")
    def test_handles_nested_json(self):
        """Should handle nested JSON structures."""
        text = """```json
{
  "person": {
    "name": "Alice",
    "scores": [95, 87, 92]
  }
}
```"""
        result = extract_json(text)

        assert result == {"person": {"name": "Alice", "scores": [95, 87, 92]}}

    @pytest.mark.req("REQ-YG-016")
    def test_handles_whitespace(self):
        """Should handle JSON with extra whitespace."""
        text = """   {
  "key"  :  "value"
}   """
        result = extract_json(text)

        assert result == {"key": "value"}

    @pytest.mark.req("REQ-YG-016")
    def test_prefers_json_codeblock_over_raw(self):
        """Should extract from codeblock even if other JSON present."""
        text = """Some intro {"wrong": true}

```json
{"correct": true}
```
"""
        result = extract_json(text)

        # Should find the codeblock, not the inline JSON
        assert result == {"correct": True}

    @pytest.mark.req("REQ-YG-016")
    def test_invalid_json_in_codeblock_falls_through(self):
        """Invalid JSON in codeblock should try next strategy."""
        text = """```json
{not valid json}
```

The actual data is {"valid": true}.
"""
        result = extract_json(text)

        # Should fall through to curly pattern
        assert result == {"valid": True}

    @pytest.mark.req("REQ-YG-016")
    def test_empty_string(self):
        """Should handle empty string."""
        result = extract_json("")

        assert result == ""

    @pytest.mark.req("REQ-YG-016")
    def test_multiline_json(self):
        """Should handle multiline JSON in code block."""
        text = """```json
{
  "line1": "value1",
  "line2": "value2",
  "line3": "value3"
}
```"""
        result = extract_json(text)

        assert result == {"line1": "value1", "line2": "value2", "line3": "value3"}


class TestNestedJsonExtraction:
    """Tests for nested JSON extraction with balanced braces."""

    @pytest.mark.req("REQ-YG-016")
    def test_simple_pattern_finds_inner_first(self):
        """Simple pattern finds innermost valid JSON first."""
        # Current behavior: simple pattern matches {deep: 123} first
        text = 'Before {"outer": {"inner": {"deep": 123}}} after'
        result = extract_json(text)

        # Finds innermost simple object first
        assert result == {"deep": 123}

    @pytest.mark.req("REQ-YG-016")
    def test_nested_array_finds_simple_first(self):
        """Simple pattern finds simple array elements first."""
        # Simple arrays like [1, 2] are matched before nested [[1,2], [3,4]]
        text = "Data: [[1, 2], [3, 4]] end"
        result = extract_json(text)

        # Finds first simple array
        assert result == [1, 2]

    @pytest.mark.req("REQ-YG-016")
    def test_codeblock_with_nested_json(self):
        """Code block extraction handles nested JSON correctly."""
        text = """```json
{"outer": {"inner": {"deep": "value"}}}
```"""
        result = extract_json(text)

        # Code block preserves structure
        assert result == {"outer": {"inner": {"deep": "value"}}}

    @pytest.mark.req("REQ-YG-016")
    def test_balanced_braces_fallback(self):
        """Balanced brace extraction works when simple patterns fail."""
        # When simple pattern doesn't find valid JSON, falls back to balanced extraction
        text = '{"key with spaces": {"nested": true}}'
        result = extract_json(text)

        # Raw JSON parsing succeeds
        assert result == {"key with spaces": {"nested": True}}

    @pytest.mark.req("REQ-YG-016")
    def test_none_input(self):
        """Should handle None input gracefully."""
        result = extract_json(None)

        assert result is None

    @pytest.mark.req("REQ-YG-016")
    def test_whitespace_only(self):
        """Should handle whitespace-only input."""
        result = extract_json("   \n\t  ")

        assert result == ""


class TestFindBalancedJson:
    """Tests for find_balanced_json helper function."""

    @pytest.mark.req("REQ-YG-016")
    def test_simple_object(self):
        """Should find simple balanced object."""
        text = 'prefix {"key": "value"} suffix'
        result = find_balanced_json(text, "{", "}")

        assert result == '{"key": "value"}'

    @pytest.mark.req("REQ-YG-016")
    def test_nested_object(self):
        """Should find nested balanced object."""
        text = 'start {"outer": {"inner": "value"}} end'
        result = find_balanced_json(text, "{", "}")

        assert result == '{"outer": {"inner": "value"}}'

    @pytest.mark.req("REQ-YG-016")
    def test_deeply_nested(self):
        """Should find deeply nested structure."""
        text = '{"a": {"b": {"c": {"d": 1}}}}'
        result = find_balanced_json(text, "{", "}")

        assert result == '{"a": {"b": {"c": {"d": 1}}}}'

    @pytest.mark.req("REQ-YG-016")
    def test_simple_array(self):
        """Should find simple balanced array."""
        text = "data: [1, 2, 3] done"
        result = find_balanced_json(text, "[", "]")

        assert result == "[1, 2, 3]"

    @pytest.mark.req("REQ-YG-016")
    def test_nested_array(self):
        """Should find nested array."""
        text = "matrix: [[1, 2], [3, 4]] result"
        result = find_balanced_json(text, "[", "]")

        assert result == "[[1, 2], [3, 4]]"

    @pytest.mark.req("REQ-YG-016")
    def test_no_start_char(self):
        """Should return None if start char not found."""
        text = "no brackets here"
        result = find_balanced_json(text, "{", "}")

        assert result is None

    @pytest.mark.req("REQ-YG-016")
    def test_unbalanced_brackets(self):
        """Should return None for unbalanced brackets."""
        text = '{"key": "value"'  # Missing closing brace
        result = find_balanced_json(text, "{", "}")

        assert result is None

    @pytest.mark.req("REQ-YG-016")
    def test_invalid_json_content(self):
        """Should return None for balanced but invalid JSON."""
        text = "{not valid json content}"
        result = find_balanced_json(text, "{", "}")

        assert result is None

    @pytest.mark.req("REQ-YG-016")
    def test_object_with_array_inside(self):
        """Should find object containing arrays."""
        text = 'response: {"items": [1, 2, 3]} end'
        result = find_balanced_json(text, "{", "}")

        assert result == '{"items": [1, 2, 3]}'

    @pytest.mark.req("REQ-YG-016")
    def test_first_match_wins(self):
        """Should return first balanced structure."""
        text = '{"first": 1} {"second": 2}'
        result = find_balanced_json(text, "{", "}")

        assert result == '{"first": 1}'
