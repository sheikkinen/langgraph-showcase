"""Subgraph pattern linter validations.

Validates subgraph nodes follow YAMLGraph subgraph pattern requirements:
- Subgraph nodes must have 'graph' field pointing to existing file
- Subgraph nodes should have input_mapping and output_mapping (warnings)
"""

from pathlib import Path
from typing import Any

from yamlgraph.tools.linter_checks import LintIssue, load_graph


def check_subgraph_node_requirements(
    node_name: str,
    node_config: dict[str, Any],
    graph_path: Path,
    project_root: Path | None = None,
) -> list[LintIssue]:
    """Check subgraph node requirements.

    Args:
        node_name: Name of the subgraph node
        node_config: Node configuration dict
        graph_path: Path to the graph file for relative path resolution
        project_root: Project root directory

    Returns:
        List of validation issues
    """
    issues = []

    # E501: Subgraph node missing 'graph' field
    graph_field = node_config.get("graph")
    if not graph_field:
        issues.append(
            LintIssue(
                severity="error",
                code="E501",
                message=f"Subgraph node '{node_name}' missing required 'graph' field",
                fix="Add 'graph' field: graph: subgraphs/subgraph_name.yaml",
            )
        )
        return issues  # Can't check file existence without graph field

    # E502: Subgraph file path does not exist
    # Resolve relative to the graph file's directory or project root
    graph_dir = graph_path.parent
    subgraph_path = graph_dir / graph_field

    # If not found relative to graph file, try relative to project root
    if not subgraph_path.exists() and project_root:
        subgraph_path = project_root / graph_field

    if not subgraph_path.exists():
        issues.append(
            LintIssue(
                severity="error",
                code="E502",
                message=f"Subgraph node '{node_name}' references non-existent graph file '{graph_field}'",
                fix=f"Create subgraph file at '{graph_field}' or fix the path",
            )
        )

    # W501: Subgraph node missing input_mapping
    if "input_mapping" not in node_config:
        issues.append(
            LintIssue(
                severity="warning",
                code="W501",
                message=f"Subgraph node '{node_name}' missing input_mapping",
                fix="Add input_mapping to pass data to subgraph: input_mapping: {parent_key: subgraph_key}",
            )
        )

    # W502: Subgraph node missing output_mapping
    if "output_mapping" not in node_config:
        issues.append(
            LintIssue(
                severity="warning",
                code="W502",
                message=f"Subgraph node '{node_name}' missing output_mapping",
                fix="Add output_mapping to receive data from subgraph: output_mapping: {parent_key: subgraph_key}",
            )
        )

    return issues


def check_subgraph_patterns(
    graph_path: Path, project_root: Path | None = None
) -> list[LintIssue]:
    """Validate all subgraph nodes in the graph follow pattern requirements.

    Args:
        graph_path: Path to the graph YAML file
        project_root: Project root directory for path resolution

    Returns:
        List of all subgraph-related validation issues
    """
    issues = []
    graph = load_graph(graph_path)

    for node_name, node_config in graph.get("nodes", {}).items():
        if node_config.get("type") == "subgraph":
            # Check subgraph requirements
            issues.extend(
                check_subgraph_node_requirements(
                    node_name, node_config, graph_path, project_root
                )
            )

    return issues


__all__ = [
    "check_subgraph_patterns",
    "check_subgraph_node_requirements",
]
