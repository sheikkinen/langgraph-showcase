"""Pydantic models and state definitions.

Framework models for error handling and generic reports.
Demo-specific output schemas are defined inline in graph YAML files.
"""

from showcase.models.schemas import (
    ErrorType,
    GenericReport,
    PipelineError,
)
from showcase.models.state import (
    AgentState,
    ReflexionState,
    RouterState,
    ShowcaseState,
    create_initial_state,
)

__all__ = [
    # Framework models
    "ErrorType",
    "PipelineError",
    "GenericReport",
    # States
    "ShowcaseState",
    "RouterState",
    "ReflexionState",
    "AgentState",
    "create_initial_state",
]
