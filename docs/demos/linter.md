# Demo: Graph Linter

**Capability:** Static analysis for YAML graph configurations
**CLI Command:** `yamlgraph graph lint <graph_path> [graph_path ...]`
**Modules:** `linter/checks.py`, `linter/graph_linter.py`, `linter/patterns/*`
**Requirements:** REQ-YG-003, REQ-YG-053

## Scenario

Validate graph YAML files before execution to catch misconfigurations, typos, and silent failure modes that would otherwise only surface at runtime.

## Quick Start

```bash
# Lint a single graph
yamlgraph graph lint examples/demos/hello/graph.yaml

# Lint all demo graphs
yamlgraph graph lint examples/demos/*/graph.yaml

# Lint a graph with known defects (exit code 1)
yamlgraph graph lint tests/fixtures/linter/edge_refs_fail.yaml
```

## Acceptance Flow

### 1. Clean Graph — Zero Issues

```bash
$ yamlgraph graph lint examples/demos/hello/graph.yaml
✅ graph.yaml - No issues found

✅ All graphs passed linting
```

**Exit code:** 0

### 2. Typo in Edge Reference — E006

```yaml
# tests/fixtures/linter/edge_refs_fail.yaml
edges:
  - from: genrate    # ← typo
    to: END
```

```bash
$ yamlgraph graph lint tests/fixtures/linter/edge_refs_fail.yaml
❌ edge_refs_fail.yaml
   ❌ [E006] Edge 'from' references non-existent node 'genrate'
      Fix: Check spelling; defined nodes: generate
```

### 3. Passthrough Without Output — E601

```yaml
# tests/fixtures/linter/passthrough_fail.yaml
nodes:
  transform:
    type: passthrough
    # missing output — silent no-op at runtime
```

```bash
$ yamlgraph graph lint tests/fixtures/linter/passthrough_fail.yaml
❌ passthrough_fail.yaml
   ❌ [E601] Passthrough node 'transform' has no 'output' — it will be a silent no-op
      Fix: Add 'output:' mapping to node 'transform'
```

### 4. tool_call Missing Fields — E701, E702

```yaml
# tests/fixtures/linter/tool_call_fail.yaml
nodes:
  do_search:
    type: tool_call
    state_key: result
    # missing: tool, args
```

```bash
$ yamlgraph graph lint tests/fixtures/linter/tool_call_fail.yaml
❌ tool_call_fail.yaml
   ❌ [E701] tool_call node 'do_search' missing required 'tool' field
      Fix: Add 'tool: <tool_name>' to node 'do_search'
   ❌ [E702] tool_call node 'do_search' missing required 'args' field
      Fix: Add 'args:' mapping to node 'do_search'
```

### 5. Condition Syntax — W801

```yaml
# Wrong: braces in condition
condition: "{state.score} < 0.8"

# Right: bare variable names
condition: "score < 0.8"
```

```bash
$ yamlgraph graph lint tests/fixtures/linter/condition_syntax_fail.yaml
⚠️ condition_syntax_fail.yaml
   ⚠ [W801] Condition '{state.score} < 0.8' uses braces — conditions use bare variable names
      Fix: Remove {{ }} braces and 'state.' prefix from condition expression
```

### 6. Batch Linting

```bash
$ yamlgraph graph lint examples/demos/*/graph.yaml
✅ graph.yaml - No issues found
✅ graph.yaml - No issues found
...
⚠️ graph.yaml
   ⚠ [W001] Tool 'analyze_text' is defined but never used
      Fix: Remove unused tool 'analyze_text' from tools section
✅ graph.yaml - No issues found

Found 0 error(s) and 1 warning(s)
```

