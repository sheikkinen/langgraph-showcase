"""YAMLGraph Linter - Static analysis for YAML graph configurations.

Public API:
    lint_graph: Main linting function for YAML graph files
    LintIssue: Data model for lint issues

Example:
    from yamlgraph.linter import lint_graph, LintIssue

    issues = lint_graph(Path("graph.yaml"))
    for issue in issues:
        print(f"{issue.severity}: {issue.message}")
"""

from yamlgraph.linter.checks import LintIssue
from yamlgraph.linter.graph_linter import lint_graph

__all__ = [
    "lint_graph",
    "LintIssue",
]
