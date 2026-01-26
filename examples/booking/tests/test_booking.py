"""Unit tests for booking example."""

from datetime import datetime


class TestSlotModel:
    """Test Slot Pydantic model."""

    def test_slot_creation(self):
        """Should create a slot with required fields."""
        from examples.booking.nodes.schema import Slot

        slot = Slot(
            id="slot_1",
            start=datetime(2026, 1, 23, 9, 0),
            end=datetime(2026, 1, 23, 10, 0),
            provider="Dr. Smith",
        )

        assert slot.id == "slot_1"
        assert slot.provider == "Dr. Smith"

    def test_slot_display_format(self):
        """Should format display string correctly."""
        from examples.booking.nodes.schema import Slot

        slot = Slot(
            id="slot_1",
            start=datetime(2026, 1, 23, 9, 0),
            end=datetime(2026, 1, 23, 10, 0),
            provider="Dr. Jones",
        )

        assert "Dr. Jones" in slot.display
        assert "09:00" in slot.display


class TestBookingModel:
    """Test Booking Pydantic model."""

    def test_booking_creation(self):
        """Should create a booking with slot."""
        from examples.booking.nodes.schema import Booking, Slot

        slot = Slot(
            id="slot_1",
            start=datetime(2026, 1, 23, 9, 0),
            end=datetime(2026, 1, 23, 10, 0),
        )

        booking = Booking(
            id="book_123",
            slot=slot,
            patient_name="Alice",
            patient_phone="+358401234567",
        )

        assert booking.id == "book_123"
        assert booking.patient_name == "Alice"
        assert booking.slot.id == "slot_1"

    def test_booking_auto_created_at(self):
        """Should auto-set created_at if not provided."""
        from examples.booking.nodes.schema import Booking, Slot

        slot = Slot(
            id="slot_1",
            start=datetime(2026, 1, 23, 9, 0),
            end=datetime(2026, 1, 23, 10, 0),
        )

        booking = Booking(
            id="book_123",
            slot=slot,
            patient_name="Bob",
            patient_phone="",
        )

        assert booking.created_at is not None


class TestGetMockSlots:
    """Test mock slot generation."""

    def test_generates_four_slots(self):
        """Should generate 4 slots."""
        from examples.booking.nodes.slots_handler import get_mock_slots

        slots = get_mock_slots()

        assert len(slots) == 4

    def test_slots_have_different_providers(self):
        """Should alternate between providers."""
        from examples.booking.nodes.slots_handler import get_mock_slots

        slots = get_mock_slots()
        providers = [s.provider for s in slots]

        assert "Dr. Smith" in providers
        assert "Dr. Jones" in providers

    def test_slots_two_hours_apart(self):
        """Should space slots 2 hours apart."""
        from examples.booking.nodes.slots_handler import get_mock_slots

        slots = get_mock_slots(datetime(2026, 1, 23, 9, 0))

        assert slots[0].start.hour == 9
        assert slots[1].start.hour == 11
        assert slots[2].start.hour == 13
        assert slots[3].start.hour == 15


class TestCheckAvailability:
    """Test check_availability handler."""

    def test_returns_slots(self):
        """Should return available_slots and slots_display."""
        from examples.booking.nodes.slots_handler import check_availability

        result = check_availability({})

        assert "available_slots" in result
        assert "slots_display" in result
        assert len(result["available_slots"]) == 4

    def test_slots_display_is_string(self):
        """Should format slots_display as string."""
        from examples.booking.nodes.slots_handler import check_availability

        result = check_availability({})

        assert isinstance(result["slots_display"], str)
        assert "Dr." in result["slots_display"]


class TestBookSlot:
    """Test book_slot handler."""

    def test_books_selected_slot(self):
        """Should book the selected slot."""
        from examples.booking.nodes.slots_handler import book_appointment

        state = {
            "selected_slot": "slot_1",
            "patient_name": "Alice",
            "patient_phone": "+358401234567",
        }

        result = book_appointment(state)

        assert "booking" in result
        assert "booking_display" in result
        assert "booking_id" in result
        assert result["booking"]["patient_name"] == "Alice"

    def test_defaults_to_first_slot(self):
        """Should default to first slot if selected not found."""
        from examples.booking.nodes.slots_handler import book_appointment

        state = {
            "selected_slot": "nonexistent",
            "patient_name": "Bob",
        }

        result = book_appointment(state)

        assert result["booking"]["slot"]["id"] == "slot_0"

    def test_generates_booking_id(self):
        """Should generate unique booking ID."""
        from examples.booking.nodes.slots_handler import book_appointment

        result = book_appointment({"selected_slot": "slot_2"})

        assert len(result["booking_id"]) == 8


