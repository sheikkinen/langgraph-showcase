"""Booking domain models."""

from datetime import datetime

from pydantic import BaseModel


class Slot(BaseModel):
    """Available time slot."""

    id: str
    start: datetime
    end: datetime
    provider: str = "Dr. Smith"

    @property
    def display(self) -> str:
        return f"{self.start:%A %d.%m. at %H:%M} with {self.provider}"


class Booking(BaseModel):
    """Confirmed booking."""

    id: str
    slot: Slot
    patient_name: str
    patient_phone: str
    created_at: datetime = None

    def model_post_init(self, _context):
        if self.created_at is None:
            self.created_at = datetime.now()
