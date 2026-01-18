# Code Analysis Graph

Run automated code quality analysis and generate LLM-powered recommendations.

---

## Overview

The `code-analysis` graph uses an agent to run multiple analysis tools, then generates prioritized recommendations for code improvements.

**Tools included:**
- `ruff` - Linting and style checks
- `pytest` - Test execution and coverage
- `bandit` - Security vulnerability scanning
- `radon` - Cyclomatic complexity analysis
- `vulture` - Dead code detection

---

## Quick Start

```bash
yamlgraph graph run graphs/code-analysis.yaml \
  --var path="yamlgraph" \
  --var package="yamlgraph"
```

---

## Graph Structure

```yaml
version: "1.0"
name: code-analysis

tools:
  run_ruff:
    type: shell
    command: ruff check {path} --output-format=text 2>&1 || echo "No issues"
    description: "Run ruff linter"

  run_tests:
    type: shell
    command: python -m pytest {path} -q --tb=no 2>&1 | tail -10
    description: "Run pytest"

  run_bandit:
    type: shell
    command: bandit -r {path} -ll -q 2>&1 || echo "No security issues"
    description: "Run security scanner"

  # ... more tools

nodes:
  run_analysis:
    type: agent
    prompt: code-analysis/analyzer
    tools: [run_ruff, run_tests, run_bandit, ...]
    max_iterations: 12
    state_key: analysis_results

  generate_recommendations:
    type: llm
    prompt: code-analysis/recommend
    requires: [analysis_results]
    state_key: recommendations

edges:
  - from: START
    to: run_analysis
  - from: run_analysis
    to: generate_recommendations
  - from: generate_recommendations
    to: END
```

---

## Tools Reference

| Tool | Command | Purpose |
|------|---------|---------|
| `run_ruff` | `ruff check {path}` | Lint and style violations |
| `run_tests` | `pytest {path}` | Test pass/fail status |
| `run_coverage` | `pytest --cov={package}` | Test coverage report |
| `run_bandit` | `bandit -r {path}` | Security vulnerabilities |
| `run_radon` | `radon cc {path}` | Function complexity |
| `run_vulture` | `vulture {path}` | Dead/unused code |
| `count_lines` | `wc -l` | Lines of code |
| `find_todos` | `grep TODO/FIXME` | Pending work items |

---

## Prompts

### Analyzer Prompt

`prompts/code-analysis/analyzer.yaml`:

```yaml
system: |
  You are a code quality analyst. Run the available tools
  to gather comprehensive quality metrics:
  - run_ruff: Check linting issues
  - run_tests: Get test results
  - run_bandit: Scan for security issues
  - run_radon: Check complexity
  - run_vulture: Find dead code

user: |
  Analyze the codebase at: {path}
  Package name: {package}
```

### Recommendations Prompt

`prompts/code-analysis/recommend.yaml`:

```yaml
system: |
  Generate prioritized recommendations:

  ## Critical - Security issues, failing tests
  ## High Priority - High complexity, type errors
  ## Medium Priority - Dead code, linting
  ## Low Priority - TODOs, style improvements

  Include: issue, location, fix suggestion, effort estimate.

user: |
  Analysis Results:
  {analysis}

  Generate actionable recommendations.
```

---

## Output Format

The graph produces a structured recommendations report:

```markdown
# Code Quality Recommendations

## Critical (0 issues)
No critical issues found.

## High Priority (2 issues)

### 1. High complexity in graph_loader.py
- **File**: yamlgraph/graph_loader.py
- **Function**: compile_graph (complexity: 12)
- **Fix**: Extract edge processing into separate function
- **Effort**: Moderate (1-4 hours)

## Medium Priority (5 issues)
...
```

---

## Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `path` | Yes | Directory to analyze (e.g., `yamlgraph`) |
| `package` | Yes | Package name for coverage (e.g., `yamlgraph`) |

---

## Prerequisites

Install analysis tools:

```bash
pip install ruff bandit radon vulture
```

---

## See Also

- [Graph YAML Reference](graph-yaml.md) - Full graph configuration options
- [Patterns](patterns.md) - Agent and tool patterns
