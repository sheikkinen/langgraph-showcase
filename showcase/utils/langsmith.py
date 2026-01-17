"""LangSmith Utilities - Tracing and observability helpers.

Provides functions for interacting with LangSmith traces,
printing execution trees, and logging run information.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from showcase.config import PROJECT_ROOT

logger = logging.getLogger(__name__)


def get_client() -> Any | None:
    """Get a LangSmith client if available.

    Returns:
        LangSmith Client instance or None if not configured
    """
    try:
        from langsmith import Client

        # Support both LANGCHAIN_* and LANGSMITH_* env vars
        api_key = os.environ.get("LANGCHAIN_API_KEY") or os.environ.get(
            "LANGSMITH_API_KEY"
        )
        if not api_key:
            return None

        endpoint = (
            os.environ.get("LANGCHAIN_ENDPOINT")
            or os.environ.get("LANGSMITH_ENDPOINT")
            or "https://api.smith.langchain.com"
        )
        return Client(api_url=endpoint, api_key=api_key)
    except ImportError:
        logger.debug("LangSmith package not installed, client unavailable")
        return None


def get_project_name() -> str:
    """Get the current LangSmith project name.

    Returns:
        Project name from environment or default
    """
    return (
        os.environ.get("LANGCHAIN_PROJECT")
        or os.environ.get("LANGSMITH_PROJECT")
        or "showcase-app"
    )


def is_tracing_enabled() -> bool:
    """Check if LangSmith tracing is enabled.

    Returns:
        True if tracing is enabled
    """
    # Support both env var names and values
    tracing_v2 = os.environ.get("LANGCHAIN_TRACING_V2", "").lower()
    tracing = os.environ.get("LANGSMITH_TRACING", "").lower()
    return tracing_v2 == "true" or tracing == "true"


def get_latest_run_id(project_name: str | None = None) -> str | None:
    """Get the ID of the most recent run.

    Args:
        project_name: Optional project name (uses default if not provided)

    Returns:
        Run ID string or None
    """
    client = get_client()
    if not client:
        return None

    project = project_name or get_project_name()

    try:
        runs = list(client.list_runs(project_name=project, limit=1))
        if runs:
            return str(runs[0].id)
    except Exception as e:
        logger.warning("Could not get latest run: %s", e)

    return None


def share_run(run_id: str | None = None) -> str | None:
    """Create a public share link for a run.

    Args:
        run_id: Run ID (uses latest if not provided)

    Returns:
        Public URL string or None if failed

    Example:
        >>> url = share_run()
        >>> print(url)
        https://eu.smith.langchain.com/public/abc123.../r
    """
    client = get_client()
    if not client:
        return None

    if not run_id:
        run_id = get_latest_run_id()

    if not run_id:
        return None

    try:
        # Use the share_run method from LangSmith SDK
        return client.share_run(run_id)
    except Exception as e:
        logger.warning("Could not share run: %s", e)
        return None


def read_run_shared_link(run_id: str) -> str | None:
    """Get existing share link for a run if it exists.

    Args:
        run_id: The run ID to check

    Returns:
        Public URL string or None if not shared
    """
    client = get_client()
    if not client:
        return None

    try:
        return client.read_run_shared_link(run_id)
    except Exception as e:
        logger.debug("Could not read run shared link for %s: %s", run_id, e)
        return None


def print_run_tree(run_id: str | None = None, verbose: bool = False) -> None:
    """Print an execution tree for a run.

    Args:
        run_id: Specific run ID (uses latest if not provided)
        verbose: Include timing and status details
    """
    client = get_client()
    if not client:
        logger.warning("LangSmith client not available")
        return

    if not run_id:
        run_id = get_latest_run_id()

    if not run_id:
        logger.warning("No run found")
        return

    try:
        run = client.read_run(run_id)
        _print_run_node(run, client, verbose=verbose, indent=0)
    except Exception as e:
        logger.warning("Error reading run: %s", e)


def _print_run_node(
    run,
    client,
    verbose: bool = False,
    indent: int = 0,
    is_last: bool = True,
    prefix: str = "",
):
    """Recursively print a run node and its children in tree format.

    Args:
        run: The LangSmith run object
        client: LangSmith client
        verbose: Include timing details
        indent: Current indentation level
        is_last: Whether this is the last sibling
        prefix: Prefix string for tree drawing
    """
    # Status emoji
    if run.status == "success":
        status = "✅"
    elif run.status == "error":
        status = "❌"
    else:
        status = "⏳"

    # Timing
    timing = ""
    if run.end_time and run.start_time:
        duration = (run.end_time - run.start_time).total_seconds()
        timing = f" ({duration:.1f}s)"

    # Tree connectors
    if indent == 0:
        connector = "📊 "
        new_prefix = ""
    else:
        connector = "└─ " if is_last else "├─ "
        new_prefix = prefix + ("   " if is_last else "│  ")

    # Clean up run name for display
    display_name = run.name
    if display_name.startswith("Chat"):
        display_name = f"🤖 {display_name}"
    elif "generate" in display_name.lower():
        display_name = f"📝 {display_name}"
    elif "analyze" in display_name.lower():
        display_name = f"🔍 {display_name}"
    elif "summarize" in display_name.lower():
        display_name = f"📊 {display_name}"

    logger.info("%s%s%s%s %s", prefix, connector, display_name, timing, status)

    # Get child runs
    try:
        children = list(
            client.list_runs(
                parent_run_id=run.id,
                limit=50,
            )
        )
        # Sort by start time to show in execution order
        children.sort(key=lambda r: r.start_time or datetime.min)

        for i, child in enumerate(children):
            child_is_last = i == len(children) - 1
            _print_run_node(
                child,
                client,
                verbose=verbose,
                indent=indent + 1,
                is_last=child_is_last,
                prefix=new_prefix,
            )
    except Exception as e:
        logger.debug("Could not fetch child runs for %s: %s", run.id, e)


def log_execution(
    step_name: str,
    inputs: dict | None = None,
    outputs: dict | None = None,
    log_dir: str | Path | None = None,
) -> None:
    """Log execution details to a file.

    Args:
        step_name: Name of the pipeline step
        inputs: Input data for the step
        outputs: Output data from the step
        log_dir: Directory for log files (default: outputs/logs)
    """
    import json

    if log_dir is None:
        log_dir = PROJECT_ROOT / "outputs" / "logs"
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    log_file = log_path / f"{datetime.now().strftime('%Y%m%d')}_execution.jsonl"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "step": step_name,
        "inputs": inputs or {},
        "outputs": outputs or {},
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def get_run_url(run_id: str | None = None) -> str | None:
    """Get the LangSmith URL for a run.

    Args:
        run_id: Run ID (uses latest if not provided)

    Returns:
        URL string or None
    """
    if not run_id:
        run_id = get_latest_run_id()

    if not run_id:
        return None

    endpoint = os.environ.get("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    project = get_project_name()

    # Convert API endpoint to web URL
    web_url = endpoint.replace("api.", "").replace("/api", "")
    if "smith.langchain" in web_url:
        return f"{web_url}/o/default/projects/p/{project}/runs/{run_id}"

    return f"{web_url}/projects/{project}/runs/{run_id}"
