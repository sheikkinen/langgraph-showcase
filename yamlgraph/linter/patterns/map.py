"""Map pattern linter validations.

Validates map nodes follow YAMLGraph map pattern requirements:
- Required fields: over, as, node, collect
- No top-level prompt (only in nested node)
- 'over' should resolve to list type
"""

from pathlib import Path
from typing import Any

from yamlgraph.linter.checks import LintIssue, load_graph


def check_map_node_structure(
    node_name: str, node_config: dict[str, Any]
) -> list[LintIssue]:
    """Check map node structural requirements.

    Args:
        node_name: Name of the map node
        node_config: Node configuration dict

    Returns:
        List of validation issues
    """
    issues = []

    # E201: missing required field 'over'
    if "over" not in node_config:
        issues.append(
            LintIssue(
                severity="error",
                code="E201",
                message=f"Map node '{node_name}' missing required field 'over'",
                fix="Add 'over' field: over: \"{state.list_field}\" to specify list to iterate over",
            )
        )

    # E202: missing required field 'as'
    if "as" not in node_config:
        issues.append(
            LintIssue(
                severity="error",
                code="E202",
                message=f"Map node '{node_name}' missing required field 'as'",
                fix="Add 'as' field: as: item_name to specify variable name for each item",
            )
        )

    # E203: missing required field 'node' (nested sub-node)
    if "node" not in node_config:
        issues.append(
            LintIssue(
                severity="error",
                code="E203",
                message=f"Map node '{node_name}' missing required field 'node'",
                fix="Add nested 'node' field with prompt and state_key for processing each item",
            )
        )

    # E204: missing required field 'collect'
    if "collect" not in node_config:
        issues.append(
            LintIssue(
                severity="error",
                code="E204",
                message=f"Map node '{node_name}' missing required field 'collect'",
                fix="Add 'collect' field: collect: results to specify where to store collected results",
            )
        )

    # E205: should NOT have 'prompt' at top level (only in nested node)
    if "prompt" in node_config:
        issues.append(
            LintIssue(
                severity="error",
                code="E205",
                message=f"Map node '{node_name}' should not have top-level 'prompt' field",
                fix="Move 'prompt' field into nested 'node' configuration",
            )
        )

    return issues


def check_map_node_types(
    node_name: str, node_config: dict[str, Any]
) -> list[LintIssue]:
    """Check map node field types and values.

    Args:
        node_name: Name of the map node
        node_config: Node configuration dict

    Returns:
        List of validation issues
    """
    issues = []

    # W201: 'over' expression should look like it resolves to list type
    over_value = node_config.get("over")
    if (
        over_value
        and isinstance(over_value, str)
        and not (over_value.startswith("{state.") and over_value.endswith("}"))
    ):
        issues.append(
            LintIssue(
                severity="warning",
                code="W201",
                message=f"Map node '{node_name}' 'over' field should reference state list",
                fix='Use state reference: over: "{state.list_field}"',
            )
        )

    # Check nested node structure if present
    nested_node = node_config.get("node")
    if (
        nested_node
        and isinstance(nested_node, dict)
        and "prompt" not in nested_node
        and "type" not in nested_node
    ):
        issues.append(
            LintIssue(
                severity="warning",
                code="W202",
                message=f"Map node '{node_name}' nested node missing prompt or type",
                fix="Add 'prompt' field to nested node for LLM processing",
            )
        )

    return issues


def check_map_patterns(
    graph_path: Path, project_root: Path | None = None
) -> list[LintIssue]:
    """Validate all map nodes in the graph follow pattern requirements.

    Args:
        graph_path: Path to the graph YAML file
        project_root: Project root directory for prompt resolution

    Returns:
        List of all map-related validation issues
    """
    issues = []
    graph = load_graph(graph_path)

    for node_name, node_config in graph.get("nodes", {}).items():
        if node_config.get("type") == "map":
            # Check node structure
            issues.extend(check_map_node_structure(node_name, node_config))

            # Check field types and values
            issues.extend(check_map_node_types(node_name, node_config))

    return issues


__all__ = [
    "check_map_patterns",
    "check_map_node_structure",
    "check_map_node_types",
]
