"""Type-safe constants for YAML graph configuration.

Provides enums for node types, error handlers, and other magic strings
used throughout the codebase to enable static type checking and IDE support.
"""

from enum import StrEnum


class NodeType(StrEnum):
    """Valid node types in YAML graph configuration."""

    LLM = "llm"
    ROUTER = "router"
    TOOL = "tool"
    AGENT = "agent"
    PYTHON = "python"
    MAP = "map"

    @classmethod
    def requires_prompt(cls, node_type: str) -> bool:
        """Check if node type requires a prompt field.

        Args:
            node_type: The node type string

        Returns:
            True if the node type requires a prompt
        """
        return node_type in (cls.LLM, cls.ROUTER)


class ErrorHandler(StrEnum):
    """Valid on_error handling strategies."""

    SKIP = "skip"  # Skip node and continue pipeline
    RETRY = "retry"  # Retry with max_retries attempts
    FAIL = "fail"  # Raise exception immediately
    FALLBACK = "fallback"  # Try fallback provider

    @classmethod
    def all_values(cls) -> set[str]:
        """Return all valid error handler values.

        Returns:
            Set of valid error handler strings
        """
        return {handler.value for handler in cls}


class EdgeType(StrEnum):
    """Valid edge types in graph configuration."""

    SIMPLE = "simple"  # Direct edge from -> to
    CONDITIONAL = "conditional"  # Edge with conditions


class SpecialNodes(StrEnum):
    """Special node names with semantic meaning."""

    START = "__start__"
    END = "__end__"


# Re-export for convenience
__all__ = ["NodeType", "ErrorHandler", "EdgeType", "SpecialNodes"]
