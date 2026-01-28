# Feature Request: FR-013 - Slim Core (Move Demos to Examples)

**Priority:** MEDIUM  
**Type:** Refactoring  
**Status:** Implemented (v0.4.2)  
**Effort:** 2-3 days  
**Requested:** 2026-01-28  
**Completed:** 2026-01-28

## Summary

Move demo graphs, prompts, and scripts from core directories to `examples/`, keeping the core package slim.

## Problem

The core package contains ~2,500 lines of demo content that inflates the published package:

| Directory | Lines | Files | Purpose |
|-----------|-------|-------|---------|
| `graphs/` | 878 | 16 | Demo graphs |
| `prompts/` | 1,147 | 39 | Demo prompts |
| `scripts/` | 1,593 | ~10 | Demo scripts |
| **Total** | ~3,600 | ~65 | Demo content |

This content is useful for learning but doesn't belong in the core package.

## Proposed Solution

### Phase 1: Reorganize to Examples

```
examples/
├── demos/                    # NEW: consolidated demos
│   ├── hello/
│   │   ├── graph.yaml
│   │   └── prompts/
│   ├── router/
│   ├── reflexion/
│   ├── git-report/
│   ├── memory/
│   ├── map/
│   ├── interview/
│   ├── code-analysis/
│   └── demo.sh              # Moved from scripts/
├── booking/                  # Already exists
├── npc/                      # Already exists
└── ...
```

### Phase 2: Core Retains Only

```
graphs/
└── hello.yaml               # Minimal working example

prompts/
└── greet.yaml               # Minimal example prompt
```

### Phase 3: Update Package Config

```toml
[tool.setuptools.package-data]
yamlgraph = [
    "schemas/*.json",
]
# Remove graphs/ and prompts/ from package
```

## Acceptance Criteria

- [ ] All demo graphs moved to `examples/demos/`
- [ ] All demo prompts moved with their graphs
- [ ] `scripts/demo.sh` moved to `examples/demos/`
- [ ] Core retains only `hello.yaml` example
- [ ] `pyproject.toml` updated to exclude demos from package
- [ ] README updated with new paths
- [ ] All examples still work after move
- [ ] Tests updated/moved as needed

## Migration Impact

| Item | Before | After |
|------|--------|-------|
| Core package size | ~10,500 lines | ~7,000 lines |
| Demo location | `graphs/`, `prompts/` | `examples/demos/` |
| `demo.sh` location | `scripts/` | `examples/demos/` |

## Alternatives Considered

1. **Keep as-is**: Rejected - inflates package unnecessarily
2. **Separate demos repo**: Overkill for this project size
3. **Git submodule**: Adds complexity without benefit

## Related

- FR-012: Legacy CLI removal (completed)
- `examples/` directory structure
- `pyproject.toml` package configuration
