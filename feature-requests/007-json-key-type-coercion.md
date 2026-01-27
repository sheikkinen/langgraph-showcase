# Feature Request: Handle JSON integer key coercion in schema

**Priority:** MEDIUM  
**Type:** Enhancement  
**Status:** Proposed  
**Effort:** 1 day  
**Requested:** 2026-01-27

## Summary

Schema coding dict keys lose integer type after Redis round-trip. Silent template failures result.

## Problem

YAML schema:
```yaml
coding:
  0: Erinomainen
  1: Hyvä
```

After Redis (JSON serialization):
- Before: `{0: "Erinomainen", 1: "Hyvä"}`
- After: `{"0": "Erinomainen", "1": "Hyvä"}`

Jinja lookup `1 in {"0": ..., "1": ...}` returns False. Silent failure.

## Proposed Solution

**Option A (recommended):** Normalize coding keys to strings on schema load:
```python
field["coding"] = {str(k): v for k, v in field["coding"].items()}
```

**Option B:** Jinja filter:
```python
def code_label(value, coding):
    return coding.get(value) or coding.get(str(value)) or value
```

## Acceptance Criteria

- [ ] Consistent key types after checkpoint round-trip
- [ ] Existing templates work without modification
- [ ] Tests added

## Related

- questionnaire-api fix: 6174ff7 (template workaround)
