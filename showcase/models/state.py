"""LangGraph State Definition.

Defines the TypedDict state used by the showcase pipeline,
following LangGraph's state management pattern.
"""

from typing import TypedDict

from showcase.models.schemas import Analysis, GeneratedContent


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
        error: Any error message from the pipeline
    """
    # Input fields
    thread_id: str
    topic: str
    style: str
    word_count: int
    
    # Pipeline outputs
    generated: GeneratedContent | None
    analysis: Analysis | None
    final_summary: str | None
    
    # Metadata
    current_step: str
    error: str | None


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
        thread_id=thread_id or str(uuid.uuid4())[:8],
        topic=topic,
        style=style,
        word_count=word_count,
        generated=None,
        analysis=None,
        final_summary=None,
        current_step="init",
        error=None,
    )
