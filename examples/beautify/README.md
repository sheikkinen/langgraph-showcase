# Beautify

Transform a yamlgraph `graph.yaml` into a beautiful HTML infographic with Mermaid diagrams.

## Usage

```bash
# Basic
python -m examples.beautify.run examples/booking/graph.yaml

# With options
python -m examples.beautify.run examples/booking/graph.yaml --theme light --open

# Via yamlgraph CLI
yamlgraph graph run examples/beautify/graph.yaml --var graph_path=examples/booking/graph.yaml
```

## Options

| Option | Description |
|--------|-------------|
| `--output, -o` | Output HTML path |
| `--theme, -t` | `dark` (default) or `light` |
| `--title` | Override title |
| `--open` | Open in browser |

## Pipeline

```
load_graph → analyze → mermaid → render_html → save_output
   (py)       (llm)     (llm)       (py)          (py)
```

- **analyze**: Generates title, summary, features, and node descriptions
- **mermaid**: Creates styled flowchart diagram

## Output

- Hero section with title and features
- Mermaid architecture diagram
- Node cards with descriptions

## Requirements

- `ANTHROPIC_API_KEY` environment variable
- No additional dependencies (uses CDN for Tailwind/Mermaid)
