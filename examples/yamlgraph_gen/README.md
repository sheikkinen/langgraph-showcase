# YAMLGraph Generator

Generate YAMLGraph pipelines from natural language descriptions.

## Features

- 🧩 **Snippet-based composition**: Composable YAML fragments for flexible generation
- 🎯 **Pattern classification**: Router, map, interrupt, agent, and combinations
- ✅ **Validation pipeline**: Structure check → lint → optional execution
- 📝 **Prompt generation**: Automatic prompt file creation with schemas

## Quick Start

```bash
# Using the helper script (recommended)
cd examples/yamlgraph_gen

# Generate a simple pipeline
python run_generator.py "Create a Q&A pipeline"

# Generate to specific directory
python run_generator.py -o ./my-graph "Create a router pipeline"

# Generate, lint, and run with input
python run_generator.py --run -o ./my-graph --input topic="AI" "Create a topic analyzer"

# Run existing graph
python run_generator.py --run-only -o ./my-graph --input question="What is ML?"

# Lint only
python run_generator.py --lint-only -o ./my-graph
```

### Direct Invocation

```bash
# From project root
python -c "
from yamlgraph.graph_loader import load_and_compile
graph = load_and_compile('examples/yamlgraph_gen/graph.yaml').compile()
result = graph.invoke({
    'request': 'Create a customer support router',
    'output_dir': './my-support-bot'
})
"
```

## Architecture

```
request (natural language)
    │
    ▼
┌─────────────────┐
│ classify_patterns│  → Identify: router, map, interrupt, etc.
└────────┬────────┘
         │
    ▼────┴────▼
 clear      unclear
   │           │
   ▼           ▼
load_snippets  clarify_request (interrupt)
   │           │
   └─────┬─────┘
         ▼
┌─────────────────┐
│ select_snippets │  → Pick nodes, edges, patterns, scaffolds
└────────┬────────┘
         ▼
┌─────────────────┐
│ assemble_graph  │  → Compose snippets into graph.yaml
└────────┬────────┘
         ▼
┌─────────────────┐
│ generate_prompts│  → Create prompt files for each node
└────────┬────────┘
         ▼
┌─────────────────┐
│ validate        │  → Structure check → lint → report
└────────┬────────┘
         ▼
      output/
```

## Files

| File | Description |
|------|-------------|
| `graph.yaml` | Main generator pipeline |
| `prompts/*.yaml` | Prompt templates for each node |
| `tools/*.py` | Python tools (file ops, linter, etc.) |
| `snippets/` | Composable YAML fragments |

## Snippets Library

```
snippets/
├── nodes/           # Single node definitions
│   ├── llm-basic.yaml
│   ├── map-basic.yaml
│   └── router-basic.yaml
├── edges/           # Edge patterns
│   ├── linear.yaml
│   └── conditional.yaml
├── patterns/        # Mini-graphs (2-3 nodes with edges)
│   ├── generate-then-map.yaml
│   └── classify-then-process.yaml
├── scaffolds/       # Graph headers
│   └── graph-header.yaml
└── prompt-scaffolds/  # Prompt templates
    ├── llm-basic.yaml
    └── router-classify.yaml
```

## Tests

```bash
# Unit tests (60 tests, fast)
pytest examples/yamlgraph_gen/tests/ -v

# E2E tests (5 tests, requires LLM API key)
pytest examples/yamlgraph_gen/e2e_tests/ -v -m e2e --no-cov
```

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| Unit | 60 | ✅ All passing |
| E2E | 5 | ✅ All passing |

## Planning Docs

See [docs/](docs/) for detailed implementation plan and phase documentation.
