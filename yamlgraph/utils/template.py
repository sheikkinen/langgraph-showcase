"""Template utilities - Variable extraction and validation.

This module provides functions to extract required variables from
prompt templates and validate that all required variables are provided
before execution.

Supports both simple {variable} placeholders and Jinja2 templates.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def extract_variables(template: str) -> set[str]:
    """Extract all variable names required by a template.

    Handles both simple {var} and Jinja2 {{ var }}, {% for x in var %} syntax.

    Args:
        template: Template string with placeholders

    Returns:
        Set of variable names required by the template

    Examples:
        >>> extract_variables("Hello {name}")
        {'name'}

        >>> extract_variables("{% for item in items %}{{ item }}{% endfor %}")
        {'items'}
    """
    variables: set[str] = set()

    # Simple format: {var} - but NOT {{ (Jinja2)
    # Match {word} but not {{word}} - use negative lookbehind/lookahead
    simple_pattern = r"(?<!\{)\{(\w+)\}(?!\})"
    variables.update(re.findall(simple_pattern, template))

    # Jinja2 variable: {{ var }} or {{ var.field }}
    jinja_var_pattern = r"\{\{\s*(\w+)"
    variables.update(re.findall(jinja_var_pattern, template))

    # Jinja2 loop: {% for x in var %}
    jinja_loop_pattern = r"\{%\s*for\s+\w+\s+in\s+(\w+)"
    variables.update(re.findall(jinja_loop_pattern, template))

    # Jinja2 condition: {% if var %} or {% if var.field %}
    jinja_if_pattern = r"\{%\s*if\s+(\w+)"
    variables.update(re.findall(jinja_if_pattern, template))

    # Remove loop iteration variables (they're not inputs)
    # e.g., in "{% for item in items %}", "item" is not required
    loop_iter_pattern = r"\{%\s*for\s+(\w+)\s+in"
    loop_vars = set(re.findall(loop_iter_pattern, template))
    variables -= loop_vars

    # Remove common non-input variables
    # - state: injected by node_factory
    # - loop: Jinja2 loop context
    # - range: Jinja2 builtin function
    excluded = {"state", "loop", "range", "true", "false", "none"}
    variables -= excluded

    return variables


def validate_variables(
    template: str,
    provided: dict[str, Any],
    prompt_name: str,
) -> None:
    """Validate that all required template variables are provided.

    Raises ValueError with helpful message listing all missing variables.

    Args:
        template: Template string with placeholders
        provided: Dictionary of provided variable values
        prompt_name: Name of the prompt (for error messages)

    Raises:
        ValueError: If any required variables are missing

    Examples:
        >>> validate_variables("Hello {name}", {"name": "World"}, "greet")
        # No error

        >>> validate_variables("Hello {name}", {}, "greet")
        ValueError: Missing required variable(s) for prompt 'greet': name
    """
    required = extract_variables(template)
    provided_keys = set(provided.keys())
    missing = required - provided_keys

    if missing:
        raise ValueError(
            f"Missing required variable(s) for prompt '{prompt_name}': "
            f"{', '.join(sorted(missing))}"
        )
