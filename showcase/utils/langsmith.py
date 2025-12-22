"""LangSmith Utilities - Tracing and observability helpers.

Provides functions for interacting with LangSmith traces,
printing execution trees, and logging run information.
"""

import os
from datetime import datetime
from pathlib import Path

# Find showcase root (4 levels up from src/showcase/utils/langsmith.py)
SHOWCASE_ROOT = Path(__file__).parent.parent.parent


def get_client():
    """Get a LangSmith client if available.
    
    Returns:
        LangSmith Client instance or None if not configured
    """
    try:
        from langsmith import Client
        
        api_key = os.environ.get("LANGCHAIN_API_KEY") or os.environ.get("LANGSMITH_API_KEY")
        if not api_key:
            return None
            
        endpoint = os.environ.get("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
        return Client(api_url=endpoint, api_key=api_key)
    except ImportError:
        return None


def get_project_name() -> str:
    """Get the current LangSmith project name.
    
    Returns:
        Project name from environment or default
    """
    return os.environ.get("LANGCHAIN_PROJECT", "showcase-app")


def is_tracing_enabled() -> bool:
    """Check if LangSmith tracing is enabled.
    
    Returns:
        True if tracing is enabled
    """
    return os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true"


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
        print(f"Warning: Could not get latest run: {e}")
    
    return None


def print_run_tree(run_id: str | None = None, verbose: bool = False):
    """Print an execution tree for a run.
    
    Args:
        run_id: Specific run ID (uses latest if not provided)
        verbose: Include timing and status details
    """
    client = get_client()
    if not client:
        print("⚠️  LangSmith client not available")
        return
    
    if not run_id:
        run_id = get_latest_run_id()
    
    if not run_id:
        print("⚠️  No run found")
        return
    
    try:
        run = client.read_run(run_id)
        _print_run_node(run, client, verbose=verbose, indent=0)
    except Exception as e:
        print(f"⚠️  Error reading run: {e}")


def _print_run_node(run, client, verbose: bool = False, indent: int = 0):
    """Recursively print a run node and its children."""
    prefix = "  " * indent
    connector = "└─" if indent > 0 else "📊"
    
    # Status emoji
    if run.status == "success":
        status = "✅"
    elif run.status == "error":
        status = "❌"
    else:
        status = "⏳"
    
    # Timing
    timing = ""
    if verbose and run.end_time and run.start_time:
        duration = (run.end_time - run.start_time).total_seconds()
        timing = f" ({duration:.1f}s)"
    
    print(f"{prefix}{connector} {run.name}{timing} {status}")
    
    # Get child runs
    try:
        children = list(client.list_runs(
            parent_run_id=run.id,
            limit=50,
        ))
        for child in children:
            _print_run_node(child, client, verbose=verbose, indent=indent + 1)
    except Exception:
        pass


def log_execution(
    step_name: str,
    inputs: dict | None = None,
    outputs: dict | None = None,
    log_dir: str | Path | None = None,
):
    """Log execution details to a file.
    
    Args:
        step_name: Name of the pipeline step
        inputs: Input data for the step
        outputs: Output data from the step
        log_dir: Directory for log files (default: outputs/logs)
    """
    import json
    
    if log_dir is None:
        log_dir = SHOWCASE_ROOT / "outputs" / "logs"
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
