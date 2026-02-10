"""Unit tests for Jinja2 prompt template formatting.

Tests the format_prompt function's Jinja2 rendering capabilities
without requiring external prompt files.
"""

import pytest

from yamlgraph.executor_base import format_prompt

# Jinja2 template for testing - matches what analyze_list.yaml would contain
ANALYZE_LIST_TEMPLATE = """Analyze the following {{ items|length }} items:

{% for item in items %}
### {{ loop.index }}. {{ item.title }}

**Topic**: {{ item.topic }}
**Word Count**: {{ item.word_count }}
{% if item.tags %}**Tags**: {{ item.tags | join(", ") }}{% endif %}
{% if item.content %}
**Content**:
{{ item.content[:200] }}{% if item.content|length > 200 %}...{% endif %}
{% endif %}

{% endfor %}
{% if min_confidence %}
Only include results with confidence >= {{ min_confidence }}.
{% endif %}
"""


@pytest.mark.req("REQ-YG-012", "REQ-YG-013")
def test_jinja2_analyze_list_prompt():
    """Test Jinja2 template with loops, filters, and conditionals."""
    # Test data
    variables = {
        "items": [
            {
                "title": "Introduction to AI",
                "topic": "Artificial Intelligence",
                "word_count": 500,
                "tags": ["AI", "machine learning", "technology"],
                "content": "Artificial intelligence is transforming how we interact with technology...",
            },
            {
                "title": "Machine Learning Basics",
                "topic": "ML Fundamentals",
                "word_count": 750,
                "tags": ["ML", "algorithms", "data"],
                "content": "Machine learning involves training models on data to make predictions...",
            },
        ],
        "min_confidence": 0.8,
    }

    result = format_prompt(ANALYZE_LIST_TEMPLATE, variables)

    # Verify Jinja2 features are working
    assert "2 items" in result  # {{ items|length }} filter
    assert "1. Introduction to AI" in result  # {{ loop.index }}
    assert "2. Machine Learning Basics" in result
    assert "**Tags**: AI, machine learning, technology" in result  # join filter
    assert "**Tags**: ML, algorithms, data" in result
    assert "confidence >= 0.8" in result  # conditional rendering
    assert "**Content**:" in result  # if/else conditional

    # Verify loop counter
    assert "### 1." in result
    assert "### 2." in result


@pytest.mark.req("REQ-YG-012", "REQ-YG-013")
def test_jinja2_prompt_with_empty_list():
    """Test Jinja2 template with empty items."""
    variables = {"items": [], "min_confidence": None}

    result = format_prompt(ANALYZE_LIST_TEMPLATE, variables)

    # Should handle empty list gracefully
    assert "0 items" in result
    assert "### 1." not in result  # No items to iterate


@pytest.mark.req("REQ-YG-012", "REQ-YG-013")
def test_jinja2_prompt_without_optional_fields():
    """Test Jinja2 template without optional fields."""
    variables = {
        "items": [
            {
                "title": "Short Content",
                "topic": "Brief",
                "word_count": 100,
                "tags": [],  # Empty tags
                "content": "Short content without tags",
            },
        ],
    }

    result = format_prompt(ANALYZE_LIST_TEMPLATE, variables)

    # Should handle missing/empty optional fields
    assert "1 items" in result
    assert "Short Content" in result
    # Should not show tags section if empty
    assert "**Tags**:" not in result or "**Tags**: \n" in result
    # Should not show min_confidence note if not provided
    assert "confidence >=" not in result
