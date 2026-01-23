"""Tests for Appointment API routes."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with in-memory database."""
    from examples.booking.api.app import create_app
    from examples.booking.api.db import BookingDB

    db = BookingDB(":memory:")
    db.init_schema()
    app = create_app(db=db)
    yield TestClient(app)
    db.close()


@pytest.fixture
def client_with_slot(client):
    """Create client with a calendar and slot already created."""
    cal_resp = client.post("/calendars", json={"name": "Dr. Smith", "type": "provider"})
    calendar_id = cal_resp.json()["id"]
    slot_resp = client.post(
        f"/calendars/{calendar_id}/slots",
        json={"start": "2025-01-15T10:00:00", "duration_min": 60},
    )
    slot_id = slot_resp.json()["id"]
    return client, calendar_id, slot_id


class TestAppointmentRoutes:
    """Tests for /appointments endpoints."""

    def test_create_appointment(self, client_with_slot):
        """POST /appointments should create appointment and mark slot unavailable."""
        client, _, slot_id = client_with_slot
        response = client.post(
            "/appointments",
            json={"slot_id": slot_id, "patient_name": "John Doe"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["slot_id"] == slot_id
        assert data["patient_name"] == "John Doe"
        assert data["status"] == "booked"
        assert "id" in data

        # Slot should now be unavailable
        slot_resp = client.get(f"/slots/{slot_id}")
        assert slot_resp.json()["available"] is False

    def test_create_appointment_slot_not_found(self, client):
        """POST /appointments should 404 for missing slot."""
        response = client.post(
            "/appointments",
            json={"slot_id": "nonexistent", "patient_name": "John Doe"},
        )
        assert response.status_code == 404

    def test_create_appointment_slot_unavailable(self, client_with_slot):
        """POST /appointments should 409 for already-booked slot."""
        client, _, slot_id = client_with_slot
        # First booking succeeds
        client.post(
            "/appointments",
            json={"slot_id": slot_id, "patient_name": "John Doe"},
        )
        # Second booking fails
        response = client.post(
            "/appointments",
            json={"slot_id": slot_id, "patient_name": "Jane Doe"},
        )
        assert response.status_code == 409

    def test_list_appointments_empty(self, client):
        """GET /appointments should return empty list."""
        response = client.get("/appointments")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_appointments(self, client_with_slot):
        """GET /appointments should return all appointments."""
        client, _, slot_id = client_with_slot
        client.post(
            "/appointments",
            json={"slot_id": slot_id, "patient_name": "John Doe"},
        )
        response = client.get("/appointments")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_get_appointment(self, client_with_slot):
        """GET /appointments/{id} should return appointment."""
        client, _, slot_id = client_with_slot
        create_resp = client.post(
            "/appointments",
            json={"slot_id": slot_id, "patient_name": "John Doe"},
        )
        appt_id = create_resp.json()["id"]

        response = client.get(f"/appointments/{appt_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == appt_id

    def test_get_appointment_not_found(self, client):
        """GET /appointments/{id} should 404 for missing appointment."""
        response = client.get("/appointments/nonexistent")
        assert response.status_code == 404

    def test_cancel_appointment(self, client_with_slot):
        """PATCH /appointments/{id}/cancel should cancel and release slot."""
        client, _, slot_id = client_with_slot
        create_resp = client.post(
            "/appointments",
            json={"slot_id": slot_id, "patient_name": "John Doe"},
        )
        appt_id = create_resp.json()["id"]

        response = client.patch(f"/appointments/{appt_id}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

        # Slot should be available again
        slot_resp = client.get(f"/slots/{slot_id}")
        assert slot_resp.json()["available"] is True

    def test_cancel_appointment_not_found(self, client):
        """PATCH /appointments/{id}/cancel should 404 for missing appointment."""
        response = client.patch("/appointments/nonexistent/cancel")
        assert response.status_code == 404

    def test_delete_appointment(self, client_with_slot):
        """DELETE /appointments/{id} should delete appointment."""
        client, _, slot_id = client_with_slot
        create_resp = client.post(
            "/appointments",
            json={"slot_id": slot_id, "patient_name": "John Doe"},
        )
        appt_id = create_resp.json()["id"]

        response = client.delete(f"/appointments/{appt_id}")
        assert response.status_code == 204

        # Verify gone
        get_resp = client.get(f"/appointments/{appt_id}")
        assert get_resp.status_code == 404

    def test_delete_appointment_not_found(self, client):
        """DELETE /appointments/{id} should 404 for missing appointment."""
        response = client.delete("/appointments/nonexistent")
        assert response.status_code == 404
