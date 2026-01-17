"""Dynamic state class generation from graph configuration.

Builds TypedDict programmatically from YAML graph config, eliminating
the need for state_class coupling between YAML and Python.
"""

from operator import add
from typing import Annotated, Any, TypedDict


def sorted_add(existing: list, new: list) -> list:
    """Reducer that adds items and sorts by _map_index if present.

    Used for map node fan-in to guarantee order regardless of
    parallel execution timing.

    Args:
        existing: Current list in state
        new: New items to add

    Returns:
        Combined list sorted by _map_index (if items have it)
    """
    combined = (existing or []) + (new or [])

    # Sort by _map_index if items have it
    if combined and isinstance(combined[0], dict) and "_map_index" in combined[0]:
        combined = sorted(combined, key=lambda x: x.get("_map_index", 0))

    return combined


# =============================================================================
# Base Fields - Always included in generated state
# =============================================================================

# Infrastructure fields present in all graphs
BASE_FIELDS: dict[str, type] = {
    # Core tracking
    "thread_id": str,
    "current_step": str,
    # Error handling - singular for current error
    "error": Any,
    # Error handling with reducer (accumulates)
    "errors": Annotated[list, add],
    # Messages with reducer (accumulates)
    "messages": Annotated[list, add],
    # Loop tracking
    "_loop_counts": dict,
    "_loop_limit_reached": bool,
    "_agent_iterations": int,
    "_agent_limit_reached": bool,
    # Timestamps
    "started_at": Any,
    "completed_at": Any,
}

# Common input fields used across graph types
# These are always included to support --var inputs
COMMON_INPUT_FIELDS: dict[str, type] = {
    "input": str,  # Agent prompt input
    "topic": str,  # Content generation topic
    "style": str,  # Writing style
    "word_count": int,  # Target word count
    "message": str,  # Router message input
}

# Type mapping for YAML state config
TYPE_MAP: dict[str, type] = {
    "str": str,
    "string": str,
    "int": int,
    "integer": int,
    "float": float,
    "bool": bool,
    "boolean": bool,
    "list": list,
    "dict": dict,
    "any": Any,
}


def parse_state_config(state_config: dict) -> dict[str, type]:
    """Parse YAML state section into field types.

    Supports simple type strings:
        state:
          concept: str
          count: int

    Args:
        state_config: Dict from YAML 'state' section

    Returns:
        Dict of field_name -> Python type
    """
    fields: dict[str, type] = {}

    for field_name, type_spec in state_config.items():
        if isinstance(type_spec, str):
            # Simple type: "str", "int", etc.
            python_type = TYPE_MAP.get(type_spec.lower(), Any)
            fields[field_name] = python_type
        else:
            # Unknown format, use Any
            fields[field_name] = Any

    return fields


def build_state_class(config: dict) -> type:
    """Build TypedDict state class from graph configuration.

    Dynamically generates a TypedDict with:
    - Base infrastructure fields (errors, messages, thread_id, etc.)
    - Common input fields (topic, style, input, message, etc.)
    - Custom fields from YAML 'state' section
    - Fields extracted from node state_key
    - Special fields for agent/router node types

    Args:
        config: Parsed YAML graph configuration dict

    Returns:
        TypedDict class with total=False (all fields optional)
    """
    # Start with base and common fields
    fields: dict[str, type] = {}
    fields.update(BASE_FIELDS)
    fields.update(COMMON_INPUT_FIELDS)

    # Add custom state fields from YAML 'state' section
    state_config = config.get("state", {})
    custom_fields = parse_state_config(state_config)
    fields.update(custom_fields)

    # Extract fields from nodes
    nodes = config.get("nodes", {})
    node_fields = extract_node_fields(nodes)
    fields.update(node_fields)

    # Build TypedDict programmatically
    return TypedDict("GraphState", fields, total=False)


def extract_node_fields(nodes: dict) -> dict[str, type]:
    """Extract state fields from node configurations.

    Analyzes node configs to determine required state fields:
    - state_key: Where node stores its output
    - type: agent → adds input, _tool_results
    - type: router → adds _route

    Args:
        nodes: Dict of node_name -> node_config

    Returns:
        Dict of field_name -> type for the state
    """
    fields: dict[str, type] = {}

    for node_name, node_config in nodes.items():
        if not isinstance(node_config, dict):
            continue

        # state_key → Any (accepts Pydantic models)
        if state_key := node_config.get("state_key"):
            fields[state_key] = Any

        # Node type-specific fields
        node_type = node_config.get("type", "llm")

        if node_type == "agent":
            fields["input"] = str
            fields["_tool_results"] = list

        elif node_type == "router":
            fields["_route"] = str

        elif node_type == "map":
            # Map node collect field needs sorted reducer for ordered fan-in
            if collect_key := node_config.get("collect"):
                fields[collect_key] = Annotated[list, sorted_add]

    return fields


def create_initial_state(
    topic: str = "",
    style: str = "informative",
    word_count: int = 300,
    thread_id: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create an initial state for a new pipeline run.

    Args:
        topic: The topic to generate content about
        style: Writing style (default: informative)
        word_count: Target word count (default: 300)
        thread_id: Optional thread ID (auto-generated if not provided)
        **kwargs: Additional state fields (e.g., input for agents)

    Returns:
        Initialized state dictionary
    """
    import uuid
    from datetime import datetime

    return {
        "thread_id": thread_id or uuid.uuid4().hex[:16],
        "topic": topic,
        "style": style,
        "word_count": word_count,
        "current_step": "init",
        "error": None,
        "errors": [],
        "messages": [],
        "started_at": datetime.now(),
        "completed_at": None,
        **kwargs,
    }