class TestCancelAppointment:
    """Test cancel_appointment handler."""

    def test_cancels_existing_appointment(self):
        """Should cancel an existing appointment."""
        # First create a booking
        from examples.booking.nodes.slots_handler import (
            book_appointment,
            cancel_appointment,
        )
        booking_result = book_appointment({
            "selected_slot": "slot_1",
            "patient_name": "Alice",
        })
        booking_id = booking_result["booking_id"]

        # Now cancel it
        state = {"appointment_id": booking_id}
        result = cancel_appointment(state)

        assert "cancellation" in result
        assert "cancellation_display" in result
        assert result["cancellation"]["id"] == booking_id

    def test_cancel_nonexistent_appointment(self):
        """Should handle nonexistent appointment."""
        from examples.booking.nodes.slots_handler import cancel_appointment

        result = cancel_appointment({"appointment_id": "nonexistent"})

        assert "error" in result
        assert "Unable to cancel" in result["cancellation_display"]


class TestDBIntegration:
    """Test tool handlers with DB integration."""

    def test_check_availability_with_db(self, tmp_path):
        """Should use DB when available."""
        from examples.booking.api.db import BookingDB
        from examples.booking.nodes.slots_handler import check_availability

        # Create test DB
        db_path = tmp_path / "test.db"
        db = BookingDB(str(db_path))
        db.init_schema()

        # Create calendar and slots
        cal = db.create_calendar("Test Clinic", "provider")
        db.create_slot(cal.id, datetime(2026, 1, 26, 9, 0), datetime(2026, 1, 26, 10, 0))
        db.create_slot(cal.id, datetime(2026, 1, 26, 11, 0), datetime(2026, 1, 26, 12, 0))

        state = {"db": db}
        result = check_availability(state)

        assert len(result["available_slots"]) == 2
        assert "Test Clinic" in result["slots_display"]

    def test_book_appointment_with_db(self, tmp_path):
        """Should book using DB."""
        from examples.booking.api.db import BookingDB
        from examples.booking.nodes.slots_handler import book_appointment

        # Create test DB
        db_path = tmp_path / "test.db"
        db = BookingDB(str(db_path))
        db.init_schema()

        # Create calendar and slot
        cal = db.create_calendar("Test Clinic", "provider")
        slot = db.create_slot(cal.id, datetime(2026, 1, 26, 9, 0), datetime(2026, 1, 26, 10, 0))

        state = {
            "db": db,
            "selected_slot": slot.id,
            "patient_name": "Alice",
            "patient_phone": "+358401234567",
        }
        result = book_appointment(state)

        assert "booking" in result
        assert result["booking"]["patient_name"] == "Alice"
        assert result["booking"]["slot_id"] == slot.id

        # Check slot is now unavailable
        updated_slot = db.get_slot(slot.id)
        assert not updated_slot.available

    def test_cancel_appointment_with_db(self, tmp_path):
        """Should cancel using DB."""
        from examples.booking.api.db import BookingDB
        from examples.booking.nodes.slots_handler import (
            cancel_appointment,
        )

        # Create test DB
        db_path = tmp_path / "test.db"
        db = BookingDB(str(db_path))
        db.init_schema()

        # Create calendar, slot, and appointment
        cal = db.create_calendar("Test Clinic", "provider")
        slot = db.create_slot(cal.id, datetime(2026, 1, 26, 9, 0), datetime(2026, 1, 26, 10, 0))
        appointment = db.create_appointment(slot.id, "Alice", "+358401234567")

        state = {"db": db, "appointment_id": appointment.id}
        result = cancel_appointment(state)

        assert "cancellation" in result
        assert result["cancellation"]["status"] == "cancelled"

        # Check slot is now available again
        updated_slot = db.get_slot(slot.id)
        assert updated_slot.available
