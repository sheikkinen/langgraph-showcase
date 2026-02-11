"""Utility functions for observability and logging."""

from yamlgraph.utils.conditions import evaluate_condition
from yamlgraph.utils.expressions import (
    resolve_state_expression,
    resolve_state_path,
    resolve_template,
)
from yamlgraph.utils.json_extract import extract_json
from yamlgraph.utils.logging import get_logger, setup_logging
from yamlgraph.utils.prompts import load_prompt, load_prompt_path, resolve_prompt_path
from yamlgraph.utils.template import extract_variables, validate_variables
from yamlgraph.utils.token_tracker import (
    TokenUsageCallbackHandler,
    create_token_tracker,
)
from yamlgraph.utils.tracing import (
    create_tracer,
    get_trace_url,
    inject_tracer_config,
    is_tracing_enabled,
    share_trace,
)

__all__ = [
    # Conditions
    "evaluate_condition",
    # Expression resolution (consolidated)
    "resolve_state_path",
    "resolve_state_expression",
    "resolve_template",
    # JSON extraction
    "extract_json",
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
    # Tracing (FR-022)
    "is_tracing_enabled",
    "create_tracer",
    "get_trace_url",
    "share_trace",
    "inject_tracer_config",
    # Token tracking (FR-027 P2-8)
    "TokenUsageCallbackHandler",
    "create_token_tracker",
]
