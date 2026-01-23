"""FastAPI application factory for booking API."""

from datetime import timedelta
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from examples.booking.api.db import BookingDB
from examples.booking.api.models import (
    Appointment,
    Calendar,
    CreateAppointment,
    CreateCalendar,
    CreateSlot,
    Slot,
)

# --- Chat Request/Response Models ---


class ChatRequest(BaseModel):
    """Request to start or continue chat."""

    message: str = "start"


class ResumeRequest(BaseModel):
    """Request to resume after interrupt."""

    answer: str


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    status: str
    question: str | None = None
    response: str | None = None
    state: dict[str, Any] | None = None


def create_app(db: BookingDB | None = None, graph: Any | None = None) -> FastAPI:
    """Create FastAPI app with optional database and graph injection.

    Args:
        db: Database instance. If None, creates default SQLite DB.
        graph: Compiled LangGraph application. If None, chat endpoints return 503.

    Returns:
        Configured FastAPI application.
    """
    if db is None:
        db = BookingDB("booking.db")
        db.init_schema()

    app = FastAPI(title="Booking API", version="0.1.0")

    # Store db and graph in app state for access in routes
    app.state.db = db
    app.state.graph = graph

    # --- Calendar Routes ---

    @app.post("/calendars", response_model=Calendar, status_code=201)
    def create_calendar(data: CreateCalendar) -> Calendar:
        """Create a new calendar."""
        return app.state.db.create_calendar(name=data.name, type=data.type)

    @app.get("/calendars", response_model=list[Calendar])
    def list_calendars() -> list[Calendar]:
        """List all calendars."""
        return app.state.db.list_calendars()

    @app.get("/calendars/{calendar_id}", response_model=Calendar)
    def get_calendar(calendar_id: str) -> Calendar:
        """Get a calendar by ID."""
        cal = app.state.db.get_calendar(calendar_id)
        if cal is None:
            raise HTTPException(status_code=404, detail="Calendar not found")
        return cal

    @app.delete("/calendars/{calendar_id}", status_code=204)
    def delete_calendar(calendar_id: str) -> None:
        """Delete a calendar."""
        deleted = app.state.db.delete_calendar(calendar_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Calendar not found")

    # --- Slot Routes ---

    @app.post("/calendars/{calendar_id}/slots", response_model=Slot, status_code=201)
    def create_slot(calendar_id: str, data: CreateSlot) -> Slot:
        """Create a new slot in a calendar."""
        # Verify calendar exists
        if app.state.db.get_calendar(calendar_id) is None:
            raise HTTPException(status_code=404, detail="Calendar not found")
        end = data.start + timedelta(minutes=data.duration_min)
        return app.state.db.create_slot(
            calendar_id=calendar_id, start=data.start, end=end
        )

    @app.get("/calendars/{calendar_id}/slots", response_model=list[Slot])
    def list_slots(calendar_id: str, available: bool | None = None) -> list[Slot]:
        """List all slots for a calendar, optionally filtering by availability."""
        slots = app.state.db.list_slots(calendar_id)
        if available is not None:
            slots = [s for s in slots if s.available == available]
        return slots

    @app.get("/slots/{slot_id}", response_model=Slot)
    def get_slot(slot_id: str) -> Slot:
        """Get a slot by ID."""
        slot = app.state.db.get_slot(slot_id)
        if slot is None:
            raise HTTPException(status_code=404, detail="Slot not found")
        return slot

    @app.delete("/slots/{slot_id}", status_code=204)
    def delete_slot(slot_id: str) -> None:
        """Delete a slot."""
        deleted = app.state.db.delete_slot(slot_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Slot not found")

    # --- Appointment Routes ---

    @app.post("/appointments", response_model=Appointment, status_code=201)
    def create_appointment(data: CreateAppointment) -> Appointment:
        """Create a new appointment (books a slot)."""
        slot = app.state.db.get_slot(data.slot_id)
        if slot is None:
            raise HTTPException(status_code=404, detail="Slot not found")
        if not slot.available:
            raise HTTPException(status_code=409, detail="Slot already booked")
        # Mark slot unavailable
        app.state.db.mark_slot_unavailable(data.slot_id)
        return app.state.db.create_appointment(
            slot_id=data.slot_id,
            patient_name=data.patient_name,
            patient_phone=data.patient_phone,
        )

    @app.get("/appointments", response_model=list[Appointment])
    def list_appointments() -> list[Appointment]:
        """List all appointments."""
        return app.state.db.list_appointments()

    @app.get("/appointments/{appointment_id}", response_model=Appointment)
    def get_appointment(appointment_id: str) -> Appointment:
        """Get an appointment by ID."""
        appt = app.state.db.get_appointment(appointment_id)
        if appt is None:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return appt

    @app.patch("/appointments/{appointment_id}/cancel", response_model=Appointment)
    def cancel_appointment(appointment_id: str) -> Appointment:
        """Cancel an appointment (releases the slot)."""
        appt = app.state.db.get_appointment(appointment_id)
        if appt is None:
            raise HTTPException(status_code=404, detail="Appointment not found")
        # cancel_appointment handles slot release internally
        app.state.db.cancel_appointment(appointment_id)
        # Return updated appointment
        return app.state.db.get_appointment(appointment_id)

    @app.delete("/appointments/{appointment_id}", status_code=204)
    def delete_appointment(appointment_id: str) -> None:
        """Delete an appointment."""
        deleted = app.state.db.delete_appointment(appointment_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Appointment not found")

    # --- Chat Routes ---

    @app.post("/chat/{thread_id}", response_model=ChatResponse)
    async def chat(thread_id: str, request: ChatRequest) -> ChatResponse:
        """Start or continue a chat session.

        If graph hits an interrupt, returns status="waiting" with the question.
        Otherwise returns status="complete" with the response.
        """
        if app.state.graph is None:
            raise HTTPException(status_code=503, detail="Graph not loaded")

        from yamlgraph.executor_async import run_graph_async

        config = {"configurable": {"thread_id": thread_id}}

        try:
            result = await run_graph_async(
                app.state.graph,
                initial_state={"input": request.message},
                config=config,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

        # Check for interrupt
        if "__interrupt__" in result:
            interrupt_value = result["__interrupt__"][0].value
            question = interrupt_value.get("question") or interrupt_value.get(
                "prompt", str(interrupt_value)
            )
            return ChatResponse(
                status="waiting",
                question=question,
                state={k: v for k, v in result.items() if not k.startswith("_")},
            )

        return ChatResponse(
            status="complete",
            response=result.get("confirmation") or result.get("response"),
            state={k: v for k, v in result.items() if not k.startswith("_")},
        )

    @app.post("/chat/{thread_id}/resume", response_model=ChatResponse)
    async def resume(thread_id: str, request: ResumeRequest) -> ChatResponse:
        """Resume a paused chat session with user's answer."""
        if app.state.graph is None:
            raise HTTPException(status_code=503, detail="Graph not loaded")

        from langgraph.types import Command

        from yamlgraph.executor_async import run_graph_async

        config = {"configurable": {"thread_id": thread_id}}

        try:
            result = await run_graph_async(
                app.state.graph,
                initial_state=Command(resume=request.answer),
                config=config,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

        # Check for another interrupt
        if "__interrupt__" in result:
            interrupt_value = result["__interrupt__"][0].value
            question = interrupt_value.get("question") or interrupt_value.get(
                "prompt", str(interrupt_value)
            )
            return ChatResponse(
                status="waiting",
                question=question,
                state={k: v for k, v in result.items() if not k.startswith("_")},
            )

        return ChatResponse(
            status="complete",
            response=result.get("confirmation") or result.get("response"),
            state={k: v for k, v in result.items() if not k.startswith("_")},
        )

    @app.get("/health")
    def health() -> dict:
        """Health check endpoint."""
        return {"status": "ok", "graph_loaded": app.state.graph is not None}

    return app
