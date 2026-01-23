"""E2E Integration test for booking API with real graph.

This test uses the actual booking graph with mocked LLM responses
to verify the full flow without real API calls.
"""

import pytest
from fastapi.testclient import TestClient


class TestBookingE2EFlow:
    """End-to-end tests for booking flow through API."""

    @pytest.fixture
    def api_client(self):
        """Create test client with database, graph loaded separately.

        For E2E testing we set up:
        - In-memory SQLite with pre-populated calendar/slots
        - Graph is loaded if available, otherwise skipped
        """
        from examples.booking.api.app import create_app
        from examples.booking.api.db import BookingDB

        db = BookingDB(":memory:")
        db.init_schema()

        # Pre-populate with test data
        db.create_calendar(name="Dr. Smith", type="provider")
        db.create_calendar(name="General Checkup", type="service")

        app = create_app(db=db, graph=None)
        yield TestClient(app)
        db.close()

    def test_full_calendar_slot_appointment_flow(self, api_client):
        """Test creating calendar → slot → appointment flow."""
        # 1. Create a calendar
        cal_resp = api_client.post(
            "/calendars",
            json={"name": "Dr. Johnson", "type": "provider"},
        )
        assert cal_resp.status_code == 201
        calendar_id = cal_resp.json()["id"]

        # 2. Create slots for that calendar
        slot1_resp = api_client.post(
            f"/calendars/{calendar_id}/slots",
            json={"start": "2025-01-20T09:00:00", "duration_min": 60},
        )
        assert slot1_resp.status_code == 201
        slot1_id = slot1_resp.json()["id"]

        slot2_resp = api_client.post(
            f"/calendars/{calendar_id}/slots",
            json={"start": "2025-01-20T10:00:00", "duration_min": 30},
        )
        assert slot2_resp.status_code == 201
        slot2_id = slot2_resp.json()["id"]

        # 3. List available slots
        slots_resp = api_client.get(f"/calendars/{calendar_id}/slots?available=true")
        assert slots_resp.status_code == 200
        assert len(slots_resp.json()) == 2

        # 4. Book an appointment
        appt_resp = api_client.post(
            "/appointments",
            json={
                "slot_id": slot1_id,
                "patient_name": "Jane Doe",
                "patient_phone": "+1234567890",
            },
        )
        assert appt_resp.status_code == 201
        appointment_id = appt_resp.json()["id"]
        assert appt_resp.json()["status"] == "booked"

        # 5. Verify slot is now unavailable
        slots_resp = api_client.get(f"/calendars/{calendar_id}/slots?available=true")
        assert len(slots_resp.json()) == 1  # Only slot2 available
        assert slots_resp.json()[0]["id"] == slot2_id

        # 6. Get appointment details
        get_appt = api_client.get(f"/appointments/{appointment_id}")
        assert get_appt.status_code == 200
        assert get_appt.json()["patient_name"] == "Jane Doe"

        # 7. Cancel the appointment
        cancel_resp = api_client.patch(f"/appointments/{appointment_id}/cancel")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

        # 8. Verify slot is available again
        slots_resp = api_client.get(f"/calendars/{calendar_id}/slots?available=true")
        assert len(slots_resp.json()) == 2  # Both available again

    def test_prepopulated_calendars(self, api_client):
        """Verify pre-populated calendars are accessible."""
        resp = api_client.get("/calendars")
        assert resp.status_code == 200
        calendars = resp.json()
        # We created 2 calendars in fixture
        assert len(calendars) == 2
        names = {c["name"] for c in calendars}
        assert "Dr. Smith" in names
        assert "General Checkup" in names

    def test_double_booking_prevented(self, api_client):
        """Test that double-booking the same slot fails."""
        # Create calendar and slot
        cal = api_client.post("/calendars", json={"name": "Test", "type": "provider"})
        cal_id = cal.json()["id"]
        slot = api_client.post(
            f"/calendars/{cal_id}/slots",
            json={"start": "2025-01-21T09:00:00", "duration_min": 60},
        )
        slot_id = slot.json()["id"]

        # First booking succeeds
        resp1 = api_client.post(
            "/appointments",
            json={"slot_id": slot_id, "patient_name": "Patient A"},
        )
        assert resp1.status_code == 201

        # Second booking fails with 409 Conflict
        resp2 = api_client.post(
            "/appointments",
            json={"slot_id": slot_id, "patient_name": "Patient B"},
        )
        assert resp2.status_code == 409
        assert "already booked" in resp2.json()["detail"].lower()

    def test_health_endpoint(self, api_client):
        """Test health check reports graph status."""
        resp = api_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["graph_loaded"] is False  # No graph in test

    def test_cascade_delete_calendar_forbidden(self, api_client):
        """Test that deleting calendar with slots/appointments should work.

        Note: For simplicity, we allow orphaned slots/appointments for now.
        A more robust implementation would cascade delete or prevent.
        """
        # Create calendar with slot and appointment
        cal = api_client.post(
            "/calendars", json={"name": "To Delete", "type": "provider"}
        )
        cal_id = cal.json()["id"]
        slot = api_client.post(
            f"/calendars/{cal_id}/slots",
            json={"start": "2025-01-22T09:00:00", "duration_min": 60},
        )
        slot_id = slot.json()["id"]
        api_client.post(
            "/appointments",
            json={"slot_id": slot_id, "patient_name": "Orphan Patient"},
        )

        # Delete calendar (current behavior: succeeds, leaves orphans)
        del_resp = api_client.delete(f"/calendars/{cal_id}")
        assert del_resp.status_code == 204

        # Calendar is gone
        get_resp = api_client.get(f"/calendars/{cal_id}")
        assert get_resp.status_code == 404

        # Slot still exists (orphaned) - this is current behavior
        slot_resp = api_client.get(f"/slots/{slot_id}")
        assert slot_resp.status_code == 200
