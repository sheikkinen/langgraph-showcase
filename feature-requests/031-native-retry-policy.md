# FR-031: Native Retry Policy

**Status**: Proposed
**Priority**: P0
**Effort**: 2-3 days
**Created**: 2026-02-13

## Summary

Replace YAMLGraph's custom `on_error: retry` with LangGraph's native `RetryPolicy` for exponential backoff, jitter, and conditional retry.

## Problem

Current retry implementation has significant limitations:

```yaml
# Current syntax
nodes:
  generate:
    on_error: retry
    max_retries: 3  # Simple count-based retry
```

**Issues**:
1. No exponential backoff - retries hammer the API immediately
2. No jitter - multiple clients retry simultaneously causing storms
3. No configurable conditions - retries all errors equally (including validation errors that will never succeed)
4. 150+ lines of custom Python code to maintain

## Solution

Adopt LangGraph's battle-tested `RetryPolicy`:

```python
RetryPolicy(
    initial_interval=0.5,    # Start with 0.5s wait
    backoff_factor=2.0,      # Double each retry: 0.5 → 1 → 2 → 4s
    max_interval=128.0,      # Cap at 128s
    max_attempts=3,          # Total attempts
    jitter=True,             # Randomize to prevent storms
    retry_on=default_retry_on  # Customizable condition
)
```

## Proposed YAML Syntax

```yaml
# Option A: Simple boolean (uses sensible defaults)
nodes:
  generate:
    retry: true

# Option B: Inline configuration
nodes:
  generate:
    retry:
      max_attempts: 5
      backoff_factor: 2.0
      jitter: true

# Option C: Named policies (graph-level, reusable)
retry_policies:
  aggressive:
    max_attempts: 10
    initial_interval: 0.1
    max_interval: 60
  gentle:
    max_attempts: 3
    initial_interval: 2.0
    backoff_factor: 3.0

nodes:
  generate:
    retry: aggressive
  web_search:
    retry: gentle
```

## Use Cases

### UC1: Rate-Limited API Calls

**Scenario**: Graph calls external APIs (web search, embeddings) with rate limits.

**Problem**: Without backoff, rapid retries hit rate limits repeatedly, wasting time and potentially getting blocked.

**Solution**:
```yaml
nodes:
  web_search:
    type: tool
    tool: tavily_search
    retry:
      max_attempts: 5
      initial_interval: 1.0
      backoff_factor: 3.0  # 1s → 3s → 9s → 27s
```

### UC2: Transient LLM Failures

**Scenario**: Cloud LLM returns 503/429 under load (common with Claude/GPT during peak hours).

**Problem**: Simple retry without jitter causes synchronized retries across all users.

**Solution**:
```yaml
nodes:
  generate:
    type: llm
    retry:
      jitter: true  # Adds randomness: 4s becomes 3.2-4.8s
```

### UC3: Conditional Retry

**Scenario**: Retry rate limits and server errors, but NOT validation errors (which will never succeed).

**Problem**: Current system retries all errors equally, wasting API calls on hopeless retries.

**Solution**:
```yaml
nodes:
  generate:
    retry:
      retry_on: ["RateLimitError", "ServiceUnavailable", "ConnectionError"]
      # Don't retry: ValidationError, AuthenticationError, BadRequestError
```

## Business Value

| Metric | Current | With RetryPolicy |
|--------|---------|------------------|
| Rate limit errors reaching user | ~5% | ~0.5% |
| Custom retry code | 150 lines | 0 lines (use LangGraph) |
| Configuration | Python-only | YAML declarative |
| Retry storms | Possible | Prevented by jitter |

## Implementation

1. **Schema** (0.5 day): Add `retry` field to node config
2. **Integration** (1 day): Wire `RetryPolicy` into node factory
3. **Graph-level policies** (0.5 day): Add `retry_policies` block
4. **Tests** (0.5 day): Unit tests for all options
5. **Deprecation** (0.5 day): Deprecate `on_error: retry` with migration path

## Migration

```yaml
# v0.4.x (deprecated)
nodes:
  generate:
    on_error: retry
    max_retries: 3

# v0.5.x (new)
nodes:
  generate:
    retry:
      max_attempts: 3
      jitter: true
```

`on_error: retry` will continue working through v0.6.x with deprecation warning.

## Dependencies

- LangGraph >= 0.2.24 (for RetryPolicy)
