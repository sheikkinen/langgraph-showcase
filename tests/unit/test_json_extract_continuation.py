"""Tests for JSON extraction continuation after invalid candidates.

Bug: find_balanced_json stops after the first balanced candidate even if
it is invalid JSON, so a later valid JSON block is never discovered.
"""

from yamlgraph.utils.json_extract import extract_json, find_balanced_json


class TestFindBalancedJsonContinuation:
    """Tests for find_balanced_json continuing after invalid candidates."""

    def test_stops_at_first_invalid_balanced_json(self) -> None:
        """Bug: Returns None when first balanced candidate is invalid JSON.

        Current behavior: finds {not json}, validates it, returns None.
        Expected: continue scanning to find {"valid": true}.
        """
        text = 'prefix {not json} middle {"valid": true} suffix'

        result = find_balanced_json(text, "{", "}")

        # Bug: returns None instead of finding valid JSON
        assert (
            result == '{"valid": true}'
        ), f"Should continue after invalid balanced candidate. Got: {result}"

    def test_multiple_invalid_before_valid(self) -> None:
        """Should skip multiple invalid balanced structures."""
        text = '{a b c} {x y z} {"finally": "valid"}'

        result = find_balanced_json(text, "{", "}")

        assert (
            result == '{"finally": "valid"}'
        ), f"Should find valid JSON after multiple invalid. Got: {result}"

    def test_nested_invalid_before_valid(self) -> None:
        """Nested but invalid JSON followed by valid."""
        text = '{outer {inner}} {"valid": 123}'

        result = find_balanced_json(text, "{", "}")

        assert (
            result == '{"valid": 123}'
        ), f"Should skip nested invalid structure. Got: {result}"

    def test_array_invalid_before_valid(self) -> None:
        """Same bug applies to array extraction."""
        text = "[not, valid, array] [1, 2, 3]"

        result = find_balanced_json(text, "[", "]")

        assert result == "[1, 2, 3]", f"Should continue for arrays too. Got: {result}"


class TestExtractJsonWithNoisy:
    """Tests for extract_json with noisy LLM outputs."""

    def test_extract_json_with_invalid_prefix(self) -> None:
        """extract_json should find valid JSON after invalid structures."""
        # Common LLM pattern: thinking aloud with curly braces before answer
        text = """
Let me think about this {mental note}.
Here's the answer:
{"result": "success", "count": 42}
"""
        result = extract_json(text)

        assert result == {
            "result": "success",
            "count": 42,
        }, f"Should extract valid JSON despite noise. Got: {result}"

    def test_extract_json_code_block_takes_priority(self) -> None:
        """Markdown code block should still take priority."""
        text = """
{invalid stuff}
```json
{"from_code_block": true}
```
{"also_valid": true}
"""
        result = extract_json(text)

        # Code block should win
        assert result == {"from_code_block": True}
