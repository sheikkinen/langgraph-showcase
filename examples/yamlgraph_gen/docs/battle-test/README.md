# YAMLGraph Generator - Battle Test Plan

Testing the yamlgraph-generator's ability to produce working graphs for each pattern.

## Status Overview

| Pattern | Generated | Lints | Runs | Notes |
|---------|-----------|-------|------|-------|
| Linear | ✅ | ✅ | ✅ | [Test case](00-linear.md) |
| Agent + Websearch | ✅ | ✅ | ✅ | [Test case](05-agent-tools.md) |
| Router | ✅ | ✅ | ✅ | [Test case](01-router.md) - Generator fixed |
| Map | ✅ | ✅ | ✅ | [Test case](02-map.md) - Generator + framework fixed |
| Interrupt | ✅ | ✅ | ✅ | [Test case](03-interrupt.md) - Checkpointer auto-added |
| Subgraph | ⬜ | ⬜ | ⬜ | [Test case](04-subgraph.md) |

## Generator Capability Gaps

| Capability | Status | Notes |
|------------|--------|-------|
| Linear nodes | ✅ | Fully supported |
| Router nodes | ✅ | Single combined node, dict routes, intent field |
| Agent + websearch | ✅ | Built-in DuckDuckGo |
| Map nodes | ✅ | over/as/node/collect pattern, START->map supported |
| Interrupt nodes | ✅ | Checkpointer auto-added, LLM-generated questions |
| Subgraph creation | ❌ | Only generates main graph |
| Custom Python tools | ⚠️ | Stubs generated, not functional |

## Test Cases

- [00-linear.md](00-linear.md) - Linear pattern test ✅
- [01-router.md](01-router.md) - Router pattern test
- [02-map.md](02-map.md) - Map pattern test
- [03-interrupt.md](03-interrupt.md) - Interrupt pattern test
- [04-subgraph.md](04-subgraph.md) - Subgraph pattern test (deferred)
- [05-agent-tools.md](05-agent-tools.md) - Agent + tools pattern test ✅

## Issue Tracking

| Issue | Pattern | Description | Status |
|-------|---------|-------------|--------|
| ~~No checkpointer~~ | interrupt | ~~Generator does not add checkpointer config~~ | ✅ Fixed (auto-adds memory checkpointer) |
| No subgraph files | subgraph | Only generates main graph | Open |
| ~~Untested map~~ | map | ~~Snippet exists but not validated~~ | ✅ Fixed |

## Execution Checklist

1. [x] Run router test → ✅ **PASSED** (generator fixed)
2. [x] Run map test → ✅ **PASSED** (generator + framework fixed)
3. [x] Run interrupt test → ✅ **PASSED** (checkpointer auto-added)
4. [x] Update generator based on findings → ✅ **Complete**
5. [ ] Subgraph test (deferred - multi-file generation)

## Generator Improvements Made

| Improvement | Files Changed | Impact |
|-------------|---------------|--------|
| Router snippet structure | `snippets/patterns/classify-then-process.yaml` | Single combined node, dict routes |
| Router prompt scaffold | `snippets/prompt-scaffolds/router-classify.yaml` | Uses `intent` field (framework requirement) |
| Assembly dict/list preservation | `prompts/assemble_graph.yaml` | Explicit examples prevent format changes |
| Self-documenting snippets | All snippet files | Pattern-specific guidance in comments |
| Prompt schema validation | `prompts/generate_prompts.yaml` | Router schema field requirements |
| Map node API update | `snippets/nodes/map-basic.yaml`, `snippets/patterns/*-map.yaml` | Current API: over/as/node/collect |
| Snippet loader fix | `tools/snippet_loader.py` | Check state.classification.patterns |
| START->map edge support | `yamlgraph/graph_loader.py` | Framework now supports conditional entry points |
