"""Utility functions for observability and logging."""

from showcase.utils.conditions import evaluate_condition
from showcase.utils.expressions import (
    resolve_state_expression,
    resolve_state_path,
    resolve_template,
)
from showcase.utils.langsmith import (
    get_client,
    get_latest_run_id,
    get_project_name,
    get_run_url,
    is_tracing_enabled,
    log_execution,
    print_run_tree,
)
from showcase.utils.logging import get_logger, setup_logging
from showcase.utils.template import extract_variables, validate_variables

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
    # Template utilities
    "extract_variables",
    "validate_variables",
]
