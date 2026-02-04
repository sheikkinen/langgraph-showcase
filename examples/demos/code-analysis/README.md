# Code Analysis Demo

Run code quality tools and generate improvement recommendations.

## Usage

```bash
yamlgraph graph run examples/demos/code-analysis/graph.yaml \
  --var path="yamlgraph" --var package="yamlgraph"
```

Analyze a specific module:

```bash
yamlgraph graph run examples/demos/code-analysis/graph.yaml \
  --var path="yamlgraph/linter" --var package="yamlgraph"
```

## What It Does

1. Runs static analysis tools (ruff, etc.)
2. Collects code metrics
3. LLM synthesizes findings into recommendations

## Tools

| Tool | Description |
|------|-------------|
| `run_ruff` | Linting with ruff |
| `run_radon` | Complexity metrics |
| `count_lines` | Line counts per module |

## Key Concepts

- **`type: tool`** nodes - Deterministic shell execution
- **Tool chaining** - Multiple tools → synthesis
- **Code quality** - Automated analysis pipeline

## Output

Structured recommendations including:
- Critical issues to fix
- Code smells detected
- Refactoring suggestions
- Complexity hotspots

## Related

- [codegen/](../../codegen/) - Full implementation agent
- [system-status](../system-status/) - Similar tool-gathering pattern
