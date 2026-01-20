# Feature Request: Graph-Relative Prompt Resolution

**Priority:** HIGH  
**Use Case:** Multi-questionnaire systems with per-graph prompts

## Problem

Currently, prompt paths are resolved relative to a global `PROMPTS_DIR` (default: `{cwd}/prompts/`). This creates friction for projects where:

1. Multiple graphs live in subdirectories (e.g., `questionnaires/audit/graph.yaml`)
2. Each graph has its own prompts alongside it
3. Subgraphs need to use prompts from their parent's context

### Current Workarounds

1. **Flat prompts directory** - All prompts in `prompts/` with prefixes:
   ```
   prompts/
     audit/opening.yaml
     audit/extract.yaml
     phq9/opening.yaml
   ```
   Works but separates prompts from their graphs.

2. **Monkey-patching config** - Set `yamlgraph.config.PROMPTS_DIR` at runtime:
   ```python
   import yamlgraph.config
   yamlgraph.config.PROMPTS_DIR = Path(".")
   ```
   Fragile, must happen before other imports.

3. **Full paths in prompt field** - Use `prompt: questionnaires/audit/prompts/opening`
   Works with workaround #2 but verbose.

## Proposed Solution

### Option A: `prompts_dir` in graph defaults

```yaml
# questionnaires/audit/graph.yaml
defaults:
  prompts_dir: questionnaires/audit/prompts
  
nodes:
  generate_opening:
    type: llm
    prompt: opening  # Resolves to questionnaires/audit/prompts/opening.yaml
```

**Implementation:**
- Add `prompts_dir` to `GraphConfig` 
- Pass it through to `resolve_prompt_path()` calls during node creation
- Falls back to global `PROMPTS_DIR` if not specified

### Option B: Graph-relative resolution (preferred)

```yaml
# questionnaires/audit/graph.yaml
defaults:
  prompts_relative: true  # New flag
  
nodes:
  generate_opening:
    type: llm
    prompt: prompts/opening  # Resolves relative to graph file location
```

**Implementation:**
- When `prompts_relative: true`, resolve prompt paths relative to `config.source_path`
- Cleaner semantics: prompts are "local" to the graph
- Works naturally with subgraphs (each resolves relative to its own location)

### Option C: Both (maximum flexibility)

Support both `prompts_dir` (explicit override) and `prompts_relative` (convenience flag).

## Benefits

1. **Colocation** - Prompts live with their graphs
2. **Portability** - Move a graph folder and prompts come with it
3. **Subgraph reuse** - Each subgraph can have its own prompts
4. **No global state** - No need to modify `PROMPTS_DIR`

## Related

- Subgraph path resolution already uses `parent_graph_path` for relative paths
- Same pattern could apply to prompts
