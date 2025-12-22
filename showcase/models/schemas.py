"""Pydantic models for structured LLM outputs.

These models define the expected structure of LLM responses,
enabling type-safe, validated outputs from prompts.
"""

from pydantic import BaseModel, Field


class Greeting(BaseModel):
    """Structured greeting response."""
    
    message: str = Field(description="The greeting message")
    tone: str = Field(description="The tone used (formal, casual, enthusiastic)")
    language: str = Field(default="en", description="Language code")


class Analysis(BaseModel):
    """Structured content analysis."""
    
    summary: str = Field(description="Brief summary of the content")
    key_points: list[str] = Field(description="Main points extracted")
    sentiment: str = Field(description="Overall sentiment: positive, neutral, or negative")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")


class GeneratedContent(BaseModel):
    """Creative content generation output."""
    
    title: str = Field(description="Title of the generated content")
    content: str = Field(description="The main generated text")
    word_count: int = Field(description="Approximate word count")
    tags: list[str] = Field(default_factory=list, description="Relevant tags")


class PipelineResult(BaseModel):
    """Combined result from multi-step pipeline."""
    
    topic: str = Field(description="Original topic")
    generated: GeneratedContent = Field(description="Generated content")
    analysis: Analysis = Field(description="Analysis of generated content")
    final_summary: str = Field(description="Final summarized output")
