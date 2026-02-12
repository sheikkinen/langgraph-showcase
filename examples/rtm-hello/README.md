# RTM Hello — TDD + Requirement Traceability

A self-contained example showing how to enforce requirement traceability
in a Python project using pytest markers and AST-based tooling.

## Quickstart

```bash
cd examples/rtm-hello
pytest                                            # 10 tests, all GREEN
python scripts/req_coverage.py                    # summary with capability coverage
python scripts/req_coverage.py --detail           # per-req test list
python scripts/req_coverage.py --implementation   # req → source files → tests
python scripts/req_coverage.py --strict           # CI gate (exit 1 on gaps)
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
5. **Implementation** via `--implementation` — links req → source → tests using:
   - `.coverage` SQLite DB (from `pytest --cov=src --cov-context=test`)
   - AST import analysis as fallback
   - Grouped by capability sections from RTM.md

## Coverage DB (optional)

For runtime traceability linking tests to source files via execution data:

```bash
pytest --cov=src --cov-context=test       # generate .coverage DB
python scripts/req_coverage.py --implementation   # uses DB + AST fallback
```
