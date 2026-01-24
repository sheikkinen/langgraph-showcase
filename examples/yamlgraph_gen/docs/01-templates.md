# Template Selection - YAMLGraph Generator

> Template catalog and classification examples.

## Template Catalog

Uses semantic matching via LLM classification, not keyword matching.

| Pattern Type | Template Source | When to Use |
|-------------|-----------------|-------------|
| `router` | `graphs/router-demo.yaml` | Classify input and route to different handlers |
| `map` | `graphs/map-demo.yaml` | Process a list of items in parallel |
| `reflexion` | `graphs/reflexion-demo.yaml` | Iterative refinement with quality threshold |
| `agent` | `graphs/git-report.yaml` | LLM with tool access for exploration |
| `linear` | `graphs/yamlgraph.yaml` | Simple sequential pipeline |
| `memory` | `graphs/memory-demo.yaml` | Multi-turn conversation with history |
| `interrupt` | `graphs/interview-demo.yaml` | Human-in-the-loop with pause/resume |
| `booking` | `examples/booking/graph.yaml` | Multi-turn conversation with tools + interrupts |
| `subgraph` | `graphs/subgraph-demo.yaml` | Modular graph composition with input/output mapping |
| `subgraph_interrupt` | `graphs/interrupt-parent.yaml` | Subgraph with interrupt output mapping |
| `tool_call` | `examples/codegen/impl-agent.yaml` | Dynamic tool execution via `type: tool_call` |
| `unclear` | → `clarify_request` | Ask user to clarify their intent |

## Classification Examples

The classifier uses these examples to improve accuracy:

| User Request | Patterns | Reasoning |
|--------------|----------|-----------|
| "Classify customer emails and respond appropriately" | `router` | Route to different handlers based on classification |
| "Process each file in the directory and summarize" | `map`, `linear` | Parallel processing + aggregation |
| "Analyze code quality with exploration" | `agent` | Needs tool access for exploration |
| "Generate content, critique it, improve until good" | `reflexion` | Iterative refinement loop |
| "Build a multi-step form with user input" | `interrupt` | Human-in-the-loop pauses |
| "Translate a book chapter by chapter" | `map` | Parallel chapter processing |
| "Create a chatbot that remembers context" | `memory` | Multi-turn with history |
| "Route simple queries to cheap model, complex to expensive" | `router` | Cost-based routing |
| "Generate list of ideas, then expand each in parallel" | `linear`, `map` | Generate → fan-out pattern |

## Additional References

| Pattern | Additional References |
|---------|----------------------|
| `interrupt` | `scripts/run_interview_demo.py`, `scripts/demo_interview_e2e.md`, `examples/npc/encounter-loop.yaml` |
| `subgraph` | `graphs/subgraphs/summarizer.yaml`, `reference/subgraph-nodes.md` |
| `tool_call` | `reference/tool-call-nodes.md` (map + tool_call combo), `tests/unit/test_tool_call_integration.py` |
| `booking` | `examples/booking/run_booking.py`, `examples/booking/nodes/slots_handler.py` |

## Demo Script Coverage

All patterns are runnable via `scripts/demo.sh`:

```bash
./demo.sh router      # Router pattern
./demo.sh map         # Map fan-out
./demo.sh reflexion   # Reflexion loop
./demo.sh git         # Agent with tools
./demo.sh memory      # Memory agent
./demo.sh interview   # Interrupt pattern (interactive)
./demo.sh subgraph    # Subgraph composition
./demo.sh codegen     # Impl-agent with tool_call
```

## Related Documents

- [00-overview.md](00-overview.md) - Core principles
- [02-snippets.md](02-snippets.md) - Snippet-based composition (replaces direct template usage)
