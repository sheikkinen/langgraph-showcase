"""LangGraph State Definition.

Defines the TypedDict state used by the showcase pipeline,
following LangGraph's state management pattern.
"""

from datetime import datetime
from typing import TypedDict

from showcase.models.schemas import Analysis, GeneratedContent, PipelineError


class ShowcaseState(TypedDict, total=False):
    """Pipeline state for the showcase graph.
    
    All fields are optional (total=False) to support incremental updates.
    
    Attributes:
        thread_id: Unique identifier for this pipeline run
        topic: The topic to generate content about
        style: Writing style (informative, casual, technical)
        word_count: Target word count for generation
        
        generated: Output from the generate node
        analysis: Output from the analyze node
        final_summary: Output from the summarize node
        
        current_step: Name of the current pipeline step
        error: Structured error information (if any)
        errors: List of all errors encountered
        
        started_at: Pipeline start timestamp
        completed_at: Pipeline completion timestamp
        
        _route: Internal field for router node routing decisions
    """
    # Input fields
    thread_id: str
    topic: str
    style: str
    word_count: int
    message: str  # For router demo
    topic: str  # For reflexion demo
    
    # Pipeline outputs
    generated: GeneratedContent | None
    analysis: Analysis | None
    final_summary: str | None
    classification: object | None  # For router demo
    response: str | None  # For router demo
    current_draft: object | None  # For reflexion demo
    critique: object | None  # For reflexion demo
    
    # Metadata
    current_step: str
    error: PipelineError | None  # Current/last error
    errors: list[PipelineError]  # All errors encountered
    
    # Router internal
    _route: str | None  # Router routing decision
    
    # Loop tracking
    _loop_counts: dict[str, int]  # Per-node iteration counts
    _loop_limit_reached: bool  # Flag when limit hit
    
    # Timestamps
    started_at: datetime | None
    completed_at: datetime | None


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
