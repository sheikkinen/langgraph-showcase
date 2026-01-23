"""Booking API Pydantic models.

FHIR-inspired: Calendar → Slot → Appointment
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# Response Models (full resources)
# =============================================================================


class Calendar(BaseModel):
    """A service or professional's schedule."""

    id: str
    name: str = Field(description="Display name, e.g., 'Dr. Smith'")
    type: Literal["provider", "service"]
    created_at: datetime = Field(default_factory=datetime.now)


class Slot(BaseModel):
    """An available time window within a calendar."""

    id: str
    calendar_id: str
    start: datetime
    end: datetime
    available: bool = True


class Appointment(BaseModel):
    """A booking linking a patient to a slot."""

    id: str
    slot_id: str
    patient_name: str
    patient_phone: str | None = None
    status: Literal["booked", "cancelled"] = "booked"
    created_at: datetime = Field(default_factory=datetime.now)


# =============================================================================
# Request Models (for creation)
# =============================================================================


class CreateCalendar(BaseModel):
    """Request to create a calendar."""

    name: str
    type: Literal["provider", "service"]


class CreateSlot(BaseModel):
    """Request to create a slot."""

    start: datetime
    duration_min: int = Field(default=60, ge=15, le=480)


class CreateAppointment(BaseModel):
    """Request to book an appointment."""

    slot_id: str
    patient_name: str
    patient_phone: str | None = None
