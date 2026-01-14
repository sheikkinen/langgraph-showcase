"""Integration test for Jinja2 prompt templates."""

from showcase.executor import load_prompt, format_prompt


def test_jinja2_analyze_list_prompt():
    """Test the analyze_list prompt with Jinja2 features."""
    prompt = load_prompt("analyze_list")

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

    # Format the template field
    result = format_prompt(prompt["template"], variables)

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


def test_jinja2_prompt_with_empty_list():
    """Test analyze_list prompt with empty items."""
    prompt = load_prompt("analyze_list")

    variables = {"items": [], "min_confidence": None}

    result = format_prompt(prompt["template"], variables)

    # Should handle empty list gracefully
    assert "0 items" in result
    assert "### 1." not in result  # No items to iterate


def test_jinja2_prompt_without_optional_fields():
    """Test analyze_list prompt without optional fields."""
    prompt = load_prompt("analyze_list")

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

    result = format_prompt(prompt["template"], variables)

    # Should handle missing/empty optional fields
    assert "1 items" in result
    assert "Short Content" in result
    # Should not show tags section if empty
    assert "**Tags**:" not in result or "**Tags**: \n" in result
    # Should not show min_confidence note if not provided
    assert "confidence >=" not in result
