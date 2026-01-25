# Test Case: Router Pattern

**Status:** ✅ PASSED (generator fixed)

## Request

```
Classify customer feedback as positive, negative, or neutral, and generate an appropriate response for each type
```

## Reference

Compare with `graphs/router-demo.yaml`

## Validation Commands

```bash
cd examples/yamlgraph_gen

# Generate
python run_generator.py -o outputs/router-test \
  'Classify customer feedback as positive, negative, or neutral, and generate an appropriate response for each type'

# Structural checks
grep -A5 "type: router" outputs/router-test/graph.yaml
grep -A10 "routes:" outputs/router-test/graph.yaml
grep -A20 "edges:" outputs/router-test/graph.yaml

# Execute
source ../../.env && cd outputs/router-test && \
yamlgraph graph run graph.yaml --var 'feedback=This product is amazing, I love it!'
```

## Success Criteria

- [ ] Router node has type: router with routes: mapping
- [ ] Route keys match schema field (e.g., intent or sentiment)
- [ ] Each route target has a corresponding handler node
- [ ] Edges connect router to all handlers
- [ ] No orphan nodes (all nodes reachable from START)
- [ ] Prompts exist for router and all handlers
- [ ] Execution routes correctly based on input

## Test Inputs

| Input | Expected Route |
|-------|----------------|
| "This product is amazing!" | positive |
| "Terrible service, never again" | negative |
| "It works as expected" | neutral |

## Results

### Success Criteria

- [x] Router node has type: router with routes: mapping
- [x] Route keys match schema field (intent)
- [x] Each route target has a corresponding handler node
- [x] Edges connect router to all handlers (conditional edge type)
- [x] No orphan nodes (all nodes reachable from START)
- [x] Prompts exist for router and all handlers
- [x] Execution routes correctly based on input

### Generated Structure

**Original (incorrect):**
- Generator created separate `classify_feedback` (type: llm) + `route_response` (type: router) nodes
- Router node missing prompt field → execution error

**Fixed:**
```yaml
nodes:
  classify_feedback:
    type: router
    prompt: classify_feedback
    routes:
      positive: generate_positive_response
      negative: generate_negative_response
      neutral: generate_neutral_response
    default_route: generate_neutral_response
    variables:
      feedback: "{state.feedback}"
    state_key: classification

edges:
  - from: START
    to: classify_feedback
  - from: classify_feedback
    to: [generate_positive_response, generate_negative_response, generate_neutral_response]
    type: conditional
```

### Execution Output

```
Status Expected   Classified   Routed To
============================================================
✅      positive   positive     generate_positive_response
✅      negative   negative     generate_negative_response
✅      neutral    neutral      generate_neutral_response
```

### Issues Found & Fixed

| Issue | Description | Severity | Status |
|-------|-------------|----------|--------|
| Generator split router into 2 nodes | Created separate LLM + router nodes instead of combined | High | ✅ Fixed |
| Prompt schema field mismatch | Used `classification` field instead of `intent`/`tone` | Medium | ✅ Fixed |
| Missing prompt in router node | Router node generated without required prompt field | High | ✅ Fixed |
| Routes format incorrect | Dict routes changed to list format | High | ✅ Fixed |
| Edge list syntax split | Conditional edge list split into multiple edges | Medium | ✅ Fixed |
| Missing variables field | Occasionally omits variables block from nodes | Low | ⚠️ LLM variance |

### Generator Fixes Applied

**Snippet Updates:**
1. `snippets/patterns/classify-then-process.yaml` - Single combined router with dict routes
2. `snippets/nodes/router-basic.yaml` - Correct router structure template
3. `snippets/prompt-scaffolds/router-classify.yaml` - Uses `intent` field

**Prompt Updates:**
4. `prompts/assemble_graph.yaml` - Explicit dict/list preservation with examples
5. `prompts/generate_prompts.yaml` - Router schema field requirements

**Architecture Improvement:**
6. Pattern-specific guidance moved to snippet comments (self-documenting)

### Framework Constraint

**Router field name hardcoded:** `yamlgraph/node_factory/llm_nodes.py:170-172`
```python
route_key = getattr(result, "tone", None) or getattr(
    result, "intent", None
)
```
All router prompts must use `intent` or `tone` as the classification field.
