# Feature Brainstorm Demo

YAMLGraph analyzes itself and proposes improvements.

## Usage

```bash
yamlgraph graph run examples/demos/feature-brainstorm/graph.yaml
```

With focus area:

```bash
yamlgraph graph run examples/demos/feature-brainstorm/graph.yaml \
  --var focus="cli"
```

## What It Does

1. Reads YAMLGraph documentation and patterns
2. Analyzes current capabilities
3. Proposes new features or improvements

## Tools

| Tool | Command | Description |
|------|---------|-------------|
| `read_patterns` | `cat reference/patterns.md` | Current patterns |
| `read_graph_yaml` | `cat reference/graph-yaml.md` | Graph spec |
| `list_examples` | `ls examples/` | Available examples |

## Key Concepts

- **Meta-analysis** - Framework analyzing itself
- **Shell tools** - Read local documentation
- **Creative generation** - LLM proposes improvements

## Use Cases

- Generate feature request ideas
- Identify documentation gaps
- Explore potential patterns

## Related

- [feature-requests/](../../../feature-requests/) - Actual feature requests
- [code-analysis](../code-analysis/) - Static analysis tools
