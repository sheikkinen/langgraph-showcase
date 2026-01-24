# Overview - YAMLGraph Generator

> Core principles, risks, and high-level architecture.

## Core Principles

1. **Template-first** - Always start from an existing graph, never from scratch
2. **Phased validation** - Lint-only for fast iteration, full execution for final validation
3. **Explicit output syntax** - Use ````yaml:output` fencing to avoid template confusion
4. **User-specified output** - User provides target directory
5. **Incremental feedback** - Stream progress at each phase, not just final result
6. **Error recovery** - Explicit fallback paths for all failure modes

## Known Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular dependency (generator uses yamlgraph) | Build tools in Python first (Phase 0), test independently |
| LLM confuses template `{state.x}` with output | Use explicit ````yaml:output` fence markers in prompts |
| Unbounded validation cost | Lint-only mode (`--quick`) for iteration; full run only at end |
| Keyword matching fails for novel requests | Add `clarify_request` node to ask user for pattern selection |
| Silent failures (permissions, missing files) | Add explicit error nodes and fallback paths in graph |
| Prompt structure errors pass generation | Validate prompt YAML structure (system/user/schema) before write |
| LLM generates invalid YAML syntax | Embed reference doc excerpts in prompts |
| Snippet assembly produces broken graph | Explicit assembly rules + lint validation |

## Reference Doc Injection

Each prompt includes a **condensed syntax reference** (~30 lines):

```yaml
# Embedded in prompts/assemble_graph.yaml and prompts/generate_prompts.yaml
system: |
  ## YAMLGraph Syntax Reference (condensed)

  ### Node Types
  - `type: llm` - prompt: path, state_key: result, variables: {key: "{state.x}"}
  - `type: map` - over: "{state.list}", as: item, node: {...}, collect: results
  - `type: router` - prompt: path, state_key: result (must return route field)
  - `type: interrupt` - message: "text" OR prompt: path, resume_key: user_input
  - `type: agent` - prompt: path, tools: [tool_names], max_iterations: N
  - `type: subgraph` - graph: path, input_mapping: {}, output_mapping: {}

  ### Edges
  - from: START, to: first_node
  - from: node_a, to: node_b
  - from: last_node, to: END
  - Conditional: from: router_node, conditions: [{if: "route == 'x'", to: handler}]

  ### State
  - Declared in `state:` block with types: str, int, float, bool, list, dict, any
  - Accessed via `{state.field_name}` in variables

  ### Prompts
  - Must have: system: | and user: | (or template: |)
  - Schema: name: ModelName, fields: {field: {type: str, description: "..."}}
```

## Architecture Overview

```
examples/yamlgraph-generator/
├── graph.yaml                    # Main generator graph
├── prompts/                      # Generator prompts
│   ├── classify_patterns.yaml
│   ├── clarify_request.yaml
│   ├── select_snippets.yaml
│   ├── assemble_graph.yaml
│   ├── generate_prompts.yaml
│   └── report_result.yaml
├── snippets/                     # Composable YAML fragments
│   ├── nodes/
│   ├── edges/
│   ├── patterns/
│   ├── prompt-scaffolds/
│   └── scaffolds/
├── tools/                        # Python tools
│   ├── file_ops.py
│   ├── snippet_loader.py
│   ├── template_loader.py
│   ├── prompt_validator.py
│   ├── linter.py
│   └── runner.py
└── tests/
```

## Tool Generation Scope

**Decision: Tool generation is OUT OF SCOPE for Phase 1-3.**

Rationale:
- Generating working Python code requires deep context (APIs, signatures, error handling)
- Most patterns don't need custom tools (LLM, router, map, interrupt work without Python)
- `agent` nodes use shell tools which don't need generation

**Handling in Phase 1-3:**
1. If user request implies custom tools → warn in `report_result`
2. Generate tool stub file with TODO comments
3. Point user to `examples/` for working tool examples

## Success Criteria

A generated graph is valid when:

1. ✅ `yamlgraph graph lint` passes
2. ✅ `yamlgraph graph run` completes without exceptions
3. ✅ All declared state keys are populated
4. ✅ Final output matches user's intent (subjective, reported to user)

## Related Documents

- [01-templates.md](01-templates.md) - Template selection
- [02-snippets.md](02-snippets.md) - Snippet architecture
- [03-graph-flow.md](03-graph-flow.md) - Graph flow
- [phase-0.md](phase-0.md) - First implementation phase
