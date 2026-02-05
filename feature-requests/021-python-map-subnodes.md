# Feature Request: Python Tool Support in Map Sub-Nodes

**Priority:** MEDIUM
**Type:** Enhancement
**Status:** Proposed
**Effort:** 0.5 days
**Requested:** 2026-02-05

## Summary

Enable `type: python` sub-nodes within `type: map` nodes, allowing fan-out over items with Python tool processing.

## Problem

Currently, map node inline `node:` configuration only supports:
- `type: llm` (via `create_node_function`)
- `type: tool_call` (via `create_tool_call_node`)

This limits the fan-out pattern to LLM-only or tool-call-only operations.

**Real use case**: Implementation mapping for ISO 13485 compliance:
- Fan-out over Python files
- Per-file: parse AST, extract elements, call LLM for annotation
- This requires a Python tool that does complex logic + LLM calls

Without this feature, workarounds are:
1. Flatten to element-level and use LLM-only map (loses per-file grouping)
2. Process sequentially in a single Python tool (loses parallelism)
3. Use `execute_prompt()` inside Python tool (works but bypasses graph orchestration)

## Proposed Solution

Extend `compile_map_node()` in `map_compiler.py` to handle `type: python`:

```python
# In compile_map_node(), around line 133:
if sub_node_type == NodeType.TOOL_CALL:
    if tools_registry is None:
        raise ValueError(...)
    sub_node = create_tool_call_node(sub_node_name, sub_node_config, tools_registry)
elif sub_node_type == NodeType.PYTHON:
    if python_tools is None:
        raise ValueError(
            f"Map node '{name}' has python sub-node but no python_tools registry"
        )
    tool_name = sub_node_config.get("tool")
    if tool_name not in python_tools:
        raise ValueError(f"Unknown python tool '{tool_name}' in map node '{name}'")
    sub_node = python_tools[tool_name]
else:
    sub_node = create_node_function(...)
```

### Usage Example

```yaml
tools:
  process_file:
    type: python
    module: "myproject.tools"
    function: process_single_file
    description: "Parse AST, extract elements, annotate"

nodes:
  discover:
    type: python
    tool: discover_files

  process:
    type: map
    over: "{state.files}"
    as: current_file
    collect: file_results
    node:
      type: python
      tool: process_file
      state_key: module_result

  assemble:
    type: python
    tool: assemble_results
```

### Implementation Changes

1. **`map_compiler.py`**:
   - Add `python_tools` parameter to `compile_map_node()`
   - Add `NodeType.PYTHON` case in sub-node creation

2. **`graph_loader.py`**:
   - Pass `python_tools` registry to `compile_map_node()`

3. **Tests**:
   - Add test for map with python sub-node
   - Test error handling (missing tool, tool not in registry)

## Acceptance Criteria

- [ ] `type: python` works in map sub-node configuration
- [ ] Tool must be defined in `tools:` section
- [ ] Clear error if tool not found in registry
- [ ] `_map_index` preserved in output for ordering
- [ ] Error handling via `wrap_for_reducer` works correctly
- [ ] Tests added for happy path and error cases
- [ ] Example added to docs or examples/

## Alternatives Considered

1. **Flatten and use LLM map**: Works but loses logical grouping (per-file → per-element)
2. **Sequential Python tool**: Works but loses parallelism benefit
3. **Nested subgraphs**: More complex, not currently supported anyway
4. **`execute_prompt()` in Python tool**: Works (current workaround) but bypasses graph-level orchestration and tracing

## Related

- [map_compiler.py](../yamlgraph/map_compiler.py) - Current implementation (lines 127-138)
- [graph_loader.py](../yamlgraph/graph_loader.py) - Passes registries to compiler
- [13485/PLAN-mapping-v2.md](../13485/PLAN-mapping-v2.md) - Use case that discovered this gap
- [examples/ocr_cleanup/](../examples/ocr_cleanup/) - Example using map with LLM sub-node
