# Feature Request: Expression Language Hardening

**ID:** 024
**Priority:** P1 - High
**Status:** ✅ Implemented (v0.4.26)
**Effort:** 2–3 days
**Requested:** 2026-02-10
**Origin:** TDD audit of expression language for `reference/expressions.md` (v0.4.25)

## Problem

The expression language has three verified defects / limitations discovered during TDD specification work (`tests/unit/test_expression_language.py`, 130 tests). All three cause **silent wrong results** — no error, no warning.

### 1. `and`/`or` keywords inside string values break conditions (BUG)

```yaml
# Looks correct. Silently fails.
condition: "status == 'done and dusted'"
# Regex \s+and\s+ splits inside the quoted value:
#   part 1: "status == 'done"   → ValueError or False
#   part 2: "dusted'"           → ValueError
# Result: False (wrong) or ValueError
```

**Violated constraint:** Condition evaluation must match user intent for valid-looking expressions.

**Traces:**
- `yamlgraph/utils/conditions.py` L108–110: `COMPOUND_OR_PATTERN.split(expr)` operates on raw string, unaware of quotes.
- `tests/unit/test_expression_language.py::TestEdgeCasesAndGotchas::test_condition_and_inside_quoted_value_breaks` — verified False instead of True.
- `tests/unit/test_expression_language.py::TestEdgeCasesAndGotchas::test_condition_or_inside_quoted_value_raises` — verified ValueError.

### 2. Right side of conditions cannot reference state

```yaml
# Intent: compare score to a dynamic threshold from state
condition: "score < threshold"
# Actual: 'threshold' parsed as literal string "threshold"
#   → 5 < "threshold" → TypeError → False
```

**Violated constraint:** Every cost-router / adaptive-threshold pattern requires comparing two state values.

**Traces:**
- `yamlgraph/utils/conditions.py` L63: `right_value = parse_literal(right_str)` — always literal, never state ref.
- `tests/unit/test_expression_language.py::TestEdgeCasesAndGotchas::test_condition_right_side_never_state_ref` — verified False.

### 3. Only binary operations — chained expressions silently wrong

```yaml
output:
  total: "{state.a + state.b + state.c}"
  # ARITHMETIC_PATTERN captures: left="state.a", op="+", right="state.b + state.c"
  # _parse_operand("state.b + state.c") → tries resolve_state_path("b + state.c") → None
  # _apply_operator(value_a, "+", None) → TypeError or wrong result
```

**Violated constraint:** Arithmetic expressions with 3+ terms look valid but produce wrong results.

**Traces:**
- `yamlgraph/utils/expressions.py` L10: `ARITHMETIC_PATTERN` captures everything after operator as single right operand.
- No test yet — this is the natural consequence of the regex-based binary parser.

## Proposed Fix

### Fix 1: Quote-aware compound split (BUG FIX)

Replace regex-based `and`/`or` split with a tokenizer that respects quoted regions:

```python
def _split_compound(expr: str, keyword: str) -> list[str] | None:
    """Split on ' and ' / ' or ' only outside quoted strings."""
    parts = []
    current = []
    in_quote = None
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch in ("'", '"') and in_quote is None:
            in_quote = ch
        elif ch == in_quote:
            in_quote = None
        if in_quote is None:
            # Check for keyword at this position
            pattern = f" {keyword} "
            if expr[i:i+len(pattern)].lower() == pattern:
                parts.append("".join(current))
                current = []
                i += len(pattern)
                continue
        current.append(ch)
        i += 1
    parts.append("".join(current))
    return parts if len(parts) > 1 else None
```

**Effort:** ~2 hours. Backward-compatible.

### Fix 2: State reference on right side (ENHANCEMENT)

If right operand starts with an identifier (no quotes, not numeric, not boolean/null), try resolving as state path before falling back to raw string:

```python
def _resolve_right_value(right_str: str, state: dict) -> Any:
    right_str = right_str.strip()
    # Try literal first
    if right_str[0] in ("'", '"') or right_str.lower() in ('true','false','null','none'):
        return parse_literal(right_str)
    try:
        as_num = parse_literal(right_str)
        if isinstance(as_num, (int, float)):
            return as_num
    except (ValueError, TypeError):
        pass
    # Try state path
    val = resolve_state_path(right_str, state)
    if val is not None:
        return val
    # Fallback: literal string
    return right_str
```

**Design decision:** When `threshold` exists in state, use it; when it doesn't, fall back to literal. This is backward-compatible — existing conditions with quoted strings or numeric literals work identically.

**Effort:** ~3 hours including tests. Requires careful testing of ambiguous cases.

### Fix 3: Chained arithmetic (ENHANCEMENT)

Two options:

**Option A (minimal):** Detect and raise `ValueError` on chained expressions instead of silent failure.

**Option B (full):** Recursive operand parsing — left-to-right evaluation of `a + b + c` as `(a + b) + c`. Requires replacing the single regex with a small expression parser.

**Recommendation:** Option A first (1 hour), Option B as follow-up if real-world demand emerges.

## Acceptance Criteria

| # | Criterion | Test |
|---|-----------|------|
| 1 | `status == 'done and dusted'` evaluates correctly | `test_condition_and_in_quoted_value_works` |
| 2 | `status == 'yes or no'` evaluates correctly | `test_condition_or_in_quoted_value_works` |
| 3 | `score < threshold` compares state.score to state.threshold | `test_condition_state_ref_on_right` |
| 4 | `a < b` where `b` is not in state falls back to literal `"b"` | `test_condition_right_literal_fallback` |
| 5 | `{state.a + state.b + state.c}` raises `ValueError` (Option A) or evaluates to sum (Option B) | `test_chained_arithmetic` |
| 6 | All existing 130 expression language tests still pass | `test_expression_language.py` |
| 7 | All existing 1500 tests still pass | Full suite |

## Impact

- **Fix 1** unblocks any condition comparing against string values containing common English words.
- **Fix 2** enables dynamic thresholds, adaptive routing, and state-to-state comparison — critical for cost-router and reflexion patterns.
- **Fix 3** prevents silent data corruption in passthrough transforms.

## Related

- `reference/expressions.md` — Expression language specification
- `tests/unit/test_expression_language.py` — TDD specification (130 tests)
- `yamlgraph/utils/conditions.py` — Condition evaluation
- `yamlgraph/utils/expressions.py` — Value expression resolution
- `docs-planning/ts-port.md` — TypeScript port (fixes would be ported)
