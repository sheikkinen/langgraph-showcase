"""Graph Linter Check Functions.

Individual check functions extracted from graph_linter.py
to keep modules under 400 lines.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

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
    "tool",
    "tool_call",
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


def load_graph(graph_path: Path) -> dict[str, Any]:
    """Load and parse a YAML graph file."""
    with open(graph_path) as f:
        return yaml.safe_load(f) or {}


def extract_variables(text: str) -> set[str]:
    """Extract {variable} placeholders from text.

    Ignores escaped {{variable}} (doubled braces).
    """
    # Find all {word} patterns but not {{word}}
    # First, temporarily replace {{ and }} to protect them
    protected = text.replace("{{", "\x00").replace("}}", "\x01")
    matches = re.findall(r"\{(\w+)\}", protected)
    return set(matches)


def get_prompt_path(prompt_name: str, prompts_dir: Path) -> Path:
    """Get the full path to a prompt file."""
    # Strip 'prompts/' prefix if present (avoids path doubling)
    if prompt_name.startswith("prompts/"):
        prompt_name = prompt_name[8:]
    # Handle case where prompt_name already has .yaml extension
    if prompt_name.endswith(".yaml"):
        return prompts_dir / prompt_name
    return prompts_dir / f"{prompt_name}.yaml"


def resolve_prompts_dir(graph: dict, graph_path: Path, project_root: Path) -> Path:
    """Resolve the prompts directory based on graph config.

    Respects prompts_relative setting to resolve relative to graph file.
    """
    defaults = graph.get("defaults", {})
    prompts_relative = graph.get("prompts_relative", False)
    prompts_dir_config = graph.get("prompts_dir") or defaults.get("prompts_dir")

    if prompts_relative and prompts_dir_config:
        # Resolve relative to graph file location
        return graph_path.parent / prompts_dir_config
    elif prompts_dir_config:
        return project_root / prompts_dir_config
    return project_root / "prompts"


def check_state_declarations(
    graph_path: Path, project_root: Path | None = None
) -> list[LintIssue]:
    """Check if variables used in prompts/tools are declared in state."""
    issues = []
    graph = load_graph(graph_path)

    if project_root is None:
        project_root = graph_path.parent

    prompts_dir = resolve_prompts_dir(graph, graph_path, project_root)

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
            if tool_name in agent_tools:
                continue

            command = tool_config.get("command", "")
            variables = extract_variables(command)
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
            prompt_path = get_prompt_path(prompt_name, prompts_dir)
            if prompt_path.exists():
                with open(prompt_path) as f:
                    prompt_content = f.read()
                variables = extract_variables(prompt_content)

                node_variables = set(node_config.get("variables", {}).keys())

                for var in variables:
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
    """Check that all tool references in nodes are defined."""
    issues = []
    graph = load_graph(graph_path)

    defined_tools = set(graph.get("tools", {}).keys())
    used_tools: set[str] = set()

    for node_name, node_config in graph.get("nodes", {}).items():
        # Check tools list (for type: agent nodes)
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

        # Check single tool property (for type: tool and type: python nodes)
        single_tool = node_config.get("tool")
        if single_tool:
            used_tools.add(single_tool)
            if single_tool not in defined_tools:
                issues.append(
                    LintIssue(
                        severity="error",
                        code="E003",
                        message=f"Tool '{single_tool}' referenced in node '{node_name}' "
                        f"but not defined in tools section",
                        fix=f"Add tool '{single_tool}' to the tools section or remove reference",
                    )
                )

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
    """Check that all prompt files referenced by nodes exist."""
    issues = []
    graph = load_graph(graph_path)

    if project_root is None:
        project_root = graph_path.parent

    prompts_dir = resolve_prompts_dir(graph, graph_path, project_root)
    defaults = graph.get("defaults", {})
    prompts_dir_config = graph.get("prompts_dir") or defaults.get(
        "prompts_dir", "prompts"
    )

    for node_name, node_config in graph.get("nodes", {}).items():
        prompt_name = node_config.get("prompt")
        if prompt_name:
            prompt_path = get_prompt_path(prompt_name, prompts_dir)
            if not prompt_path.exists():
                # Normalize the filename for error message
                display_name = (
                    prompt_name
                    if prompt_name.endswith(".yaml")
                    else f"{prompt_name}.yaml"
                )
                issues.append(
                    LintIssue(
                        severity="error",
                        code="E004",
                        message=f"Prompt file '{display_name}' not found "
                        f"for node '{node_name}'",
                        fix=f"Create file: {prompts_dir_config}/{display_name}",
                    )
                )

    return issues


def check_edge_coverage(graph_path: Path) -> list[LintIssue]:
    """Check that all nodes are reachable and have paths to END."""
    issues = []
    graph = load_graph(graph_path)

    nodes = set(graph.get("nodes", {}).keys())
    edges = graph.get("edges", [])

    reachable_from_start: set[str] = set()
    can_reach_end: set[str] = set()

    def normalize_targets(target) -> list[str]:
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
                    if target not in reachable_from_start and target != "END":
                        reachable_from_start.add(target)
                        frontier.add(target)

    # Backward traversal from END
    frontier = {"END"}
    while frontier:
        current = frontier.pop()
        for edge in edges:
            targets = normalize_targets(edge.get("to"))
            if current in targets:
                source = edge.get("from")
                if source not in can_reach_end and source != "START":
                    can_reach_end.add(source)
                    frontier.add(source)

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
    """Check that all node types are valid."""
    issues = []
    graph = load_graph(graph_path)

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


# ---------------------------------------------------------------------------
# FR-025: Cross-reference & semantic checks
# ---------------------------------------------------------------------------

# Sentinel node names that are always valid edge endpoints
_SENTINEL_NODES = {"START", "END"}


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
    """Check on_error: fallback has corresponding fallback config.

    E010 — on_error: fallback without fallback configuration
    """
    issues: list[LintIssue] = []
    graph = load_graph(graph_path)

    for node_name, node_config in graph.get("nodes", {}).items():
        if node_config.get("on_error") == "fallback" and "fallback" not in node_config:
            issues.append(
                LintIssue(
                    severity="error",
                    code="E010",
                    message=f"Node '{node_name}' has on_error: fallback but no fallback config",
                    fix=f"Add 'fallback:' config to node '{node_name}' (e.g., fallback: {{provider: openai}})",
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


__all__ = [
    "LintIssue",
    "VALID_NODE_TYPES",
    "BUILTIN_STATE_FIELDS",
    "check_state_declarations",
    "check_tool_references",
    "check_prompt_files",
    "check_edge_coverage",
    "check_node_types",
    "check_cross_references",
    "check_passthrough_nodes",
    "check_tool_call_nodes",
    "check_expression_syntax",
    "check_error_handling",
    "check_edge_types",
]
