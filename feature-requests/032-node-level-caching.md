# FR-032: Node-Level Caching

**Status**: Proposed
**Priority**: P0
**Effort**: 3-5 days
**Created**: 2026-02-13

## Summary

Add per-node result caching using LangGraph's `CachePolicy` to avoid redundant LLM calls and reduce API costs.

## Problem

Every graph execution re-invokes all nodes, even with identical inputs:

- **Dev iteration**: Change one node, re-run entire pipeline, pay for unchanged nodes
- **Repeated queries**: Same user question = same LLM call = same cost
- **Expensive operations**: Embedding generation, web searches re-run unnecessarily

No mechanism exists to cache and reuse results.

## Solution

Adopt LangGraph's `CachePolicy`:

```python
CachePolicy(
    key_func=default_cache_key,  # How to generate cache key from state
    ttl=None,                     # Time-to-live in seconds (None = forever)
)
```

## Proposed YAML Syntax

```yaml
# Option A: Simple boolean (cache indefinitely by state hash)
nodes:
  expensive_analysis:
    cache: true

# Option B: With TTL
nodes:
  web_search:
    cache:
      ttl: 3600  # Cache for 1 hour

# Option C: Development mode (short TTL, cache everything)
nodes:
  "*":  # Apply to all nodes
    cache:
      ttl: 300  # 5 minutes during dev
```

## Use Cases

### UC1: Expensive Embedding Generation

**Scenario**: Document processing graph generates embeddings for chunked text.

**Problem**: Re-processing same documents regenerates identical embeddings.

**Cost calculation**:
- 1000 documents × 100 chunks × $0.0001/embedding = $10/run
- Running 10 times during development = $100

**Solution**:
```yaml
nodes:
  generate_embeddings:
    type: tool
    tool: embed_text
    cache:
      ttl: 604800  # 1 week - embeddings don't change
```

**Savings**: With 80% cache hit rate → $2/run instead of $10 (80% reduction)

### UC2: Development Iteration Cycles

**Scenario**: Developer iterates on `step_3` while `step_1` and `step_2` are stable.

**Problem**: Every test run re-executes all steps.

**Timeline**:
- Full run: 60 seconds ($0.50)
- 20 iterations/day = 20 minutes waiting + $10/day

**Solution**:
```yaml
# dev-overlay.yaml
nodes:
  step_1:
    cache:
      ttl: 3600  # Cache during dev session
  step_2:
    cache:
      ttl: 3600
```

**Savings**: 5 seconds/iteration (step_3 only), $1/day

### UC3: Idempotent Web Searches

**Scenario**: Web search for same query returns same results within short window.

**Problem**: User asks similar questions → repeated identical searches.

**Solution**:
```yaml
nodes:
  web_search:
    type: tool
    tool: tavily_search
    cache:
      ttl: 300  # 5 minutes - fresh enough
```

**Savings**: Tavily @ $0.01/search, 100 searches/day with 70% duplicates = $0.70/day saved

### UC4: Innovation Matrix Cell Expansion

**Scenario**: 25-cell matrix expansion, some capability×constraint pairs produce similar analysis.

**Problem**: Similar inputs computed separately.

**Solution**:
```yaml
nodes:
  expand_cell:
    type: llm
    cache: true  # Cache by input hash
```

**Savings**: If 20% of cells have similar analysis → 5 fewer LLM calls

## Business Value

| Metric | Current | With CachePolicy |
|--------|---------|------------------|
| API costs (dev) | $50/day | $10/day |
| Iteration speed | 60s/run | 5s/run (cached) |
| Redundant LLM calls | 100% | 20% (80% cache hit) |
| Code to maintain | N/A | 0 (LangGraph native) |

## Implementation

1. **Schema** (0.5 day): Add `cache` field to node config
2. **Integration** (1-2 days): Wire `CachePolicy` into graph compilation
3. **Cache key customization** (1 day): Support custom key functions
4. **Storage backend** (optional): Memory default, file-based for persistence
5. **Tests** (1 day): TTL expiry, key collisions, invalidation

## Cache Key Strategy

Default key = hash of:
- Node name
- Relevant state values (inputs to node)
- Model/provider (if LLM node)

```python
def default_cache_key(state, node_config):
    relevant_state = extract_node_inputs(state, node_config)
    return hashlib.sha256(
        f"{node_config.name}:{json.dumps(relevant_state, sort_keys=True)}"
    ).hexdigest()
```

## Cache Invalidation

- TTL expiry (automatic)
- Manual: `yamlgraph cache clear`
- Per-graph: `yamlgraph cache clear --graph=pipeline.yaml`
- Development: `yamlgraph graph run pipeline.yaml --no-cache`

## Dependencies

- LangGraph >= 0.2.24 (for CachePolicy)
