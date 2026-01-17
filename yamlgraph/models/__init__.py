"""Pydantic models and state definitions.

Framework models for error handling and generic reports.
State is now generated dynamically by state_builder.py.
"""

from yamlgraph.models.graph_schema import (
    EdgeConfig,
    GraphConfigSchema,
    NodeConfig,
    validate_graph_schema,
)
from yamlgraph.models.schemas import (
    ErrorType,
    GenericReport,
    PipelineError,
)
from yamlgraph.models.state_builder import (
    build_state_class,
    create_initial_state,
)

__all__ = [
    # Framework models
    "ErrorType",
    "PipelineError",
    "GenericReport",
    # Graph config schema
    "GraphConfigSchema",
    "NodeConfig",
    "EdgeConfig",
    "validate_graph_schema",
    # Dynamic state generation
    "build_state_class",
    "create_initial_state",
]
