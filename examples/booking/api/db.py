"""SQLite database layer for booking API.

Provides CRUD operations for Calendar, Slot, and Appointment.
"""

import os
import sqlite3
import uuid
from datetime import datetime

from examples.booking.api.models import Appointment, Calendar, Slot


def generate_id(prefix: str) -> str:
    """Generate a prefixed UUID."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class BookingDB:
    """SQLite database for booking resources."""

    def __init__(self, db_path: str | None = None):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite file, or ":memory:" for in-memory.
                     Defaults to DATABASE_PATH env var or "./booking.db"
        """
        self.db_path = db_path or os.environ.get("DATABASE_PATH", "./booking.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def init_schema(self) -> None:
        """Create tables if they don't exist."""
        self.conn.executescript("""
            -- Calendars
            CREATE TABLE IF NOT EXISTS calendars (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT CHECK(type IN ('provider', 'service')),
                created_at TEXT DEFAULT (datetime('now'))
            );

            -- Slots
            CREATE TABLE IF NOT EXISTS slots (
                id TEXT PRIMARY KEY,
                calendar_id TEXT REFERENCES calendars(id) ON DELETE CASCADE,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                available INTEGER DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_slots_calendar_date
                ON slots(calendar_id, start_time);

            -- Appointments
            CREATE TABLE IF NOT EXISTS appointments (
                id TEXT PRIMARY KEY,
                slot_id TEXT UNIQUE REFERENCES slots(id),
                patient_name TEXT NOT NULL,
                patient_phone TEXT,
                status TEXT DEFAULT 'booked' CHECK(status IN ('booked', 'cancelled')),
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        self.conn.commit()

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

    # =========================================================================
    # Calendar operations
    # =========================================================================

    def create_calendar(self, name: str, type: str) -> Calendar:
        """Create a new calendar."""
        cal_id = generate_id("cal")
        now = datetime.now().isoformat()

        self.conn.execute(
            "INSERT INTO calendars (id, name, type, created_at) VALUES (?, ?, ?, ?)",
            (cal_id, name, type, now),
        )
        self.conn.commit()

        return Calendar(
            id=cal_id,
            name=name,
            type=type,  # type: ignore
            created_at=datetime.fromisoformat(now),
        )

    def get_calendar(self, calendar_id: str) -> Calendar | None:
        """Get calendar by ID."""
        row = self.conn.execute(
            "SELECT * FROM calendars WHERE id = ?", (calendar_id,)
        ).fetchone()

        if row is None:
            return None

        return Calendar(
            id=row["id"],
            name=row["name"],
            type=row["type"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def list_calendars(self) -> list[Calendar]:
        """List all calendars."""
        rows = self.conn.execute("SELECT * FROM calendars ORDER BY name").fetchall()

        return [
            Calendar(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def delete_calendar(self, calendar_id: str) -> bool:
        """Delete calendar by ID. Returns True if deleted."""
        cursor = self.conn.execute("DELETE FROM calendars WHERE id = ?", (calendar_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # =========================================================================
    # Slot operations
    # =========================================================================

    def create_slot(
        self,
        calendar_id: str,
        start: datetime,
        end: datetime,
    ) -> Slot:
        """Create a new slot."""
        slot_id = generate_id("slot")

        self.conn.execute(
            """INSERT INTO slots (id, calendar_id, start_time, end_time, available)
               VALUES (?, ?, ?, ?, 1)""",
            (slot_id, calendar_id, start.isoformat(), end.isoformat()),
        )
        self.conn.commit()

        return Slot(
            id=slot_id,
            calendar_id=calendar_id,
            start=start,
            end=end,
            available=True,
        )

    def get_slot(self, slot_id: str) -> Slot | None:
        """Get slot by ID."""
        row = self.conn.execute(
            "SELECT * FROM slots WHERE id = ?", (slot_id,)
        ).fetchone()

        if row is None:
            return None

        return Slot(
            id=row["id"],
            calendar_id=row["calendar_id"],
            start=datetime.fromisoformat(row["start_time"]),
            end=datetime.fromisoformat(row["end_time"]),
            available=bool(row["available"]),
        )

    def list_slots(
        self,
        calendar_id: str | None = None,
        available_only: bool = False,
    ) -> list[Slot]:
        """List slots with optional filters."""
        query = "SELECT * FROM slots WHERE 1=1"
        params: list = []

        if calendar_id:
            query += " AND calendar_id = ?"
            params.append(calendar_id)

        if available_only:
            query += " AND available = 1"

        query += " ORDER BY start_time"
        rows = self.conn.execute(query, params).fetchall()

        return [
            Slot(
                id=row["id"],
                calendar_id=row["calendar_id"],
                start=datetime.fromisoformat(row["start_time"]),
                end=datetime.fromisoformat(row["end_time"]),
                available=bool(row["available"]),
            )
            for row in rows
        ]

    def mark_slot_unavailable(self, slot_id: str) -> bool:
        """Mark slot as unavailable."""
        cursor = self.conn.execute(
            "UPDATE slots SET available = 0 WHERE id = ?", (slot_id,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def mark_slot_available(self, slot_id: str) -> bool:
        """Mark slot as available."""
        cursor = self.conn.execute(
            "UPDATE slots SET available = 1 WHERE id = ?", (slot_id,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_slot(self, slot_id: str) -> bool:
        """Delete slot by ID."""
        cursor = self.conn.execute("DELETE FROM slots WHERE id = ?", (slot_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # =========================================================================
    # Appointment operations
    # =========================================================================

    def create_appointment(
        self,
        slot_id: str,
        patient_name: str,
        patient_phone: str | None = None,
    ) -> Appointment:
        """Create appointment and mark slot unavailable."""
        appt_id = generate_id("appt")
        now = datetime.now().isoformat()

        self.conn.execute(
            """INSERT INTO appointments
               (id, slot_id, patient_name, patient_phone, status, created_at)
               VALUES (?, ?, ?, ?, 'booked', ?)""",
            (appt_id, slot_id, patient_name, patient_phone, now),
        )
        self.mark_slot_unavailable(slot_id)
        self.conn.commit()

        return Appointment(
            id=appt_id,
            slot_id=slot_id,
            patient_name=patient_name,
            patient_phone=patient_phone,
            status="booked",
            created_at=datetime.fromisoformat(now),
        )

    def get_appointment(self, appointment_id: str) -> Appointment | None:
        """Get appointment by ID."""
        row = self.conn.execute(
            "SELECT * FROM appointments WHERE id = ?", (appointment_id,)
        ).fetchone()

        if row is None:
            return None

        return Appointment(
            id=row["id"],
            slot_id=row["slot_id"],
            patient_name=row["patient_name"],
            patient_phone=row["patient_phone"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def list_appointments(self, calendar_id: str | None = None) -> list[Appointment]:
        """List appointments with optional calendar filter."""
        if calendar_id:
            query = """
                SELECT a.* FROM appointments a
                JOIN slots s ON a.slot_id = s.id
                WHERE s.calendar_id = ?
                ORDER BY a.created_at DESC
            """
            rows = self.conn.execute(query, (calendar_id,)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM appointments ORDER BY created_at DESC"
            ).fetchall()

        return [
            Appointment(
                id=row["id"],
                slot_id=row["slot_id"],
                patient_name=row["patient_name"],
                patient_phone=row["patient_phone"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def cancel_appointment(self, appointment_id: str) -> bool:
        """Cancel appointment and free the slot."""
        appt = self.get_appointment(appointment_id)
        if appt is None:
            return False

        self.conn.execute(
            "UPDATE appointments SET status = 'cancelled' WHERE id = ?",
            (appointment_id,),
        )
        self.mark_slot_available(appt.slot_id)
        self.conn.commit()
        return True

    def delete_appointment(self, appointment_id: str) -> bool:
        """Delete appointment and free the slot."""
        appt = self.get_appointment(appointment_id)
        if appt is None:
            return False

        self.conn.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
        self.mark_slot_available(appt.slot_id)
        self.conn.commit()
        return True


# Global instance for API routes
_db: BookingDB | None = None


def get_db() -> BookingDB:
    """Get or create database instance."""
    global _db
    if _db is None:
        _db = BookingDB()
        _db.init_schema()
    return _db
