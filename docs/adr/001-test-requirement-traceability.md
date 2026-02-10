# ADR-001: Test-to-Requirement Traceability via Pytest Markers

**Date**: 2026-02-10
**Status**: Accepted
**Context**: Capabilities & Requirements Traceability in ARCHITECTURE.md

## Decision

Use `@pytest.mark.req("REQ-YG-XXX")` markers to link tests to requirements.

## Context

ARCHITECTURE.md maps 46 requirements across 12 capabilities to modules. The missing link is **module → tests → requirement**. Three options were evaluated:

1. **Static coverage table** — aggregate `--cov` per capability. Imprecise (file coverage ≠ requirement coverage), stale on commit, no CI enforcement.
2. **Pytest markers** — `@pytest.mark.req(...)` on test functions. Precise, live, CI-enforceable.
3. **YAML mapping file** — external `tests/requirement-map.yaml`. No code changes, but drifts silently.

Option 1 was rejected as it provides zero value if option 2 is implemented immediately — it would be a static snapshot superseded by live markers on the same commit. Option 3 drifts without enforcement.

## Implementation

### 1. Register the marker in `pyproject.toml`

```toml
[tool.pytest.ini_options]
markers = [
    "req(id): links test to a requirement (e.g., REQ-YG-014)",
]
```

### 2. Tag tests

```python
@pytest.mark.req("REQ-YG-014")
def test_invoke_with_retry_succeeds():
    ...
```

Multiple requirements per test are allowed:

```python
@pytest.mark.req("REQ-YG-014", "REQ-YG-031")
def test_retry_exhaustion_raises():
    ...
```

### 3. Collection script (`scripts/req-coverage.py`)

Collect markers and report which requirements have tests and which don't:

```bash
pytest --co -q | python scripts/req-coverage.py
```

Output: requirement → test count matrix, flagging any REQ with zero tests.

### 4. CI gate (future)

Add a pre-commit or CI step that fails if any REQ-YG-* has zero marked tests.

## Consequences

- **Positive**: Precise traceability, CI-verifiable, survives refactors, incremental adoption.
- **Negative**: Discipline required to tag new tests. ~200 existing tests need tagging (can be done incrementally).
- **Migration**: Tag tests as they are touched. No big-bang required.
