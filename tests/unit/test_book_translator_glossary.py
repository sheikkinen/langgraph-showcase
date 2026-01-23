"""Unit tests for book translator glossary merge function."""

import sys
from pathlib import Path

# Add examples to path for testing
examples_path = Path(__file__).parent.parent.parent / "examples" / "book_translator"
sys.path.insert(0, str(examples_path))

from nodes.tools import get_map_result, merge_terms  # noqa: E402


class TestGetMapResult:
    """Tests for the get_map_result helper function."""

    def test_extracts_map_result(self):
        """Extract result from standard map node output."""
        item = {"_map_some_node_sub": {"data": "value"}}
        result = get_map_result(item)
        assert result == {"data": "value"}

    def test_returns_none_for_none_input(self):
        """Return None when input is None."""
        assert get_map_result(None) is None

    def test_returns_none_for_non_dict(self):
        """Return None when input is not a dict."""
        assert get_map_result("string") is None
        assert get_map_result(123) is None
        assert get_map_result([1, 2, 3]) is None

    def test_returns_none_for_empty_dict(self):
        """Return None when dict has no map keys."""
        assert get_map_result({}) is None

    def test_returns_none_for_dict_without_map_key(self):
        """Return None when dict doesn't have _map_*_sub key."""
        item = {"other_key": "value", "another": 123}
        assert get_map_result(item) is None

    def test_handles_various_node_names(self):
        """Handle different node name patterns."""
        assert get_map_result({"_map_translate_all_sub": "x"}) == "x"
        assert get_map_result({"_map_a_sub": "y"}) == "y"
        assert get_map_result({"_map_long_node_name_sub": "z"}) == "z"

    def test_returns_first_match_if_multiple(self):
        """Return a result if multiple map keys exist (edge case)."""
        item = {"_map_first_sub": "first", "_map_second_sub": "second"}
        result = get_map_result(item)
        # Should return one of them (order not guaranteed)
        assert result in ("first", "second")

    def test_preserves_pydantic_like_objects(self):
        """Return Pydantic-like objects as-is."""

        class FakeModel:
            def __init__(self):
                self.field = "value"

        model = FakeModel()
        item = {"_map_node_sub": model}
        assert get_map_result(item) is model


class TestMergeTerms:
    """Tests for glossary term merging."""

    def test_merge_empty_state(self):
        """Handle empty state gracefully."""
        state = {}
        result = merge_terms(state)

        assert "glossary" in result
        assert result["glossary"] == {}

    def test_merge_with_existing_glossary(self):
        """Preserve existing glossary terms."""
        state = {
            "glossary": {"Hello": "Hola", "World": "Mundo"},
            "term_extractions": [],
        }
        result = merge_terms(state)

        assert result["glossary"]["Hello"] == "Hola"
        assert result["glossary"]["World"] == "Mundo"

    def test_merge_new_extractions(self):
        """Add new terms from extractions (map node format)."""
        state = {
            "glossary": {},
            "term_extractions": [
                {
                    "_map_extract_glossary_sub": {
                        "terms": [{"source_term": "Hello", "translation": "Hola"}]
                    }
                },
                {
                    "_map_extract_glossary_sub": {
                        "terms": [{"source_term": "World", "translation": "Mundo"}]
                    }
                },
            ],
        }
        result = merge_terms(state)

        assert result["glossary"]["Hello"] == "Hola"
        assert result["glossary"]["World"] == "Mundo"

    def test_existing_terms_not_overwritten(self):
        """Existing terms take priority over new extractions."""
        state = {
            "glossary": {"Hello": "existing_translation"},
            "term_extractions": [
                {
                    "_map_extract_glossary_sub": {
                        "terms": [
                            {"source_term": "Hello", "translation": "new_translation"}
                        ]
                    }
                },
            ],
        }
        result = merge_terms(state)

        # Existing translation should be preserved
        assert result["glossary"]["Hello"] == "existing_translation"

    def test_handle_empty_extractions(self):
        """Handle empty term_extractions list."""
        state = {
            "glossary": {"existing": "value"},
            "term_extractions": [],
        }
        result = merge_terms(state)

        assert result["glossary"]["existing"] == "value"

    def test_handle_none_extraction_items(self):
        """Handle None values in extractions list."""
        state = {
            "glossary": {},
            "term_extractions": [
                None,
                {
                    "_map_extract_glossary_sub": {
                        "terms": [{"source_term": "Valid", "translation": "Válido"}]
                    }
                },
                None,
            ],
        }
        result = merge_terms(state)

        assert result["glossary"]["Valid"] == "Válido"

    def test_handle_missing_map_key(self):
        """Handle extractions without the map node key."""
        state = {
            "glossary": {},
            "term_extractions": [
                {"other_key": "value"},
                {
                    "_map_extract_glossary_sub": {
                        "terms": [{"source_term": "Test", "translation": "Prueba"}]
                    }
                },
            ],
        }
        result = merge_terms(state)

        assert result["glossary"]["Test"] == "Prueba"
        assert len(result["glossary"]) == 1

    def test_handle_malformed_terms(self):
        """Handle terms missing required fields."""
        state = {
            "glossary": {},
            "term_extractions": [
                {
                    "_map_extract_glossary_sub": {
                        "terms": [
                            {"source_term": "", "translation": "Empty source"},
                            {"source_term": "Valid", "translation": "Válido"},
                            {"translation": "Missing source"},  # No source_term
                        ]
                    }
                },
            ],
        }
        result = merge_terms(state)

        assert "Valid" in result["glossary"]
        assert "" not in result["glossary"]
        assert len(result["glossary"]) == 1

    def test_multiple_terms_per_extraction(self):
        """Handle multiple terms in single extraction."""
        state = {
            "glossary": {},
            "term_extractions": [
                {
                    "_map_extract_glossary_sub": {
                        "terms": [
                            {"source_term": "One", "translation": "Uno"},
                            {"source_term": "Two", "translation": "Dos"},
                            {"source_term": "Three", "translation": "Tres"},
                        ]
                    }
                },
            ],
        }
        result = merge_terms(state)

        assert len(result["glossary"]) == 3
        assert result["glossary"]["One"] == "Uno"
        assert result["glossary"]["Two"] == "Dos"
        assert result["glossary"]["Three"] == "Tres"

    def test_glossary_from_json_string(self):
        """Handle glossary passed as JSON string from CLI."""
        state = {
            "glossary": '{"existing": "value"}',
            "term_extractions": [
                {
                    "_map_extract_glossary_sub": {
                        "terms": [{"source_term": "New", "translation": "Nuevo"}]
                    }
                },
            ],
        }
        result = merge_terms(state)

        assert result["glossary"]["existing"] == "value"
        assert result["glossary"]["New"] == "Nuevo"
