# YAMLGraph Demos

Standalone demos for learning YAMLGraph concepts.

## 🎓 Learning Path

Start here and progress in order:

| # | Demo | Concept | Time |
|---|------|---------|------|
| 1 | [hello/](hello/) | Basic LLM node | 5 min |
| 2 | [router/](router/) | Conditional routing | 10 min |
| 3 | [map/](map/) | Parallel fan-out | 15 min |
| 4 | [reflexion/](reflexion/) | Self-correction loops | 15 min |
| 5 | [git-report/](git-report/) | Tool-using agents | 15 min |
| 6 | [interview/](interview/) | Human-in-the-loop | 15 min |
| 7 | [subgraph/](subgraph/) | Graph composition | 20 min |

## All Demos

| Demo | Node Types | Description |
|------|------------|-------------|
| [hello/](hello/) | `llm` | Minimal example - start here |
| [router/](router/) | `router` | Tone-based conditional routing |
| [map/](map/) | `map`, `llm` | Parallel fan-out processing |
| [reflexion/](reflexion/) | `llm` | Self-correction with loop limits |
| [yamlgraph/](yamlgraph/) | `llm` | Multi-step pipeline |
| [git-report/](git-report/) | `agent` | Git analysis with tools |
| [memory/](memory/) | `agent` | Multi-turn with memory |
| [interview/](interview/) | `interrupt` | Human-in-the-loop |
| [interrupt/](interrupt/) | `subgraph`, `interrupt` | Subgraph interrupt tests |
| [streaming/](streaming/) | `llm` | Token-by-token output |
| [subgraph/](subgraph/) | `subgraph` | Graph composition |
| [system-status/](system-status/) | `tool` | Shell tool execution |
| [web-research/](web-research/) | `agent` | Web search agent |
| [code-analysis/](code-analysis/) | `tool`, `llm` | Code quality tools |
| [feature-brainstorm/](feature-brainstorm/) | `agent` | Self-analysis |
| [data-files/](data-files/) | `llm` | External data loading |
| [run-analyzer/](run-analyzer/) | - | Analysis utilities |
| [soul/](soul/) | `llm`, `data_files` | Agent personality pattern |

## Running Demos

```bash
# From project root
yamlgraph graph run examples/demos/<name>/graph.yaml --full

# Example
yamlgraph graph run examples/demos/hello/graph.yaml --full
```

## Quick Demo Script

Run `demo.sh` to execute multiple demos in sequence:

```bash
cd examples/demos
./demo.sh
```
