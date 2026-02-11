# Feature Request: Execution Safety Guards (FR-027)

**Priority:** HIGH
**Type:** Enhancement
**Status:** P0+P1+W013 Complete (P2-8 token tracking deferred)
**Effort:** 3–5 days
**Requested:** 2026-02-11

## Summary

Defense-in-depth guards against infinite loops, unbounded map fan-out, and runaway execution cost. Currently YAMLGraph relies on LangGraph's implicit `recursion_limit=1000` as the sole backstop for most runaway scenarios. This is insufficient for a declarative framework where YAML authors may not understand the runtime implications.

## Problem

Codebase audit revealed **8 gaps** in execution safety:

| # | Gap | Blast Radius |
|---|-----|-------------|
| 1 | **No fan-out cap on map nodes** | 10k-item list → 10k `Send()` calls, each cloning full state + potential LLM call. Memory explosion + unbounded cost. |
| 2 | **`recursion_limit` never exposed** | LangGraph default 1000 steps. A looping graph could make 500+ LLM calls before the silent backstop triggers `GraphRecursionError`. |
| 3 | **`loop_limits` only checked in LLM nodes** | Cycles through tool/python/passthrough nodes bypass `check_loop_limit()` entirely. |
| 4 | **No linter warning for unguarded cycles** | Linter detects cycles (`detect_loop_nodes`) but never warns when a cycle lacks `loop_limits`. |
| 5 | **No execution timeout** | Stalled API call blocks forever. No `asyncio.timeout`, no `signal.alarm`. |
| 6 | **`DEFAULT_MAX_TOKENS = 4096` is dead code** | Defined in `config.py` but never wired to `create_llm()`. |
| 7 | **No cost / token tracking** | No `response.usage` extraction, no cumulative counting, no budget guard. |
| 8 | **`max_iterations` default mismatch** | Schema says 10, agent code defaults to 5. |

### Industry Context

Every production graph/workflow framework enforces these guards:

- **LangGraph**: `recursion_limit`, `RemainingSteps` managed value (proactive)
- **Temporal**: `execution_timeout`, `start_to_close_timeout`, per-activity retry policies
- **Prefect**: `@flow(timeout_seconds=N)`, `@task(timeout_seconds=N)`, `ThreadPoolTaskRunner(max_workers=N)`
- **Airflow**: `dagrun_timeout`, `execution_timeout`, pool slots for concurrency

## Proposed Solution

### P0 — Must-Have (prevents runaway cost/hang)

#### 1. Map `max_items` (Gap 1)

Cap fan-out in `map_compiler.py`. Truncate + warn when list exceeds limit.

```yaml
nodes:
  translate_all:
    type: map
    over: "state.chapters"
    max_items: 20       # per-node override
    node: translate_one

config:
  max_map_items: 100    # graph-level default (fallback: 100)
```

Implementation: In `compile_map_node()`, after resolving `items` list:
```python
max_items = node_config.get("max_items", graph_config.get("max_map_items", 100))
if len(items) > max_items:
    logger.warning("Map node '%s': truncating %d items to %d", node_name, len(items), max_items)
    items = items[:max_items]
```

#### 2. Expose `recursion_limit` (Gap 2)

Surface LangGraph's `recursion_limit` in YAML and CLI.

```yaml
config:
  recursion_limit: 50   # default: 50 (down from LangGraph's 1000)
```

```bash
yamlgraph graph run graph.yaml --recursion-limit 50
```

Implementation: Read from `graph_config`, pass to `graph.invoke(inputs, config={"recursion_limit": N})`.

#### 3. Enforce `loop_limits` in ALL node types (Gap 3)

Move `check_loop_limit()` call from `llm_nodes.py` into a shared wrapper applied to **all** node factories: `create_tool_node`, `create_python_node`, `create_passthrough_node`.

#### 4. Linter W012: cycle without `loop_limits` (Gap 4)

Use existing `detect_loop_nodes()` result. For each node in a cycle, warn if no `loop_limits` entry exists.

```
W012: Node 'critique' is in a cycle but has no loop_limits entry
```

### P1 — Should-Have (production safety)

#### 5. Global execution timeout (Gap 5)

```yaml
config:
  timeout: 120          # seconds, default: None (no timeout)
```

```bash
yamlgraph graph run graph.yaml --timeout 120
```

