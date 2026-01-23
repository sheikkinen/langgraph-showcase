"""Tests for Calendar routes - TDD: Red phase."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with in-memory database."""
    from examples.booking.api.app import create_app
    from examples.booking.api.db import BookingDB

    # Use in-memory database for tests
    db = BookingDB(":memory:")
    db.init_schema()

    app = create_app(db=db)
    yield TestClient(app)
    db.close()


class TestCalendarRoutes:
    """Test /calendars endpoints."""

    def test_create_calendar(self, client):
        """POST /calendars should create calendar."""
        response = client.post(
            "/calendars",
            json={"name": "Dr. Smith", "type": "provider"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Dr. Smith"
        assert data["type"] == "provider"
        assert data["id"].startswith("cal_")

    def test_create_calendar_invalid_type(self, client):
        """POST /calendars with invalid type should fail."""
        response = client.post(
            "/calendars",
            json={"name": "Test", "type": "invalid"},
        )

        assert response.status_code == 422

    def test_list_calendars_empty(self, client):
        """GET /calendars should return empty list initially."""
        response = client.get("/calendars")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_calendars(self, client):
        """GET /calendars should return all calendars."""
        client.post("/calendars", json={"name": "Dr. Smith", "type": "provider"})
        client.post("/calendars", json={"name": "Massage", "type": "service"})

        response = client.get("/calendars")

        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_get_calendar(self, client):
        """GET /calendars/{id} should return calendar."""
        create_resp = client.post(
            "/calendars", json={"name": "Dr. Jones", "type": "provider"}
        )
        calendar_id = create_resp.json()["id"]

        response = client.get(f"/calendars/{calendar_id}")

        assert response.status_code == 200
        assert response.json()["name"] == "Dr. Jones"

    def test_get_calendar_not_found(self, client):
        """GET /calendars/{id} should return 404 for non-existent."""
        response = client.get("/calendars/nonexistent")

        assert response.status_code == 404

    def test_delete_calendar(self, client):
        """DELETE /calendars/{id} should delete calendar."""
        create_resp = client.post(
            "/calendars", json={"name": "Test", "type": "provider"}
        )
        calendar_id = create_resp.json()["id"]

        response = client.delete(f"/calendars/{calendar_id}")

        assert response.status_code == 204

        # Verify deleted
        get_resp = client.get(f"/calendars/{calendar_id}")
        assert get_resp.status_code == 404

    def test_delete_calendar_not_found(self, client):
        """DELETE /calendars/{id} should return 404 for non-existent."""
        response = client.delete("/calendars/nonexistent")

        assert response.status_code == 404
