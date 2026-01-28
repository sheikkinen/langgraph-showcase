# FR-012-3: Remove Legacy CLI Code (Phase 2)

**Priority:** MEDIUM  
**Status:** IMPLEMENTED  
**Parent:** FR-012 (Deprecate Legacy CLI)  
**Target:** v0.5.0

## Summary

Remove all deprecated legacy CLI code after deprecation warnings have been in place for one release cycle.

## Prerequisites

All completed in v0.4.0:
- ✅ FR-012-0: Fix CLI checkpointer
- ✅ FR-012-1: Deprecate legacy resume
- ✅ FR-012-2: Deprecate list-runs, trace, export; delete dead cmd_run

## Code Removed

| Item | Lines | Location |
|------|-------|----------|
| `commands.py` | ~250 | `yamlgraph/cli/` - DELETED |
| `validators.py` | ~40 | `yamlgraph/cli/` - DELETED |
| `database.py` | ~320 | `yamlgraph/storage/` - DELETED |
| `build_resume_graph` | ~30 | `yamlgraph/builder.py` - DELETED |
| `run_pipeline` | ~20 | `yamlgraph/builder.py` - DELETED |
| `test_database.py` | ~145 | `tests/unit/` - DELETED |
| `test_resume.py` | ~75 | `tests/integration/` - DELETED |
| `test_cli.py` | ~130 | `tests/unit/` - DELETED |
| `test_legacy_cli_deprecation.py` | ~130 | `tests/unit/` - DELETED |
| Legacy CLI parser entries | ~50 | `yamlgraph/cli/__init__.py` |
| **Total Removed** | **~1,190** | |

## Validation Checklist

- [x] All deprecated commands removed
- [x] YamlGraphDB deleted
- [x] build_resume_graph deleted
- [x] run_pipeline deleted  
- [x] Legacy tests deleted
- [x] No import errors
- [x] All 1158 tests pass
- [x] Documentation tests updated
