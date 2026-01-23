"""Tests for SQLite database layer - TDD: Red phase."""

from datetime import datetime

import pytest


@pytest.fixture
def db():
    """Create in-memory database for testing."""
    from examples.booking.api.db import BookingDB

    database = BookingDB(":memory:")
    database.init_schema()
    yield database
    database.close()


class TestCalendarDB:
    """Test Calendar CRUD operations."""

    def test_create_calendar(self, db):
        """Should create and return calendar with generated ID."""
        cal = db.create_calendar(name="Dr. Smith", type="provider")

        assert cal.id.startswith("cal_")
        assert cal.name == "Dr. Smith"
        assert cal.type == "provider"

    def test_get_calendar(self, db):
        """Should retrieve calendar by ID."""
        created = db.create_calendar(name="Dr. Jones", type="provider")

        retrieved = db.get_calendar(created.id)

        assert retrieved is not None
        assert retrieved.name == "Dr. Jones"

    def test_get_calendar_not_found(self, db):
        """Should return None for non-existent calendar."""
        result = db.get_calendar("nonexistent")

        assert result is None

    def test_list_calendars(self, db):
        """Should list all calendars."""
        db.create_calendar(name="Dr. Smith", type="provider")
        db.create_calendar(name="Massage", type="service")

        calendars = db.list_calendars()

        assert len(calendars) == 2

    def test_delete_calendar(self, db):
        """Should delete calendar."""
        cal = db.create_calendar(name="Test", type="provider")

        deleted = db.delete_calendar(cal.id)

        assert deleted is True
        assert db.get_calendar(cal.id) is None

    def test_delete_calendar_not_found(self, db):
        """Should return False for non-existent calendar."""
        deleted = db.delete_calendar("nonexistent")

        assert deleted is False


class TestSlotDB:
    """Test Slot CRUD operations."""

    def test_create_slot(self, db):
        """Should create slot with generated ID."""
        cal = db.create_calendar(name="Dr. Smith", type="provider")

        slot = db.create_slot(
            calendar_id=cal.id,
            start=datetime(2026, 1, 24, 9, 0),
            end=datetime(2026, 1, 24, 10, 0),
        )

        assert slot.id.startswith("slot_")
        assert slot.calendar_id == cal.id
        assert slot.available is True

    def test_get_slot(self, db):
        """Should retrieve slot by ID."""
        cal = db.create_calendar(name="Test", type="provider")
        created = db.create_slot(
            calendar_id=cal.id,
            start=datetime(2026, 1, 24, 9, 0),
            end=datetime(2026, 1, 24, 10, 0),
        )

        retrieved = db.get_slot(created.id)

        assert retrieved is not None
        assert retrieved.calendar_id == cal.id

    def test_list_slots_by_calendar(self, db):
        """Should list slots for a calendar."""
        cal = db.create_calendar(name="Test", type="provider")
        db.create_slot(
            cal.id, datetime(2026, 1, 24, 9, 0), datetime(2026, 1, 24, 10, 0)
        )
        db.create_slot(
            cal.id, datetime(2026, 1, 24, 11, 0), datetime(2026, 1, 24, 12, 0)
        )

        slots = db.list_slots(calendar_id=cal.id)

        assert len(slots) == 2

    def test_list_slots_available_only(self, db):
        """Should filter available slots."""
        cal = db.create_calendar(name="Test", type="provider")
        slot1 = db.create_slot(
            cal.id, datetime(2026, 1, 24, 9, 0), datetime(2026, 1, 24, 10, 0)
        )
        db.create_slot(
            cal.id, datetime(2026, 1, 24, 11, 0), datetime(2026, 1, 24, 12, 0)
        )
        db.mark_slot_unavailable(slot1.id)

        available = db.list_slots(calendar_id=cal.id, available_only=True)

        assert len(available) == 1

    def test_delete_slot(self, db):
        """Should delete slot."""
        cal = db.create_calendar(name="Test", type="provider")
        slot = db.create_slot(
            cal.id, datetime(2026, 1, 24, 9, 0), datetime(2026, 1, 24, 10, 0)
        )

        deleted = db.delete_slot(slot.id)

        assert deleted is True
        assert db.get_slot(slot.id) is None


class TestAppointmentDB:
    """Test Appointment CRUD operations."""

    def test_create_appointment(self, db):
        """Should create appointment and mark slot unavailable."""
        cal = db.create_calendar(name="Dr. Smith", type="provider")
        slot = db.create_slot(
            cal.id, datetime(2026, 1, 24, 9, 0), datetime(2026, 1, 24, 10, 0)
        )

        appt = db.create_appointment(
            slot_id=slot.id,
            patient_name="Alice",
            patient_phone="+358401234567",
        )

        assert appt.id.startswith("appt_")
        assert appt.patient_name == "Alice"
        assert appt.status == "booked"

        # Slot should be marked unavailable
        updated_slot = db.get_slot(slot.id)
        assert updated_slot.available is False

    def test_get_appointment(self, db):
        """Should retrieve appointment by ID."""
        cal = db.create_calendar(name="Test", type="provider")
        slot = db.create_slot(
            cal.id, datetime(2026, 1, 24, 9, 0), datetime(2026, 1, 24, 10, 0)
        )
        created = db.create_appointment(slot.id, "Bob", None)

        retrieved = db.get_appointment(created.id)

        assert retrieved is not None
        assert retrieved.patient_name == "Bob"

    def test_list_appointments(self, db):
        """Should list appointments."""
        cal = db.create_calendar(name="Test", type="provider")
        slot1 = db.create_slot(
            cal.id, datetime(2026, 1, 24, 9, 0), datetime(2026, 1, 24, 10, 0)
        )
        slot2 = db.create_slot(
            cal.id, datetime(2026, 1, 24, 11, 0), datetime(2026, 1, 24, 12, 0)
        )
        db.create_appointment(slot1.id, "Alice", None)
        db.create_appointment(slot2.id, "Bob", None)

        appointments = db.list_appointments()

        assert len(appointments) == 2

    def test_cancel_appointment(self, db):
        """Should cancel appointment and free slot."""
        cal = db.create_calendar(name="Test", type="provider")
        slot = db.create_slot(
            cal.id, datetime(2026, 1, 24, 9, 0), datetime(2026, 1, 24, 10, 0)
        )
        appt = db.create_appointment(slot.id, "Alice", None)

        cancelled = db.cancel_appointment(appt.id)

        assert cancelled is True
        updated = db.get_appointment(appt.id)
        assert updated.status == "cancelled"

        # Slot should be available again
        updated_slot = db.get_slot(slot.id)
        assert updated_slot.available is True

    def test_delete_appointment(self, db):
        """Should delete appointment and free slot."""
        cal = db.create_calendar(name="Test", type="provider")
        slot = db.create_slot(
            cal.id, datetime(2026, 1, 24, 9, 0), datetime(2026, 1, 24, 10, 0)
        )
        appt = db.create_appointment(slot.id, "Alice", None)

        deleted = db.delete_appointment(appt.id)

        assert deleted is True
        assert db.get_appointment(appt.id) is None

        # Slot should be available again
        updated_slot = db.get_slot(slot.id)
        assert updated_slot.available is True
