# Snippets Architecture - YAMLGraph Generator

> Snippet-based composition approach for graph generation.

## Why Snippets?

Rather than relying solely on complete graph templates, use a **snippet-based composition** approach:

| Problem with Templates Only | Solution with Snippets |
|----------------------------|------------------------|
| "Router + map" has no single template | Compose from router snippet + map snippet |
| `impl-agent.yaml` (235 lines) overwhelming | Use 10-20 line snippets for each concept |
| `booking` overlaps with `interrupt` | Combine interrupt + tool snippets instead |
| 11 categories hurt classification accuracy | Classify into patterns, assemble from parts |

## Snippet Library Structure

```
snippets/
├── nodes/                           # Individual node patterns (10-20 lines each)
│   ├── llm-basic.yaml               # Minimal LLM node
│   ├── llm-with-schema.yaml         # LLM with inline Pydantic schema
│   ├── map-basic.yaml               # Map over list with sub-node
│   ├── map-with-tool-call.yaml      # Map + type: tool_call combo
│   ├── router-basic.yaml            # Classification/routing node
│   ├── interrupt-basic.yaml         # Simple pause for input
│   ├── interrupt-with-prompt.yaml   # LLM-generated question
│   ├── agent-with-tools.yaml        # Agent + tool binding
│   ├── subgraph-basic.yaml          # With input/output mapping
│   └── passthrough-basic.yaml       # State transformation
├── edges/                           # Edge pattern fragments
│   ├── linear.yaml                  # START → A → B → END
│   ├── conditional.yaml             # Router dispatch pattern
│   └── reflexion-loop.yaml          # Loop with quality threshold
├── patterns/                        # Mini-graphs (2-3 nodes, complete) - PRIMARY COMPOSITION UNIT
│   ├── classify-then-process.yaml   # Router → specialized handlers (includes edges)
│   ├── generate-then-map.yaml       # LLM generates list → map processes (includes edges)
│   ├── critique-loop.yaml           # Generate → critique → conditional (includes edges)
│   ├── interrupt-multi-step.yaml    # Chain of interrupt nodes (includes edges)
│   └── map-then-summarize.yaml      # Parallel process → aggregate (includes edges)
├── prompt-scaffolds/                # Prompt templates for each node type
│   ├── llm-basic.yaml               # system + user template
│   ├── router-classify.yaml         # Classification prompt with schema
│   ├── map-sub-node.yaml            # Prompt for map sub-node processing
│   ├── interrupt-question.yaml      # LLM-generated question prompt
│   └── summarize.yaml               # Aggregation/summary prompt
└── scaffolds/                       # Graph boilerplate templates
    ├── graph-header.yaml            # version, name, defaults block
    ├── checkpointer-memory.yaml     # Memory checkpointer config
    ├── checkpointer-sqlite.yaml     # SQLite checkpointer config
    └── state-declaration.yaml       # state: block pattern
```

## Snippet Format

Each snippet includes source tracking and version for automated extraction:

```yaml
# snippets/nodes/map-basic.yaml
# Version: 1.0
# Source: graphs/map-demo.yaml:19-28
# Description: Map over a list, execute sub-node for each item

expand:
  type: map
  over: "{state.ideas.ideas}"
  as: idea
  node:
    prompt: map-demo/expand_idea
    state_key: expansion
    variables:
      idea: "{state.idea}"
  collect: expansions
```

## Patterns as Primary Composition Unit

**Critical insight:** Individual node snippets require complex edge assembly. Instead, use **patterns** as the primary unit—they include nodes AND edges.

| User Request | Pattern(s) Selected | Why |
|--------------|---------------------|-----|
| "Classify and handle differently" | `classify-then-process.yaml` | Router + handlers with edges |
| "Process items in parallel" | `generate-then-map.yaml` | LLM + map + edges included |
| "Iterative refinement" | `critique-loop.yaml` | Loop edges included |
| "Multi-step form" | `interrupt-multi-step.yaml` | Interrupt chain with edges |

**Fallback:** For novel combinations, assemble from node snippets + edge snippets (harder, Phase 2+).

## Generator Flow

```
OLD: classify → pick 1 template → adapt whole thing
NEW: classify patterns → select patterns/snippets → assemble from parts + scaffolds
```

The generator now:
1. **Classifies into patterns** (not templates): "router + map", "interrupt chain", etc.
2. **Selects patterns** (preferred) or individual snippets (fallback)
3. **Assembles** using scaffolds for boilerplate
4. **Generates prompts** using prompt-scaffolds
5. **Validates** the composed result

## Snippet Extraction (Maintenance)

Snippets are extracted from working templates, not hand-written:

```bash
# Future tool: extract snippets from working graphs
yamlgraph snippet extract graphs/map-demo.yaml --output snippets/nodes/map-basic.yaml
```

This keeps snippets in sync with actual working code.

## Related Documents

- [01-templates.md](01-templates.md) - Full template catalog
- [04-assembly-rules.md](04-assembly-rules.md) - Assembly rules
- [phase-0.md](phase-0.md) - Snippet deliverables
