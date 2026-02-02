# Feature Request: Load External YAML Data Files (`data_files` Directive)

**Priority:** MEDIUM
**Type:** Feature
**Status:** Proposed → **Refined**
**Effort:** 3–4 days (Phase 1 only)
**Requested:** 2026-02-02
**Reviewed:** 2026-02-02

## Reflection: Is This Really Needed?

> Per CLAUDE.md: "Documenting patterns is cheaper than new code."

### Alternative: Shared YAML Loader Utility

Before implementing framework changes, consider a **shared utility** approach:

```python
# yamlgraph/tools/yaml_loader.py (or examples/shared/yaml_loader.py)
def load_yaml_file(state: dict) -> dict:
    """Generic YAML loader - register once, use everywhere."""
    from pathlib import Path
    import yaml

    file_path = Path(state["_yaml_file_path"])
    state_key = state.get("_yaml_state_key", "data")

    with open(file_path) as f:
        data = yaml.safe_load(f)

    return {state_key: data}
```

**Usage in any graph:**
```yaml
tools:
  load_yaml:
    type: python
    module: yamlgraph.tools.yaml_loader
    function: load_yaml_file

nodes:
  load_schema:
    type: python
    tool: load_yaml
    input:
      _yaml_file_path: "schema.yaml"  # Relative to CWD or absolute
      _yaml_state_key: "schema"
```

**Pros:** No framework changes, available today, 20 lines of code
**Cons:** Still requires a node, path resolution less elegant

### Verdict

The `data_files` directive is **still valuable** because:
1. Zero-node initialization (data available before START)
2. Consistent path resolution (relative to graph, like prompts)
3. Declarative intent ("this graph needs this data")
4. Lint-time validation (catch missing files early)

**Proceed with Phase 1 (minimal)**, document the utility pattern as fallback.

---

## Summary

Add a top-level `data_files` directive that loads external YAML files into graph state at compile/init time, eliminating the need for custom Python handlers to load structured data like questionnaire schemas, tool configs, or entity definitions.

## Problem

Currently, loading external YAML data into a graph requires boilerplate:

1. Declare `schema_path: str` and `schema: dict` in state
2. Write a custom Python handler to load YAML files
3. Register the handler in `tools:` section
4. Create a `type: python` node to invoke it
5. Initialize `schema_path` in a passthrough node

**Example of current pattern (repeated across 8+ questionnaires):**

```yaml
# graph.yaml
state:
  schema_path: str
  schema: dict

tools:
  load_schema:
    type: python
    module: questionnaire.handlers.eldercare
    function: load_schema

nodes:
  init:
    type: passthrough
    output:
      schema_path: questionnaires/audit/schema.yaml  # Hardcoded

  load_schema:
    type: python
    function: load_schema
    state_key: schema
```

**Plus Python handler:**

```python
# handlers/eldercare.py
def load_schema(state: dict) -> dict:
    schema_path = state.get("schema_path")
    path = Path(schema_path)
    with open(path) as f:
        schema = yaml.safe_load(f)
    return {"schema": schema}
```

This pattern:
- Adds ~20 lines of YAML + ~10 lines of Python per graph
- Breaks the "no Python needed" promise for common use cases
- Creates tight coupling between graph and handler location
- Requires re-registering the same handler in every graph

## Proposed Solution

Add a `data_files` directive that loads YAML files relative to the graph:

```yaml
# graph.yaml
version: "1.0"
name: audit-questionnaire

data_files:
  schema: schema.yaml  # Loaded into state.schema at init

nodes:
  generate_opening:
    type: llm
    prompt: opening
    variables:
      schema: "{state.schema}"  # Available immediately
```

### Path Resolution

Files are resolved relative to the graph file (like `prompts_dir`):

```
questionnaires/audit/
├── graph.yaml          # Contains: data_files: { schema: schema.yaml }
├── schema.yaml         # Loaded into state.schema
└── prompts/
```

### Alternative Syntax Options

**Option A: Simple mapping (recommended)**
```yaml
data_files:
  schema: schema.yaml
  locale: locales/en.yaml  # Subdirectories OK
```

