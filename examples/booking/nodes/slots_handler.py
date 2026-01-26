"""Tool node handlers for booking operations."""

import uuid
from datetime import datetime, timedelta
from typing import Any

from .schema import Booking, Slot

# Global DB instance (set by main.py)
_db = None

def set_global_db(db):
    """Set the global DB instance for tool handlers."""
    global _db
    _db = db

# In-memory store (replace with DB in production)
BOOKINGS: dict[str, Booking] = {}


def get_mock_slots(date: datetime = None) -> list[Slot]:
    """Generate mock available slots."""
    if date is None:
        date = datetime.now()

    base = date.replace(hour=9, minute=0, second=0, microsecond=0)
    slots = []

    for i in range(4):
        start = base + timedelta(hours=i * 2)
        slots.append(
            Slot(
                id=f"slot_{i}",
                start=start,
                end=start + timedelta(hours=1),
                provider="Dr. Smith" if i % 2 == 0 else "Dr. Jones",
            )
        )

    return slots


def check_availability(state: dict[str, Any]) -> dict[str, Any]:
    """Check available slots. Python tool node handler."""
    db = state.get("db") or _db
    if db is None:
        # Fallback to mock for testing
        slots = get_mock_slots()
    else:
        # Get all calendars, then slots for first calendar
        calendars = db.list_calendars()
        if not calendars:
            slots = []
        else:
            calendar_id = calendars[0].id
            slots_db = db.list_slots(calendar_id, available_only=True)
            # Convert to Slot objects for compatibility
            slots = [
                Slot(
                    id=s.id,
                    start=s.start,
                    end=s.end,
                    provider=calendars[0].name,
                )
                for s in slots_db
            ]

    return {
        "available_slots": [s.model_dump() for s in slots],
        "slots_display": "\n".join(f"- {s.display}" for s in slots) if slots else "No slots available",
    }


def book_appointment(state: dict[str, Any]) -> dict[str, Any]:
    """Book the selected slot. Python tool node handler."""
    db = state.get("db") or _db
    slot_id = state.get("selected_slot")
    patient_name = state.get("patient_name", "Patient")
    patient_phone = state.get("patient_phone", "")

    if db is None:
        # Fallback to mock
        slots = get_mock_slots()
        slot = next((s for s in slots if s.id == slot_id), slots[0])
        booking = Booking(
            id=str(uuid.uuid4())[:8],
            slot=slot,
            patient_name=patient_name,
            patient_phone=patient_phone,
        )
        BOOKINGS[booking.id] = booking
        return {
            "booking": booking.model_dump(),
            "booking_display": f"Booked: {slot.display}",
            "booking_id": booking.id,
        }
    else:
        # Use real DB
        try:
            appointment = db.create_appointment(
                slot_id=slot_id,
                patient_name=patient_name,
                patient_phone=patient_phone or None,
            )
            slot = db.get_slot(slot_id)
            return {
                "booking": appointment.model_dump(),
                "booking_display": f"Booked: {slot.start.strftime('%I:%M %p')} - {slot.end.strftime('%I:%M %p')}",
                "booking_id": appointment.id,
            }
        except Exception as e:
            return {
                "error": f"Booking failed: {str(e)}",
                "booking_display": "Unable to book appointment",
            }


def cancel_appointment(state: dict[str, Any]) -> dict[str, Any]:
    """Cancel an appointment. Python tool node handler."""
    db = state.get("db") or _db
    appointment_id = state.get("appointment_id")

    if db is None:
        # Fallback to mock
        if appointment_id in BOOKINGS:
            del BOOKINGS[appointment_id]
            return {
                "cancellation": {"id": appointment_id, "status": "cancelled"},
                "cancellation_display": f"Cancelled appointment {appointment_id}",
            }
        else:
            return {
                "error": "Appointment not found",
                "cancellation_display": "Unable to cancel appointment",
            }
    else:
        # Use real DB
        try:
            success = db.cancel_appointment(appointment_id)
            if not success:
                return {
                    "error": "Appointment not found",
                    "cancellation_display": "Unable to cancel appointment",
                }
            # Get the updated appointment
            appointment = db.get_appointment(appointment_id)
            return {
                "cancellation": appointment.model_dump(),
                "cancellation_display": f"Cancelled appointment for {appointment.patient_name}",
            }
        except Exception as e:
            return {
                "error": f"Cancellation failed: {str(e)}",
                "cancellation_display": "Unable to cancel appointment",
            }
