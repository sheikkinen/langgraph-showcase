"""Dynamic state class generation from graph configuration.

Builds TypedDict programmatically from YAML graph config, eliminating
the need for state_class coupling between YAML and Python.
"""

import logging
from operator import add
from typing import Annotated, Any, TypedDict

logger = logging.getLogger(__name__)


def last_value(_existing: Any, new: Any) -> Any:
    """Reducer that keeps the last written value (last-write-wins).

    Safe for concurrent fan-in: when multiple parallel nodes write to
    the same key, LangGraph calls the reducer instead of raising
    INVALID_CONCURRENT_GRAPH_UPDATE.

    Args:
        _existing: Previous value (ignored)
        new: New value to store

    Returns:
        The new value
    """
    return new


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
    # Core tracking (last_value reducer: safe for parallel fan-in)
    "thread_id": str,
    "current_step": Annotated[str, last_value],
    # Error handling (two patterns by design):
    # - "error" (singular): Current/last error, simple overwrite semantics
    # - "errors" (plural): Accumulated PipelineError list via add reducer
    # Note: Tool results use nested {"error": ...} which is a different pattern
    "error": Annotated[Any, last_value],
    "errors": Annotated[list, add],
    # Messages with reducer (accumulates)
    "messages": Annotated[list, add],
    # Loop tracking (last_value: safe for parallel fan-in)
    "_loop_counts": Annotated[dict, last_value],
    "_loop_limit_reached": Annotated[bool, last_value],
    "_agent_iterations": Annotated[int, last_value],
    "_agent_limit_reached": Annotated[bool, last_value],
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
            normalized = type_spec.lower()
            if normalized not in TYPE_MAP:
                supported = ", ".join(sorted(set(TYPE_MAP.keys())))
                logger.warning(
                    f"Unknown type '{type_spec}' for state field '{field_name}'. "
                    f"Supported types: {supported}. Defaulting to Any."
                )
            python_type = TYPE_MAP.get(normalized, Any)
            fields[field_name] = python_type
        else:
            # Unknown format, use Any
            logger.warning(
                f"Invalid type specification for state field '{field_name}': "
                f"expected string, got {type(type_spec).__name__}. Defaulting to Any."
            )
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
    - FR-021: Fields from data_files directive

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

    # FR-021: Add fields from data_files directive
    # Each data_files key becomes a state field of type Any
    data_files = config.get("data_files", {})
    for key in data_files:
        fields[key] = Any

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

    for _node_name, node_config in nodes.items():
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


# =============================================================================
# TypedDict Code Generation (FR-008)
# =============================================================================

# Type mapping for code generation (YAML type -> Python type string)
CODEGEN_TYPE_MAP: dict[str, str] = {
    "str": "str",
    "string": "str",
    "int": "int",
    "integer": "int",
    "float": "float",
    "bool": "bool",
    "boolean": "bool",
    "list": "list",
    "dict": "dict",
    "any": "Any",
}


def _normalize_class_name(name: str) -> str:
    """Convert graph name to PascalCase class name.

    Examples:
        "interview" -> "Interview"
        "my-awesome-graph" -> "MyAwesomeGraph"
        "web_research" -> "WebResearch"
    """
    # Replace hyphens and underscores with spaces, then title-case
    normalized = name.replace("-", " ").replace("_", " ")
    return "".join(word.capitalize() for word in normalized.split())


def generate_typeddict_code(
    config: dict,
    source_path: str | None = None,
    include_base_fields: bool = False,
) -> str:
    """Generate TypedDict Python code from graph configuration.

    Args:
        config: Parsed YAML graph configuration dict
        source_path: Optional source file path for generation comment
        include_base_fields: Include infrastructure fields (thread_id, etc.)

    Returns:
        Python source code string defining the TypedDict
    """
    # Determine class name
    graph_name = config.get("name", "Graph")
    class_name = _normalize_class_name(graph_name) + "State"

    # Collect fields (custom state + node state_keys)
    fields: dict[str, str] = {}

    # Add base fields if requested
    if include_base_fields:
        fields["thread_id"] = "str"
        fields["current_step"] = "str"
        fields["error"] = "Any"
        fields["errors"] = "list"
        fields["messages"] = "list"
        fields["_loop_counts"] = "dict"
        fields["_loop_limit_reached"] = "bool"
        fields["_agent_iterations"] = "int"
        fields["_agent_limit_reached"] = "bool"
        fields["started_at"] = "Any"
        fields["completed_at"] = "Any"

    # Parse custom state fields
    state_config = config.get("state", {})
    for field_name, type_spec in state_config.items():
        if isinstance(type_spec, str):
            python_type = CODEGEN_TYPE_MAP.get(type_spec.lower(), "Any")
            fields[field_name] = python_type

    # Extract fields from nodes
    nodes = config.get("nodes", {})
    for node_config in nodes.values():
        if not isinstance(node_config, dict):
            continue

        # state_key → Any
        if state_key := node_config.get("state_key"):
            fields[state_key] = "Any"

        # Node type-specific fields
        node_type = node_config.get("type", "llm")
        if node_type == "agent":
            fields["input"] = "str"
            fields["_tool_results"] = "list"
        elif node_type == "router":
            fields["_route"] = "str"
        elif node_type == "map":
            if collect_key := node_config.get("collect"):
                fields[collect_key] = "list"

    # Generate code
    lines = []

    # Header comment
    if source_path:
        lines.append(f"# Auto-generated by yamlgraph codegen from {source_path}")
    else:
        lines.append("# Auto-generated by yamlgraph codegen")
    lines.append(
        "# Do not edit manually - regenerate with: yamlgraph codegen <graph.yaml>"
    )
    lines.append("")

    # Imports
    lines.append("from typing import Any, TypedDict")
    lines.append("")
    lines.append("")

    # Class definition
    lines.append(f"class {class_name}(TypedDict, total=False):")
    lines.append(f'    """State for {graph_name} graph."""')
    lines.append("")

    # Fields
    if fields:
        for field_name, field_type in sorted(fields.items()):
            lines.append(f"    {field_name}: {field_type}")
    else:
        lines.append("    pass")

    lines.append("")
    return "\n".join(lines)
