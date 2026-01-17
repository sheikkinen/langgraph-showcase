"""SQLite Storage - Simple persistence for pipeline state.

Provides a lightweight wrapper around SQLite for storing
and retrieving pipeline execution state.

Supports optional connection pooling for high-throughput scenarios.
"""

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from typing import Iterator

from pydantic import BaseModel

from yamlgraph.config import DATABASE_PATH


class ConnectionPool:
    """Thread-safe SQLite connection pool.

    Maintains a pool of reusable connections for high-throughput scenarios.
    Connections are returned to the pool after use instead of being closed.
    """

    def __init__(self, db_path: Path, pool_size: int = 5):
        """Initialize connection pool.

        Args:
            db_path: Path to SQLite database
            pool_size: Maximum number of connections to maintain
        """
        self._db_path = db_path
        self._pool_size = pool_size
        self._pool: Queue[sqlite3.Connection] = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._total_connections = 0

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection."""
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get a connection from the pool.

        Creates a new connection if pool is empty and under limit.

        Yields:
            Database connection (returned to pool on exit)
        """
        conn = None
        try:
            # Try to get from pool
            try:
                conn = self._pool.get_nowait()
            except Empty:
                # Pool empty - create new connection if under limit
                with self._lock:
                    if self._total_connections < self._pool_size:
                        conn = self._create_connection()
                        self._total_connections += 1
                    else:
                        # At limit - block waiting for connection
                        pass

                if conn is None:
                    conn = self._pool.get()  # Blocking wait

            yield conn

        finally:
            # Return connection to pool
            if conn is not None:
                try:
                    self._pool.put_nowait(conn)
                except Exception:
                    # Pool full, close connection
                    conn.close()
                    with self._lock:
                        self._total_connections -= 1

    def close_all(self) -> None:
        """Close all connections in the pool."""
        while True:
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break
        with self._lock:
            self._total_connections = 0


class YamlGraphDB:
    """SQLite wrapper for yamlgraph state persistence.

    Supports two connection modes:
    - Default: Creates new connection per operation (simple, safe)
    - Pooled: Reuses connections from pool (high-throughput)

    Example:
        # Default mode (simple)
        db = YamlGraphDB()

        # Pooled mode (high-throughput)
        db = YamlGraphDB(use_pool=True, pool_size=10)
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        use_pool: bool = False,
        pool_size: int = 5,
    ):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file (default: outputs/yamlgraph.db)
            use_pool: Enable connection pooling for high-throughput scenarios
            pool_size: Maximum connections in pool (only used if use_pool=True)
        """
        if db_path is None:
            db_path = DATABASE_PATH
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._use_pool = use_pool
        self._pool: ConnectionPool | None = None
        if use_pool:
            self._pool = ConnectionPool(self.db_path, pool_size)

        self._init_db()

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get a database connection.

        Uses pool if enabled, otherwise creates new connection.

        Yields:
            Database connection
        """
        if self._pool is not None:
            with self._pool.get_connection() as conn:
                yield conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def close(self) -> None:
        """Close database connections.

        For pooled mode, closes all connections in pool.
        """
        if self._pool is not None:
            self._pool.close_all()

    def _init_db(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'running',
                    state_json TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_thread_id
                ON pipeline_runs(thread_id)
            """)
            conn.commit()

    def save_state(self, thread_id: str, state: dict, status: str = "running") -> int:
        """Save pipeline state.

        Args:
            thread_id: Unique identifier for this run
            state: State dictionary to persist
            status: Current status (running, completed, failed)

        Returns:
            Row ID of the saved state
        """
        now = datetime.now().isoformat()
        state_json = json.dumps(self._serialize_state(state), default=str)

        with self._get_connection() as conn:
            # Check if thread exists
            existing = conn.execute(
                "SELECT id FROM pipeline_runs WHERE thread_id = ?", (thread_id,)
            ).fetchone()

            if existing:
                conn.execute(
                    """UPDATE pipeline_runs
                       SET updated_at = ?, status = ?, state_json = ?
                       WHERE thread_id = ?""",
                    (now, status, state_json, thread_id),
                )
                conn.commit()
                return existing["id"]
            else:
                cursor = conn.execute(
                    """INSERT INTO pipeline_runs
                       (thread_id, created_at, updated_at, status, state_json)
                       VALUES (?, ?, ?, ?, ?)""",
                    (thread_id, now, now, status, state_json),
                )
                conn.commit()
                return cursor.lastrowid

    def load_state(self, thread_id: str) -> dict | None:
        """Load pipeline state by thread ID.

        Args:
            thread_id: Unique identifier for the run

        Returns:
            State dictionary or None if not found
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT state_json FROM pipeline_runs WHERE thread_id = ?", (thread_id,)
            ).fetchone()

            if row:
                return json.loads(row["state_json"])
            return None

    def get_run_info(self, thread_id: str) -> dict | None:
        """Get run metadata without full state.

        Args:
            thread_id: Unique identifier for the run

        Returns:
            Dictionary with id, thread_id, created_at, updated_at, status
        """
        with self._get_connection() as conn:
            row = conn.execute(
                """SELECT id, thread_id, created_at, updated_at, status
                   FROM pipeline_runs WHERE thread_id = ?""",
                (thread_id,),
            ).fetchone()

            if row:
                return dict(row)
            return None

    def list_runs(self, limit: int = 10) -> list[dict]:
        """List recent pipeline runs.

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of run metadata dictionaries
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT id, thread_id, created_at, updated_at, status
                   FROM pipeline_runs
                   ORDER BY updated_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()

            return [dict(row) for row in rows]

    def delete_run(self, thread_id: str) -> bool:
        """Delete a pipeline run.

        Args:
            thread_id: Unique identifier for the run

        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM pipeline_runs WHERE thread_id = ?", (thread_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def _serialize_state(self, state: dict) -> dict:
        """Convert state to JSON-serializable format.

        Handles Pydantic models and other complex types.

        Args:
            state: State dictionary

        Returns:
            JSON-serializable dictionary
        """
        result = {}
        for key, value in state.items():
            if isinstance(value, BaseModel):
                result[key] = value.model_dump()
            elif hasattr(value, "__dict__"):
                result[key] = vars(value)
            else:
                result[key] = value
        return result
