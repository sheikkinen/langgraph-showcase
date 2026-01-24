# YAMLGraph Generator - Planning Documentation

> A yamlgraph that generates yamlgraphs from natural language descriptions.

## Overview

This folder contains the modular planning documentation for the YAMLGraph Generator project.

## Document Index

| Document | Description |
|----------|-------------|
| [00-overview.md](00-overview.md) | Core principles, risks, and architecture |
| [01-templates.md](01-templates.md) | Template selection and classification |
| [02-snippets.md](02-snippets.md) | Snippet-based composition architecture |
| [03-graph-flow.md](03-graph-flow.md) | Graph flow diagrams and state schema |
| [04-assembly-rules.md](04-assembly-rules.md) | Assembly and prompt generation rules |
| [phase-0.md](phase-0.md) | Phase 0: Standalone Tools + Snippets |
| [phase-1.md](phase-1.md) | Phase 1: Snippet-Based Generator |
| [phase-2.md](phase-2.md) | Phase 2: Clarification & Error Paths |
| [phase-3.md](phase-3.md) | Phase 3: Execution Validation |
| [phase-4.md](phase-4.md) | Phase 4: Polish & Documentation |

## Code Samples

| File | Description |
|------|-------------|
| [samples/file_ops.py](samples/file_ops.py) | File operations tool |
| [samples/snippet_loader.py](samples/snippet_loader.py) | Snippet loading tool |
| [samples/prompt_validator.py](samples/prompt_validator.py) | Prompt validation tool |
| [samples/template_loader.py](samples/template_loader.py) | Template loading tool |
| [samples/linter.py](samples/linter.py) | Lint integration tool |
| [samples/runner.py](samples/runner.py) | Graph runner tool |
| [samples/state_schema.yaml](samples/state_schema.yaml) | State schema definition |

## Quick Start

1. Read [00-overview.md](00-overview.md) for core principles
2. Review [02-snippets.md](02-snippets.md) for the composition approach
3. Start with [phase-0.md](phase-0.md) for implementation

## Implementation

See the parent folder for the implementation (`examples/yamlgraph_gen/`).

## Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 0 | ✅ Complete | Tools + snippets - 62 unit tests passing |
| Phase 1 | ✅ Complete | Basic generator graph - 5 E2E tests passing |
| Phase 2 | ✅ Complete | Clarification via router + interrupt |
| Phase 3 | ✅ Complete | Lint validation integrated |
| Phase 4 | ✅ Complete | README generation, gallery (5 examples) |

## Quick Usage

```bash
# Generate a new graph
python examples/yamlgraph_gen/run_generator.py "Create a Q&A pipeline"

# Generate to specific directory
python examples/yamlgraph_gen/run_generator.py -o ./my-graph "Create a router pipeline"

# Generate, lint, and run
python examples/yamlgraph_gen/run_generator.py --run "Create a simple pipeline"

# Run existing graph with input
python examples/yamlgraph_gen/run_generator.py --run-only -o ./my-graph --input question="What is AI?"

# Lint only
python examples/yamlgraph_gen/run_generator.py --lint-only -o ./my-graph
```

## Open Items

- [ ] How to handle graphs that need external APIs (e.g., websearch)? → Implement python tool stubs
- [x] Generate README.md for output? → Done (Phase 4)
- [x] Include example test inputs in generated output? → Done (in README.md)
- [x] Fix prompt path resolution (prompts_relative: true)
- [x] Fix linter path doubling issue

## Existing Examples

For working pattern examples, see:
- `graphs/router-demo.yaml` - Router pattern
- `graphs/map-demo.yaml` - Map pattern
- `graphs/interrupt-parent.yaml` - Interrupt pattern
- `examples/cost-router/` - Cost-based routing
- `examples/book_translator/` - Linear pipeline
