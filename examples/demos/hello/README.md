# Hello World Demo

Minimal YAMLGraph example demonstrating basic LLM call with variable substitution.

## Usage

```bash
yamlgraph graph run examples/demos/hello/graph.yaml \
  --var name="World" --var style="enthusiastic"
```

## What It Does

1. Takes `name` and `style` as input
2. Generates a personalized greeting

## Pipeline

```
START → greet → END
```

## Key Concepts

- **`type: llm`** - Basic LLM node
- **Variable substitution** - `{state.name}` syntax
- **Prompt files** - Prompts in `prompts/` directory
- **`prompts_relative: true`** - Prompts relative to graph file

## Files

```
hello/
├── graph.yaml          # Graph definition
└── prompts/
    └── greet.yaml      # Greeting prompt
```

## Learning Path

This is the **first demo** to try. Next: [router](../router/) for conditional logic.
