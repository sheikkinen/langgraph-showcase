"""Tool node handlers for booking operations."""
from datetime import datetime, timedelta
from typing import Any
import uuid

from .schema import Slot, Booking


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
        slots.append(Slot(
            id=f"slot_{i}",
            start=start,
            end=start + timedelta(hours=1),
            provider="Dr. Smith" if i % 2 == 0 else "Dr. Jones"
        ))
    
    return slots


def check_availability(state: dict[str, Any]) -> dict[str, Any]:
    """Check available slots. Python tool node handler."""
    slots = get_mock_slots()
    return {
        "available_slots": [s.model_dump() for s in slots],
        "slots_display": "\n".join(f"- {s.display}" for s in slots)
    }


def book_slot(state: dict[str, Any]) -> dict[str, Any]:
    """Book the selected slot. Python tool node handler."""
    slot_id = state.get("selected_slot")
    patient_name = state.get("patient_name", "Patient")
    patient_phone = state.get("patient_phone", "")
    
    # Find the slot
    slots = get_mock_slots()
    slot = next((s for s in slots if s.id == slot_id), slots[0])
    
    booking = Booking(
        id=str(uuid.uuid4())[:8],
        slot=slot,
        patient_name=patient_name,
        patient_phone=patient_phone
    )
    
    BOOKINGS[booking.id] = booking
    
    return {
        "booking": booking.model_dump(),
        "booking_display": f"Booked: {slot.display}",
        "booking_id": booking.id
    }
