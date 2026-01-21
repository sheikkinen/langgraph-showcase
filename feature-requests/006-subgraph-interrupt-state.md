# Feature Request: Subgraph State Exposure During Interrupts

**ID:** 006
**Priority:** P2 - Nice to Have
**Status:** ✅ Implemented (v0.3.8)
**Effort:** 2-3 days
**Requested:** 2026-01-20
**Implemented:** 2026-01-20

## Summary

Expose selected subgraph state to the parent graph when a subgraph hits an interrupt node. Currently, `output_mapping` only applies when the subgraph completes (reaches END).

## Motivation

When building multi-part questionnaire flows with subgraphs, the parent graph has no visibility into the current subgraph's progress during interrupts. This makes debugging and monitoring difficult:

**Current behavior:**
```python
result = parent_graph.invoke({"user_message": ""}, config)
# result contains only parent state, subgraph state is hidden
print(result.get("phase"))      # None
print(result.get("extracted"))  # None
print(result.get("gaps"))       # None
```

**Use cases:**
- CLI debug output showing extraction progress
- API response including current phase and extracted fields
- Monitoring dashboards tracking conversation state
- Logging for troubleshooting stuck conversations

## Proposed Solution

### Option A: `interrupt_output_mapping`

Add a separate mapping that applies during interrupts:

```yaml
nodes:
  run_demographics:
    type: subgraph
    graph: demographics/graph.yaml
    input_mapping:
      user_message: user_message
    output_mapping:            # Applied on subgraph completion
      demographics_complete: complete
      demographics_extracted: extracted
    interrupt_output_mapping:  # Applied on subgraph interrupt
      current_phase: phase
      current_extracted: extracted
      current_gaps: gaps
```

### Option B: Unified mapping with `on_interrupt` flag

```yaml
nodes:
  run_demographics:
    type: subgraph
    graph: demographics/graph.yaml
    output_mapping:
      demographics_complete:
        from: complete
        on: complete           # Only on completion
      demographics_extracted:
        from: extracted
        on: complete
      current_phase:
        from: phase
        on: interrupt          # During interrupts
      current_extracted:
        from: extracted
        on: [interrupt, complete]  # Both
```

### Option C: Auto-prefix subgraph state

Automatically expose subgraph state with a prefix:

```yaml
nodes:
  run_demographics:
    type: subgraph
    graph: demographics/graph.yaml
    expose_state: true         # or: expose_state: "demographics_"
```

Result would include:
```python
{
    "demographics_phase": "probing",
    "demographics_extracted": {...},
    "demographics_gaps": ["gender", "living_arrangement"]
}
```

## Recommendation

**Option A** is cleanest - explicit separate mapping for interrupt vs completion. It's easy to understand and doesn't change existing behavior.

## Implementation Notes

### Initial Approach (Failed)

The naive approach assumed `compiled.invoke()` returns a dict with `__interrupt__`:

```python
child_output = compiled.invoke(child_input, child_config)
if "__interrupt__" in child_output:
    return apply_mapping(child_output, interrupt_mapping)
```

**Problem:** When invoked from within a parent node, `compiled.invoke()` raises `GraphInterrupt` exception instead of returning. The exception propagates up, bypassing any mapping code.

### Working Solution: Pregel Internal API

