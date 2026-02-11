"""Semantic & cross-reference linter checks (FR-025, FR-026).

Split from checks.py to keep modules under 400 lines.

Check functions:
- check_cross_references (E006, E008)
- check_passthrough_nodes (E601)
- check_tool_call_nodes (E701, E702)
- check_expression_syntax (W801, W007)
- check_error_handling (E010, E011)
- check_edge_types (E802)
"""

from __future__ import annotations

import re
from pathlib import Path

from yamlgraph.linter.checks import BUILTIN_STATE_FIELDS, LintIssue, load_graph

# Sentinel node names that are always valid edge endpoints
_SENTINEL_NODES = {"START", "END"}

# Node types that do NOT support retry/fallback error handling
_NON_LLM_NODE_TYPES = {"tool", "python", "tool_call", "passthrough"}


def check_cross_references(graph_path: Path) -> list[LintIssue]:
    """Check edge from/to and loop_limits reference existing nodes.

    E006 — edge endpoint references non-existent node
    E008 — loop_limits key references non-existent node
    """
    issues: list[LintIssue] = []
    graph = load_graph(graph_path)

    node_names = set(graph.get("nodes", {}).keys())
    valid_targets = node_names | _SENTINEL_NODES

    # E006: edge from/to validation
    for edge in graph.get("edges", []):
        from_node = edge.get("from")
        if from_node and from_node not in valid_targets:
            issues.append(
                LintIssue(
                    severity="error",
                    code="E006",
                    message=f"Edge 'from' references non-existent node '{from_node}'",
                    fix=f"Check spelling; defined nodes: {', '.join(sorted(node_names))}",
                )
            )
        to_value = edge.get("to")
        to_targets = (
            to_value if isinstance(to_value, list) else [to_value] if to_value else []
        )
        for target in to_targets:
            if target not in valid_targets:
                issues.append(
                    LintIssue(
                        severity="error",
                        code="E006",
                        message=f"Edge 'to' references non-existent node '{target}'",
                        fix=f"Check spelling; defined nodes: {', '.join(sorted(node_names))}",
                    )
                )

    # E008: loop_limits keys
    for key in graph.get("loop_limits", {}):
        if key not in node_names:
            issues.append(
                LintIssue(
                    severity="error",
                    code="E008",
                    message=f"loop_limits references non-existent node '{key}'",
                    fix=f"Check spelling; defined nodes: {', '.join(sorted(node_names))}",
                )
            )

    return issues


def check_passthrough_nodes(graph_path: Path) -> list[LintIssue]:
    """Check passthrough nodes have required output field.

    E601 — passthrough node missing output (silent no-op)
    """
    issues: list[LintIssue] = []
    graph = load_graph(graph_path)

    for node_name, node_config in graph.get("nodes", {}).items():
        if node_config.get("type") == "passthrough" and "output" not in node_config:
            issues.append(
                LintIssue(
                    severity="error",
                    code="E601",
                    message=f"Passthrough node '{node_name}' has no 'output' — it will be a silent no-op",
                    fix=f"Add 'output:' mapping to node '{node_name}'",
                )
            )

    return issues


def check_tool_call_nodes(graph_path: Path) -> list[LintIssue]:
    """Check tool_call nodes have required tool and args fields.

    E701 — tool_call node missing 'tool' field
    E702 — tool_call node missing 'args' field
    """
    issues: list[LintIssue] = []
    graph = load_graph(graph_path)

    for node_name, node_config in graph.get("nodes", {}).items():
        if node_config.get("type") != "tool_call":
            continue
        if "tool" not in node_config:
            issues.append(
                LintIssue(
                    severity="error",
                    code="E701",
                    message=f"tool_call node '{node_name}' missing required 'tool' field",
                    fix=f"Add 'tool: <tool_name>' to node '{node_name}'",
                )
            )
        if "args" not in node_config:
            issues.append(
                LintIssue(
                    severity="error",
                    code="E702",
                    message=f"tool_call node '{node_name}' missing required 'args' field",
                    fix=f"Add 'args:' mapping to node '{node_name}'",
                )
            )

    return issues


def check_expression_syntax(graph_path: Path) -> list[LintIssue]:
    """Check condition and variable expression syntax.

    W801 — condition uses {braces} or state. prefix (should be bare names)
    W007 — variable expression uses {name} without state. prefix
    """
    issues: list[LintIssue] = []
    graph = load_graph(graph_path)

    # W801: condition expressions should NOT have braces or state. prefix
    for edge in graph.get("edges", []):
        condition = edge.get("condition")
        if not condition or not isinstance(condition, str):
            continue
        if re.search(r"\{state\.", condition) or re.search(r"\{[a-zA-Z_]", condition):
            issues.append(
                LintIssue(
                    severity="warning",
                    code="W801",
                    message=f"Condition '{condition}' uses braces — conditions use bare variable names",
                    fix="Remove {{ }} braces and 'state.' prefix from condition expression",
                )
            )

    # W007: variable expressions in node.variables / node.output should use {state.xxx}
    state_fields = set(graph.get("state", {}).keys())
    state_fields.update(BUILTIN_STATE_FIELDS)

    for node_name, node_config in graph.get("nodes", {}).items():
        # Check variables and output mappings
        for section in ("variables", "output"):
            mapping = node_config.get(section) or {}
            if not isinstance(mapping, dict):
                continue
            for _key, value in mapping.items():
                if not isinstance(value, str):
                    continue
                # Find {xxx} patterns that are NOT {state.xxx} and NOT {{escaped}}
                protected = value.replace("{{", "\x00").replace("}}", "\x01")
                bare_refs = re.findall(r"\{(\w+)\}", protected)
                for ref in bare_refs:
                    if ref in state_fields:
                        issues.append(
                            LintIssue(
                                severity="warning",
                                code="W007",
                                message=(
                                    f"Variable '{{{{ {ref} }}}}' in node '{node_name}' "
                                    f"appears to reference state field '{ref}' "
                                    f"without 'state.' prefix"
                                ),
                                fix=f"Use '{{{{state.{ref}}}}}' instead of '{{{{{ref}}}}}'",
                            )
                        )

    return issues


