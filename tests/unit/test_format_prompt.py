"""Tests for prompt formatting with Jinja2 support."""

import pytest

from showcase.executor import format_prompt


class TestFormatPrompt:
    """Test the format_prompt function with both simple and Jinja2 templates."""

    def test_simple_format_basic(self):
        """Test basic string formatting with {variable} syntax."""
        template = "Hello {name}!"
        variables = {"name": "World"}
        result = format_prompt(template, variables)
        assert result == "Hello World!"

    def test_simple_format_multiple_variables(self):
        """Test formatting with multiple variables."""
        template = "Topic: {topic}, Style: {style}, Words: {word_count}"
        variables = {"topic": "AI", "style": "casual", "word_count": 500}
        result = format_prompt(template, variables)
        assert result == "Topic: AI, Style: casual, Words: 500"

    def test_simple_format_missing_variable(self):
        """Test that missing variables raise KeyError."""
        template = "Hello {name}!"
        variables = {}
        with pytest.raises(KeyError):
            format_prompt(template, variables)

    def test_jinja2_basic_variable(self):
        """Test Jinja2 template with basic {{ variable }} syntax."""
        template = "Hello {{ name }}!"
        variables = {"name": "World"}
        result = format_prompt(template, variables)
        assert result == "Hello World!"

    def test_jinja2_for_loop(self):
        """Test Jinja2 template with for loop."""
        template = """{% for item in items %}
- {{ item }}
{% endfor %}"""
        variables = {"items": ["apple", "banana", "cherry"]}
        result = format_prompt(template, variables)
        # Jinja2 preserves whitespace from template
        assert "- apple" in result
        assert "- banana" in result
        assert "- cherry" in result

    def test_jinja2_conditional(self):
        """Test Jinja2 template with if/else."""
        template = """{% if premium %}Premium User{% else %}Regular User{% endif %}"""

        result_premium = format_prompt(template, {"premium": True})
        assert result_premium == "Premium User"

        result_regular = format_prompt(template, {"premium": False})
        assert result_regular == "Regular User"

    def test_jinja2_filter_slice(self):
        """Test Jinja2 template with slice filter."""
        template = "Summary: {{ text[:50] }}..."
        variables = {
            "text": "This is a very long text that should be truncated to show only first fifty characters"
        }
        result = format_prompt(template, variables)
        # Check that the text is sliced to 50 characters
        assert result.startswith(
            "Summary: This is a very long text that should be truncated"
        )
        assert result.endswith("...")
        assert len(result) < len(variables["text"]) + len("Summary: ...")

    def test_jinja2_filter_upper(self):
        """Test Jinja2 template with upper filter."""
        template = "{{ name | upper }}"
        variables = {"name": "world"}
        result = format_prompt(template, variables)
        assert result == "WORLD"

    def test_jinja2_complex_template(self):
        """Test complex Jinja2 template with loops and conditionals."""
        template = """Items in {{ category }}:
{% for item in items %}
  {% if item.available %}
  - {{ item.name }}: ${{ item.price }}
  {% endif %}
{% endfor %}"""
        variables = {
            "category": "Fruits",
            "items": [
                {"name": "Apple", "price": 1.50, "available": True},
                {"name": "Banana", "price": 0.75, "available": False},
                {"name": "Cherry", "price": 2.00, "available": True},
            ],
        }
        result = format_prompt(template, variables)
        assert "Apple: $1.5" in result
        assert "Cherry: $2.0" in result
        assert "Banana" not in result

    def test_jinja2_missing_variable_graceful(self):
        """Test that Jinja2 missing variables are handled (rendered as empty by default)."""
        template = "Hello {{ name }}!"
        variables = {}
        result = format_prompt(template, variables)
        # Jinja2 by default renders undefined variables as empty strings
        assert result == "Hello !"

    def test_detection_uses_jinja2_for_double_braces(self):
        """Test that {{ triggers Jinja2 mode."""
        template = "Value: {{ x }}"
        variables = {"x": 42}
        result = format_prompt(template, variables)
        assert result == "Value: 42"

    def test_detection_uses_jinja2_for_statements(self):
        """Test that {% triggers Jinja2 mode."""
        template = "{% if true %}Yes{% endif %}"
        variables = {}
        result = format_prompt(template, variables)
        assert result == "Yes"

    def test_backward_compatibility_no_jinja2_syntax(self):
        """Test that templates without Jinja2 syntax still use simple format."""
        # This ensures backward compatibility
        template = "Simple {var} template"
        variables = {"var": "test"}
        result = format_prompt(template, variables)
        assert result == "Simple test template"

    def test_empty_template(self):
        """Test formatting empty template."""
        template = ""
        variables = {}
        result = format_prompt(template, variables)
        assert result == ""

    def test_template_with_no_placeholders(self):
        """Test template with no variables."""
        template = "Just plain text"
        variables = {"unused": "value"}
        result = format_prompt(template, variables)
        assert result == "Just plain text"
