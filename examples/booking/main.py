"""Booking API entry point.

Run with:
    uvicorn examples.booking.main:app --reload

Or:
    python -m examples.booking.main
"""

import logging
import os
from contextlib import asynccontextmanager

from examples.booking.api.app import create_app
from examples.booking.api.db import BookingDB

logger = logging.getLogger(__name__)

# Database path (use env var for Fly.io volume mount)
DB_PATH = os.getenv("BOOKING_DB_PATH", "booking.db")

# Graph path
GRAPH_PATH = os.getenv("BOOKING_GRAPH_PATH", "examples/booking/graph.yaml")

# Global resources
_db: BookingDB | None = None
_graph = None


@asynccontextmanager
async def lifespan(app):
    """Initialize database and graph at startup, cleanup on shutdown."""
    global _db, _graph

    # Initialize database
    _db = BookingDB(DB_PATH)
    _db.init_schema()
    logger.info(f"✅ Database initialized: {DB_PATH}")

    # Set global DB for tool handlers
    from examples.booking.nodes.slots_handler import set_global_db

    set_global_db(_db)

    # Try to load graph (optional - works without for REST-only mode)
    try:
        from yamlgraph.executor_async import load_and_compile_async

        _graph = await load_and_compile_async(GRAPH_PATH)
        logger.info(f"✅ Graph loaded: {GRAPH_PATH}")
    except FileNotFoundError:
        logger.warning(f"⚠️ Graph not found: {GRAPH_PATH} (REST-only mode)")
        _graph = None
    except Exception as e:
        logger.warning(f"⚠️ Graph load failed: {e} (REST-only mode)")
        _graph = None

    # Update app state
    app.state.db = _db
    app.state.graph = _graph

    yield

    # Cleanup
    if _db:
        _db.close()
        logger.info("✅ Database closed")


# Create app with lifespan
app = create_app()
app.router.lifespan_context = lifespan


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "examples.booking.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
