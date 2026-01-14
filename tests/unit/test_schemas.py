"""Tests for showcase.models.schemas module."""

import pytest
from pydantic import ValidationError

from showcase.models import Analysis, GeneratedContent, Greeting, PipelineResult


class TestGreeting:
    """Tests for Greeting model."""

    def test_valid_greeting(self):
        """Valid greeting should be created."""
        greeting = Greeting(
            message="Hello, World!",
            tone="casual",
            language="en",
        )
        assert greeting.message == "Hello, World!"
        assert greeting.tone == "casual"
        assert greeting.language == "en"

    def test_default_language(self):
        """Default language should be 'en'."""
        greeting = Greeting(message="Hi", tone="formal")
        assert greeting.language == "en"

    def test_missing_required_fields(self):
        """Missing required fields should raise error."""
        with pytest.raises(ValidationError):
            Greeting(message="Hi")  # missing tone


class TestAnalysis:
    """Tests for Analysis model."""

    def test_valid_analysis(self):
        """Valid analysis should be created."""
        analysis = Analysis(
            summary="Test summary",
            key_points=["Point 1", "Point 2"],
            sentiment="positive",
            confidence=0.9,
        )
        assert analysis.summary == "Test summary"
        assert len(analysis.key_points) == 2
        assert analysis.sentiment == "positive"
        assert analysis.confidence == 0.9

    def test_confidence_bounds_low(self):
        """Confidence below 0 should raise error."""
        with pytest.raises(ValidationError):
            Analysis(
                summary="Test",
                key_points=[],
                sentiment="neutral",
                confidence=-0.1,
            )

    def test_confidence_bounds_high(self):
        """Confidence above 1 should raise error."""
        with pytest.raises(ValidationError):
            Analysis(
                summary="Test",
                key_points=[],
                sentiment="neutral",
                confidence=1.1,
            )

    def test_confidence_bounds_valid(self):
        """Confidence at boundaries should be valid."""
        analysis_low = Analysis(
            summary="Test", key_points=[], sentiment="neutral", confidence=0.0
        )
        analysis_high = Analysis(
            summary="Test", key_points=[], sentiment="neutral", confidence=1.0
        )
        assert analysis_low.confidence == 0.0
        assert analysis_high.confidence == 1.0


class TestGeneratedContent:
    """Tests for GeneratedContent model."""

    def test_valid_content(self):
        """Valid generated content should be created."""
        content = GeneratedContent(
            title="Test Title",
            content="This is the content.",
            word_count=4,
            tags=["test"],
        )
        assert content.title == "Test Title"
        assert content.word_count == 4

    def test_default_tags(self):
        """Default tags should be empty list."""
        content = GeneratedContent(
            title="Test",
            content="Content",
            word_count=1,
        )
        assert content.tags == []

    def test_model_dump(self):
        """Model should serialize to dict."""
        content = GeneratedContent(
            title="Test",
            content="Content",
            word_count=1,
            tags=["a", "b"],
        )
        data = content.model_dump()
        assert data["title"] == "Test"
        assert data["tags"] == ["a", "b"]


class TestPipelineResult:
    """Tests for PipelineResult model."""

    def test_valid_result(self):
        """Valid pipeline result should be created."""
        generated = GeneratedContent(title="Test", content="Content", word_count=1)
        analysis = Analysis(
            summary="Summary",
            key_points=["Point"],
            sentiment="positive",
            confidence=0.8,
        )
        result = PipelineResult(
            topic="test topic",
            generated=generated,
            analysis=analysis,
            final_summary="Final summary",
        )
        assert result.topic == "test topic"
        assert result.generated.title == "Test"
        assert result.analysis.sentiment == "positive"
