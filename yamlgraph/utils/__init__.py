"""Utility functions for observability and logging."""

from yamlgraph.utils.conditions import evaluate_condition
from yamlgraph.utils.expressions import (
    resolve_state_expression,
    resolve_state_path,
    resolve_template,
)
from yamlgraph.utils.langsmith import (
    get_client,
    get_latest_run_id,
    get_project_name,
    get_run_url,
    is_tracing_enabled,
    log_execution,
    print_run_tree,
)
from yamlgraph.utils.logging import get_logger, setup_logging
from yamlgraph.utils.prompts import load_prompt, load_prompt_path, resolve_prompt_path
from yamlgraph.utils.template import extract_variables, validate_variables

__all__ = [
    # Conditions
    "evaluate_condition",
    # Expression resolution (consolidated)
    "resolve_state_path",
    "resolve_state_expression",
    "resolve_template",
    # LangSmith
    "get_client",
    "get_project_name",
    "is_tracing_enabled",
    "get_latest_run_id",
    "print_run_tree",
    "log_execution",
    "get_run_url",
    # Logging
    "get_logger",
    "setup_logging",
    # Prompts
    "resolve_prompt_path",
    "load_prompt",
    "load_prompt_path",
    # Template utilities
    "extract_variables",
    "validate_variables",
]
