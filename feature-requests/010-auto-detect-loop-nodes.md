# Feature Request: Auto-detect Loop Nodes for skip_if_exists

**Priority:** HIGH
**Type:** DX Improvement
**Status:** Proposed
**Effort:** 1 day
**Requested:** 2026-01-28

## Summary

Automatically detect nodes in graph cycles and disable `skip_if_exists` for them, eliminating a common footgun where loop nodes silently stop after one iteration.

## Problem

YamlGraph has 34 occurrences of `skip_if_exists: false` scattered across the codebase. This is a **leaky abstraction**:

1. **Hidden requirement**: Loop nodes must have `skip_if_exists: false` or they run once and stop
2. **Subtle bugs**: Forgetting this flag causes silent failures - loops appear to work but only run once
3. **Conflated concerns**: One flag handles both "resume support" and "loop re-execution"
4. **Documentation burden**: Every loop example must include this non-obvious flag

```yaml
# Current: Easy to forget, causes subtle bugs
generate:
  type: llm
  prompt: generate
  skip_if_exists: false  # WHY? Not obvious without deep knowledge
```

## Proposed Solution

### Auto-detection at Graph Load Time

Detect cycles in the edge graph and automatically set `skip_if_exists: false` for nodes within cycles:

```python
# yamlgraph/graph_loader.py

def detect_loop_nodes(edges: list[dict]) -> set[str]:
    """Find nodes that are part of cycles (loops)."""
    # Build adjacency graph
    # Find strongly connected components or simple cycle detection
    # Return set of node names in cycles
    ...

def load_graph_config(path: str) -> dict:
    config = yaml.safe_load(...)

    # Auto-detect loop nodes
    loop_nodes = detect_loop_nodes(config["edges"])

    for node_name in loop_nodes:
        if "skip_if_exists" not in config["nodes"][node_name]:
            config["nodes"][node_name]["skip_if_exists"] = False
            logger.debug(f"Auto-disabled skip_if_exists for loop node: {node_name}")

    return config
```

### Behavior

| Scenario | skip_if_exists | Behavior |
|----------|----------------|----------|
| Node in cycle, no explicit setting | `false` (auto) | Re-runs each iteration ✓ |
| Node in cycle, explicit `true` | `true` (override) | User override respected |
| Node in cycle, explicit `false` | `false` | No change |
| Linear node, no explicit setting | `true` (default) | Resume support ✓ |

### Example

```yaml
# Before: Requires explicit skip_if_exists on every loop node
nodes:
  generate:
    type: llm
    prompt: generate
    skip_if_exists: false  # Easy to forget!
  evaluate:
    type: router
    prompt: evaluate
    skip_if_exists: false  # Easy to forget!

edges:
  - from: generate
    to: evaluate
  - from: evaluate
    to: generate
    condition: "needs_improvement"
```

```yaml
# After: Just works - loop detected automatically
nodes:
  generate:
    type: llm
    prompt: generate
  evaluate:
    type: router
    prompt: evaluate

edges:
  - from: generate
    to: evaluate
  - from: evaluate
    to: generate
    condition: "needs_improvement"
# Loop auto-detected: generate ↔ evaluate have skip_if_exists=false
```

## Implementation

### 1. Cycle Detection Algorithm

Use depth-first search to find back edges (Tarjan's or simple DFS):

```python
def detect_loop_nodes(edges: list[dict]) -> set[str]:
    """Detect nodes that participate in cycles."""
    from collections import defaultdict

    # Build adjacency list
    graph = defaultdict(set)
    all_nodes = set()
    for edge in edges:
        from_node = edge.get("from")
        to_nodes = edge.get("to")
        if isinstance(to_nodes, str):
            to_nodes = [to_nodes]
        for to_node in to_nodes:
            graph[from_node].add(to_node)
            all_nodes.add(from_node)
            all_nodes.add(to_node)

    # Find nodes in cycles using DFS with coloring
    loop_nodes = set()
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in all_nodes}

    def dfs(node: str, path: set[str]) -> None:
        color[node] = GRAY
        path.add(node)

        for neighbor in graph[node]:
            if color[neighbor] == GRAY:
                # Back edge found - all nodes in current path are in a cycle
                loop_nodes.update(path)
            elif color[neighbor] == WHITE:
                dfs(neighbor, path.copy())

        color[node] = BLACK

    for node in all_nodes:
        if color[node] == WHITE:
            dfs(node, set())

    return loop_nodes
```

### 2. Integration Point

Add to `graph_loader.py` after YAML parsing, before graph building.

### 3. Logging

```
DEBUG: Auto-disabled skip_if_exists for loop nodes: generate, evaluate
```

## Acceptance Criteria

- [ ] `detect_loop_nodes()` correctly identifies nodes in cycles
- [ ] Auto-sets `skip_if_exists: false` for detected loop nodes
- [ ] Explicit `skip_if_exists: true` in YAML overrides auto-detection
- [ ] Linear (non-loop) nodes retain default `skip_if_exists: true`
- [ ] Works with conditional edges
- [ ] Works with router nodes
- [ ] Logs auto-detected loop nodes at DEBUG level
- [ ] Existing graphs with explicit `skip_if_exists: false` still work
- [ ] Unit tests for cycle detection algorithm
- [ ] Integration test with reflexion-demo.yaml

## Migration

**Non-breaking**: Existing graphs work unchanged. Explicit `skip_if_exists: false` becomes optional but still supported.

## Testing

```python
def test_detect_simple_loop():
    edges = [
        {"from": "A", "to": "B"},
        {"from": "B", "to": "A"},
    ]
    assert detect_loop_nodes(edges) == {"A", "B"}

def test_detect_no_loop():
    edges = [
        {"from": "A", "to": "B"},
        {"from": "B", "to": "C"},
    ]
    assert detect_loop_nodes(edges) == set()

def test_detect_reflexion_pattern():
    edges = [
        {"from": "START", "to": "generate"},
        {"from": "generate", "to": "evaluate"},
        {"from": "evaluate", "to": "generate", "condition": "..."},
        {"from": "evaluate", "to": "END", "condition": "..."},
    ]
    assert detect_loop_nodes(edges) == {"generate", "evaluate"}
```

## Related

- `yamlgraph/node_factory/llm_nodes.py` - skip_if_exists implementation
- `graphs/reflexion-demo.yaml` - example loop graph
- `reference/patterns.md` - loop pattern documentation
