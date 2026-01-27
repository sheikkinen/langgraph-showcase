"""Router pattern linter validations.

Validates router nodes follow YAMLGraph router pattern requirements:
- Routes must be dict (not list)
- Schema must use 'intent' or 'tone' field
- Default route recommended
- Conditional edges must target lists
"""

from pathlib import Path
from typing import Any

from yamlgraph.tools.linter_checks import LintIssue, load_graph


def check_router_node_structure(
    node_name: str, node_config: dict[str, Any]
) -> list[LintIssue]:
    """Check router node structural requirements.

    Args:
        node_name: Name of the router node
        node_config: Node configuration dict

    Returns:
        List of validation issues
    """
    issues = []

    # E101: routes must be dict, not list
    routes = node_config.get("routes")
    if routes is not None:
        if isinstance(routes, list):
            issues.append(
                LintIssue(
                    severity="error",
                    code="E101",
                    message=f"Router node '{node_name}' has routes as list; must be dict",
                    fix="Change routes to dict mapping: {'route_name': 'target_node'}",
                )
            )
        elif not isinstance(routes, dict):
            issues.append(
                LintIssue(
                    severity="error",
                    code="E101",
                    message=f"Router node '{node_name}' routes must be dict, got {type(routes).__name__}",
                    fix="Routes should be: {'positive': 'handle_positive', 'negative': 'handle_negative'}",
                )
            )

    # W101: missing default_route
    if "default_route" not in node_config:
        issues.append(
            LintIssue(
                severity="warning",
                code="W101",
                message=f"Router node '{node_name}' missing default_route field",
                fix="Add default_route: 'fallback_node' for unhandled classifications",
            )
        )

    return issues


def check_router_schema_fields(
    node_name: str,
    node_config: dict[str, Any],
    graph_path: Path,
    project_root: Path | None = None,
) -> list[LintIssue]:
    """Check router prompt schema uses required field names.

    Router framework hardcodes requirement for 'intent' or 'tone' field.

    Args:
        node_name: Name of the router node
        node_config: Node configuration dict
        graph_path: Path to the graph file
        project_root: Project root directory

    Returns:
        List of validation issues
    """
    issues = []
    prompt_name = node_config.get("prompt")

    if not prompt_name:
        return issues

    # Resolve prompt file path
    import yaml

    from yamlgraph.tools.linter_checks import get_prompt_path, resolve_prompts_dir

    graph = load_graph(graph_path)
    prompts_dir = resolve_prompts_dir(
        graph, graph_path, project_root or graph_path.parent
    )
    prompt_path = get_prompt_path(prompt_name, prompts_dir)

    if not prompt_path.exists():
        return issues  # Let existing prompt file check handle this

    try:
        with open(prompt_path) as f:
            prompt_data = yaml.safe_load(f) or {}

        schema = prompt_data.get("schema", {})
        fields = schema.get("fields", {})

        # E102: Must have 'intent' or 'tone' field (framework hardcoded requirement)
        if "intent" not in fields and "tone" not in fields:
            available_fields = list(fields.keys())
            issues.append(
                LintIssue(
                    severity="error",
                    code="E102",
                    message=f"Router node '{node_name}' prompt schema missing 'intent' or 'tone' field",
                    fix=f"Add 'intent' field to schema (available: {available_fields}). Framework requires 'intent' or 'tone' for routing.",
                )
            )

    except (yaml.YAMLError, OSError):
        # Don't add additional errors if file can't be parsed
        pass

    return issues


def check_router_edge_targets(node_name: str, graph: dict[str, Any]) -> list[LintIssue]:
    """Check that conditional edges targeting router use list format.

    Args:
        node_name: Name of the router node
        graph: Full graph configuration

    Returns:
        List of validation issues
    """
    issues = []
    edges = graph.get("edges", [])

    for i, edge in enumerate(edges):
        to_node = edge.get("to")

        # Check conditional edges targeting this router
        if (
            to_node == node_name
            and edge.get("condition")
            and not isinstance(to_node, list)
        ):
            issues.append(
                LintIssue(
                    severity="error",
                    code="E103",
                    message=f"Conditional edge {i + 1} targets router '{node_name}' with single node",
                    fix=f"Change 'to' to list: [{node_name}] for conditional router edges",
                )
            )

    return issues


def check_router_patterns(
    graph_path: Path, project_root: Path | None = None
) -> list[LintIssue]:
    """Validate all router nodes in the graph follow pattern requirements.

    Args:
        graph_path: Path to the graph YAML file
        project_root: Project root directory for prompt resolution

    Returns:
        List of all router-related validation issues
    """
    issues = []
    graph = load_graph(graph_path)

    for node_name, node_config in graph.get("nodes", {}).items():
        if node_config.get("type") == "router":
            # Check node structure
            issues.extend(check_router_node_structure(node_name, node_config))

            # Check schema fields
            issues.extend(
                check_router_schema_fields(
                    node_name, node_config, graph_path, project_root
                )
            )

            # Check edge targets
            issues.extend(check_router_edge_targets(node_name, graph))

    return issues


__all__ = [
    "check_router_patterns",
    "check_router_node_structure",
    "check_router_schema_fields",
    "check_router_edge_targets",
]
