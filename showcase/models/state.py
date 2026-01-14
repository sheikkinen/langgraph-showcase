"""LangGraph State Definitions.

Defines typed state schemas for different graph types.
Provides specialized states for each demo while maintaining
backward compatibility via ShowcaseState alias.
"""

from datetime import datetime
from typing import Annotated, TypedDict
from operator import add

from showcase.models.schemas import (
    Analysis,
    Critique,
    DraftContent,
    GeneratedContent,
    PipelineError,
    ToneClassification,
)


# =============================================================================
# Base State - Common fields for all graphs
# =============================================================================


class BaseState(TypedDict, total=False):
    """Common fields for all graphs.

    Provides shared functionality like error tracking and timestamps.
    """

    thread_id: str
    current_step: str
    error: PipelineError | None
    errors: list[PipelineError]
    started_at: datetime | None
    completed_at: datetime | None


# =============================================================================
# Specialized States
# =============================================================================


class ContentState(BaseState, total=False):
    """State for content generation pipeline.

    Used by: graphs/showcase.yaml
    """

    topic: str
    style: str
    word_count: int
    generated: GeneratedContent | None
    analysis: Analysis | None
    final_summary: str | None


class RouterState(BaseState, total=False):
    """State for router demo.

    Used by: graphs/router-demo.yaml
    """

    message: str
    classification: ToneClassification | None
    response: str | None
    _route: str | None


class ReflexionState(BaseState, total=False):
    """State for self-correction loops.

    Used by: graphs/reflexion-demo.yaml
    """

    topic: str
    current_draft: DraftContent | None
    critique: Critique | None
    _loop_counts: dict[str, int]
    _loop_limit_reached: bool


class AgentState(BaseState, total=False):
    """State for agent with tool use.

    Used by: graphs/git-report.yaml

    Note: messages uses Annotated with add reducer for accumulation.
    """

    input: str
    messages: Annotated[list, add]  # Accumulates across iterations
    analysis: str | None
    report: object | None  # Flexible for different report types
    _tool_results: list[dict] | None  # Raw tool outputs
    _agent_iterations: int
    _agent_limit_reached: bool


# =============================================================================
# Backward Compatibility
# =============================================================================


# Alias for backward compatibility - existing code uses ShowcaseState
ShowcaseState = ContentState


def create_initial_state(
    topic: str,
    style: str = "informative",
    word_count: int = 300,
    thread_id: str | None = None,
) -> ShowcaseState:
    """Create an initial state for a new pipeline run.

    Args:
        topic: The topic to generate content about
        style: Writing style (default: informative)
        word_count: Target word count (default: 300)
        thread_id: Optional thread ID (auto-generated if not provided)

    Returns:
        Initialized ShowcaseState dictionary
    """
    import uuid

    return ShowcaseState(
        thread_id=thread_id or uuid.uuid4().hex[:16],  # 16 chars for better uniqueness
        topic=topic,
        style=style,
        word_count=word_count,
        generated=None,
        analysis=None,
        final_summary=None,
        current_step="init",
        error=None,
        errors=[],
        started_at=datetime.now(),
        completed_at=None,
    )
