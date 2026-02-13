# FR-030: Map Node Concurrency Control

## Problem

Map nodes use LangGraph's `Send()` API which parallelizes all items simultaneously. This causes problems with:

1. **Local LLMs** (LM Studio, Ollama): Can only handle one request at a time, causing hangs or timeouts
2. **Rate-limited APIs**: Burst of 25+ requests may hit rate limits
3. **Memory pressure**: Large fan-out with heavy processing can exhaust resources

## Current Behavior

```yaml
expand_all:
  type: map
  over: "{state.pairs}"  # 25 items
  as: pair
  max_items: 25
  node:
    prompt: expand_cell
```

All 25 LLM calls execute simultaneously via `Send()`.

## Proposed Solution

Add `max_concurrency` parameter to control parallel execution:

```yaml
expand_all:
  type: map
  over: "{state.pairs}"
  as: pair
  max_items: 25
  max_concurrency: 1  # Sequential execution (for local LLMs)
  # max_concurrency: 5  # Batched execution (for rate-limited APIs)
  # max_concurrency: 0  # Unlimited (default, current behavior)
  node:
    prompt: expand_cell
```

## Implementation Notes

Options:
1. **Semaphore wrapper**: Wrap sub-node execution in asyncio.Semaphore
2. **Batched Send()**: Emit Send() calls in batches, wait for completion between batches
3. **Sequential fallback**: When `max_concurrency: 1`, use simple loop instead of Send()

LangGraph's `Send()` doesn't natively support concurrency limits, so this would need custom implementation.

## Use Cases

- `innovation_matrix/pipeline.yaml`: 25 cell expansions, fails with LM Studio
- Any map node with >10 items targeting local/rate-limited providers

## Acceptance Criteria

- [ ] `max_concurrency: 1` processes items sequentially
- [ ] `max_concurrency: N` processes in batches of N
- [ ] `max_concurrency: 0` or omitted = unlimited (current behavior)
- [ ] Works with all sub-node types (llm, python, router)

## Priority

Medium - Workaround exists (use cloud provider), but limits local development.
