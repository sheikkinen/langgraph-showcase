"""Shared test fixtures for yamlgraph tests.

This module provides test-only Pydantic models and fixtures for testing.
These models are intentionally NOT imported from yamlgraph.models to
demonstrate that the framework is truly generic and works with any schema.
"""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field

from yamlgraph.models import create_initial_state

# =============================================================================
# Test-Only Pydantic Models (Fixtures)
# =============================================================================
# These replicate demo model structures but are defined here to prove
# the framework is generic and doesn't depend on demo-specific schemas.
# Named with "Fixture" suffix to avoid pytest collection warnings.


class FixtureGeneratedContent(BaseModel):
    """Test fixture for generated content."""

    title: str = Field(description="Title of the generated content")
    content: str = Field(description="The main generated text")
    word_count: int = Field(description="Approximate word count")
    tags: list[str] = Field(default_factory=list, description="Relevant tags")


class FixtureAnalysis(BaseModel):
    """Test fixture for content analysis."""

    summary: str = Field(description="Brief summary of the content")
    key_points: list[str] = Field(description="Main points extracted")
    sentiment: str = Field(description="Overall sentiment")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")


class FixtureToneClassification(BaseModel):
    """Test fixture for tone classification."""

    tone: str = Field(description="Detected tone: positive, negative, or neutral")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    reasoning: str = Field(description="Explanation for the classification")


class FixtureDraftContent(BaseModel):
    """Test fixture for draft content."""

    content: str = Field(description="The draft content")
    version: int = Field(default=1, description="Draft version number")


class FixtureCritique(BaseModel):
    """Test fixture for critique output."""

    score: float = Field(ge=0.0, le=1.0, description="Quality score 0-1")
    feedback: str = Field(description="Specific improvement suggestions")
    issues: list[str] = Field(
        default_factory=list, description="List of identified issues"
    )
    should_refine: bool = Field(
        default=True, description="Whether refinement is needed"
    )


class FixtureGitReport(BaseModel):
    """Test fixture for git report."""

    title: str = Field(description="Report title")
    summary: str = Field(description="Executive summary")
    key_findings: list[str] = Field(description="Main findings")
    recommendations: list[str] = Field(default_factory=list, description="Suggestions")


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_generated_content() -> FixtureGeneratedContent:
    """Sample generated content for testing."""
    return FixtureGeneratedContent(
        title="Test Article",
        content="This is test content about artificial intelligence. " * 20,
        word_count=100,
        tags=["test", "ai"],
    )


@pytest.fixture
def sample_analysis() -> FixtureAnalysis:
    """Sample analysis for testing."""
    return FixtureAnalysis(
        summary="This is a test summary of the content.",
        key_points=["Point 1", "Point 2", "Point 3"],
        sentiment="positive",
        confidence=0.85,
    )


@pytest.fixture
def sample_state(sample_generated_content, sample_analysis) -> dict:
    """Complete sample state for testing."""
    state = create_initial_state(
        topic="artificial intelligence",
        style="informative",
        word_count=300,
        thread_id="test123",
    )
    state["generated"] = sample_generated_content
    state["analysis"] = sample_analysis
    state["final_summary"] = "This is the final summary."
    state["current_step"] = "summarize"
    return state


@pytest.fixture
def empty_state() -> dict:
    """Initial empty state for testing."""
    return create_initial_state(
        topic="test topic",
        style="casual",
        word_count=200,
    )


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Temporary output directory for testing."""
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_llm_response():
    """Mock LLM that returns predictable responses."""

    def _create_mock(response_content: str | dict = "Mocked response"):
        mock = MagicMock()
        mock_response = MagicMock()
        mock_response.content = response_content
        mock.invoke.return_value = mock_response
        return mock

    return _create_mock


@pytest.fixture
def mock_structured_llm(sample_generated_content, sample_analysis):
    """Mock LLM with structured output support."""

    def _create_mock(model_type: str):
        mock = MagicMock()
        if model_type == "generate":
            mock.invoke.return_value = sample_generated_content
        elif model_type == "analyze":
            mock.invoke.return_value = sample_analysis
        else:
            mock.invoke.return_value = "Mocked summary"
        return mock

    return _create_mock
