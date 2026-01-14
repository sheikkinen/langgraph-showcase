"""Tests for showcase.executor module."""

import pytest

from showcase.executor import load_prompt, format_prompt


class TestLoadPrompt:
    """Tests for load_prompt function."""

    def test_load_existing_prompt(self):
        """Should load an existing prompt file."""
        prompt = load_prompt("generate")
        assert "system" in prompt
        assert "user" in prompt

    def test_load_analyze_prompt(self):
        """Should load analyze prompt."""
        prompt = load_prompt("analyze")
        assert "system" in prompt
        assert "{content}" in prompt["user"]

    def test_load_nonexistent_prompt(self):
        """Should raise FileNotFoundError for missing prompt."""
        with pytest.raises(FileNotFoundError):
            load_prompt("nonexistent_prompt")


class TestFormatPrompt:
    """Tests for format_prompt function."""

    def test_format_single_variable(self):
        """Should format single variable."""
        template = "Hello, {name}!"
        result = format_prompt(template, {"name": "World"})
        assert result == "Hello, World!"

    def test_format_multiple_variables(self):
        """Should format multiple variables."""
        template = "Topic: {topic}, Style: {style}"
        result = format_prompt(template, {"topic": "AI", "style": "casual"})
        assert result == "Topic: AI, Style: casual"

    def test_format_empty_variables(self):
        """Should handle empty variables dict."""
        template = "No variables here"
        result = format_prompt(template, {})
        assert result == "No variables here"

    def test_format_missing_variable_raises(self):
        """Should raise KeyError for missing variable."""
        template = "Hello, {name}!"
        with pytest.raises(KeyError):
            format_prompt(template, {})

    def test_format_with_numbers(self):
        """Should handle numeric variables."""
        template = "Count: {word_count}"
        result = format_prompt(template, {"word_count": 300})
        assert result == "Count: 300"
