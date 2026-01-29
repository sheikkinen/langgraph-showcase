"""Interrupt pattern linter validations.

Validates interrupt nodes follow YAMLGraph interrupt pattern requirements:
- Required resume_key field for storing user input
- Either prompt or message field (not both)
- Graph must have checkpointer configuration
- state_key should be declared in state section
"""

from pathlib import Path
from typing import Any

from yamlgraph.linter.checks import LintIssue, load_graph


def check_interrupt_node_structure(
    node_name: str, node_config: dict[str, Any]
) -> list[LintIssue]:
    """Check interrupt node structural requirements.

    Args:
        node_name: Name of the interrupt node
        node_config: Node configuration dict

    Returns:
        List of validation issues
    """
    issues = []

    # E301: missing required field 'resume_key'
    if "resume_key" not in node_config:
        issues.append(
            LintIssue(
                severity="error",
                code="E301",
                message=f"Interrupt node '{node_name}' missing required field 'resume_key'",
                fix="Add 'resume_key' field: resume_key: user_input_variable to store user response",
            )
        )

    # E302: must have either 'prompt' or 'message' field
    has_prompt = "prompt" in node_config
    has_message = "message" in node_config

    if not has_prompt and not has_message:
        issues.append(
            LintIssue(
                severity="error",
                code="E302",
                message=f"Interrupt node '{node_name}' missing 'prompt' or 'message' field",
                fix="Add either 'prompt' field (for LLM-generated question) or 'message' field (for static text)",
            )
        )
    elif has_prompt and has_message:
        issues.append(
            LintIssue(
                severity="warning",
                code="W302",
                message=f"Interrupt node '{node_name}' has both 'prompt' and 'message' fields",
                fix="Use either 'prompt' (dynamic) or 'message' (static), not both",
            )
        )

    return issues


def check_interrupt_state_declarations(
    node_name: str, node_config: dict[str, Any], graph: dict[str, Any]
) -> list[LintIssue]:
    """Check that interrupt node state_key is declared in state section.

    Args:
        node_name: Name of the interrupt node
        node_config: Node configuration dict
        graph: Full graph configuration

    Returns:
        List of validation issues
    """
    issues = []

    # E303: state_key should be declared in state section
    state_key = node_config.get("state_key")
    if state_key:
        state_declarations = graph.get("state", {})
        if state_key not in state_declarations:
            issues.append(
                LintIssue(
                    severity="error",
                    code="E303",
                    message=f"Interrupt node '{node_name}' state_key '{state_key}' not declared in state section",
                    fix=f"Add '{state_key}' to state section: state: {state_key}: str",
                )
            )

    # Also check resume_key is declared
    resume_key = node_config.get("resume_key")
    if resume_key and resume_key not in graph.get("state", {}):
        issues.append(
            LintIssue(
                severity="error",
                code="E303",
                message=f"Interrupt node '{node_name}' resume_key '{resume_key}' not declared in state section",
                fix=f"Add '{resume_key}' to state section: state: {resume_key}: str",
            )
        )

    return issues


def check_interrupt_checkpointer(graph: dict[str, Any]) -> list[LintIssue]:
    """Check that graph with interrupt nodes has checkpointer configuration.

    Args:
        graph: Full graph configuration

    Returns:
        List of validation issues
    """
    issues = []

    # Check if graph has any interrupt nodes
    has_interrupt_nodes = any(
        node_config.get("type") == "interrupt"
        for node_config in graph.get("nodes", {}).values()
    )

    if has_interrupt_nodes:
        # W301: Graph with interrupt nodes should have checkpointer
        checkpointer = graph.get("checkpointer")
        if not checkpointer:
            issues.append(
                LintIssue(
                    severity="warning",
                    code="W301",
                    message="Graph with interrupt nodes missing checkpointer configuration",
                    fix="Add checkpointer section: checkpointer: {type: memory} or {type: sqlite, path: 'checkpoints.db'}",
                )
            )
        elif not isinstance(checkpointer, dict):
            issues.append(
                LintIssue(
                    severity="error",
                    code="E304",
                    message="Graph checkpointer must be a dict configuration",
                    fix="Use proper checkpointer format: checkpointer: {type: memory}",
                )
            )
        elif "type" not in checkpointer:
            issues.append(
                LintIssue(
                    severity="error",
                    code="E304",
                    message="Graph checkpointer missing required 'type' field",
                    fix="Add type to checkpointer: checkpointer: {type: memory}",
                )
            )

    return issues


def check_interrupt_patterns(
    graph_path: Path, project_root: Path | None = None
) -> list[LintIssue]:
    """Validate all interrupt nodes in the graph follow pattern requirements.

    Args:
        graph_path: Path to the graph YAML file
        project_root: Project root directory for prompt resolution

    Returns:
        List of all interrupt-related validation issues
    """
    issues = []
    graph = load_graph(graph_path)

    # Check graph-level requirements (checkpointer)
    issues.extend(check_interrupt_checkpointer(graph))

    # Check each interrupt node
    for node_name, node_config in graph.get("nodes", {}).items():
        if node_config.get("type") == "interrupt":
            # Check node structure
            issues.extend(check_interrupt_node_structure(node_name, node_config))

            # Check state declarations
            issues.extend(
                check_interrupt_state_declarations(node_name, node_config, graph)
            )

    return issues


__all__ = [
    "check_interrupt_patterns",
    "check_interrupt_node_structure",
    "check_interrupt_state_declarations",
    "check_interrupt_checkpointer",
]
