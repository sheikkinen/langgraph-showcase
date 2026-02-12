# TDD + Requirement Traceability Guide

## The Rule

Every test function MUST have `@pytest.mark.req("REQ-CALC-XXX")` linking
it to a requirement in `docs/RTM.md`.

## TDD Workflow with RTM

1. **Add requirement** to `docs/RTM.md` first
2. **Write failing test** with `@pytest.mark.req("REQ-CALC-XXX")` → RED
3. **Implement** until green → GREEN
4. **Verify**: `python scripts/req_coverage.py --strict` → PASS

## Enforcement

- `tests/conftest.py` rejects any test missing `@pytest.mark.req`
- `scripts/req_coverage.py --strict` exits non-zero if any REQ has zero tests

## Verification Commands

```bash
pytest                                          # all tests must have markers
python scripts/req_coverage.py                  # coverage summary
python scripts/req_coverage.py --detail         # per-req test list
python scripts/req_coverage.py --strict         # CI gate
```

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
