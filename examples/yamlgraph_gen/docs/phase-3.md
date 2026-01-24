# Phase 3: Execution Validation

> Add full graph execution as final validation step.

## Overview

Actually run the generated graph with test inputs to catch runtime errors.

## Prerequisites

- [x] Phase 0 complete: tools tested
- [x] Phase 1 complete: basic generator working
- [x] Phase 2 complete: clarification and errors

## Deliverables

| Deliverable | Description |
|-------------|-------------|
| `run_graph` tool integration | Execute generated graph |
| Execution result parsing | Extract errors from output |
| Semantic error detection | Identify LLM-level issues |

## Graph Changes

### Add Execution Step

```yaml
nodes:
  run_graph:
    type: python
    tool: runner
    requires: [lint_result]  # Only run if lint passes

edges:
  - from: lint_graph
    conditions:
      - if: "lint_result.valid == true"
        to: run_graph
      - if: "lint_result.valid == false"
        to: report_lint_error

  - from: run_graph
    conditions:
      - if: "run_result.valid == true"
        to: report_result
      - if: "run_result.valid == false"
        to: report_run_error
```

## Runner Tool

See: [samples/runner.py](samples/runner.py)

```python
def run_graph(graph_path: str, variables: dict) -> dict:
    """Run the generated graph with real LLM execution."""
    args = ["yamlgraph", "graph", "run", graph_path]
    for key, value in variables.items():
        args.extend(["--var", f"{key}={value}"])

    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=300,  # 5 min max
    )
    return {
        "valid": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "errors": _parse_run_errors(result.stderr) if result.returncode != 0 else [],
    }
```

## Success Criteria

- [x] Generated graphs actually run with test inputs
- [x] Lint validation catches structural errors
- [ ] Full execution validation in pipeline (deferred - using external helper script)

## Implementation Notes

Execution validation is done via the helper script `run_generator.py`:
- `--run` flag runs the generated graph after generation
- `--run-only` flag runs an existing graph
- Input can be passed via `--input key=value`

The E2E tests validate that generated graphs:
1. Pass linting (no structural errors)
2. Have all required prompt files

## Test Cases

1. **Success**: Generated graph runs end-to-end ✅ (validated manually)
2. **Prompt error**: Variable mismatch → caught by linter
3. **State error**: Missing state key → caught by linter

## Next Phase

→ [phase-4.md](phase-4.md) - Polish & Documentation (IN PROGRESS)
