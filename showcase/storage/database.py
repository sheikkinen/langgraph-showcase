"""SQLite Storage - Simple persistence for pipeline state.

Provides a lightweight wrapper around SQLite for storing
and retrieving pipeline execution state.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from showcase.config import DATABASE_PATH


class ShowcaseDB:
    """SQLite wrapper for showcase state persistence."""
    
    def __init__(self, db_path: str | Path | None = None):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file (default: outputs/showcase.db)
        """
        if db_path is None:
            db_path = DATABASE_PATH
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
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
                "SELECT id FROM pipeline_runs WHERE thread_id = ?",
                (thread_id,)
            ).fetchone()
            
            if existing:
                conn.execute(
                    """UPDATE pipeline_runs 
                       SET updated_at = ?, status = ?, state_json = ?
                       WHERE thread_id = ?""",
                    (now, status, state_json, thread_id)
                )
                return existing["id"]
            else:
                cursor = conn.execute(
                    """INSERT INTO pipeline_runs 
                       (thread_id, created_at, updated_at, status, state_json)
                       VALUES (?, ?, ?, ?, ?)""",
                    (thread_id, now, now, status, state_json)
                )
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
                "SELECT state_json FROM pipeline_runs WHERE thread_id = ?",
                (thread_id,)
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
                (thread_id,)
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
                (limit,)
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
                "DELETE FROM pipeline_runs WHERE thread_id = ?",
                (thread_id,)
            )
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
