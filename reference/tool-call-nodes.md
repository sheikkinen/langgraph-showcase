# Tool Call Nodes Reference

Tool call nodes enable dynamic tool execution where the tool name and arguments are resolved from state at runtime. This enables LLM-driven tool orchestration without hardcoding tool dispatch logic.

---

## Overview

Tool call nodes solve the dynamic dispatch pattern:

```
state.task = {tool: "search_file", args: {path: "foo.py"}}
    ↓
type: tool_call resolves tool + args from state
    ↓
result = search_file(path="foo.py")
```

**Key features:**
- Tool name resolved dynamically from state
- Arguments resolved dynamically from state
- Uses graph's `tools:` section (single source of truth)
- Graceful error handling for unknown tools or exceptions
- Works inside `type: map` for batch tool execution

---

## Basic Syntax

```yaml
nodes:
  call_tool:
    type: tool_call
    tool: "{state.task.tool}"       # Tool name from state
    args: "{state.task.args}"       # Tool arguments from state
    state_key: result               # Where to store result
```

---

## Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `type` | `string` | Yes | Must be `"tool_call"` |
| `tool` | `string` | Yes | State expression for tool name |
| `args` | `string` | Yes | State expression for tool arguments dict |
| `state_key` | `string` | No | State key for result (default: node name) |

---

## Result Structure

Tool call nodes always return a structured result:

```python
{
    "task_id": 1,           # From state.task.id if present
    "tool": "search_file",  # Resolved tool name
    "success": True,        # True if tool executed without error
    "result": {...},        # Tool return value (on success)
    "error": None           # Error message (on failure)
}
```

### Success Case
```python
{"task_id": 1, "tool": "search_file", "success": True, "result": {"matches": [...]}, "error": None}
```

### Unknown Tool
```python
{"task_id": 1, "tool": "bad_tool", "success": False, "result": None, "error": "Unknown tool: bad_tool"}
```

### Tool Exception
```python
{"task_id": 1, "tool": "search_file", "success": False, "result": None, "error": "FileNotFoundError: ..."}
```

---

## Common Pattern: Map + Tool Call

The primary use case is LLM-driven discovery where an LLM generates a list of tool calls, then a map node executes them:

```yaml
state:
  discovery_plan: DiscoveryPlan   # LLM generates this
  discovery_findings: list        # Collected results

nodes:
  plan_discovery:
    prompt: plan_discovery
    state_key: discovery_plan
    # LLM outputs: {tasks: [{id: 1, tool: "search_file", args: {...}}, ...]}

  execute_discovery:
    type: map
    over: "{state.discovery_plan.tasks}"
    as: task
    node:
      type: tool_call
      tool: "{state.task.tool}"
      args: "{state.task.args}"
      state_key: discovery_result
    collect: discovery_findings

edges:
  - from: plan_discovery
    to: execute_discovery
```

---

## Tools Registry

Tool call nodes use the graph's `tools:` section as the registry. Only `type: python` tools are currently supported:

```yaml
tools:
  search_file:
    type: python
    module: yamlgraph.tools.analysis.code_context
    function: search_in_file

  read_lines:
    type: python
    module: yamlgraph.tools.analysis.code_context
    function: read_lines
```

The tool name in `{state.task.tool}` must match a key in the `tools:` section.

---

## Error Handling

Tool call nodes never raise exceptions. Errors are captured in the result:

1. **Unknown tool**: `success=False`, `error="Unknown tool: X"`
2. **Tool exception**: `success=False`, `error="<exception message>"`
3. **Invalid args**: `success=False`, `error="<type error message>"`

This allows downstream nodes to process partial results even when some tools fail.

---

## Comparison with type: python

| Aspect | `type: python` | `type: tool_call` |
|--------|----------------|-------------------|
| Tool selection | Static (in YAML) | Dynamic (from state) |
| Use case | Known tool at design time | LLM chooses tool at runtime |
| Error handling | Can raise | Always returns result dict |
| Args source | Variables in YAML | Resolved from state |

---

## See Also

- [Map Nodes](map-nodes.md) - For parallel tool execution
- [Patterns](patterns.md) - LLM-driven orchestration patterns
- [impl-agent](impl-agent.md) - Example using tool_call for discovery
