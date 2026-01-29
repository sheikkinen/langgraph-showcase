"""LangSmith tools for agent use.

Provides tool wrappers for LangSmith functions, enabling agents
to inspect previous runs, check for errors, and implement
self-correcting behavior.

Example YAML configuration:
    tools:
      check_last_run:
        type: python
        module: yamlgraph.tools.langsmith_tools
        function: get_run_details_tool
        description: "Get status and errors from a pipeline run"

      get_errors:
        type: python
        module: yamlgraph.tools.langsmith_tools
        function: get_run_errors_tool
        description: "Get detailed error info from a run"

      failed_runs:
        type: python
        module: yamlgraph.tools.langsmith_tools
        function: get_failed_runs_tool
        description: "List recent failed runs"
"""

from __future__ import annotations

import logging
from typing import Any

from yamlgraph.utils.langsmith import (
    get_failed_runs,
    get_run_details,
    get_run_errors,
)

logger = logging.getLogger(__name__)


def get_run_details_tool(run_id: str | None = None) -> dict[str, Any]:
    """Get detailed information about a LangSmith run.

    This tool wrapper returns run details in a format suitable for
    agent consumption.

    Args:
        run_id: Run ID to inspect. If not provided, uses the latest run.

    Returns:
        Dict with run details or error message:
        - id: Run identifier
        - name: Run name (usually the graph/pipeline name)
        - status: "success", "error", or "pending"
        - error: Error message if status is "error"
        - start_time: When the run started (ISO format)
        - end_time: When the run completed (ISO format)
        - inputs: The input data for the run
        - outputs: The output data from the run
        - run_type: Type of run (chain, llm, tool, etc.)
    """
    result = get_run_details(run_id)
    if result is None:
        return {"error": "Could not retrieve run details", "success": False}

    result["success"] = True
    return result


def get_run_errors_tool(run_id: str | None = None) -> dict[str, Any]:
    """Get all errors from a run and its child nodes.

    This tool retrieves error information from both the parent run
    and all child runs (individual nodes in the graph).

    Args:
        run_id: Run ID to inspect. If not provided, uses the latest run.

    Returns:
        Dict with error information:
        - success: Whether the query succeeded
        - error_count: Number of errors found
        - errors: List of error dicts, each with:
            - node: Name of the failed node
            - error: Error message
            - run_type: Type of the failed run
    """
    errors = get_run_errors(run_id)
    return {
        "success": True,
        "error_count": len(errors),
        "errors": errors,
        "has_errors": len(errors) > 0,
    }


def get_failed_runs_tool(
    limit: int = 10,
    project_name: str | None = None,
) -> dict[str, Any]:
    """Get recent failed runs from the LangSmith project.

    This tool helps identify patterns in failures across multiple runs.

    Args:
        limit: Maximum number of failed runs to return (default: 10)
        project_name: LangSmith project name. Uses default if not provided.

    Returns:
        Dict with failed run information:
        - success: Whether the query succeeded
        - failed_count: Number of failed runs found
        - runs: List of failed run summaries, each with:
            - id: Run identifier
            - name: Run name
            - error: Error message
            - start_time: When the run started (ISO format)
    """
    runs = get_failed_runs(project_name=project_name, limit=limit)
    return {
        "success": True,
        "failed_count": len(runs),
        "runs": runs,
    }