**Exit code:** 0 (warnings don't fail), 1 (any error)

## Issue Code Reference

### Core Checks (`checks.py`)

| Code | Sev | What it catches |
|------|-----|-----------------|
| E001 | error | Variable in tool command not declared in state |
| E002 | error | Variable in prompt not declared in state |
| E003 | error | Tool referenced in node but not defined |
| E004 | error | Prompt file does not exist |
| E005 | error | Invalid node type |
| E006 | error | Edge from/to references non-existent node |
| E008 | error | loop_limits key references non-existent node |
| E010 | error | `on_error: fallback` without fallback config |
| E601 | error | Passthrough node missing `output` (silent no-op) |
| E701 | error | tool_call node missing `tool` field |
| E702 | error | tool_call node missing `args` field |
| E802 | error | Conditional edge with string `to` (needs list) |
| W001 | warn | Tool defined but never used |
| W002 | warn | Node not reachable from START |
| W003 | warn | Node has no path to END |
| W007 | warn | Variable `{name}` missing `state.` prefix |
| W801 | warn | Condition uses `{braces}` instead of bare names |

### Pattern Checks (`patterns/`)

| Code | Sev | Pattern | What it catches |
|------|-----|---------|-----------------|
| E101 | error | Router | Routes must be dict |
| E102 | error | Router | Prompt schema missing `intent`/`tone` |
| E103 | error | Router | Conditional edge targets single node |
| W101 | warn | Router | Missing `default_route` |
| E201 | error | Map | Missing `over` field |
| E202 | error | Map | Missing `as` field |
| E203 | error | Map | Missing `node` field |
| E204 | error | Map | Missing `collect` field |
| E205 | error | Map | Top-level `prompt` (should be in `node`) |
| W201 | warn | Map | `over` should reference `{state.xxx}` |
| W202 | warn | Map | Nested node missing `prompt`/`type` |
| E301 | error | Interrupt | Missing `resume_key` |
| E302 | error | Interrupt | Missing both `prompt` and `message` |
| E303 | error | Interrupt | `state_key`/`resume_key` not in state |
| E304 | error | Interrupt | Checkpointer config malformed |
| W301 | warn | Interrupt | Missing checkpointer for interrupt graph |
| W302 | warn | Interrupt | Both `prompt` and `message` set |
| E401 | error | Agent | References undefined tool |
| W401 | warn | Agent | No tools configured |
| E501 | error | Subgraph | Missing `graph` field |
| E502 | error | Subgraph | Graph file doesn't exist |
| W501 | warn | Subgraph | Missing `input_mapping` |
| W502 | warn | Subgraph | Missing `output_mapping` |

**Total: 26 unique codes** (18 errors, 8 warnings)

## Test Fixtures

Dual-sided fixtures in `tests/fixtures/linter/`:

| Check | Pass Fixture | Fail Fixture |
|-------|-------------|-------------|
| E006 — Edge refs | `edge_refs_pass.yaml` | `edge_refs_fail.yaml` |
| E008 — Loop limits | `loop_limits_pass.yaml` | `loop_limits_fail.yaml` |
| E601 — Passthrough | `passthrough_pass.yaml` | `passthrough_fail.yaml` |
| E701/E702 — tool_call | `tool_call_pass.yaml` | `tool_call_fail.yaml` |
| W801 — Condition syntax | `condition_syntax_pass.yaml` | `condition_syntax_fail.yaml` |
| W007 — Variable prefix | `variable_expr_pass.yaml` | `variable_expr_fail.yaml` |
| E010 — Fallback config | `fallback_pass.yaml` | `fallback_fail.yaml` |
| E802 — Conditional edge | `conditional_edge_pass.yaml` | `conditional_edge_fail.yaml` |

## Programmatic API

```python
from pathlib import Path
from yamlgraph.linter import lint_graph, LintIssue

result = lint_graph(Path("graph.yaml"), project_root=Path("."))

print(f"Valid: {result.valid}")
for issue in result.issues:
    print(f"[{issue.code}] {issue.severity}: {issue.message}")
    if issue.fix:
        print(f"  Fix: {issue.fix}")
```

## CI Integration

```yaml
# .github/workflows/lint.yml
- name: Lint graphs
  run: yamlgraph graph lint examples/demos/*/graph.yaml
```

Exit code 1 on any error — warnings pass.
