# RTM Hello — TDD + Requirement Traceability

A self-contained example showing how to enforce requirement traceability
in a Python project using pytest markers and AST-based tooling.

## Quickstart

```bash
cd examples/rtm-hello
pytest                                    # 11 tests, all GREEN
python scripts/req_coverage.py            # 4/4 requirements covered
python scripts/req_coverage.py --detail   # per-req test list
python scripts/req_coverage.py --strict   # CI gate (exit 1 on gaps)
```

## Project Structure

```
examples/rtm-hello/
├── docs/
│   ├── RTM.md              # Requirements table (source of truth)
│   └── RTM-guide.md        # TDD + RTM methodology
├── src/
│   └── calculator.py       # Implementation (add, sub, mul)
├── tests/
│   ├── conftest.py          # Enforcement hook (@pytest.mark.req required)
│   └── test_calculator.py   # Tagged tests
├── scripts/
│   └── req_coverage.py      # Traceability checker
├── pyproject.toml            # Marker registration + ruff config
└── README.md                 # This file
```

## Delivery Checklist

- [ ] `pytest` → all GREEN
- [ ] `python scripts/req_coverage.py --strict` → 4/4, exit 0
- [ ] Remove a `@pytest.mark.req` → `pytest` fails with traceability violation
- [ ] Add `REQ-CALC-005` to RTM.md without test → `--strict` fails

## How It Works

1. **Requirements** live in `docs/RTM.md` as a parseable Markdown table
2. **Tests** must have `@pytest.mark.req("REQ-CALC-XXX")`
3. **Enforcement** via `tests/conftest.py` — pytest rejects unmarked tests
4. **Coverage** via `scripts/req_coverage.py` — AST extracts markers, checks all reqs

## Next Steps

See the parent [YAMLGraph](../../) project for the full-scale implementation:
- 64 requirements across 18 capabilities
- Coverage-DB + AST hybrid resolution
- `.coverage` SQLite integration for runtime traceability
