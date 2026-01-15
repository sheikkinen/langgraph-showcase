"""Showcase package - LangGraph pipeline demonstration.

Framework for building LLM pipelines with YAML configuration.
Demo-specific output schemas are defined inline in graph YAML files.
"""

from showcase.builder import build_resume_graph, build_showcase_graph, run_pipeline
from showcase.executor import execute_prompt, get_executor
from showcase.models import (
    ErrorType,
    GenericReport,
    PipelineError,
    ShowcaseState,
    create_initial_state,
)
from showcase.storage import ShowcaseDB

__all__ = [
    # Builder
    "build_showcase_graph",
    "build_resume_graph",
    "run_pipeline",
    # Executor
    "execute_prompt",
    "get_executor",
    # Framework models
    "ErrorType",
    "PipelineError",
    "GenericReport",
    # State
    "ShowcaseState",
    "create_initial_state",
    # Storage
    "ShowcaseDB",
]
