"""Node functions for the showcase pipeline.

Each node is a function that takes state and returns a partial update.
"""

import logging

from showcase.executor import execute_prompt
from showcase.models import (
    Analysis,
    ErrorType,
    GeneratedContent,
    PipelineError,
    ShowcaseState,
)

logger = logging.getLogger(__name__)


def _add_error(state: ShowcaseState, error: PipelineError) -> dict:
    """Helper to add an error to the state.
    
    Args:
        state: Current pipeline state
        error: The error to add
        
    Returns:
        State update dict with error info
    """
    errors = list(state.get("errors", []))
    errors.append(error)
    return {
        "error": error,
        "errors": errors,
    }


def generate_node(state: ShowcaseState) -> dict:
    """Generate content based on topic.
    
    This node uses the 'generate' prompt to create content
    with structured output.
    """
    print(f"📝 Generating content about: {state['topic']}")
    logger.info("Starting content generation", extra={"topic": state["topic"]})
    
    try:
        result = execute_prompt(
            "generate",
            variables={
                "topic": state["topic"],
                "word_count": state.get("word_count", 300),
                "style": state.get("style", "informative"),
            },
            output_model=GeneratedContent,
            temperature=0.8,
        )
        
        print(f"   ✓ Generated: {result.title} ({result.word_count} words)")
        logger.info("Content generated", extra={"title": result.title, "words": result.word_count})
        
        return {
            "generated": result,
            "current_step": "generate",
        }
    except Exception as e:
        print(f"   ✗ Error: {e}")
        logger.error("Generation failed", exc_info=True)
        
        error = PipelineError.from_exception(e, node="generate")
        return {
            **_add_error(state, error),
            "current_step": "generate",
        }


def analyze_node(state: ShowcaseState) -> dict:
    """Analyze the generated content.
    
    This node uses the 'analyze' prompt to extract
    structured insights from the generated content.
    """
    generated = state.get("generated")
    if not generated:
        error = PipelineError(
            type=ErrorType.STATE_ERROR,
            message="No content to analyze",
            node="analyze",
            retryable=False,
        )
        return {**_add_error(state, error), "current_step": "analyze"}
    
    print(f"🔍 Analyzing: {generated.title}")
    logger.info("Starting analysis", extra={"title": generated.title})
    
    try:
        result = execute_prompt(
            "analyze",
            variables={"content": generated.content},
            output_model=Analysis,
            temperature=0.3,
        )
        
        print(f"   ✓ Sentiment: {result.sentiment} (confidence: {result.confidence:.2f})")
        logger.info("Analysis complete", extra={"sentiment": result.sentiment})
        
        return {
            "analysis": result,
            "current_step": "analyze",
        }
    except Exception as e:
        print(f"   ✗ Error: {e}")
        logger.error("Analysis failed", exc_info=True)
        
        error = PipelineError.from_exception(e, node="analyze")
        return {
            **_add_error(state, error),
            "current_step": "analyze",
        }


def summarize_node(state: ShowcaseState) -> dict:
    """Create final summary from generated content and analysis.
    
    This node combines the outputs from previous nodes
    into a final summary.
    """
    generated = state.get("generated")
    analysis = state.get("analysis")
    
    if not generated or not analysis:
        error = PipelineError(
            type=ErrorType.STATE_ERROR,
            message="Missing data for summary",
            node="summarize",
            retryable=False,
        )
        return {**_add_error(state, error), "current_step": "summarize"}
    
    print("📊 Creating final summary...")
    logger.info("Starting summary")
    
    try:
        result = execute_prompt(
            "summarize",
            variables={
                "topic": state["topic"],
                "generated_content": generated.content,
                "analysis_summary": analysis.summary,
                "key_points": ", ".join(analysis.key_points),
                "sentiment": analysis.sentiment,
            },
            temperature=0.5,
        )
        
        print("   ✓ Summary complete")
        logger.info("Summary complete")
        
        return {
            "final_summary": result,
            "current_step": "summarize",
        }
    except Exception as e:
        print(f"   ✗ Error: {e}")
        logger.error("Summary failed", exc_info=True)
        
        error = PipelineError.from_exception(e, node="summarize")
        return {
            **_add_error(state, error),
            "current_step": "summarize",
        }


def should_continue(state: ShowcaseState) -> str:
    """Decide whether to continue or end the pipeline.
    
    Returns:
        'continue' to proceed to analysis, 'end' to stop
    """
    if state.get("error"):
        return "end"
    if state.get("generated") is None:
        return "end"
    return "continue"
