"""Graph linter for validating YAML graph files.

Checks for common issues:
- Missing state declarations
- Undefined tool references
- Missing prompt files
- Unreachable nodes
- Invalid node types
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Valid node types
VALID_NODE_TYPES = {
    "agent",
    "interrupt",
    "llm",
    "map",
    "passthrough",
    "python",
    "router",
    "subgraph",
}

# Built-in state fields that don't need declaration
BUILTIN_STATE_FIELDS = {
    "thread_id",
    "current_step",
    "error",
    "errors",
    "messages",
    "_loop_counts",
    "_loop_limit_reached",
    "_agent_iterations",
    "_agent_limit_reached",
    "started_at",
    "completed_at",
}


class LintIssue(BaseModel):
    """A single lint issue found in the graph."""

    severity: str  # "error", "warning", "info"
    code: str  # e.g., "E001", "W002"
    message: str
    line: int | None = None
    fix: str | None = None


class LintResult(BaseModel):
    """Result of linting a graph file."""

    file: str
    issues: list[LintIssue]
    valid: bool


def _load_graph(graph_path: Path) -> dict[str, Any]:
    """Load and parse a YAML graph file."""
    with open(graph_path) as f:
        return yaml.safe_load(f) or {}


def _extract_variables(text: str) -> set[str]:
    """Extract {variable} placeholders from text.

    Ignores escaped {{variable}} (doubled braces).
    """
    # Find all {word} patterns but not {{word}}
    # First, temporarily replace {{ and }} to protect them
    protected = text.replace("{{", "\x00").replace("}}", "\x01")
    matches = re.findall(r"\{(\w+)\}", protected)
    return set(matches)


def _get_prompt_path(prompt_name: str, prompts_dir: Path) -> Path:
    """Get the full path to a prompt file."""
    return prompts_dir / f"{prompt_name}.yaml"


def _resolve_prompts_dir(graph: dict, graph_path: Path, project_root: Path) -> Path:
    """Resolve the prompts directory based on graph config.

    Logic mirrors yamlgraph.utils.prompts.resolve_prompt_path():
    1. If prompts_dir is set in graph defaults: use it relative to project_root
    2. Otherwise: project_root/prompts (default)

    Args:
        graph: Parsed graph config
        graph_path: Path to the graph YAML file
        project_root: Project root directory

    Returns:
        Resolved prompts directory path
    """
    # Check both top-level and defaults section
    defaults = graph.get("defaults", {})
    prompts_dir_config = graph.get("prompts_dir") or defaults.get("prompts_dir")
    if prompts_dir_config:
        # prompts_dir from graph config - resolve relative to project_root
        return project_root / prompts_dir_config
    return project_root / "prompts"


def check_state_declarations(
    graph_path: Path, project_root: Path | None = None
) -> list[LintIssue]:
    """Check if variables used in prompts/tools are declared in state.

    Args:
        graph_path: Path to the graph YAML file
        project_root: Root directory containing prompts/ folder

    Returns:
        List of lint issues for missing state declarations
    """
    issues = []
    graph = _load_graph(graph_path)

    if project_root is None:
        project_root = graph_path.parent

    prompts_dir = _resolve_prompts_dir(graph, graph_path, project_root)

    # Get declared state variables
    declared_state = set(graph.get("state", {}).keys())
    declared_state.update(BUILTIN_STATE_FIELDS)

    # Also include state_keys from nodes as they become available at runtime
    for node_config in graph.get("nodes", {}).values():
        if "state_key" in node_config:
            declared_state.add(node_config["state_key"])

    # Find tools used by agent nodes (their variables come from LLM, not state)
    agent_tools: set[str] = set()
    for node_config in graph.get("nodes", {}).values():
        if node_config.get("type") == "agent":
            agent_tools.update(node_config.get("tools", []))

    # Check shell tool commands for variables (skip agent tools)
    for tool_name, tool_config in graph.get("tools", {}).items():
        if tool_config.get("type") == "shell":
            # Skip tools used by agent nodes - their args come from LLM
            if tool_name in agent_tools:
                continue

            command = tool_config.get("command", "")
            variables = _extract_variables(command)
            for var in variables:
                if var not in declared_state:
                    issues.append(
                        LintIssue(
                            severity="error",
                            code="E001",
                            message=f"Variable '{var}' used in tool '{tool_name}' "
                            f"but not declared in state",
                            fix=f"Add '{var}: str' to the state section",
                        )
                    )

    # Check prompt files for variables
    for _node_name, node_config in graph.get("nodes", {}).items():
        prompt_name = node_config.get("prompt")
        if prompt_name:
            prompt_path = _get_prompt_path(prompt_name, prompts_dir)
            if prompt_path.exists():
                with open(prompt_path) as f:
                    prompt_content = f.read()
                variables = _extract_variables(prompt_content)

                # Node-level variables provide values for prompt placeholders
                node_variables = set(node_config.get("variables", {}).keys())

                for var in variables:
                    # Variable is valid if it's in state OR defined in node variables
                    if var not in declared_state and var not in node_variables:
                        issues.append(
                            LintIssue(
                                severity="error",
                                code="E002",
                                message=f"Variable '{var}' used in prompt "
                                f"'{prompt_name}' but not declared in state",
                                fix=f"Add '{var}: str' to the state section",
                            )
                        )

    return issues


def check_tool_references(graph_path: Path) -> list[LintIssue]:
    """Check that all tool references in nodes are defined.

    Args:
        graph_path: Path to the graph YAML file

    Returns:
        List of lint issues for undefined/unused tools
    """
    issues = []
    graph = _load_graph(graph_path)

    defined_tools = set(graph.get("tools", {}).keys())
    used_tools: set[str] = set()

    # Find all tool references in nodes
    for node_name, node_config in graph.get("nodes", {}).items():
        node_tools = node_config.get("tools", [])
        for tool in node_tools:
            used_tools.add(tool)
            if tool not in defined_tools:
                issues.append(
                    LintIssue(
                        severity="error",
                        code="E003",
                        message=f"Tool '{tool}' referenced in node '{node_name}' "
                        f"but not defined in tools section",
                        fix=f"Add tool '{tool}' to the tools section or remove reference",
                    )
                )

    # Check for unused tools
    for tool in defined_tools - used_tools:
        issues.append(
            LintIssue(
                severity="warning",
                code="W001",
                message=f"Tool '{tool}' is defined but never used",
                fix=f"Remove unused tool '{tool}' from tools section",
            )
        )

    return issues


def check_prompt_files(
    graph_path: Path, project_root: Path | None = None
) -> list[LintIssue]:
    """Check that all prompt files referenced by nodes exist.

    Args:
        graph_path: Path to the graph YAML file
        project_root: Root directory containing prompts/ folder

    Returns:
        List of lint issues for missing prompt files
    """
    issues = []
    graph = _load_graph(graph_path)

    if project_root is None:
        project_root = graph_path.parent

    prompts_dir = _resolve_prompts_dir(graph, graph_path, project_root)
    # Use relative path for fix suggestion
    defaults = graph.get("defaults", {})
    prompts_dir_config = graph.get("prompts_dir") or defaults.get(
        "prompts_dir", "prompts"
    )

    for node_name, node_config in graph.get("nodes", {}).items():
        prompt_name = node_config.get("prompt")
        if prompt_name:
            prompt_path = _get_prompt_path(prompt_name, prompts_dir)
            if not prompt_path.exists():
                issues.append(
                    LintIssue(
                        severity="error",
                        code="E004",
                        message=f"Prompt file '{prompt_name}.yaml' not found "
                        f"for node '{node_name}'",
                        fix=f"Create file: {prompts_dir_config}/{prompt_name}.yaml",
                    )
                )

    return issues


def check_edge_coverage(graph_path: Path) -> list[LintIssue]:
    """Check that all nodes are reachable and have paths to END.

    Args:
        graph_path: Path to the graph YAML file

    Returns:
        List of lint issues for unreachable/dead-end nodes
    """
    issues = []
    graph = _load_graph(graph_path)

    nodes = set(graph.get("nodes", {}).keys())
    edges = graph.get("edges", [])

    # Build adjacency lists
    reachable_from_start: set[str] = set()
    can_reach_end: set[str] = set()
    nodes_in_edges: set[str] = set()

    def normalize_targets(target) -> list[str]:
        """Handle both single target and list of targets."""
        if isinstance(target, list):
            return target
        return [target] if target else []

    # Forward traversal from START
    frontier = {"START"}
    while frontier:
        current = frontier.pop()
        for edge in edges:
            if edge.get("from") == current:
                targets = normalize_targets(edge.get("to"))
                for target in targets:
                    nodes_in_edges.add(target)
                    if target not in reachable_from_start and target != "END":
                        reachable_from_start.add(target)
                        frontier.add(target)

    # Backward traversal from END
    frontier = {"END"}
    visited_backward: set[str] = set()
    while frontier:
        current = frontier.pop()
        visited_backward.add(current)
        for edge in edges:
            targets = normalize_targets(edge.get("to"))
            if current in targets:
                source = edge.get("from")
                nodes_in_edges.add(source)
                if source not in can_reach_end and source != "START":
                    can_reach_end.add(source)
                    frontier.add(source)

    # Check for orphaned nodes (not in any edge)
    for node in nodes:
        if node not in reachable_from_start:
            issues.append(
                LintIssue(
                    severity="warning",
                    code="W002",
                    message=f"Node '{node}' is not reachable from START",
                    fix=f"Add edge from START or another node to '{node}'",
                )
            )
        elif node not in can_reach_end:
            issues.append(
                LintIssue(
                    severity="warning",
                    code="W003",
                    message=f"Node '{node}' has no path to END",
                    fix=f"Add edge from '{node}' to END or another node",
                )
            )

    return issues


def check_node_types(graph_path: Path) -> list[LintIssue]:
    """Check that all node types are valid.

    Args:
        graph_path: Path to the graph YAML file

    Returns:
        List of lint issues for invalid node types
    """
    issues = []
    graph = _load_graph(graph_path)

    for node_name, node_config in graph.get("nodes", {}).items():
        node_type = node_config.get("type")
        if node_type and node_type not in VALID_NODE_TYPES:
            issues.append(
                LintIssue(
                    severity="error",
                    code="E005",
                    message=f"Invalid node type '{node_type}' in node '{node_name}'",
                    fix=f"Use one of: {', '.join(sorted(VALID_NODE_TYPES))}",
                )
            )

    return issues


def lint_graph(
    graph_path: Path | str, project_root: Path | str | None = None
) -> LintResult:
    """Lint a YAML graph file for issues.

    Args:
        graph_path: Path to the graph YAML file
        project_root: Root directory containing prompts/ folder

    Returns:
        LintResult with all issues found
    """
    graph_path = Path(graph_path)
    if project_root:
        project_root = Path(project_root)

    all_issues: list[LintIssue] = []

    # Run all checks
    all_issues.extend(check_state_declarations(graph_path, project_root))
    all_issues.extend(check_tool_references(graph_path))
    all_issues.extend(check_prompt_files(graph_path, project_root))
    all_issues.extend(check_edge_coverage(graph_path))
    all_issues.extend(check_node_types(graph_path))

    # Determine validity (no errors)
    has_errors = any(issue.severity == "error" for issue in all_issues)

    return LintResult(
        file=str(graph_path),
        issues=all_issues,
        valid=not has_errors,
    )
