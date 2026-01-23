"""Session adapter for NPC Encounter API.

Provides stateless session management with checkpointer-based state persistence.
All session state lives in the checkpointer (SQLite or Redis), not in Python objects.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphInterrupt
from langgraph.types import Command

logger = logging.getLogger(__name__)

# Module-level caches
_encounter_graph = None
_npc_creation_graph = None
_checkpointer = None


def _reset_checkpointer():
    """Reset checkpointer cache (for testing)."""
    global _checkpointer
    _checkpointer = None


def _reset_graphs():
    """Reset graph caches (for testing)."""
    global _encounter_graph, _npc_creation_graph
    _encounter_graph = None
    _npc_creation_graph = None


def get_checkpointer():
    """Get or create checkpointer.

    Uses Redis if REDIS_URL is set, otherwise MemorySaver.
    Note: MemorySaver supports both sync and async operations.
    For production, use Redis for persistence across restarts.
    """
    global _checkpointer
    if _checkpointer is None:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            from langgraph.checkpoint.redis import RedisSaver

            _checkpointer = RedisSaver.from_conn_string(redis_url)
            _checkpointer.setup()
        else:
            # MemorySaver works with both sync and async
            # For persistence, set REDIS_URL or use file-based storage
            _checkpointer = MemorySaver()
    return _checkpointer


async def get_encounter_graph():
    """Get cached encounter graph with checkpointer."""
    global _encounter_graph
    if _encounter_graph is None:
        from yamlgraph.graph_loader import compile_graph, load_graph_config

        config = load_graph_config("examples/npc/encounter-multi.yaml")
        graph = compile_graph(config)
        _encounter_graph = graph.compile(checkpointer=get_checkpointer())
    return _encounter_graph


async def get_npc_creation_graph():
    """Get cached NPC creation graph (no checkpointer - one-shot)."""
    global _npc_creation_graph
    if _npc_creation_graph is None:
        from yamlgraph.graph_loader import compile_graph, load_graph_config

        config = load_graph_config("examples/npc/npc-creation.yaml")
        graph = compile_graph(config)
        _npc_creation_graph = graph.compile()
    return _npc_creation_graph


@dataclass
class TurnResult:
    """Result from encounter turn processing."""

    turn_number: int
    narrations: list[dict]
    scene_image: str | None
    turn_summary: str | None
    is_complete: bool
    error: str | None = None


class EncounterSession:
    """Stateless session adapter - all state in checkpointer."""

    def __init__(self, app, session_id: str):
        """Initialize session wrapper.

        Args:
            app: Compiled LangGraph application with checkpointer
            session_id: Unique session identifier for checkpointing
        """
        self._app = app
        self._session_id = session_id
        self._config = {"configurable": {"thread_id": session_id}}

    async def _is_resume(self) -> bool:
        """Check if session exists via checkpointer."""
        try:
            checkpoint = await self._app.checkpointer.aget(self._config)
            return checkpoint is not None
        except Exception:
            return False

    async def start(self, npcs: list[dict], location: str) -> TurnResult:
        """Start new encounter with pre-created NPCs."""
        initial_state = {
            "npcs": npcs,
            "location": location,
            "location_description": f"A bustling scene at {location}",
            "turn_number": 1,
            "encounter_history": [],
            "perceptions": [],
            "decisions": [],
            "narrations": [],
        }
        try:
            result = await self._app.ainvoke(initial_state, self._config)
            return await self._parse_result(result)
        except GraphInterrupt:
            # Graph hit interrupt node - encounter started, waiting for DM input
            # This is normal - return a "waiting" state
            return TurnResult(
                turn_number=1,
                narrations=[
                    {
                        "npc": "System",
                        "text": f"Encounter started at {location}. {len(npcs)} NPCs present. Enter your first narration.",
                    }
                ],
                scene_image=None,
                turn_summary=None,
                is_complete=False,
            )
        except Exception as e:
            return TurnResult(
                turn_number=1,
                narrations=[],
                scene_image=None,
                turn_summary=None,
                is_complete=False,
                error=str(e),
            )

    async def turn(self, dm_input: str) -> TurnResult:
        """Process DM input, return NPC responses."""
        try:
            result = await self._app.ainvoke(Command(resume=dm_input), self._config)
            return await self._parse_result(result)
        except Exception as e:
            return TurnResult(
                turn_number=0,
                narrations=[],
                scene_image=None,
                turn_summary=None,
                is_complete=False,
                error=str(e),
            )

    async def _parse_result(self, result: dict) -> TurnResult:
        """Parse graph result - async for checkpointer access."""
        npcs = result.get("npcs", [])
        raw_narrations = result.get("narrations", [])
        turn_summary = result.get("turn_summary")
        scene_image = result.get("scene_image")

        # Log what we received
        logger.info(f"📊 Result keys: {list(result.keys())}")
        logger.info(f"🎭 Raw narrations: {len(raw_narrations)}")
        logger.info(f"🖼️ Scene image: {scene_image}")
        logger.info(
            f"📝 Turn summary: {turn_summary[:100] if turn_summary else '(none)'}..."
        )

        # Check if graph hit an interrupt AND we don't have actual narrations yet
        # (Initial state has no narrations, but after processing we do)
        if "__interrupt__" in result and not raw_narrations and not turn_summary:
            # Graph is waiting for input - return a waiting message
            location = result.get("location", "unknown location")
            npc_names = [n.get("name", "Unknown") for n in npcs] if npcs else []
            return TurnResult(
                turn_number=result.get("turn_number", 1),
                narrations=[
                    {
                        "npc": "System",
                        "text": f"Encounter at {location}. NPCs: {', '.join(npc_names) or 'none'}. Enter your narration.",
                    }
                ],
                scene_image=scene_image,
                turn_summary=None,
                is_complete=False,
            )

        # Check if graph is waiting (interrupted) - use async method
        state = await self._app.aget_state(self._config)
        is_complete = not (hasattr(state, "next") and state.next)

        # Transform narrations to expected format
        # Map nodes collect raw outputs, we need to pair with NPC names
        # Map nodes return dicts with {'_map_index': N, 'value': '...'}
        formatted_narrations = []

        # Only take one narration per NPC (map nodes may return multiple)
        seen_indices = set()
        for narration in raw_narrations:
            # Extract the actual text from map node output
            if isinstance(narration, dict):
                # Map node output format: {'_map_index': N, 'value': '...'}
                map_index = narration.get("_map_index", len(seen_indices))
                if map_index in seen_indices:
                    continue  # Skip duplicates
                seen_indices.add(map_index)

                # Get the text value
                text = (
                    narration.get("value")
                    or narration.get("text")
                    or narration.get("narration")
                    or str(narration)
                )
                npc_name = (
                    npcs[map_index].get("name", f"NPC {map_index + 1}")
                    if map_index < len(npcs)
                    else f"NPC {map_index + 1}"
                )
            elif isinstance(narration, str):
                npc_index = len(formatted_narrations)
                npc_name = (
                    npcs[npc_index].get("name", f"NPC {npc_index + 1}")
                    if npc_index < len(npcs)
                    else f"NPC {npc_index + 1}"
                )
                text = narration
            else:
                npc_index = len(formatted_narrations)
                npc_name = (
                    npcs[npc_index].get("name", f"NPC {npc_index + 1}")
                    if npc_index < len(npcs)
                    else f"NPC {npc_index + 1}"
                )
                text = str(narration)

            formatted_narrations.append({"npc": npc_name, "text": text})

        logger.info(
            f"✅ Formatted {len(formatted_narrations)} narrations: {[n['npc'] for n in formatted_narrations]}"
        )

        return TurnResult(
            turn_number=result.get("turn_number", 1),
            narrations=formatted_narrations,
            scene_image=result.get("scene_image"),
            turn_summary=result.get("turn_summary"),
            is_complete=is_complete,
        )


async def create_npcs_from_concepts(concepts: list[dict]) -> list[dict]:
    """Create NPCs using npc-creation.yaml graph.

    Args:
        concepts: List of NPC concept dicts with keys like:
            - concept: str (e.g., "a gruff dwarven bartender")
            - race: str (optional)
            - character_class: str (optional)
            - location: str (optional)

    Returns:
        List of created NPC dicts ready for encounter.
    """
    app = await get_npc_creation_graph()
    npcs = []

    for i, concept_data in enumerate(concepts):
        thread_id = f"npc-create-{i}-{id(concept_data)}"
        config = {"configurable": {"thread_id": thread_id}}

        try:
            result = await app.ainvoke(concept_data, config)

            # Extract NPC from result
            identity = result.get("identity", {})
            if hasattr(identity, "model_dump"):
                identity = identity.model_dump()

            personality = result.get("personality", {})
            if hasattr(personality, "model_dump"):
                personality = personality.model_dump()

            behavior = result.get("behavior", {})
            if hasattr(behavior, "model_dump"):
                behavior = behavior.model_dump()

            npc = {
                "name": identity.get("name", f"NPC {i + 1}"),
                "race": identity.get("race", concept_data.get("race", "Unknown")),
                "character_class": identity.get("character_class", ""),
                "appearance": identity.get("appearance", ""),
                "voice": identity.get("voice", ""),
                "personality": personality,
                "behavior": behavior,
                "goals": behavior.get("goals", []),
            }
            npcs.append(npc)
        except Exception as e:
            # Fallback: use concept as-is
            npcs.append(
                {
                    "name": f"NPC {i + 1}",
                    "race": concept_data.get("race", "Unknown"),
                    "character_class": concept_data.get("character_class", "Commoner"),
                    "appearance": concept_data.get("concept", "")[:100],
                    "error": str(e),
                }
            )

    return npcs
