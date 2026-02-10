# Safety Guards Demo — FR-027

Demonstrates the 4 execution safety features that protect YAMLGraph pipelines
against unbounded execution: runaway loops, fan-out explosions, and stack overflow.

## Quick Start

```bash
# Lint — should pass clean
yamlgraph graph lint examples/demos/safety-guards/graph.yaml

# Run
yamlgraph graph run examples/demos/safety-guards/graph.yaml \
  --var topic="quantum computing" \
  --var topics='["physics", "math", "biology"]'
```

## What's Protected

### 1. `config.recursion_limit` — Global Recursion Cap

Controls the maximum LangGraph recursion depth. Prevents stack overflow if
edges or subgraphs create deep call chains.

```yaml
config:
  recursion_limit: 30   # default: 50 (LangGraph default is 1000)
```

### 2. `config.max_map_items` — Default Map Fan-Out Cap

Graph-level ceiling for all `type: map` nodes. If some upstream LLM returns
a list of 10,000 items, the map node truncates to this limit with a warning.

```yaml
config:
  max_map_items: 20     # default: 100
```

### 3. `max_items` — Per-Node Map Override

Override the graph-level default for a specific map node.

```yaml
nodes:
  expand:
    type: map
    over: "{state.topics}"
    as: topic
    max_items: 5         # <-- this node caps at 5, regardless of graph default
    node: ...
    collect: fun_facts
```

**What happens at runtime** when a list of 50 items hits a `max_items: 5` node:
```
WARNING Map node 'expand': truncating 50 items to 5
```
Only the first 5 items are fanned out.

### 4. `loop_limits` + Linter W012 — Cycle Guards

Every node participating in a cycle **must** have a `loop_limits` entry.
The linter enforces this at design time:

```bash
$ yamlgraph graph lint graph-without-limits.yaml
⚠️ graph.yaml
   ⚠ [W012] Node 'review' is in a cycle but has no loop_limits entry
      Fix: Add 'review: <limit>' to loop_limits section
```

At runtime, when a node hits its limit, `_loop_limit_reached` is set in state
and further iterations are skipped — no exception, no infinite loop.

```yaml
loop_limits:
  review: 3    # max 3 iterations
  revise: 3    # max 3 iterations
```

This applies to **all** node types — LLM, tool, python, and passthrough.

## Try Breaking It

Remove one guard at a time and re-lint to see the warning:

```bash
# 1. Remove 'revise' from loop_limits → W012 fires
sed '/revise: 3/d' graph.yaml | yamlgraph graph lint /dev/stdin

# 2. Set max_items: 1000 and pass a huge list → truncation warning at runtime
```