**Option B: Extended with validation**
```yaml
data_files:
  schema:
    path: schema.yaml
    validate: questionnaire.models.Schema  # Optional Pydantic model
    required: true
```

**Option C: Array syntax**
```yaml
data_files:
  - path: schema.yaml
    as: schema
  - path: locale/en.yaml
    as: strings
```

### Environment Variable Support

```yaml
data_files:
  schema: "${SCHEMA_PATH:-schema.yaml}"
```

## Acceptance Criteria

### Phase 1: Minimal (v0.1) - 3-4 days
- [ ] `data_files` directive loads YAML files into state at graph initialization
- [ ] Paths resolved relative to graph file location (like `prompts_dir`)
- [ ] Security: Paths must resolve within graph directory (no `../../../etc/passwd`)
- [ ] Clear error messages for missing files
- [ ] Tests for path resolution, missing files, security
- [ ] Documentation with examples
- [ ] JSON schema updated for IDE support

### Phase 2: Enhanced (v0.2) - Deferred
- [ ] Environment variable substitution in paths (`${VAR}` syntax)
- [ ] Optional Pydantic validation (`validate:` key)
- [ ] Size limits for loaded files (configurable, default 1MB)

### Phase 3: Subgraphs (v0.3) - Deferred
- [ ] Subgraph data_files behavior (isolated by default)
- [ ] Explicit inheritance via `inherit_data: [key1, key2]`
- [ ] Merge vs override semantics documented

