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
from pathlib import Path

from pydantic import BaseModel

from yamlgraph.tools.linter_checks import (
    LintIssue,
    check_edge_coverage,
    check_node_types,
    check_prompt_files,
    check_state_declarations,
    check_tool_references,
)
from yamlgraph.tools.linter_patterns import (
    check_agent_patterns,
    check_interrupt_patterns,
    check_map_patterns,
    check_router_patterns,
    check_subgraph_patterns,
)

logger = logging.getLogger(__name__)


class LintResult(BaseModel):
    """Result of linting a graph file."""

    file: str
    issues: list[LintIssue]
    valid: bool


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

    # Pattern-specific checks
    all_issues.extend(check_router_patterns(graph_path, project_root))
    all_issues.extend(check_map_patterns(graph_path, project_root))
    all_issues.extend(check_interrupt_patterns(graph_path, project_root))
    all_issues.extend(check_agent_patterns(graph_path, project_root))
    all_issues.extend(check_subgraph_patterns(graph_path, project_root))

    # Determine validity (no errors)
    has_errors = any(issue.severity == "error" for issue in all_issues)

    return LintResult(
        file=str(graph_path),
        issues=all_issues,
        valid=not has_errors,
    )


# Re-export for backwards compatibility
__all__ = [
    "LintIssue",
    "LintResult",
    "lint_graph",
    # Re-export check functions for direct use
    "check_state_declarations",
    "check_tool_references",
    "check_prompt_files",
    "check_edge_coverage",
    "check_node_types",
    "check_router_patterns",
    "check_map_patterns",
    "check_interrupt_patterns",
    "check_agent_patterns",
    "check_subgraph_patterns",
]
