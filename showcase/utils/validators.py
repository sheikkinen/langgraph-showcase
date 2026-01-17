"""Graph configuration validators.

Validation functions for YAML graph configuration structures.
"""

from typing import Any

from showcase.constants import ErrorHandler, NodeType


def validate_required_sections(config: dict[str, Any]) -> None:
    """Validate required top-level sections exist.

    Args:
        config: Parsed YAML configuration dictionary

    Raises:
        ValueError: If required sections are missing
    """
    if not config.get("nodes"):
        raise ValueError("Graph config missing required 'nodes' section")
    if not config.get("edges"):
        raise ValueError("Graph config missing required 'edges' section")


def validate_node_prompt(node_name: str, node_config: dict[str, Any]) -> None:
    """Validate node has required prompt if applicable.

    Args:
        node_name: Name of the node
        node_config: Node configuration dictionary

    Raises:
        ValueError: If prompt is required but missing
    """
    node_type = node_config.get("type", NodeType.LLM)
    # Only llm and router nodes require prompts
    # tool, python, agent, and map nodes don't require prompts
    if NodeType.requires_prompt(node_type) and not node_config.get("prompt"):
        raise ValueError(f"Node '{node_name}' missing required 'prompt' field")


def validate_router_node(
    node_name: str, node_config: dict[str, Any], all_nodes: dict[str, Any]
) -> None:
    """Validate router node has routes pointing to valid nodes.

    Args:
        node_name: Name of the node
        node_config: Node configuration dictionary
        all_nodes: All nodes in the graph for target validation

    Raises:
        ValueError: If router configuration is invalid
    """
    if node_config.get("type") != NodeType.ROUTER:
        return

    if not node_config.get("routes"):
        raise ValueError(f"Router node '{node_name}' missing required 'routes' field")

    for route_key, target_node in node_config["routes"].items():
        if target_node not in all_nodes:
            raise ValueError(
                f"Router node '{node_name}' route '{route_key}' points to "
                f"nonexistent node '{target_node}'"
            )


def validate_edges(edges: list[dict[str, Any]]) -> None:
    """Validate each edge has required from/to fields.

    Args:
        edges: List of edge configurations

    Raises:
        ValueError: If edge is missing required fields
    """
    for i, edge in enumerate(edges):
        if "from" not in edge:
            raise ValueError(f"Edge {i} missing required 'from' field")
        if "to" not in edge:
            raise ValueError(f"Edge {i} missing required 'to' field")

        # Validate condition expressions at load time
        if "condition" in edge:
            validate_condition_expression(edge["condition"], i)


def validate_condition_expression(condition: str, edge_index: int) -> None:
    """Validate a condition expression has valid syntax.

    Performs compile-time validation of condition expressions to catch
    syntax errors early rather than at runtime.

    Supports expression conditions like "score < 0.8", "a.b >= 1 and c == 'done'"

    Args:
        condition: Condition expression like "score < 0.8"
        edge_index: Edge index for error messages

    Raises:
        ValueError: If condition has invalid syntax
    """
    import re

    # Expression syntax check - must match comparison pattern
    # Valid: "score < 0.8", "a.b >= 1", "x == 'done'"
    # Also valid: compound expressions "a > 1 and b < 2"
    comparison_pattern = r"[a-zA-Z_][\w.]*\s*(<=|>=|==|!=|<|>)\s*.+"
    compound_pattern = r"\s+(and|or)\s+"

    # Split by and/or and validate each part
    parts = re.split(compound_pattern, condition, flags=re.IGNORECASE)
    # parts includes the 'and'/'or' tokens, so filter to just comparisons
    comparisons = [p.strip() for p in parts if p.strip().lower() not in ("and", "or")]

    for part in comparisons:
        if not re.match(comparison_pattern, part.strip()):
            raise ValueError(
                f"Edge {edge_index} has invalid condition syntax: '{condition}'. "
                f"Expected format: 'field <op> value' (e.g., 'score < 0.8')"
            )


def validate_on_error(node_name: str, node_config: dict[str, Any]) -> None:
    """Validate on_error value is valid.

    Args:
        node_name: Name of the node
        node_config: Node configuration dictionary

    Raises:
        ValueError: If on_error value is invalid
    """
    on_error = node_config.get("on_error")
    if on_error and on_error not in ErrorHandler.all_values():
        raise ValueError(
            f"Node '{node_name}' has invalid on_error value '{on_error}'. "
            f"Valid values: {', '.join(ErrorHandler.all_values())}"
        )


def validate_map_node(node_name: str, node_config: dict[str, Any]) -> None:
    """Validate map node has required fields.

    Args:
        node_name: Name of the node
        node_config: Node configuration dictionary

    Raises:
        ValueError: If map node configuration is invalid
    """
    if node_config.get("type") != NodeType.MAP:
        return

    required_fields = ["over", "as", "node", "collect"]
    for field in required_fields:
        if field not in node_config:
            raise ValueError(f"Map node '{node_name}' missing required '{field}' field")


def validate_config(config: dict[str, Any]) -> None:
    """Validate YAML configuration structure.

    Args:
        config: Parsed YAML dictionary

    Raises:
        ValueError: If required fields are missing or invalid
    """
    validate_required_sections(config)

    nodes = config["nodes"]
    for node_name, node_config in nodes.items():
        validate_node_prompt(node_name, node_config)
        validate_router_node(node_name, node_config, nodes)
        validate_on_error(node_name, node_config)
        validate_map_node(node_name, node_config)

    validate_edges(config["edges"])
