"""Snippet loader for yamlgraph-generator."""

from pathlib import Path

import yaml

SNIPPETS_DIR = Path(__file__).parent.parent / "snippets"

# Pattern to snippets mapping
PATTERN_SNIPPETS = {
    "linear": ["nodes/llm-basic", "edges/linear", "scaffolds/graph-header"],
    "router": [
        "nodes/router-basic",
        "edges/conditional",
        "patterns/classify-then-process",
        "scaffolds/graph-header",
    ],
    "map": [
        "nodes/map-basic",
        "edges/linear",
        "patterns/map-then-summarize",
        "scaffolds/graph-header",
    ],
    "interrupt": [
        "nodes/interrupt-basic",
        "patterns/interrupt-multi-step",
        "scaffolds/graph-header",
        "scaffolds/checkpointer-memory",
    ],
    "agent": [
        "nodes/agent-with-tools",
        "edges/linear",
        "scaffolds/graph-header",
    ],
    "subgraph": [
        "nodes/subgraph-basic",
        "edges/linear",
        "scaffolds/graph-header",
    ],
}


def list_snippets(category: str | None = None) -> list[str]:
    """List available snippets, optionally filtered by category.

    Categories: nodes, edges, patterns, scaffolds, prompt-scaffolds
    """
    if category:
        base = SNIPPETS_DIR / category
        if not base.exists():
            return []
        return [p.stem for p in base.glob("*.yaml")]

    # All categories
    result = []
    for cat in ["nodes", "edges", "patterns", "scaffolds", "prompt-scaffolds"]:
        cat_path = SNIPPETS_DIR / cat
        if cat_path.exists():
            result.extend([f"{cat}/{p.stem}" for p in cat_path.glob("*.yaml")])
    return result


def load_snippet(snippet_path: str) -> dict:
    """Load a single snippet by path (e.g., 'patterns/generate-then-map').

    Returns dict with keys: content, data, path, category, name
    """
    # Handle both 'category/name' and 'category/name.yaml'
    if not snippet_path.endswith(".yaml"):
        snippet_path = f"{snippet_path}.yaml"

    full_path = SNIPPETS_DIR / snippet_path
    if not full_path.exists():
        raise FileNotFoundError(f"Snippet not found: {snippet_path}")

    content = full_path.read_text()
    data = yaml.safe_load(content)

    return {
        "content": content,
        "data": data,
        "path": str(full_path),
        "category": full_path.parent.name,
        "name": full_path.stem,
    }


def load_snippets(paths: list[str]) -> dict[str, dict]:
    """Load multiple snippets by path.

    Returns dict: {snippet_path: snippet_data}
    """
    import contextlib

    result = {}
    for path in paths:
        with contextlib.suppress(FileNotFoundError):
            result[path] = load_snippet(path)
    return result


def load_snippets_for_patterns(patterns: list[str]) -> dict:
    """Load all snippets needed for the given patterns.

    Args:
        patterns: List of pattern names like ["router", "map"]

    Returns:
        dict with snippet_contents and available_snippets
    """
    snippet_paths = set()
    for pattern in patterns:
        if pattern in PATTERN_SNIPPETS:
            snippet_paths.update(PATTERN_SNIPPETS[pattern])

    snippet_contents = load_snippets(list(snippet_paths))

    return {
        "snippet_contents": snippet_contents,
        "patterns": patterns,
    }


def load_snippets_for_patterns_node(state: dict) -> dict:
    """Yamlgraph node wrapper for load_snippets_for_patterns.

    Extracts patterns from state and returns snippet contents.
    """
    patterns = state.get("patterns") or []
    return load_snippets_for_patterns(patterns)


def get_snippet_index() -> dict:
    """Get index of all snippets organized by category.

    Returns dict: {category: [{name, description, path}]}
    """
    index = {}
    for cat in ["nodes", "edges", "patterns", "scaffolds", "prompt-scaffolds"]:
        cat_path = SNIPPETS_DIR / cat
        if not cat_path.exists():
            continue

        snippets = []
        for p in cat_path.glob("*.yaml"):
            try:
                data = yaml.safe_load(p.read_text())
                snippets.append(
                    {
                        "name": p.stem,
                        "path": f"{cat}/{p.stem}",
                        "description": data.get("description", "") if data else "",
                    }
                )
            except yaml.YAMLError:
                snippets.append(
                    {
                        "name": p.stem,
                        "path": f"{cat}/{p.stem}",
                        "description": "",
                    }
                )

        if snippets:
            index[cat] = snippets

    return index
