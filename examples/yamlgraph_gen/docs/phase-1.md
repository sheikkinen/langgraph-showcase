# Phase 1: Snippet-Based Generator

> Create the basic graph with: classify patterns → select snippets → assemble → generate → lint → report

## Overview

Build the main generator graph (v1) without fix loop or clarification.

## Prerequisites

- [x] Phase 0 complete: all tools tested, snippets extracted

## Deliverables

| File | Description |
|------|-------------|
| `graph.yaml` | Main generator graph (v1) |
| `prompts/classify_patterns.yaml` | Identify pattern combo |
| `prompts/clarify_request.yaml` | Clarification (stub for Phase 2) |
| `prompts/select_snippets.yaml` | Choose snippets |
| `prompts/assemble_graph.yaml` | Compose snippets (see [04-assembly-rules.md](04-assembly-rules.md)) |
| `prompts/generate_prompts.yaml` | Create prompt files |
| `prompts/report_result.yaml` | Final summary |

## Graph Structure (v1)

```yaml
version: "1.0"
name: yamlgraph-generator
description: Generate YAMLGraph pipelines from natural language

nodes:
  classify_patterns:
    type: router
    prompt: classify_patterns
    state_key: classification

  load_snippets:
    type: python
    tool: snippet_loader

  select_snippets:
    type: llm
    prompt: select_snippets
    state_key: selected_snippets

  assemble_graph:
    type: llm
    prompt: assemble_graph
    state_key: assembled_graph

  generate_prompts:
    type: llm
    prompt: generate_prompts
    state_key: generated_prompts

  write_files:
    type: python
    tool: file_ops

  validate_structure:
    type: python
    tool: prompt_validator

  lint_graph:
    type: python
    tool: linter

  report_result:
    type: llm
    prompt: report_result
    state_key: report

edges:
  - from: START
    to: classify_patterns
  - from: classify_patterns
    to: load_snippets
  - from: load_snippets
    to: select_snippets
  - from: select_snippets
    to: assemble_graph
  - from: assemble_graph
    to: generate_prompts
  - from: generate_prompts
    to: write_files
  - from: write_files
    to: validate_structure
  - from: validate_structure
    to: lint_graph
  - from: lint_graph
    to: report_result
  - from: report_result
    to: END
```

## Success Criteria

- [x] Can generate a working "router + map" combo (pattern composition)
- [x] Can generate a working single-pattern graph (router, map, linear)
- [x] Lint passes on generated graphs
- [x] Clear error messages when lint fails

## Test Results

**5/5 E2E tests passing:**
- `test_generate_simple_linear_graph` ✅
- `test_generate_router_graph` ✅
- `test_generate_map_graph` ✅
- `test_generated_graph_lints_clean` ✅
- `test_router_plus_map` ✅

## Key Implementation Notes

1. **Router field detection**: Uses `intent` field (must be 'clear' or 'unclear')
2. **Prompt paths**: Use basename only (`prompt: my_node`), not `prompts/my_node.yaml`
3. **Required defaults**:
   ```yaml
   defaults:
     prompts_dir: prompts
     prompts_relative: true
   ```
4. **Sanitization**: Double `.yaml.yaml` extensions are auto-fixed

## Next Phase

→ [phase-2.md](phase-2.md) - Clarification & Error Paths (COMPLETE)
