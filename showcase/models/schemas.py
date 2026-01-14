"""Pydantic models for structured LLM outputs.

These models define the expected structure of LLM responses,
enabling type-safe, validated outputs from prompts.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Error Types
# =============================================================================


class ErrorType(str, Enum):
    """Types of errors that can occur in the pipeline."""
    
    LLM_ERROR = "llm_error"  # LLM API errors (rate limit, timeout, etc.)
    VALIDATION_ERROR = "validation_error"  # Pydantic validation failures
    PROMPT_ERROR = "prompt_error"  # Missing prompt, template errors
    STATE_ERROR = "state_error"  # Missing required state data
    UNKNOWN_ERROR = "unknown_error"  # Catch-all


class PipelineError(BaseModel):
    """Structured error information for pipeline failures."""
    
    type: ErrorType = Field(description="Category of error")
    message: str = Field(description="Human-readable error message")
    node: str = Field(description="Node where error occurred")
    timestamp: datetime = Field(default_factory=datetime.now)
    retryable: bool = Field(default=False, description="Whether this error can be retried")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error context")
    
    @classmethod
    def from_exception(
        cls, 
        e: Exception, 
        node: str, 
        error_type: ErrorType | None = None
    ) -> "PipelineError":
        """Create a PipelineError from an exception.
        
        Args:
            e: The exception that occurred
            node: Name of the node where error occurred
            error_type: Optional explicit error type
            
        Returns:
            PipelineError instance
        """
        # Infer error type from exception
        if error_type is None:
            exc_name = type(e).__name__.lower()
            if "rate" in exc_name or "timeout" in exc_name or "api" in exc_name:
                error_type = ErrorType.LLM_ERROR
                retryable = True
            elif "validation" in exc_name:
                error_type = ErrorType.VALIDATION_ERROR
                retryable = False
            elif "file" in exc_name or "prompt" in exc_name:
                error_type = ErrorType.PROMPT_ERROR
                retryable = False
            else:
                error_type = ErrorType.UNKNOWN_ERROR
                retryable = False
        else:
            retryable = error_type == ErrorType.LLM_ERROR
        
        return cls(
            type=error_type,
            message=str(e),
            node=node,
            retryable=retryable,
            details={"exception_type": type(e).__name__},
        )


# =============================================================================
# LLM Output Models
# =============================================================================


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


# =============================================================================
# Router Models
# =============================================================================


class ToneClassification(BaseModel):
    """Classification result for tone-based routing."""
    
    tone: str = Field(description="Detected tone: positive, negative, or neutral")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    reasoning: str = Field(description="Explanation for the classification")
