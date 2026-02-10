"""Tests for NPC session adapter.

TDD: Red → Green → Refactor
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGetCheckpointer:
    """Tests for checkpointer factory."""

    @pytest.mark.req("REQ-YG-026")
    def test_returns_memory_saver_by_default(self):
        """Without REDIS_URL, should return MemorySaver."""
        from examples.npc.api.session import _reset_checkpointer, get_checkpointer

        _reset_checkpointer()

        with patch.dict("os.environ", {}, clear=True):
            checkpointer = get_checkpointer()
            assert checkpointer is not None
            # MemorySaver type check
            assert "memory" in type(checkpointer).__module__.lower()

    @pytest.mark.req("REQ-YG-026")
    def test_caches_checkpointer(self):
        """Should return same instance on repeated calls."""
        from examples.npc.api.session import _reset_checkpointer, get_checkpointer

        _reset_checkpointer()

        cp1 = get_checkpointer()
        cp2 = get_checkpointer()
        assert cp1 is cp2


class TestEncounterSession:
    """Tests for EncounterSession class."""

    @pytest.fixture
    def mock_app(self):
        """Create mock LangGraph app."""
        app = MagicMock()
        app.checkpointer = MagicMock()
        app.checkpointer.aget = AsyncMock(return_value=None)
        app.aget_state = AsyncMock(return_value=MagicMock(next=[], values={}))
        return app

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-026")
    async def test_is_resume_false_for_new_session(self, mock_app):
        """New session should return False for _is_resume."""
        from examples.npc.api.session import EncounterSession

        mock_app.checkpointer.aget.return_value = None

        session = EncounterSession(mock_app, "test-session-123")
        result = await session._is_resume()

        assert result is False
        mock_app.checkpointer.aget.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-026")
    async def test_is_resume_true_for_existing_session(self, mock_app):
        """Existing session should return True for _is_resume."""
        from examples.npc.api.session import EncounterSession

        mock_app.checkpointer.aget.return_value = {"some": "checkpoint"}

        session = EncounterSession(mock_app, "test-session-123")
        result = await session._is_resume()

        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-026")
    async def test_start_creates_initial_state(self, mock_app):
        """Start should invoke graph with initial state."""
        from examples.npc.api.session import EncounterSession

        mock_app.ainvoke = AsyncMock(
            return_value={
                "turn_number": 1,
                "narrations": [],
                "scene_image": None,
            }
        )
        mock_app.aget_state.return_value = MagicMock(next=["await_dm"], values={})

        session = EncounterSession(mock_app, "test-session-123")
        npcs = [{"name": "Thorin", "race": "Dwarf"}]
        result = await session.start(npcs, "The Red Dragon Inn")

        assert result.turn_number == 1
        assert result.is_complete is False  # Has next node
        mock_app.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-026")
    async def test_turn_resumes_with_command(self, mock_app):
        """Turn should resume graph with Command."""
        from examples.npc.api.session import EncounterSession

        mock_app.ainvoke = AsyncMock(
            return_value={
                "turn_number": 2,
                "narrations": [{"npc": "Thorin", "text": "Hmm..."}],
                "scene_image": None,
            }
        )
        mock_app.aget_state.return_value = MagicMock(next=["await_dm"], values={})

        session = EncounterSession(mock_app, "test-session-123")
        result = await session.turn("A stranger enters the tavern")

        assert result.turn_number == 2
        assert len(result.narrations) == 1

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-026")
    async def test_turn_catches_errors(self, mock_app):
        """Turn should catch exceptions and return error."""
        from examples.npc.api.session import EncounterSession

        mock_app.ainvoke = AsyncMock(side_effect=Exception("LLM failed"))

        session = EncounterSession(mock_app, "test-session-123")
        result = await session.turn("A stranger enters")

        assert result.error is not None
        assert "LLM failed" in result.error


class TestTurnResult:
    """Tests for TurnResult dataclass."""

    @pytest.mark.req("REQ-YG-026")
    def test_creates_with_defaults(self):
        """TurnResult should have sensible defaults."""
        from examples.npc.api.session import TurnResult

        result = TurnResult(
            turn_number=1,
            narrations=[],
            scene_image=None,
            turn_summary=None,
            is_complete=False,
        )

        assert result.turn_number == 1
        assert result.error is None

    @pytest.mark.req("REQ-YG-026")
    def test_error_field_optional(self):
        """Error field should be optional."""
        from examples.npc.api.session import TurnResult

        result = TurnResult(
            turn_number=1,
            narrations=[],
            scene_image=None,
            turn_summary=None,
            is_complete=False,
            error="Something went wrong",
        )

        assert result.error == "Something went wrong"


class TestCreateNpcsFromConcepts:
    """Tests for NPC creation helper."""

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-026")
    async def test_creates_npcs_from_concepts(self):
        """Should create NPCs using npc-creation graph."""
        from examples.npc.api.session import create_npcs_from_concepts

        concepts = [
            {"concept": "a gruff dwarven bartender", "race": "Dwarf"},
        ]

        with patch("examples.npc.api.session.get_npc_creation_graph") as mock_get:
            mock_app = MagicMock()
            mock_app.ainvoke = AsyncMock(
                return_value={
                    "identity": {
                        "name": "Thorin Ironfoot",
                        "race": "Dwarf",
                        "character_class": "Commoner",
                        "appearance": "Stocky with copper beard",
                    },
                    "personality": {"traits": ["Gruff", "Loyal"]},
                    "behavior": {"goals": ["Run the tavern"]},
                }
            )
            mock_get.return_value = mock_app

            npcs = await create_npcs_from_concepts(concepts)

            assert len(npcs) == 1
            assert npcs[0]["name"] == "Thorin Ironfoot"
            assert npcs[0]["race"] == "Dwarf"

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-026")
    async def test_handles_creation_errors_gracefully(self):
        """Should return fallback NPC on error."""
        from examples.npc.api.session import create_npcs_from_concepts

        concepts = [
            {"concept": "a mysterious elf", "race": "Elf"},
        ]

        with patch("examples.npc.api.session.get_npc_creation_graph") as mock_get:
            mock_app = MagicMock()
            mock_app.ainvoke = AsyncMock(side_effect=Exception("Graph failed"))
            mock_get.return_value = mock_app

            npcs = await create_npcs_from_concepts(concepts)

            assert len(npcs) == 1
            assert "error" in npcs[0]
            assert npcs[0]["race"] == "Elf"
