# Assembly Rules - YAMLGraph Generator

> Rules for graph assembly and prompt generation.

## Graph Assembly Rules

The `assemble_graph` step must follow these explicit rules:

```yaml
# In prompts/assemble_graph.yaml
system: |
  You are assembling a YAMLGraph from snippets and patterns.

  ## ASSEMBLY RULES

  1. **Header first**: Always start with scaffold/graph-header.yaml
     - Set `name:` to user's project name (slugified)
     - Set `description:` to user's request summary

  2. **Checkpointer**: If any interrupt nodes, add checkpointer block:
     - Use `type: memory` for demos
     - Use `type: sqlite` for production (path: ":memory:" or file path)

  3. **State block**: Collect all `state_key` values from nodes into `state:` block:
     - Each `state_key: foo` adds `foo: any` to state
     - Each `resume_key: bar` adds `bar: str` to state
     - Add input fields based on user request

  4. **Nodes block**: Merge all nodes from patterns/snippets:
     - If node names conflict, rename with suffix (_1, _2)
     - Preserve all node properties exactly
     - Replace placeholder prompt paths with generated paths

  5. **Edges block**:
     - Pattern snippets include edges - use them directly
     - For multi-pattern: wire last node of pattern A to first of pattern B
     - Always: START → first_node, last_node → END

  6. **Tools block**: Only if agent or python nodes present
     - Extract tool definitions from snippets
     - Ensure module paths are correct for output_dir

  ## OUTPUT FORMAT

  Output the complete graph.yaml using explicit fencing:
  ```yaml:graph
  version: "1.0"
  name: ...
  ```

  ## VARIABLE SYNTAX

  CRITICAL: Template variables like {state.topic} must appear LITERALLY.
  Do NOT substitute values. The graph engine handles substitution at runtime.
```

## Prompt Generation Rules

```yaml
# In prompts/generate_prompts.yaml
system: |
  You are generating prompt files for YAMLGraph nodes.

  ## PROMPT RULES

  1. **Use prompt-scaffolds**: Start from snippets/prompt-scaffolds/ for node type

  2. **Required sections**:
     - `system:` - Role and context for LLM
     - `user:` - Template with {variable} placeholders

  3. **Schema** (if node has state_key):
     - Add `schema:` block with `name:` and `fields:`
     - Field types: str, int, float, bool, list, dict, any
     - Add `description:` for each field

  4. **Variables**: Use {state.field} syntax for state access
     - Must match variables: block in graph node
     - Or use {variable_name} matching node's variables

  ## OUTPUT FORMAT

  Output each prompt using explicit fencing with path:
  ```yaml:prompt:prompts/node_name.yaml
  system: |
    ...
  ```
```

## Validation Strategy

### No Mocking

- Mocking defeats the purpose - we need real LLM feedback
- Generated prompts might have subtle issues only visible at runtime
- Cost is not a concern for a generator that runs occasionally

### No Dry-Run

- YAMLGraph doesn't have meaningful dry-run (would need to skip LLM)
- Validation requires actual execution to catch:
  - Prompt template errors
  - Schema mismatches
  - Tool execution failures
  - State propagation bugs

### Full Execution with Test Inputs

1. **Lint first** - Catch structural issues cheaply
2. **Run with minimal inputs** - Simple test data to verify flow
3. **Parse all errors** - Both Python exceptions and LLM complaints
4. **Fix loop** - Max 3 iterations, then report remaining issues

## Related Documents

- [02-snippets.md](02-snippets.md) - Snippet architecture
- [03-graph-flow.md](03-graph-flow.md) - Graph flow
- [samples/prompt_validator.py](samples/prompt_validator.py) - Validation code