def check_error_handling(graph_path: Path) -> list[LintIssue]:
    """Check error handling configuration.

    E010 — on_error: fallback without fallback configuration
    E011 — on_error: retry/fallback on tool/python node (unsupported)
    """
    issues: list[LintIssue] = []
    graph = load_graph(graph_path)

    for node_name, node_config in graph.get("nodes", {}).items():
        on_error = node_config.get("on_error")
        node_type = node_config.get("type", "llm")

        # E010: fallback without config
        if on_error == "fallback" and "fallback" not in node_config:
            issues.append(
                LintIssue(
                    severity="error",
                    code="E010",
                    message=f"Node '{node_name}' has on_error: fallback but no fallback config",
                    fix=f"Add 'fallback:' config to node '{node_name}' (e.g., fallback: {{provider: openai}})",
                )
            )

        # E011: retry/fallback on non-LLM nodes (unsupported)
        if on_error in ("retry", "fallback") and node_type in _NON_LLM_NODE_TYPES:
            issues.append(
                LintIssue(
                    severity="error",
                    code="E011",
                    message=(
                        f"Node '{node_name}' (type: {node_type}) has on_error: {on_error} "
                        f"but only LLM nodes support retry/fallback"
                    ),
                    fix=f"Change on_error to 'skip' or 'fail' for node '{node_name}'",
                )
            )

    return issues


def check_edge_types(graph_path: Path) -> list[LintIssue]:
    """Check conditional edges have list 'to' target.

    E802 — conditional edge with string 'to' (silently becomes normal edge)
    """
    issues: list[LintIssue] = []
    graph = load_graph(graph_path)

    for edge in graph.get("edges", []):
        edge_type = edge.get("type")
        if edge_type == "conditional" and not isinstance(edge.get("to"), list):
            from_node = edge.get("from", "?")
            issues.append(
                LintIssue(
                    severity="error",
                    code="E802",
                    message=(
                        f"Conditional edge from '{from_node}' has string 'to' — "
                        f"conditional edges require a list of targets"
                    ),
                    fix="Change 'to: node' to 'to: [node_a, node_b]'",
                )
            )

    return issues


def check_unguarded_cycles(graph_path: Path) -> list[LintIssue]:
    """Warn when cycle nodes lack loop_limits entries.

    W012 — node in cycle without loop_limits
    """
    from yamlgraph.graph_loader import detect_loop_nodes

    issues: list[LintIssue] = []
    graph = load_graph(graph_path)

    edges = graph.get("edges", [])
    loop_nodes = detect_loop_nodes(edges)
    loop_limits = graph.get("loop_limits", {})

    for node in sorted(loop_nodes):
        if node not in loop_limits:
            issues.append(
                LintIssue(
                    severity="warning",
                    code="W012",
                    message=f"Node '{node}' is in a cycle but has no loop_limits entry",
                    fix=f"Add '{node}: <limit>' to loop_limits section",
                )
            )

    return issues


def check_dynamic_map_without_max_items(
    node_name: str, node_config: dict, graph_config: dict
) -> list[LintIssue]:
    """Warn when map over: is a dynamic expression without max_items.

    W013 — dynamic fan-out without explicit cap.
    A dynamic expression is any string containing '{' (state reference).
    Suppressed when node has max_items or graph config has max_map_items.
    """
    issues: list[LintIssue] = []

    over = node_config.get("over")
    if not isinstance(over, str) or "{" not in over:
        return issues

    # Suppressed by node-level max_items
    if "max_items" in node_config:
        return issues

    # Suppressed by graph-level max_map_items
    if graph_config.get("max_map_items") is not None:
        return issues

    issues.append(
        LintIssue(
            severity="warning",
            code="W013",
            message=(
                f"Map node '{node_name}' fans out over dynamic expression "
                f"'{over}' without max_items"
            ),
            fix=f"Add 'max_items: <limit>' to node '{node_name}' or 'max_map_items' to config",
        )
    )

    return issues


__all__ = [
    "check_cross_references",
    "check_passthrough_nodes",
    "check_tool_call_nodes",
    "check_expression_syntax",
    "check_error_handling",
    "check_edge_types",
    "check_unguarded_cycles",
    "check_dynamic_map_without_max_items",
]
