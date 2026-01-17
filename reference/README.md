# YAML Configuration Reference

Welcome to the LangGraph Showcase reference documentation. This guide explains how to configure YAML-based LLM pipelines.

## Documents

### [Quick Start](quickstart.md)
Create your first pipeline in 5 minutes. Start here if you're new.

### [Graph YAML Reference](graph-yaml.md)
Complete reference for graph configuration files (`graphs/*.yaml`):
- Top-level properties (version, name, defaults)
- Node types (llm, router, map, python, agent)
- Edge definitions and conditions
- Tools for agents
- Error handling
- Loop limits
- Dynamic state generation

### [Prompt YAML Reference](prompt-yaml.md)
Complete reference for prompt template files (`prompts/*.yaml`):
- Inline schema definitions
- System and user messages
- Jinja2 templating
- Field types and constraints

### [Map Nodes Reference](map-nodes.md)
Parallel fan-out/fan-in processing with LangGraph's `Send()` API:
- Process lists in parallel
- Automatic result collection
- Sub-node types (llm, router, python)
- Animated storyboard examples

### [Common Patterns](patterns.md)
Copy-paste patterns for common use cases:
1. Linear pipeline
2. Conditional routing
3. Self-correction loops (Reflexion)
4. Tool-using agents
5. Error recovery
6. Multi-input consolidation
7. Stateful memory
8. Parallel fan-out (Map)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Graph YAML                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ nodes    │  │ edges    │  │ tools    │  │ defaults │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
└───────┼─────────────┼─────────────┼─────────────┼───────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌───────────────┐ ┌─────────────┐ ┌───────────┐ ┌─────────────────┐
│ node_factory  │ │graph_loader │ │shell tools│ │ LLM settings    │
│ creates nodes │ │builds edges │ │for agents │ │ provider, temp  │
└───────┬───────┘ └──────┬──────┘ └─────┬─────┘ └────────┬────────┘
        │                │              │               │
        ▼                ▼              ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LangGraph StateGraph                       │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Prompt YAML                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────────────┐  │
│  │ schema   │  │ system   │  │ user / template              │  │
│  │ (output) │  │ (persona)│  │ (with variables)             │  │
│  └────┬─────┘  └────┬─────┘  └────────────┬─────────────────┘  │
└───────┼─────────────┼──────────────────────┼────────────────────┘
        │             │                      │
        ▼             ▼                      ▼
┌───────────────┐ ┌─────────────┐ ┌─────────────────────────────┐
│schema_loader  │ │SystemMessage│ │ format_prompt               │
│→ Pydantic     │ │             │ │ (simple or Jinja2)          │
└───────────────┘ └─────────────┘ └─────────────────────────────┘
```

---

## File Locations

| Type | Location | Example |
|------|----------|---------|
| Graphs | `graphs/*.yaml` | `graphs/showcase.yaml` |
| Prompts | `prompts/*.yaml` | `prompts/generate.yaml` |
| Grouped prompts | `prompts/group/*.yaml` | `prompts/router-demo/classify.yaml` |
| State classes | Auto-generated from YAML | `build_state_class(config)` |
| Output schemas | Inline in prompt YAML | `schema:` block |

---

## Key Concepts

### State
A TypedDict that flows through the pipeline. Nodes read from and write to state.

```python
class ShowcaseState(TypedDict, total=False):
    topic: str
    generated: GeneratedContent
    analysis: Analysis
    final_summary: str
```

### Nodes
Processing steps. Each node:
1. Reads variables from state
2. Executes a prompt
3. Writes result to state

### Edges
Define flow between nodes. Can be:
- Linear: `from: A, to: B`
- Conditional: Based on state values
- Terminal: `to: END`

### Prompts
Self-contained YAML files with:
- Output schema (optional)
- System message
- User message with variables
