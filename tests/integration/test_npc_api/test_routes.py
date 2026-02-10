"""Tests for NPC encounter API routes.

Tests endpoint behavior, HTMX responses, and session handling.
Uses mocking to avoid actual LLM calls.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_turn_result():
    """Create mock TurnResult."""
    from examples.npc.api.session import TurnResult

    return TurnResult(
        turn_number=1,
        narrations=[{"npc": "Grok", "text": "Hello traveler!"}],
        scene_image="/static/images/tavern.png",
        turn_summary="The party enters the tavern.",
        is_complete=False,
    )


class TestEncounterStart:
    """Tests for POST /encounter/start endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-009")
    async def test_start_requires_session_id(self):
        """Start endpoint validates required session_id."""
        from examples.npc.api.routes.encounter import router

        app = FastAPI()
        app.include_router(router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/encounter/start",
                data={"location": "tavern"},  # Missing session_id
            )

        # FastAPI returns 422 for validation errors
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-009")
    async def test_start_accepts_valid_input(self, mock_turn_result):
        """Start endpoint accepts valid form data."""
        from examples.npc.api.routes import encounter

        # Mock the dependencies
        mock_session = AsyncMock()
        mock_session.start = AsyncMock(return_value=mock_turn_result)

        async def mock_get_session(session_id):
            return mock_session

        # Mock create_npcs_from_concepts to return simple NPCs
        async def mock_create_npcs(concepts):
            return [{"name": "Grok", "race": "dwarf"}]

        # Patch the module-level functions
        with (
            patch.object(encounter, "_get_session", mock_get_session),
            patch.object(encounter, "create_npcs_from_concepts", mock_create_npcs),
            patch.object(encounter, "templates") as mock_tmpl,
        ):
            # Configure mock template to return proper Response
            mock_tmpl.TemplateResponse.return_value = HTMLResponse(
                content="<div>Started</div>",
                headers={"HX-Trigger": "encounter-updated"},
            )

            app = FastAPI()
            app.include_router(encounter.router)

            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post(
                    "/encounter/start",
                    data={
                        "session_id": "test-123",
                        "location": "tavern",
                        "npc_concepts": ["a gruff dwarf"],
                    },
                )

            assert response.status_code == 200
            assert mock_session.start.called

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-009")
    async def test_start_creates_npcs_from_concepts(self, mock_turn_result):
        """Start endpoint creates NPCs from concept strings."""
        from examples.npc.api.routes import encounter

        mock_session = AsyncMock()
        mock_session.start = AsyncMock(return_value=mock_turn_result)

        create_npcs_called_with = []

        async def mock_create_npcs(concepts):
            create_npcs_called_with.extend(concepts)
            return [{"name": f"NPC-{i}", "race": "test"} for i in range(len(concepts))]

        with (
            patch.object(
                encounter, "_get_session", AsyncMock(return_value=mock_session)
            ),
            patch.object(encounter, "create_npcs_from_concepts", mock_create_npcs),
            patch.object(encounter, "templates") as mock_tmpl,
        ):
            mock_tmpl.TemplateResponse.return_value = HTMLResponse(
                content="<div>OK</div>"
            )

            app = FastAPI()
            app.include_router(encounter.router)

            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                await client.post(
                    "/encounter/start",
                    data={
                        "session_id": "test-123",
                        "location": "tavern",
                        "npc_concepts": ["a dwarf", "an elf"],
                    },
                )

            # Should have called create_npcs with concept dicts
            assert len(create_npcs_called_with) == 2
            assert create_npcs_called_with[0]["concept"] == "a dwarf"


