"""Tests for yamlgraph.utils.template module - Variable extraction and validation."""

import pytest


class TestExtractVariables:
    """Tests for extract_variables function."""

    def test_extract_simple_variables(self):
        """Should extract {var} placeholders."""
        from yamlgraph.utils.template import extract_variables

        template = "Hello {name}, your style is {style}."
        variables = extract_variables(template)
        assert variables == {"name", "style"}

    def test_extract_single_variable(self):
        """Should extract a single variable."""
        from yamlgraph.utils.template import extract_variables

        template = "Welcome {user}!"
        variables = extract_variables(template)
        assert variables == {"user"}

    def test_extract_no_variables(self):
        """Should return empty set when no variables."""
        from yamlgraph.utils.template import extract_variables

        template = "No variables here"
        variables = extract_variables(template)
        assert variables == set()

    def test_extract_duplicate_variables(self):
        """Should deduplicate variables."""
        from yamlgraph.utils.template import extract_variables

        template = "{name} and {name} again"
        variables = extract_variables(template)
        assert variables == {"name"}

    def test_extract_jinja2_variable(self):
        """Should extract {{ var }} Jinja2 variables."""
        from yamlgraph.utils.template import extract_variables

        template = "Hello {{ name }}!"
        variables = extract_variables(template)
        assert "name" in variables

    def test_extract_jinja2_variable_with_field_access(self):
        """Should extract base variable from {{ var.field }}."""
        from yamlgraph.utils.template import extract_variables

        template = "User: {{ user.name }}"
        variables = extract_variables(template)
        assert "user" in variables

    def test_extract_jinja2_loop_variable(self):
        """Should extract iterable from {% for x in items %}."""
        from yamlgraph.utils.template import extract_variables

        template = "{% for item in items %}{{ item.name }}{% endfor %}"
        variables = extract_variables(template)
        assert "items" in variables
        # 'item' is a loop variable, not a required input
        assert "item" not in variables

    def test_extract_jinja2_if_variable(self):
        """Should extract variable from {% if condition %}."""
        from yamlgraph.utils.template import extract_variables

        template = "{% if show_details %}Details here{% endif %}"
        variables = extract_variables(template)
        assert "show_details" in variables

    def test_exclude_state_variable(self):
        """State is injected by framework, not a required input."""
        from yamlgraph.utils.template import extract_variables

        template = "{{ state.topic }}"
        variables = extract_variables(template)
        # state is excluded - it's injected by node_factory
        assert "state" not in variables

    def test_exclude_jinja2_builtins(self):
        """Should exclude Jinja2 builtins like loop, range."""
        from yamlgraph.utils.template import extract_variables

        template = "{% for i in range(10) %}{{ loop.index }}{% endfor %}"
        variables = extract_variables(template)
        assert "range" not in variables
        assert "loop" not in variables

    def test_mixed_simple_and_jinja2(self):
        """Should handle templates mixing {var} and {{ var }}."""
        from yamlgraph.utils.template import extract_variables

        template = "Simple {name} and Jinja2 {{ topic }}"
        variables = extract_variables(template)
        assert "name" in variables
        assert "topic" in variables


class TestValidateVariables:
    """Tests for validate_variables function."""

    def test_validate_all_provided(self):
        """Should not raise when all variables provided."""
        from yamlgraph.utils.template import validate_variables

        template = "Hello {name}, style: {style}"
        # Should not raise
        validate_variables(template, {"name": "World", "style": "formal"}, "greet")

    def test_validate_missing_single_variable(self):
        """Should raise ValueError for single missing variable."""
        from yamlgraph.utils.template import validate_variables

        template = "Hello {name}, style: {style}"
        with pytest.raises(ValueError, match="Missing required variable.*name"):
            validate_variables(template, {"style": "formal"}, "greet")

    def test_validate_missing_multiple_variables(self):
        """Should list ALL missing variables in error."""
        from yamlgraph.utils.template import validate_variables

        template = "Hello {name}, style: {style}"
        with pytest.raises(ValueError) as exc_info:
            validate_variables(template, {}, "greet")
        error_msg = str(exc_info.value)
        assert "name" in error_msg
        assert "style" in error_msg

    def test_validate_extra_variables_ok(self):
        """Should not raise when extra variables provided."""
        from yamlgraph.utils.template import validate_variables

        template = "Hello {name}"
        # Should not raise - extra vars are fine
        validate_variables(template, {"name": "World", "extra": "ignored"}, "greet")

    def test_validate_prompt_name_in_error(self):
        """Error message should include prompt name."""
        from yamlgraph.utils.template import validate_variables

        template = "Hello {name}"
        with pytest.raises(ValueError, match="greet"):
            validate_variables(template, {}, "greet")

    def test_validate_empty_template(self):
        """Should not raise for template without variables."""
        from yamlgraph.utils.template import validate_variables

        template = "No variables here"
        # Should not raise
        validate_variables(template, {}, "static")

    def test_validate_jinja2_template(self):
        """Should validate Jinja2 templates correctly."""
        from yamlgraph.utils.template import validate_variables

        template = "{% for item in items %}{{ item }}{% endfor %}"
        with pytest.raises(ValueError, match="items"):
            validate_variables(template, {}, "list_template")


class TestExecutePromptValidation:
    """Integration tests for validation in execute_prompt."""

    def test_execute_prompt_raises_on_missing_variable(self):
        """Should raise clear error when required variable is missing."""
        from yamlgraph.executor import execute_prompt

        with pytest.raises(ValueError, match="Missing required variable.*name"):
            execute_prompt(
                prompt_name="greet",
                variables={"style": "formal"},  # Missing 'name'
            )

    def test_execute_prompt_lists_all_missing_variables(self):
        """Error should list ALL missing variables, not just first."""
        from yamlgraph.executor import execute_prompt

        with pytest.raises(ValueError) as exc_info:
            execute_prompt(
                prompt_name="greet",
                variables={},  # Missing both 'name' and 'style'
            )
        error_msg = str(exc_info.value)
        assert "name" in error_msg
        assert "style" in error_msg
