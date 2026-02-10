"""YamlGraph - YAML-first LLM pipeline framework.

Framework for building LLM pipelines with YAML configuration.
State is generated dynamically from graph config.
"""

from pathlib import Path

from yamlgraph.executor import execute_prompt, get_executor
from yamlgraph.graph_loader import load_and_compile
from yamlgraph.models import (
    ErrorType,
    GenericReport,
    PipelineError,
    build_state_class,
    create_initial_state,
)
from yamlgraph.utils.tracing import (
    create_tracer,
    get_trace_url,
    inject_tracer_config,
    is_tracing_enabled,
    share_trace,
)


def get_schema_path() -> Path:
    """Get path to the bundled JSON Schema for graph YAML files.

    Returns:
        Path to the bundled graph-v1.json schema file.
    """
    return Path(__file__).parent / "schemas" / "graph-v1.json"


__all__ = [
    # Graph loader
    "load_and_compile",
    # Executor
    "execute_prompt",
    "get_executor",
    # Framework models
    "ErrorType",
    "PipelineError",
    "GenericReport",
    # Dynamic state
    "build_state_class",
    "create_initial_state",
    # Schema
    "get_schema_path",
    # Tracing (FR-022)
    "is_tracing_enabled",
    "create_tracer",
    "get_trace_url",
    "share_trace",
    "inject_tracer_config",
]
