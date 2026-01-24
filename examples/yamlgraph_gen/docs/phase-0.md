# Phase 0: Standalone Tools + Snippets

> Build and test all tools independently before creating the graph.

## Overview

Build tools in Python first (no yamlgraph dependency). Extract initial snippets from working graphs.

## Deliverables - Tools

| File | Description | Sample |
|------|-------------|--------|
| `tools/file_ops.py` | read, write, list | [samples/file_ops.py](samples/file_ops.py) |
| `tools/snippet_loader.py` | load and index snippets | [samples/snippet_loader.py](samples/snippet_loader.py) |
| `tools/template_loader.py` | load full graphs (fallback) | [samples/template_loader.py](samples/template_loader.py) |
| `tools/prompt_validator.py` | validate YAML structure | [samples/prompt_validator.py](samples/prompt_validator.py) |
| `tools/linter.py` | run `yamlgraph graph lint` | [samples/linter.py](samples/linter.py) |
| `tools/runner.py` | run generated graph | [samples/runner.py](samples/runner.py) |
| Unit tests for each tool | | |

## Deliverables - Snippets (nodes)

| Snippet | Source |
|---------|--------|
| `snippets/nodes/llm-basic.yaml` | `graphs/yamlgraph.yaml` |
| `snippets/nodes/map-basic.yaml` | `graphs/map-demo.yaml` |
| `snippets/nodes/router-basic.yaml` | `graphs/router-demo.yaml` |
| `snippets/nodes/interrupt-basic.yaml` | `graphs/interview-demo.yaml` |
| `snippets/nodes/agent-with-tools.yaml` | `graphs/git-report.yaml` |
| `snippets/nodes/subgraph-basic.yaml` | `graphs/subgraph-demo.yaml` |

## Deliverables - Snippets (edges)

| Snippet | Description |
|---------|-------------|
| `snippets/edges/linear.yaml` | START → nodes → END pattern |
| `snippets/edges/conditional.yaml` | Router dispatch pattern |
| `snippets/edges/reflexion-loop.yaml` | Loop with quality threshold |

## Deliverables - Snippets (patterns - PRIMARY)

| Snippet | Description |
|---------|-------------|
| `snippets/patterns/generate-then-map.yaml` | LLM → map combo (complete with edges) |
| `snippets/patterns/classify-then-process.yaml` | Router → handlers (complete with edges) |
| `snippets/patterns/map-then-summarize.yaml` | Parallel → aggregate (complete with edges) |
| `snippets/patterns/interrupt-multi-step.yaml` | Chained interrupts (complete with edges) |

## Deliverables - Snippets (prompt-scaffolds)

| Snippet | Description |
|---------|-------------|
| `snippets/prompt-scaffolds/llm-basic.yaml` | Simple system + user template |
| `snippets/prompt-scaffolds/router-classify.yaml` | Classification with schema |
| `snippets/prompt-scaffolds/map-sub-node.yaml` | Map item processing |
| `snippets/prompt-scaffolds/summarize.yaml` | Aggregation prompt |

## Deliverables - Snippets (scaffolds)

| Snippet | Description |
|---------|-------------|
| `snippets/scaffolds/graph-header.yaml` | version, name, defaults |
| `snippets/scaffolds/checkpointer-memory.yaml` | Memory checkpointer |
| `snippets/scaffolds/checkpointer-sqlite.yaml` | SQLite checkpointer |

## Success Criteria

- [ ] All tools work standalone: `python -c "from tools.snippet_loader import list_snippets; ..."`
- [ ] Snippets are valid YAML with version + source tracking comments
- [ ] Patterns are complete mini-graphs (nodes + edges)
- [ ] 100% test coverage on tools
- [ ] Tools handle all error cases gracefully

## Next Phase

→ [phase-1.md](phase-1.md) - Snippet-Based Generator
