"""YAMLGraph meta-template tools for implementation agent.

Extract patterns from existing graph and prompt YAML files.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml


def extract_graph_template(graph_path: str) -> dict:
    """Extract reusable patterns from a graph YAML file.

    Args:
        graph_path: Path to the graph YAML file

    Returns:
        dict with:
        - node_types: List of node types used
        - edge_patterns: List of edge pattern types
        - state_fields: List of state field definitions
        - tool_patterns: List of tool type patterns
        or dict with 'error' key if failed
    """
    path = Path(graph_path)
    if not path.exists():
        return {"error": f"File not found: {graph_path}"}

    try:
        content = path.read_text()
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        return {"error": f"YAML parse error: {e}"}

    if not isinstance(data, dict):
        return {"error": "Invalid graph format: expected dict"}

    result = {
        "node_types": [],
        "edge_patterns": [],
        "state_fields": [],
        "tool_patterns": [],
    }

    # Extract node types
    nodes = data.get("nodes", {})
    node_types_seen = set()
    for node_name, node_config in nodes.items():
        if isinstance(node_config, dict):
            node_type = node_config.get("type", "unknown")
            node_types_seen.add(node_type)

    result["node_types"] = sorted(node_types_seen)

    # Extract edge patterns
    edges = data.get("edges", [])
    has_conditional = False
    has_sequential = False

    for edge in edges:
        if isinstance(edge, str):
            has_sequential = True
        elif isinstance(edge, dict):
            # Check for conditional edges
            for edge_def in edge.values():
                if isinstance(edge_def, dict) and "condition" in edge_def:
                    has_conditional = True

    # Also check string edges for condition syntax
    for edge in edges:
        if isinstance(edge, str) and ":" in edge and "condition" in str(edges):
            has_conditional = True

    if has_sequential:
        result["edge_patterns"].append("sequential")
    if has_conditional:
        result["edge_patterns"].append("conditional")

    # Extract state fields
    state = data.get("state", {})
    if isinstance(state, dict):
        for field_name, field_type in state.items():
            result["state_fields"].append({"name": field_name, "type": str(field_type)})

    # Extract tool patterns
    tools = data.get("tools", {})
    tool_types_seen = set()
    for tool_name, tool_config in tools.items():
        if isinstance(tool_config, dict):
            tool_type = tool_config.get("type", "unknown")
            tool_types_seen.add(tool_type)

    result["tool_patterns"] = sorted(tool_types_seen)

    return result


def extract_prompt_template(prompt_path: str) -> dict:
    """Extract patterns from a prompt YAML file.

    Args:
        prompt_path: Path to the prompt YAML file

    Returns:
        dict with:
        - system_structure: Analysis of system prompt sections
        - variables: List of variable names found
        - schema_patterns: Schema field patterns if present
        - jinja_patterns: Jinja2 constructs used
        or dict with 'error' key if failed
    """
    path = Path(prompt_path)
    if not path.exists():
        return {"error": f"File not found: {prompt_path}"}

    try:
        content = path.read_text()
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        return {"error": f"YAML parse error: {e}"}

    if not isinstance(data, dict):
        return {"error": "Invalid prompt format: expected dict"}

    result = {
        "system_structure": {},
        "variables": [],
        "schema_patterns": [],
        "jinja_patterns": [],
    }

    # Extract system prompt structure
    system = data.get("system", "")
    if system:
        sections = _extract_sections(system)
        result["system_structure"] = {"sections": sections, "length": len(system)}

    # Extract variables from all text fields
    variables = set()
    for key in ["system", "user"]:
        text = data.get(key, "")
        if text:
            # Find {variable} patterns (simple format)
            simple_vars = re.findall(r"\{(\w+)\}", str(text))
            variables.update(simple_vars)

            # Find {{ variable }} patterns (Jinja2)
            jinja_vars = re.findall(r"\{\{\s*(\w+)", str(text))
            variables.update(jinja_vars)

    result["variables"] = sorted(variables)

    # Extract schema patterns
    schema = data.get("schema", {})
    if isinstance(schema, dict):
        properties = schema.get("properties", {})
        for prop_name, prop_def in properties.items():
            prop_type = (
                prop_def.get("type", "unknown")
                if isinstance(prop_def, dict)
                else "unknown"
            )
            result["schema_patterns"].append({"name": prop_name, "type": prop_type})

    # Extract Jinja patterns
    jinja_constructs = set()
    full_text = str(data.get("system", "")) + str(data.get("user", ""))

    if "{%" in full_text:
        if "{% if" in full_text:
            jinja_constructs.add("if")
        if "{% for" in full_text:
            jinja_constructs.add("for")
        if "{% endif" in full_text:
            jinja_constructs.add("endif")
        if "{% endfor" in full_text:
            jinja_constructs.add("endfor")
        if "{% else" in full_text:
            jinja_constructs.add("else")
        if "{% elif" in full_text:
            jinja_constructs.add("elif")

    result["jinja_patterns"] = sorted(jinja_constructs)

    return result


def _extract_sections(text: str) -> list[str]:
    """Extract section headers from text (## or ### style)."""
    sections = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("##"):
            # Remove ## prefix and clean
            section = line.lstrip("#").strip()
            if section:
                sections.append(section)

    return sections
