# TDD + Requirement Traceability Guide

## The Rule

Every test function MUST have `@pytest.mark.req("REQ-CALC-XXX")` linking
it to a requirement in `docs/RTM.md`.

## TDD Workflow with RTM

1. **Add requirement** to `docs/RTM.md` first
2. **Write failing test** with `@pytest.mark.req("REQ-CALC-XXX")` → RED
3. **Implement** until green → GREEN
4. **Verify**: `python scripts/req_coverage.py --strict` → PASS
5. **Trace**: `python scripts/req_coverage.py --implementation` → full chain

## Enforcement

- `tests/conftest.py` rejects any test missing `@pytest.mark.req`
- `scripts/req_coverage.py --strict` exits non-zero if any REQ has zero tests

## Verification Commands

```bash
pytest                                              # all tests must have markers
python scripts/req_coverage.py                      # summary with capability coverage
python scripts/req_coverage.py --detail             # per-req test list
python scripts/req_coverage.py --implementation     # req → source files → tests
python scripts/req_coverage.py --strict             # CI gate (exit 1 on gaps)
```

## Implementation Traceability

The `--implementation` flag shows the full chain: requirement → source files → tests.

Source file resolution uses a hybrid approach:
1. **Coverage DB** (best) — `.coverage` SQLite from `pytest --cov=src --cov-context=test`
2. **AST imports** (fallback) — parses `from calculator import ...` in test files
3. **No link** — tests that don't touch source (e.g. pure assertion tests)

## Adding a New Feature

1. Add `REQ-CALC-XXX` row to `docs/RTM.md`
2. Write test: `@pytest.mark.req("REQ-CALC-XXX")` → RED
3. Implement → GREEN
4. `req_coverage.py --strict` → PASS

## Multi-Requirement Tagging

A test can cover multiple requirements:

```python
@pytest.mark.req("REQ-CALC-001", "REQ-CALC-004")
def test_add_rejects_string():
    with pytest.raises(TypeError):
        add("a", 1)
```
