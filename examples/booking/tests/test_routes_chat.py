"""Tests for Chat API routes (booking conversation).

These tests use a mock graph runner since the actual LangGraph
would require LLM calls. We test the HTTP layer here.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mock graph."""
    from examples.booking.api.app import create_app
    from examples.booking.api.db import BookingDB

    db = BookingDB(":memory:")
    db.init_schema()
    app = create_app(db=db, graph=None)  # No graph = mock mode
    yield TestClient(app)
    db.close()


class TestChatRoutes:
    """Tests for /chat endpoints."""

    def test_start_chat_no_graph(self, client):
        """POST /chat/{thread_id} should 503 when graph not loaded."""
        response = client.post(
            "/chat/session123",
            json={"message": "I need to book an appointment"},
        )
        assert response.status_code == 503

    def test_resume_chat_no_graph(self, client):
        """POST /chat/{thread_id}/resume should 503 when graph not loaded."""
        response = client.post(
            "/chat/session123/resume",
            json={"answer": "Dr. Smith"},
        )
        assert response.status_code == 503


class TestChatRoutesWithMockGraph:
    """Tests with a simple mock graph that simulates interrupt behavior."""

    @pytest.fixture
    def mock_client(self):
        """Create test client with mock graph that returns interrupt."""
        from unittest.mock import MagicMock

        from examples.booking.api.app import create_app
        from examples.booking.api.db import BookingDB

        db = BookingDB(":memory:")
        db.init_schema()

        # Create mock graph
        mock_graph = MagicMock()
        # The app will use run_graph_async, we mock at app level
        app = create_app(db=db, graph=mock_graph)

        # Store mock for test manipulation
        app.state.mock_graph = mock_graph

        yield TestClient(app)
        db.close()

    def test_health_check(self, mock_client):
        """GET /health should return graph status."""
        response = mock_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "graph_loaded" in data
