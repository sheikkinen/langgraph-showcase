"""LangGraph native checkpointer integration.

Provides SQLite-based checkpointing for graph state persistence,
enabling time travel, replay, and resume from any checkpoint.
"""

import sqlite3
from pathlib import Path
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph

from showcase.config import DATABASE_PATH


def get_checkpointer(db_path: str | Path | None = None) -> SqliteSaver:
    """Get a SQLite checkpointer for graph compilation.

    The checkpointer enables:
    - Automatic state persistence after each node
    - Time travel via get_state_history()
    - Resume from any checkpoint
    - Fault tolerance with pending writes

    Args:
        db_path: Path to SQLite database file.
                 Defaults to outputs/showcase.db

    Returns:
        SqliteSaver instance for use with graph.compile()

    Example:
        >>> checkpointer = get_checkpointer()
        >>> graph = workflow.compile(checkpointer=checkpointer)
        >>> result = graph.invoke(input, {"configurable": {"thread_id": "abc"}})
    """
    if db_path is None:
        db_path = DATABASE_PATH

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path), check_same_thread=False)
    return SqliteSaver(conn)


def get_state_history(
    graph: CompiledStateGraph,
    thread_id: str,
) -> list[Any]:
    """Get checkpoint history for a thread.

    Returns checkpoints in reverse chronological order (most recent first).

    Args:
        graph: Compiled graph with checkpointer
        thread_id: Thread identifier to query

    Returns:
        List of StateSnapshot objects, or empty list if thread doesn't exist

    Example:
        >>> history = get_state_history(graph, "my-thread")
        >>> for snapshot in history:
        ...     print(f"Step {snapshot.metadata.get('step')}: {snapshot.values}")
    """
    config = {"configurable": {"thread_id": thread_id}}
    try:
        return list(graph.get_state_history(config))
    except Exception:
        return []