Implementation: Wrap `graph.ainvoke()` in `asyncio.wait_for(coro, timeout=N)`. For sync path, use `signal.alarm` on Unix.

#### 6. Wire `max_tokens` to LLM calls (Gap 6)

```yaml
config:
  max_tokens: 4096      # graph-level default

nodes:
  summarize:
    type: llm
    max_tokens: 2048    # per-node override
```

Pass to `create_llm()` → LLM provider's `max_tokens` parameter.

#### 7. Fix `max_iterations` default mismatch (Gap 8)

Single source of truth: read from Pydantic schema default (10), remove hardcoded `default=5` in agent code.

### P2 — Nice-to-Have (observability)

#### 8. Token / cost tracking callback (Gap 7)

Extract `response.usage_metadata` from LLM responses. Accumulate in state field `_token_usage: dict`. Log summary at graph completion.

```python
# Accumulated in state
{
    "_token_usage": {
        "total_input_tokens": 12500,
        "total_output_tokens": 3200,
        "total_calls": 8
    }
}
```

#### 9. Linter E012: map node without `max_items` on dynamic expressions

Warn when `over:` expression is a state reference (not a literal list) and no `max_items` is set.

```
W013: Map node 'translate_all' fans out over dynamic expression 'state.chapters' without max_items
```

## YAML Surface Area (complete view)

```yaml
config:
  recursion_limit: 50     # P0 — max super-steps
  max_map_items: 100      # P0 — default fan-out cap
  timeout: 120            # P1 — global execution timeout (seconds)
  max_tokens: 4096        # P1 — per-LLM-call output cap

loop_limits:              # P0 — enforced on ALL node types
  critique: 3

nodes:
  translate_all:
    type: map
    over: "state.chapters"
    max_items: 20          # P0 — per-node fan-out override
    node: translate_one

  summarize:
    type: llm
    max_tokens: 2048       # P1 — per-node token override
```

## Acceptance Criteria

### P0
- [x] Map fan-out capped by `max_items` / `config.max_map_items` (default 100)
- [x] `recursion_limit` configurable via YAML `config:` and CLI `--recursion-limit` (default 50)
- [x] `check_loop_limit()` enforced in tool, python, and passthrough nodes
- [x] Linter W012: warns on cycles without `loop_limits`
- [x] All P0 items covered by tests with `@pytest.mark.req`

### P1
- [x] Global execution timeout via `config.timeout` and CLI `--timeout`
- [x] `max_tokens` wired from config to `create_llm()` calls
- [x] `max_iterations` default mismatch fixed (single source of truth)

### P2
- [ ] Token usage accumulated in `_token_usage` state field
- [x] Linter W013: warns on dynamic map `over:` without `max_items`

### Cross-cutting
- [x] Schema `graph-v1.json` updated for all new config keys
- [x] `reference/graph-yaml.md` documents all new keys
- [x] `ARCHITECTURE.md` requirements added (REQ-YG-055+)
- [x] `CHANGELOG.md` updated
- [x] Version bumped

## Alternatives Considered

1. **LangGraph `RemainingSteps` managed value** — Attractive for proactive loop detection, but requires injecting into YAMLGraph's dynamic state builder. Could be added as an enhancement on top of `recursion_limit` exposure. Not mutually exclusive.

2. **Budget guard middleware** — A `BudgetGuard` callback that aborts execution when cost exceeds a threshold. Requires per-model pricing tables. Better suited as a separate FR once token tracking (P2) is in place.

3. **Batch processing for map nodes** — `batch_size: N` to process map items in groups of N rather than all at once. More complex than simple `max_items` cap. Could be added later as FR-028.

## Related

- FR-010: Auto-detect loop nodes (`detect_loop_nodes()`)
- FR-021: Python map sub-nodes
- FR-026: Chaplain audit fixes (map_compiler non-dict guard)
- `yamlgraph/map_compiler.py` — fan-out via `Send()`
- `yamlgraph/error_handlers.py` — `check_loop_limit()`
- `yamlgraph/node_factory/llm_nodes.py` — loop limit check (LLM-only)
- `yamlgraph/config.py` — `DEFAULT_MAX_TOKENS` (dead code)
- `yamlgraph/models/graph_schema.py` — `max_iterations` schema default
- `yamlgraph/tools/agent.py` — `max_iterations` runtime default
- LangGraph docs: [Graph API — Recursion Limit](https://docs.langchain.com/oss/python/langgraph/graph-api#recursion-limit)
