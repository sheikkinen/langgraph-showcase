"""Pydantic models for structured LLM outputs.

This module contains FRAMEWORK models only - models used by the framework itself.
Demo-specific output schemas are defined inline in graph YAML files.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Error Types
# =============================================================================


class ErrorType(StrEnum):
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
    retryable: bool = Field(
        default=False, description="Whether this error can be retried"
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional error context"
    )

    @classmethod
    def from_exception(
        cls, e: Exception, node: str, error_type: ErrorType | None = None
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
# Generic Report Model (Flexible for Any Use Case)
# =============================================================================


class GenericReport(BaseModel):
    """Flexible report structure for any use case.

    Use this when you don't need a custom schema - works for most
    analysis and summary tasks. The LLM can populate any combination
    of the optional fields as needed.

    Example usage in graph YAML:
        nodes:
          analyze:
            type: llm
            prompt: my_analysis
            output_model: yamlgraph.models.GenericReport

    Example prompts can request specific sections:
        "Analyze the repository and provide:
         - A summary of findings
         - Key findings as bullet points
         - Recommendations for improvement"
    """

    title: str = Field(description="Report title")
    summary: str = Field(description="Executive summary")
    sections: dict[str, Any] = Field(
        default_factory=dict,
        description="Named sections with any content (strings, dicts, lists)",
    )
    findings: list[str] = Field(
        default_factory=list, description="Key findings or bullet points"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Suggested actions or areas to focus on"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional key-value data (author, version, tags, etc.)",
    )
