"""Tests for API models - TDD: Red phase."""

from datetime import datetime

import pytest


class TestCalendarModel:
    """Test Calendar Pydantic model."""

    def test_calendar_creation(self):
        """Should create a calendar with required fields."""
        from examples.booking.api.models import Calendar

        calendar = Calendar(
            id="cal_1",
            name="Dr. Smith",
            type="provider",
        )

        assert calendar.id == "cal_1"
        assert calendar.name == "Dr. Smith"
        assert calendar.type == "provider"
        assert calendar.created_at is not None

    def test_calendar_type_validation(self):
        """Should only allow 'provider' or 'service' types."""
        from pydantic import ValidationError

        from examples.booking.api.models import Calendar

        with pytest.raises(ValidationError):
            Calendar(id="cal_1", name="Test", type="invalid")

    def test_calendar_service_type(self):
        """Should accept 'service' type."""
        from examples.booking.api.models import Calendar

        calendar = Calendar(id="cal_2", name="Massage Therapy", type="service")

        assert calendar.type == "service"


class TestSlotModel:
    """Test Slot Pydantic model."""

    def test_slot_creation(self):
        """Should create a slot with required fields."""
        from examples.booking.api.models import Slot

        slot = Slot(
            id="slot_1",
            calendar_id="cal_1",
            start=datetime(2026, 1, 24, 9, 0),
            end=datetime(2026, 1, 24, 10, 0),
        )

        assert slot.id == "slot_1"
        assert slot.calendar_id == "cal_1"
        assert slot.available is True  # Default

    def test_slot_available_default(self):
        """Should default to available=True."""
        from examples.booking.api.models import Slot

        slot = Slot(
            id="slot_2",
            calendar_id="cal_1",
            start=datetime(2026, 1, 24, 11, 0),
            end=datetime(2026, 1, 24, 12, 0),
        )

        assert slot.available is True

    def test_slot_booked(self):
        """Should allow setting available=False."""
        from examples.booking.api.models import Slot

        slot = Slot(
            id="slot_3",
            calendar_id="cal_1",
            start=datetime(2026, 1, 24, 13, 0),
            end=datetime(2026, 1, 24, 14, 0),
            available=False,
        )

        assert slot.available is False


class TestAppointmentModel:
    """Test Appointment Pydantic model."""

    def test_appointment_creation(self):
        """Should create an appointment with required fields."""
        from examples.booking.api.models import Appointment

        appt = Appointment(
            id="appt_1",
            slot_id="slot_1",
            patient_name="Alice",
            patient_phone="+358401234567",
        )

        assert appt.id == "appt_1"
        assert appt.slot_id == "slot_1"
        assert appt.patient_name == "Alice"
        assert appt.status == "booked"  # Default
        assert appt.created_at is not None

    def test_appointment_phone_optional(self):
        """Should allow None phone."""
        from examples.booking.api.models import Appointment

        appt = Appointment(
            id="appt_2",
            slot_id="slot_2",
            patient_name="Bob",
        )

        assert appt.patient_phone is None

    def test_appointment_status_cancelled(self):
        """Should allow 'cancelled' status."""
        from examples.booking.api.models import Appointment

        appt = Appointment(
            id="appt_3",
            slot_id="slot_3",
            patient_name="Charlie",
            status="cancelled",
        )

        assert appt.status == "cancelled"

    def test_appointment_invalid_status(self):
        """Should reject invalid status."""
        from pydantic import ValidationError

        from examples.booking.api.models import Appointment

        with pytest.raises(ValidationError):
            Appointment(
                id="appt_4",
                slot_id="slot_4",
                patient_name="Dave",
                status="pending",  # Invalid
            )


class TestCreateModels:
    """Test Create* request models."""

    def test_create_calendar(self):
        """Should create calendar without id (auto-generated)."""
        from examples.booking.api.models import CreateCalendar

        req = CreateCalendar(name="Dr. Jones", type="provider")

        assert req.name == "Dr. Jones"
        assert req.type == "provider"

    def test_create_slot(self):
        """Should create slot with duration."""
        from examples.booking.api.models import CreateSlot

        req = CreateSlot(
            start=datetime(2026, 1, 24, 9, 0),
            duration_min=60,
        )

        assert req.start == datetime(2026, 1, 24, 9, 0)
        assert req.duration_min == 60

    def test_create_appointment(self):
        """Should create appointment request."""
        from examples.booking.api.models import CreateAppointment

        req = CreateAppointment(
            slot_id="slot_1",
            patient_name="Eve",
            patient_phone="+358409876543",
        )

        assert req.slot_id == "slot_1"
        assert req.patient_name == "Eve"
