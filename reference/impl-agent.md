# Implementation Agent

Analyze codebases and generate precise implementation plans for user stories.

---

## Overview

The `impl-agent` graph provides automated code analysis with:

- **AST-based structure extraction** - Classes, functions, imports with line numbers
- **Text search** - Grep-style pattern matching across files
- **Semantic analysis** - Jedi-based cross-file reference tracking
- **Test discovery** - Find related test files

---

## Quick Start

```bash
# Simple feature request
yamlgraph graph run examples/codegen/impl-agent.yaml \
  -v 'story=Add a timeout parameter to the websearch tool' \
  -v 'scope=yamlgraph/tools'

# Refactoring with cross-file analysis
yamlgraph graph run examples/codegen/impl-agent.yaml \
  -v 'story=Rename find_related_tests to find_test_files and update all callers' \
  -v 'scope=yamlgraph/tools'
```

---

## Tools Available

| Tool | Description |
|------|-------------|
| `list_modules` | List all modules in a package with summaries |
| `get_structure` | Get classes, functions, imports with line numbers |
| `read_lines` | Read specific line range from a file |
| `search_file` | Search for pattern in a single file (grep) |
| `search_code` | Search for pattern across directory (grep -r) |
| `find_tests` | Find test functions that mention a symbol |
| `find_refs` | Find ALL references to a symbol (jedi) |
| `get_callers` | Find functions that call a given function (jedi) |
| `get_callees` | Find functions called by a given function (jedi) |

---

## Output Format

```python
implementation_plan:
  summary: "Brief description of the change"
  already_exists: ["Existing code found at file.py:42"]
  changes: ["file.py:10-20 MODIFY - What to change"]
  test_changes: ["tests/test_file.py - Add test for X"]
  risks: ["API may break if..."]
```

---

## When to Use Each Tool

| Change Type | Tools |
|-------------|-------|
| **Add field/function** | `search_file` (verify doesn't exist) |
| **Rename symbol** | `find_refs` (all usages) |
| **Refactor API** | `find_refs` + `get_callers` |
| **Find tests** | `find_tests` |

---

## Installation

Jedi is optional but recommended for semantic analysis:

```bash
pip install yamlgraph[analysis]
```

---

## Graph Structure

```
START → parse_story → discover → analyze → plan → END
```

- **parse_story** - Extract change type and key terms
- **discover** - Find relevant files using `list_modules`
- **analyze** - Deep analysis with all tools
- **plan** - Generate implementation plan
