"""Shared test fixtures for langgraph-showcase tests."""

from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest

from showcase.models import (
    Analysis,
    GeneratedContent,
    ShowcaseState,
    create_initial_state,
)
from showcase.storage import ShowcaseDB


@pytest.fixture
def sample_generated_content() -> GeneratedContent:
    """Sample generated content for testing."""
    return GeneratedContent(
        title="Test Article",
        content="This is test content about artificial intelligence. " * 20,
        word_count=100,
        tags=["test", "ai"],
    )


@pytest.fixture
def sample_analysis() -> Analysis:
    """Sample analysis for testing."""
    return Analysis(
        summary="This is a test summary of the content.",
        key_points=["Point 1", "Point 2", "Point 3"],
        sentiment="positive",
        confidence=0.85,
    )


@pytest.fixture
def sample_state(sample_generated_content, sample_analysis) -> ShowcaseState:
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
def empty_state() -> ShowcaseState:
    """Initial empty state for testing."""
    return create_initial_state(
        topic="test topic",
        style="casual",
        word_count=200,
    )


@pytest.fixture
def temp_db(tmp_path: Path) -> Generator[ShowcaseDB, None, None]:
    """Temporary database for testing."""
    db_path = tmp_path / "test.db"
    db = ShowcaseDB(db_path=db_path)
    yield db


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