LangGraph's execution engine is called **Pregel** (named after [Google's Pregel paper](https://research.google/pubs/pub36726/) for distributed graph processing).

The Pregel runtime passes internal mechanisms via `config["configurable"]`:

```python
config = {
    "configurable": {
        "thread_id": "...",
        "__pregel_send": <deque.extend>,      # Inject state updates
        "__pregel_checkpointer": <Saver>,     # Checkpoint access
        "__pregel_task_id": "...",            # Current task ID
        # ... more internal plumbing
    }
}
```

**Solution:** Use `__pregel_send` to inject mapped child state **before** re-raising the interrupt:

```python
except GraphInterrupt as e:
    if interrupt_output_mapping:
        # Get child state from checkpointer
        child_state = compiled.get_state(child_config)
        parent_updates = _map_output_state(child_state.values, interrupt_output_mapping)

        # Use Pregel's internal send to inject updates
        send = config.get("configurable", {}).get("__pregel_send")
        if send:
            send([(k, v) for k, v in parent_updates.items()])

    raise  # Re-raise to pause the graph
```

### Caveats

⚠️ **`__pregel_send` is an internal, undocumented API.** It may change in future LangGraph versions.

There is no official way to update state when a node raises an exception. This solution was discovered by inspecting the config passed to nodes and testing behavior.

### References

**LangGraph Source Code:**
- [CONFIG_KEY_SEND constant](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/_internal/_constants.py#L29) - `__pregel_send` definition
- [Pregel.bulk_update_state](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/pregel/main.py#L1429) - How `CONFIG_KEY_SEND` is used internally
- [PregelProtocol](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/pregel/protocol.py) - Abstract interface for Pregel graphs

**LangGraph Documentation:**
- [Google Pregel Paper](https://research.google/pubs/pub36726/) - Original distributed graph processing model
- [LangGraph Interrupts](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/) - Official interrupt documentation
- [LangGraph Subgraphs](https://langchain-ai.github.io/langgraph/how-tos/subgraph/) - Subgraph patterns
- [LangGraph Errors Reference](https://langchain-ai.github.io/langgraph/reference/errors/) - `GraphInterrupt` exception docs

## Recommended Pattern: Pre-Interrupt Snapshot

While FR-006 handles the **parent-side injection**, the child graph can prepare its state for export using a pre-interrupt node:

```
Child Graph Flow:
  [analyze] → [prepare_snapshot] → [interrupt]
                      ↑
              Explicitly formats what
              parent should see
```

### Child Graph

```yaml
# demographics/graph.yaml
state:
  phase: str
  extracted: object
  gaps: list
  export: object        # ← Published state for parent

nodes:
  analyze:
    type: llm
    output: analysis

  prepare_for_interrupt:
    type: python
    tool: build_export_snapshot
    # Copies selected fields to export

  wait_for_user:
    type: interrupt
```

### Parent Graph

```yaml
nodes:
  run_demographics:
    type: subgraph
    graph: demographics/graph.yaml
    interrupt_output_mapping:
      current_phase: export.phase        # Read from prepared snapshot
      current_extracted: export.extracted
      current_gaps: export.gaps
```

### Benefits

- ✅ Child explicitly controls what gets exposed
- ✅ Clean separation — child prepares, parent maps
- ✅ No parent knowledge of child's internal structure needed
- ✅ Easy to add computed/formatted fields for export

### Caveat: Still Requires Pregel Internal API

⚠️ **This pattern does NOT remove the dependency on `__pregel_send`.**

The pre-interrupt snapshot only prepares data in the child's state. The parent still needs FR-006's exception-handler mechanism to inject that data before re-raising `GraphInterrupt`:

```python
# node_factory.py - FR-006 implementation
except GraphInterrupt:
    child_state = compiled.get_state(child_config)
    parent_updates = _map_output_state(child_state.values, interrupt_output_mapping)

    # STILL REQUIRED: Pregel internal API to inject state
    send = config.get("configurable", {}).get("__pregel_send")
    if send:
        send([(k, v) for k, v in parent_updates.items()])

    raise  # Graph pauses here
```

Without `__pregel_send`, the mapped state cannot be injected before the graph pauses. There is no official LangGraph API for updating state when a node raises an exception.

**Risk:** If LangGraph changes `__pregel_send` in a future version, this feature will break.

---

## Alternatives Considered

### 1. Access subgraph state via checkpointer
**Rejected:** Requires knowing subgraph thread_id structure, not portable.

### 2. Return full subgraph state nested
**Rejected:** Pollutes parent state, hard to work with.

### 3. Debug mode that logs subgraph state
**Partial:** Useful for logging but doesn't help API responses.

### 4. Separate state-capture node in parent graph
**Rejected:** When subgraph raises `GraphInterrupt`, the parent graph pauses immediately. No post-interrupt node can run — there's no "between interrupt and pause" hook in LangGraph's exception model.

## Acceptance Criteria

- [x] `interrupt_output_mapping` recognized in subgraph node config
- [x] Mapping applies when subgraph returns with `__interrupt__`
- [x] Original `output_mapping` still only applies on completion
- [x] Works with nested subgraphs
- [x] Schema validation for new config key
- [x] Documentation updated
- [x] Test with multi-turn subgraph flow

## Example Use Case

questionnaire-api parent orchestrator:

```yaml
nodes:
  run_demographics:
    type: subgraph
    graph: demographics/graph.yaml
    input_mapping:
      user_message: user_message
    output_mapping:
      demographics_complete: complete
      demographics_extracted: extracted
    interrupt_output_mapping:
      active_subgraph: "'demographics'"  # Literal
      current_phase: phase
      current_extracted: extracted
      current_gaps: gaps
```

CLI can then show:
```
🤖 What year were you born?
----------------------------------------
Subgraph: demographics
Phase: probing
Extracted: {birth_year: 1956, gender: 2}
Gaps: [primary_language, marital_status, living_arrangement, residence_type, referral_source]
```

## Related

- Feature #001: Interrupt Node (dependency - this extends interrupt behavior)
- LangGraph subgraph docs: https://langchain-ai.github.io/langgraph/how-tos/subgraph/