### Out of Scope
- Circular dependency detection (files don't reference each other)
- Hot reloading (data is loaded once at compile time)
- Non-YAML formats (JSON support trivial to add later)

## Use Cases

| Use Case | Description |
|----------|-------------|
| **Questionnaire schemas** | Field definitions, coding values, scoring rules |
| **Agent tool configs** | Tool definitions separate from agent graph |
| **Multi-language support** | Load locale-specific strings |
| **API schemas** | OpenAPI specs as structured data |
| **Entity catalogs** | Products, user types, reference data |
| **Shared configs** | Cross-graph settings loaded once |

## Implementation Notes

### Phase 1 Implementation

```python
# yamlgraph/data_loader.py (new file, ~50 lines)

from pathlib import Path
from typing import Any
import yaml


class DataFileError(Exception):
    """Error loading data file."""
    pass


def load_data_files(config: dict, graph_path: Path) -> dict[str, Any]:
    """Load external YAML files into initial state.

    Args:
        config: Graph configuration dict
        graph_path: Path to the graph YAML file

    Returns:
        Dict of state_key -> loaded data

    Raises:
        DataFileError: If file not found or path escapes graph directory
    """
    data_files = config.get("data_files", {})
    if not data_files:
        return {}

    graph_dir = graph_path.parent.resolve()
    loaded = {}

    for key, value in data_files.items():
        # Option A only: simple string paths
        if not isinstance(value, str):
            raise DataFileError(
                f"data_files[{key}]: Expected string path, got {type(value).__name__}"
            )

        rel_path = value
        file_path = (graph_dir / rel_path).resolve()

        # Security: prevent path traversal (Python 3.9+)
        try:
            file_path.relative_to(graph_dir)
        except ValueError:
            raise DataFileError(
                f"data_files[{key}]: Path '{rel_path}' escapes graph directory.\n"
                f"  Resolved: {file_path}\n"
                f"  Must be within: {graph_dir}"
            )

        if not file_path.exists():
            raise DataFileError(
                f"data_files[{key}]: File not found\n"
                f"  Path: {file_path}\n"
                f"  Hint: Create the file or check the path in your graph YAML"
            )

        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            # Empty files return None from safe_load; normalize to empty dict
            loaded[key] = data if data is not None else {}

    return loaded
```

### Integration Points

| File | Change | Lines |
|------|--------|-------|
| `yamlgraph/data_loader.py` | New file | ~50 |
| `yamlgraph/graph_loader.py` | Call `load_data_files()` in `load_and_compile()` | ~10 |
| `yamlgraph/models/graph_schema.py` | Add `data_files: dict[str, str]` | ~5 |
| `yamlgraph/cli/commands/lint.py` | Validate file existence | ~15 |
| `tests/unit/test_data_loader.py` | New test file | ~80 |
| `reference/data-files.md` | Documentation | ~60 |

**Total:** ~220 lines new/changed

### Caching Semantics

```python
# Data loaded once during compile_graph(), stored in compiled graph
config = load_graph_config("graph.yaml")
data = load_data_files(config.raw, graph_path)  # ← Here
graph = compile_graph(config)

# Each invoke() gets data merged into initial state
result = graph.invoke({"user_input": "...", **data})
```

**Implication:** All threads share the same loaded data (read-only). This is correct for reference data like schemas.

### State Key Collision

If `data_files` key conflicts with user input:

```python
# User input wins - data_files are defaults, not overrides
result = graph.invoke({**data, "user_input": "...", "schema": custom_schema})
```

**Rationale:** Data files are compile-time defaults; runtime input should be able to override.

## Alternatives Considered

### 1. Keep using Python handlers
- **Pros:** Maximum flexibility
- **Cons:** Violates DRY, requires Python for common patterns

### 2. Inline data in graph.yaml
- **Pros:** Single file
- **Cons:** Graphs become huge, can't share schemas across graphs

### 3. `include` directive (like C preprocessor)
- **Pros:** Familiar pattern
- **Cons:** Complicates parsing, harder to reason about final state

### 4. Extended `passthrough` with file loading
```yaml
nodes:
  init:
    type: passthrough
    load_files:
      schema: schema.yaml
```
- **Pros:** Explicit node-based loading
- **Cons:** Still requires a node, can't load before first node runs

## Related

- **questionnaire-api**: Uses this pattern in 8+ questionnaires
  - `questionnaires/audit/graph.yaml` + `schema.yaml`
  - `questionnaires/interrai-ca/graph.yaml` + `schema.yaml`
  - `questionnaires/motyb/graph.yaml` + `schema.yaml`
- **Existing similar features:**
  - `prompts_dir` / `prompts_relative` - Graph-relative prompt resolution
  - `defaults.prompts_dir` - Default prompt directory
- **LangChain precedent:** `hub.pull()` loads external resources

---

## Implementation Checklist

### Day 1: Core Implementation
- [ ] Create `yamlgraph/data_loader.py` with `load_data_files()`
- [ ] Add `DataFileError` exception
- [ ] Write unit tests:
  - [ ] Happy path: single file, multiple files, nested subdirs
  - [ ] Missing file: clear error message
  - [ ] Path traversal: `../secret.yaml`, `../../etc/passwd`
  - [ ] Symlink traversal: symlink pointing outside graph dir
  - [ ] Empty file: returns `{}` not `None`
  - [ ] Invalid YAML: clear parse error

### Day 2: Integration
- [ ] Integrate into `graph_loader.py`
- [ ] Update `GraphConfigSchema` with `data_files` field
- [ ] Add integration test with real graph

### Day 3: Tooling & Docs
- [ ] Add lint check for missing data files
- [ ] Update JSON schema for IDE support
- [ ] Write `reference/data-files.md` documentation
- [ ] Add example to `examples/` or update existing graph

### Day 4: Polish
- [ ] Edge case testing (empty files, large files, unicode)
- [ ] Error message improvements
- [ ] PR review and merge

---

## Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| **JSON support?** | ❌ Deferred to Phase 2 | Keep Phase 1 minimal; YAML covers primary use cases |
| **File size limit?** | ❌ No limit Phase 1 | Defer until real problem; add warning for >1MB in logs |
| **Naming** | `data_files` | Explicit, matches `prompts_dir` pattern, avoids `data` ambiguity |
| **Empty files** | Return `{}` | Normalize `None` to empty dict for safer access |
| **State collision** | Input wins | Data files are defaults; runtime input can override |
| **Parent traversal** | ❌ Blocked | Strict containment within graph directory |
