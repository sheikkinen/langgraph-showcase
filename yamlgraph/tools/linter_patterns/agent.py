"""Agent pattern linter validations.

Validates agent nodes follow YAMLGraph agent pattern requirements:
- Agent nodes should have tools (warning if missing)
- Agent tools must reference defined tools or built-in tools
"""

from pathlib import Path
from typing import Any

from yamlgraph.tools.linter_checks import LintIssue, load_graph


def check_agent_node_tools(
    node_name: str, node_config: dict[str, Any], graph: dict[str, Any]
) -> list[LintIssue]:
    """Check agent node tool requirements.

    Args:
        node_name: Name of the agent node
        node_config: Node configuration dict
        graph: Full graph configuration

    Returns:
        List of validation issues
    """
    issues = []

    # Get defined tools from graph
    defined_tools = set(graph.get("tools", {}).keys())

    # Built-in tools that don't need to be defined in tools section
    BUILT_IN_TOOLS = {"websearch"}

    # W401: Agent node with no tools (warning)
    node_tools = node_config.get("tools", [])
    if not node_tools:
        issues.append(
            LintIssue(
                severity="warning",
                code="W401",
                message=f"Agent node '{node_name}' has no tools configured",
                fix="Add 'tools' field with list of tool names: tools: [tool1, tool2]",
            )
        )

    # E401: Agent node tools must reference defined tools or built-in tools
    for tool in node_tools:
        if tool not in defined_tools and tool not in BUILT_IN_TOOLS:
            available_tools = sorted(defined_tools | BUILT_IN_TOOLS)
            issues.append(
                LintIssue(
                    severity="error",
                    code="E401",
                    message=f"Agent node '{node_name}' references undefined tool '{tool}'",
                    fix=f"Define tool '{tool}' in tools section or use one of: {available_tools}",
                )
            )

    return issues


def check_agent_patterns(
    graph_path: Path, project_root: Path | None = None
) -> list[LintIssue]:
    """Validate all agent nodes in the graph follow pattern requirements.

    Args:
        graph_path: Path to the graph YAML file
        project_root: Project root directory for prompt resolution

    Returns:
        List of all agent-related validation issues
    """
    issues = []
    graph = load_graph(graph_path)

    for node_name, node_config in graph.get("nodes", {}).items():
        if node_config.get("type") == "agent":
            # Check agent tool requirements
            issues.extend(check_agent_node_tools(node_name, node_config, graph))

    return issues


__all__ = [
    "check_agent_patterns",
    "check_agent_node_tools",
]
