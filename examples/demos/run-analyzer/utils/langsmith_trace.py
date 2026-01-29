"""LangSmith Trace Printing Utilities.

Extracted from langsmith.py to keep modules under 400 lines.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def print_run_node(
    run: Any,
    client: Any,
    verbose: bool = False,
    indent: int = 0,
    is_last: bool = True,
    prefix: str = "",
) -> None:
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
            print_run_node(
                child,
                client,
                verbose=verbose,
                indent=indent + 1,
                is_last=child_is_last,
                prefix=new_prefix,
            )
    except Exception as e:
        logger.debug("Could not fetch child runs for %s: %s", run.id, e)


__all__ = ["print_run_node"]
