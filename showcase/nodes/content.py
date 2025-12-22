"""Node functions for the showcase pipeline.

Each node is a function that takes state and returns a partial update.
"""

from showcase.executor import execute_prompt
from showcase.models import Analysis, GeneratedContent, ShowcaseState


def generate_node(state: ShowcaseState) -> dict:
    """Generate content based on topic.
    
    This node uses the 'generate' prompt to create content
    with structured output.
    """
    print(f"📝 Generating content about: {state['topic']}")
    
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
    
    return {
        "generated": result,
        "current_step": "generate",
    }


def analyze_node(state: ShowcaseState) -> dict:
    """Analyze the generated content.
    
    This node uses the 'analyze' prompt to extract
    structured insights from the generated content.
    """
    generated = state.get("generated")
    if not generated:
        return {"error": "No content to analyze", "current_step": "analyze"}
    
    print(f"🔍 Analyzing: {generated.title}")
    
    result = execute_prompt(
        "analyze",
        variables={"content": generated.content},
        output_model=Analysis,
        temperature=0.3,
    )
    
    print(f"   ✓ Sentiment: {result.sentiment} (confidence: {result.confidence:.2f})")
    
    return {
        "analysis": result,
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
        return {"error": "Missing data for summary", "current_step": "summarize"}
    
    print("📊 Creating final summary...")
    
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
    
    return {
        "final_summary": result,
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
