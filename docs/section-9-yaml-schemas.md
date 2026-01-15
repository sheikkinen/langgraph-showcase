# Section 9: YAML-Defined Output Schemas

**Goal**: Move demo-specific Pydantic models from Python code to YAML configuration, keeping only generic/framework models in Python.

**Status**: ✅ Implemented (commit 3cc791c)

---

## Problem Statement

Current state has demo-specific models hardcoded in Python:

```
showcase/models/
├── schemas.py   # 217 lines - mix of generic + demo-specific
└── state.py     # 150 lines - demo-specific state classes
```

Demo-specific models that should move to YAML:
- `Greeting` - test fixture
- `Analysis` - showcase.yaml specific
- `GeneratedContent` - showcase.yaml specific  
- `PipelineResult` - showcase.yaml specific
- `ToneClassification` - router-demo specific
- `DraftContent` - reflexion-demo specific
- `Critique` - reflexion-demo specific
- `GitReport` - git-report specific

Generic models to keep in Python:
- `PipelineError` / `ErrorType` - framework error handling
- `GenericReport` - reusable flexible schema
- `BaseState` - common state fields

---

## Solution: Inline Schema in Prompt YAML

### YAML Schema Definition Format

Add `schema:` block to prompt YAML files:

```yaml
# prompts/router-demo/classify_tone.yaml
schema:
  name: ToneClassification
  fields:
    tone:
      type: str
      description: "Detected tone: positive, negative, or neutral"
    confidence:
      type: float
      constraints: {ge: 0.0, le: 1.0}
      description: "Confidence score 0-1"
    reasoning:
      type: str
      description: "Explanation for the classification"

system: |
  You are a tone classifier...

user: |
  Classify: {message}
```

---

## Implementation Summary

### What Was Implemented

**Phase 1: Schema Loader** (showcase/schema_loader.py)
- `resolve_type()` - Parse type strings like `str`, `int`, `float`, `bool`, `list[str]`, `dict[str, Any]`
- `build_pydantic_model()` - Create Pydantic models dynamically with Field descriptors
- `load_schema_from_yaml()` - Load schema from prompt YAML file
- 15 unit tests in `tests/unit/test_schema_loader.py`

**Phase 2: Node Factory Integration** (showcase/node_factory.py)
- `resolve_prompt_path()` - Find YAML file from prompt name
- `get_output_model_for_node()` - Priority-based model resolution (explicit > inline > None)
- Integration with `create_node_function()` for automatic schema loading
- 5 integration tests in `tests/unit/test_inline_schema.py`

**Phase 3: Prompt Migration** (all prompts now have inline schemas)
- `prompts/router-demo/classify_tone.yaml` - ToneClassification
- `prompts/generate.yaml` - GeneratedContent
- `prompts/analyze.yaml` - Analysis
- `prompts/reflexion-demo/draft.yaml` - DraftContent
- `prompts/reflexion-demo/critique.yaml` - Critique
- `prompts/reflexion-demo/refine.yaml` - DraftContent (reuses same schema)
- `prompts/git_report.yaml` - GitReport

**Graph YAMLs Updated** (removed `output_model` directives)
- `graphs/router-demo.yaml`
- `graphs/showcase.yaml`
- `graphs/reflexion-demo.yaml`
- `graphs/git-report.yaml`

### What Was NOT Changed

**Python models kept in schemas.py** - Still needed for:
- State class type hints (`showcase/models/state.py`)
- Integration tests (`tests/integration/test_providers.py`)
- CLI attribute access (`showcase/cli/commands.py`)
- Export functions (`showcase/storage/export.py`)

The inline schema feature provides **flexibility**, not replacement. Prompts can now be self-contained while Python code retains full type safety.

---

## Type System

### Supported Type Syntax

| YAML Type | Python Type |
|-----------|-------------|
| `str` | `str` |
| `int` | `int` |
| `float` | `float` |
| `bool` | `bool` |
| `list[str]` | `list[str]` |
| `list[int]` | `list[int]` |
| `dict[str, Any]` | `dict[str, Any]` |
| `Any` | `Any` |

### Field Constraints

```yaml
schema:
  name: MyModel
  fields:
    score:
      type: float
      description: "Quality score"
      constraints:
        ge: 0.0
        le: 1.0
    tags:
      type: list[str]
      default: []
      optional: true
```

---

## Priority Order

When resolving output models, the system uses this priority:

1. **Explicit `output_model` in graph YAML** (highest priority)
   ```yaml
   nodes:
     analyze:
       output_model: showcase.models.Analysis
   ```

2. **Inline `schema` in prompt YAML** (second priority)
   ```yaml
   schema:
     name: Analysis
     fields: ...
   ```

3. **None** (no structured output, raw text)

---

## Trade-offs

### Benefits
- ✅ Prompts are self-contained (single YAML file per prompt)
- ✅ Schema is visible alongside the prompt that uses it
- ✅ Easier to understand what a prompt returns
- ✅ No need to update Python code for new prompts

### Limitations
- ❌ No IDE autocomplete for dynamically generated models
- ❌ Runtime schema parsing adds complexity
- ❌ Complex validators require Python (inline schemas support basic constraints only)
- ❌ Dynamic models harder to debug

---

## Future Improvements

1. Support for nested models (model fields referencing other inline models)
2. Schema inheritance/composition
3. Custom validators in YAML (simple expressions)
4. Schema caching for performance