class TestEncounterTurn:
    """Tests for POST /encounter/turn endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-009")
    async def test_turn_requires_dm_input(self):
        """Turn endpoint validates required dm_input."""
        from examples.npc.api.routes.encounter import router

        app = FastAPI()
        app.include_router(router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/encounter/turn",
                data={"session_id": "test-123"},  # Missing dm_input
            )

        # FastAPI returns 422 for validation errors
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-009")
    async def test_turn_resumes_existing_session(self, mock_turn_result):
        """Turn endpoint resumes existing session."""
        from examples.npc.api.routes import encounter

        mock_session = AsyncMock()
        mock_session._is_resume = AsyncMock(return_value=True)  # Session exists
        mock_session.turn = AsyncMock(return_value=mock_turn_result)

        with (
            patch.object(
                encounter, "_get_session", AsyncMock(return_value=mock_session)
            ),
            patch.object(encounter, "templates") as mock_tmpl,
        ):
            mock_tmpl.TemplateResponse.return_value = HTMLResponse(
                content="<div>Turn</div>"
            )

            app = FastAPI()
            app.include_router(encounter.router)

            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post(
                    "/encounter/turn",
                    data={
                        "session_id": "test-123",
                        "dm_input": "The party enters the tavern",
                    },
                )

            assert response.status_code == 200
            assert mock_session.turn.called
            mock_session.turn.assert_called_once_with("The party enters the tavern")

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-009")
    async def test_turn_handles_no_session(self, mock_turn_result):
        """Turn on non-existent session returns error."""
        from examples.npc.api.routes import encounter

        mock_session = AsyncMock()
        mock_session._is_resume = AsyncMock(return_value=False)  # Session doesn't exist

        with (
            patch.object(
                encounter, "_get_session", AsyncMock(return_value=mock_session)
            ),
            patch.object(encounter, "templates") as mock_tmpl,
        ):
            mock_tmpl.TemplateResponse.return_value = HTMLResponse(
                content="<div>Error</div>",
                status_code=400,
            )

            app = FastAPI()
            app.include_router(encounter.router)

            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post(
                    "/encounter/turn",
                    data={
                        "session_id": "nonexistent",
                        "dm_input": "Hello",
                    },
                )

            # Should return 400 error
            assert response.status_code == 400


class TestEncounterState:
    """Tests for GET /encounter/{session_id} endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-009")
    async def test_get_nonexistent_session_returns_404(self):
        """GET non-existent session returns 404."""
        from examples.npc.api.routes import encounter

        mock_session = AsyncMock()
        mock_session._is_resume = AsyncMock(return_value=False)

        with patch.object(
            encounter, "_get_session", AsyncMock(return_value=mock_session)
        ):
            app = FastAPI()
            app.include_router(encounter.router)

            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.get("/encounter/nonexistent")

            assert response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-009")
    async def test_get_state_returns_current_state(self):
        """GET state endpoint returns current session state."""
        from examples.npc.api.routes import encounter

        mock_session = AsyncMock()
        mock_session._is_resume = AsyncMock(return_value=True)

        # Mock the graph for aget_state
        mock_graph = AsyncMock()
        mock_graph.aget_state = AsyncMock(
            return_value=AsyncMock(
                values={
                    "turn_number": 2,
                    "narrations": [],
                    "npcs": [],
                    "location": "tavern",
                }
            )
        )

        with (
            patch.object(
                encounter, "_get_session", AsyncMock(return_value=mock_session)
            ),
            patch.object(
                encounter, "get_encounter_graph", AsyncMock(return_value=mock_graph)
            ),
            patch.object(encounter, "templates") as mock_tmpl,
        ):
            mock_tmpl.TemplateResponse.return_value = HTMLResponse(
                content="<div>State</div>"
            )

            app = FastAPI()
            app.include_router(encounter.router)

            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.get("/encounter/test-123")

            assert response.status_code == 200


class TestHtmxIntegration:
    """Tests for HTMX-specific behavior."""

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-009")
    async def test_response_has_hx_trigger_header(self, mock_turn_result):
        """Responses include HX-Trigger for client-side updates."""
        from examples.npc.api.routes import encounter

        mock_session = AsyncMock()
        mock_session.start = AsyncMock(return_value=mock_turn_result)

        with (
            patch.object(
                encounter, "_get_session", AsyncMock(return_value=mock_session)
            ),
            patch.object(
                encounter,
                "create_npcs_from_concepts",
                AsyncMock(return_value=[{"name": "Grok"}]),
            ),
            patch.object(encounter, "templates") as mock_tmpl,
        ):
            # Return response with HX-Trigger header
            mock_tmpl.TemplateResponse.return_value = HTMLResponse(
                content="<div>Response</div>",
                headers={"HX-Trigger": "encounter-updated"},
            )

            app = FastAPI()
            app.include_router(encounter.router)

            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post(
                    "/encounter/start",
                    data={
                        "session_id": "test-123",
                        "location": "tavern",
                        "npc_concepts": ["a dwarf"],
                    },
                )

            assert response.status_code == 200
            assert "HX-Trigger" in response.headers
            assert response.headers["HX-Trigger"] == "encounter-updated"
