# Feature Request: JSON Extraction from LLM Output

**Priority:** MEDIUM  
**Use Case:** Structured extraction where LLMs add explanatory text

## Problem

When using `output:` schema in prompts, LLMs often return:

```
```json
{"frequency": 3, "amount": null}
```

**Reasoning:** The user explicitly mentioned drinking 2-3 times per week...
```

The JSON is valid but wrapped in markdown and followed by explanation. Currently:
- The raw string goes to `state_key`
- Downstream handlers must parse it manually
- Common pattern leads to repeated boilerplate

## Current Workaround

```python
def detect_gaps(state: dict) -> dict:
    extracted = state.get("extracted") or {}
    
    # Parse JSON from markdown code blocks
    if isinstance(extracted, str):
        import re, json
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', extracted, re.DOTALL)
        if match:
            extracted = json.loads(match.group(1).strip())
```

## Proposed Solution

### Node-level option

```yaml
extract_fields:
  type: llm
  prompt: extract
  state_key: extracted
  parse_json: true  # Extract JSON from response
```

**Behavior when `parse_json: true`:**
1. Try to parse response as raw JSON first
2. If that fails, look for ```json ... ``` code block
3. If that fails, look for ``` ... ``` (any code block)
4. If that fails, look for `{...}` pattern
5. Store parsed dict/list in state_key
6. Optionally store raw response in `{state_key}_raw`

### With validation

```yaml
extract_fields:
  type: llm
  prompt: extract
  state_key: extracted
  parse_json: true
  json_schema:  # Optional validation
    type: object
    additionalProperties: true
```

## Alternative: Output model parsing

If `output_model` is specified, yamlgraph already uses structured output. But when using inline `output:` schema, the LLM doesn't always follow format strictly.

Could add a fallback parser:
```yaml
output:
  type: object
  properties:
    frequency:
      type: integer
  parse_from_markdown: true  # Try to extract if not valid JSON
```

## Benefits

1. **Less boilerplate** - Common pattern handled automatically
2. **Robust extraction** - Handles various LLM output formats
3. **Cleaner handlers** - Python functions receive parsed dicts
