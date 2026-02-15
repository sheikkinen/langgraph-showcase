# Feature Request: Runtime State Interpolation in Prompt Paths

**Priority:** LOW (can work around with current architecture)
**Use Case:** Reusable subgraphs with questionnaire-specific prompts

## Problem

Subgraphs are compiled at graph load time. Prompt paths are resolved during compilation, not execution. This means:

```yaml
# _common/interview-flow.yaml (reusable subgraph)
nodes:
  extract_fields:
    type: llm
    prompt: "{state.prompts_dir}/extract"  # ❌ Doesn't work - literal string
```

The `{state.prompts_dir}` is treated as a literal path, not interpolated.

## Current Workaround

Don't use subgraphs for flows that need different prompts. Instead:
1. Inline the flow in each questionnaire's graph
2. Use static prompt paths per questionnaire

This works but loses the DRY benefit of subgraphs.

## Proposed Solution

### Runtime prompt resolution

```yaml
nodes:
  extract_fields:
    type: llm
    prompt: "{state.prompts_dir}/extract"
    prompt_runtime: true  # Resolve at execution time
```

**Implementation:**
- When `prompt_runtime: true`, defer prompt resolution to node execution
- At execution time, interpolate `{state.field}` patterns
- Then resolve the resulting path normally

### Alternative: Prompt as variable

```yaml
nodes:
  extract_fields:
    type: llm
    prompt_var: extract_prompt  # Read prompt path from state
    variables:
      schema: "{state.schema}"
```

Parent graph sets `extract_prompt` in state before calling subgraph.

## Trade-offs

**Pros:**
- True reusable subgraphs
- Single interview flow for all questionnaires

**Cons:**
- Complexity: prompts resolved at two different times
- Validation: can't check prompt exists at compile time
- Performance: prompt loaded on each execution (could cache)

## Recommendation

Given the workarounds exist, this is lower priority than graph-relative prompts. The current architecture (inline flows with static prompts) works and is explicit about which prompts each questionnaire uses.

If implemented, combine with graph-relative prompts for best effect.
