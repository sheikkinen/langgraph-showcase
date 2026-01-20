"""Tests for JSON extraction from LLM output (FR-B)."""


from yamlgraph.utils.json_extract import extract_json


class TestExtractJson:
    """Tests for extract_json utility."""

    def test_extract_raw_json_object(self):
        """Should parse raw JSON object."""
        text = '{"name": "test", "value": 42}'
        result = extract_json(text)

        assert result == {"name": "test", "value": 42}

    def test_extract_raw_json_array(self):
        """Should parse raw JSON array."""
        text = '[1, 2, 3]'
        result = extract_json(text)

        assert result == [1, 2, 3]

    def test_extract_json_codeblock(self):
        """Should extract JSON from ```json ... ``` block."""
        text = '''Here is the result:

```json
{"frequency": 3, "amount": null}
```

Reasoning: The user mentioned drinking 2-3 times per week.
'''
        result = extract_json(text)

        assert result == {"frequency": 3, "amount": None}

    def test_extract_any_codeblock(self):
        """Should extract JSON from ``` ... ``` block without language."""
        text = '''```
{"status": "ok"}
```'''
        result = extract_json(text)

        assert result == {"status": "ok"}

    def test_extract_curly_pattern(self):
        """Should extract JSON from {...} pattern in text."""
        text = 'The extracted data is {"key": "value"} from the input.'
        result = extract_json(text)

        assert result == {"key": "value"}

    def test_extract_array_pattern(self):
        """Should extract JSON from [...] pattern in text."""
        text = 'Items: ["a", "b", "c"] found.'
        result = extract_json(text)

        assert result == ["a", "b", "c"]

    def test_returns_original_on_failure(self):
        """Should return original text if no JSON found."""
        text = "This is just plain text with no JSON."
        result = extract_json(text)

        assert result == text

    def test_handles_nested_json(self):
        """Should handle nested JSON structures."""
        text = '''```json
{
  "person": {
    "name": "Alice",
    "scores": [95, 87, 92]
  }
}
```'''
        result = extract_json(text)

        assert result == {"person": {"name": "Alice", "scores": [95, 87, 92]}}

    def test_handles_whitespace(self):
        """Should handle JSON with extra whitespace."""
        text = '''   {
  "key"  :  "value"
}   '''
        result = extract_json(text)

        assert result == {"key": "value"}

    def test_prefers_json_codeblock_over_raw(self):
        """Should extract from codeblock even if other JSON present."""
        text = '''Some intro {"wrong": true}

```json
{"correct": true}
```
'''
        result = extract_json(text)

        # Should find the codeblock, not the inline JSON
        assert result == {"correct": True}

    def test_invalid_json_in_codeblock_falls_through(self):
        """Invalid JSON in codeblock should try next strategy."""
        text = '''```json
{not valid json}
```

The actual data is {"valid": true}.
'''
        result = extract_json(text)

        # Should fall through to curly pattern
        assert result == {"valid": True}

    def test_empty_string(self):
        """Should handle empty string."""
        result = extract_json("")

        assert result == ""

    def test_multiline_json(self):
        """Should handle multiline JSON in code block."""
        text = '''```json
{
  "line1": "value1",
  "line2": "value2",
  "line3": "value3"
}
```'''
        result = extract_json(text)

        assert result == {"line1": "value1", "line2": "value2", "line3": "value3"}
