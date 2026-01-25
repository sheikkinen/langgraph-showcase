# YAMLGraph Linter Reflection & Enhancement Opportunities

## Current Linter Capabilities

The yamlgraph linter (`yamlgraph/tools/graph_linter.py`) currently performs these checks:

### 1. State Declarations (E001, E002)
- Validates that variables used in prompts and tools are declared in `state:` section
- Checks variables in:
  - Shell tool commands
  - Prompt file placeholders
- Handles built-in state fields (thread_id, current_step, errors, etc.)
- Accounts for runtime state_key additions

### 2. Tool References (E003, W001)
- Error if tool referenced in node but not defined
- Warning for unused tool definitions

### 3. Prompt Files (E004)
- Checks that prompt files exist for nodes with `prompt:` field
- Resolves prompt directory from graph config

### 4. Edge Coverage (W002, W003)
- Forward traversal: nodes reachable from START
- Backward traversal: nodes with path to END
- Handles conditional edges with list targets

### 5. Node Types (E005)
- Validates node type against allowed set:
  - agent, interrupt, llm, map, passthrough, python, router, subgraph

## What's Missing: Pattern-Specific Validation

The current linter validates **syntax** but not **pattern semantics**. Our battle-tested snippets contain pattern-specific requirements that could be validated.

### Opportunities from Snippets & Battle Tests

#### 1. Router Pattern Validation (from battle test fixes)

**Current snippet knowledge:**
```yaml
# snippets/nodes/router-basic.yaml
node:
  type: router
  prompt: __NODE_NAME__
  routes:
    __ROUTE_A__: handle___ROUTE_A__  # Must be dict, not list
  state_key: classification

# snippets/prompt-scaffolds/router-classify.yaml
schema:
  fields:
    intent:  # MUST be 'intent' or 'tone' (framework hardcoded)
```

**New checks we could add:**
- **E101**: Router node `routes:` must be dict, not list
- **E102**: Router prompt schema must use 'intent' or 'tone' field (not 'category', 'classification', etc.)
- **W101**: Router node missing `default_route` field
- **E103**: Conditional edge to router targets must be list (not string)

#### 2. Map Pattern Validation (✅ IMPLEMENTED)

**Current snippet knowledge:**
```yaml
# snippets/nodes/map-basic.yaml
node:
  type: map
  over: "{state.__LIST_FIELD__}"     # Required
  as: __ITEM_NAME__                  # Required
  node:                               # Nested sub-node required
    prompt: __SUB_NODE_PROMPT__
    state_key: __ITEM_RESULT__
  collect: __COLLECTED_RESULTS__     # Required
```

**Implemented checks:**
- **E201**: Map node missing required field 'over'
- **E202**: Map node missing required field 'as'
- **E203**: Map node missing required field 'node' (nested sub-node)
- **E204**: Map node missing required field 'collect'
- **E205**: Map node should NOT have 'prompt' at top level (only in nested node)
- **W201**: Map node 'over' expression should resolve to list type

#### 3. Interrupt Pattern Validation (✅ IMPLEMENTED)

**Current snippet knowledge:**
```yaml
# snippets/nodes/interrupt-basic.yaml
node:
  type: interrupt
  prompt: __NODE_NAME__  # or message: "static text"
  resume_key: "{user_input_key}"  # Required for storing user input

# Graph requires checkpointer
checkpointer:
  type: memory  # or sqlite
```

**Implemented checks:**
- **E301**: Interrupt node missing 'resume_key' field
- **E302**: Interrupt node must have either 'prompt' or 'message' field
- **W301**: Graph with interrupt nodes should have checkpointer config
- **E303**: Interrupt node state_key should be declared in state section
- **E304**: Checkpointer configuration validation
- **W302**: Warning when both 'prompt' and 'message' are specified

#### 4. Agent Pattern Validation (✅ IMPLEMENTED)

**Current snippet knowledge:**
```yaml
# snippets/nodes/agent-with-tools.yaml
node:
  type: agent
  tools: [tool1, tool2]  # Required for agent
  state_key: result
```

**Implemented checks:**
- **W401**: Agent node with no tools (warning)
- **E401**: Agent node tools must reference defined tools or built-in websearch

#### 5. Subgraph Pattern Validation (✅ IMPLEMENTED)

**Current snippet knowledge:**
```yaml
# snippets/nodes/subgraph-basic.yaml
node:
  type: subgraph
  graph: subgraphs/__SUBGRAPH_NAME__.yaml
  input_mapping:
    __PARAM__: "{state.__SOURCE__}"
  output_mapping:
    __RESULT__: __TARGET_STATE_KEY__
```

**Implemented checks:**
- **E501**: Subgraph node missing 'graph' field
- **E502**: Subgraph file path does not exist
- **W501**: Subgraph node missing input_mapping
- **W502**: Subgraph node missing output_mapping

## Implementation Strategy

### Option 1: Pattern-Aware Linter Checks

Add pattern-specific check functions to `linter_checks.py`:

```python
def check_router_nodes(graph_path: Path) -> list[LintIssue]:
    """Validate router nodes follow pattern requirements."""
    issues = []
    graph = load_graph(graph_path)

    for node_name, node_config in graph.get("nodes", {}).items():
        if node_config.get("type") == "router":
            # Check routes is dict
            routes = node_config.get("routes")
            if isinstance(routes, list):
                issues.append(LintIssue(
                    severity="error",
                    code="E101",
                    message=f"Router node '{node_name}' has routes as list; must be dict",
                    fix="Change routes to dict mapping: {route: target_node}"
                ))

            # Check for default_route
            if not node_config.get("default_route"):
                issues.append(LintIssue(
                    severity="warning",
                    code="W101",
                    message=f"Router node '{node_name}' missing default_route",
                    fix="Add default_route field for fallback routing"
                ))

    return issues
```

### Option 2: Snippet-Derived Schema Validation

Extract validation rules from snippet YAML comments:

```yaml
# snippets/nodes/router-basic.yaml
# LINT_RULES:
#   - required_type: dict
#     path: routes
#     error_code: E101
#     message: "routes must be dict, not list"
#   - required_field: default_route
#     severity: warning
#     error_code: W101
```

Then parse these annotations to auto-generate validators.

### Option 3: Reference Graph Corpus

Use our battle-tested reference graphs as validation corpus:

```python
# Extract patterns from reference graphs
REFERENCE_GRAPHS = {
    "router": "graphs/router-demo.yaml",
    "map": "graphs/map-demo.yaml",
    "interrupt": "graphs/interview-demo.yaml",
}

def validate_against_reference(graph: dict, pattern: str) -> list[LintIssue]:
    """Compare graph structure to reference implementation."""
    reference = load_graph(REFERENCE_GRAPHS[pattern])
    # Compare field presence, types, structure
```

## Recommended Next Steps

1. **✅ Map pattern validation implemented** - E201-E205, W201 with comprehensive tests
2. **✅ Interrupt pattern validation implemented** - E301-E304, W301-W302 with comprehensive tests
3. **✅ Agent pattern validation implemented** - W401, E401 with comprehensive tests
4. **✅ Subgraph pattern validation implemented** - E501-E502, W501-W502 with comprehensive tests
   def detect_patterns(graph: dict) -> set[str]:
       patterns = set()
       for node_config in graph.get("nodes", {}).values():
           node_type = node_config.get("type", "llm")
           if node_type in {"router", "map", "interrupt", "agent", "subgraph"}:
               patterns.add(node_type)
       return patterns
   ```

3. **Integrate with generator** - add linter pass after assembly:
   ```yaml
   nodes:
     assemble_graph: ...
     validate_patterns:  # NEW - pattern-specific validation
       type: python
       tool: validate_pattern_compliance
     generate_prompts: ...
   ```

## Benefits

1. **Catch issues earlier** - before graph execution
2. **Educational** - explains pattern requirements with fix suggestions
3. **Self-documenting** - snippets become source of truth for patterns
4. **Generator quality** - validate generator output meets pattern specs
5. **Framework evolution** - when patterns change, update snippets + linter together

## Example: Enhanced Linter Output

```
❌ graph.yaml (sentiment-classifier)

   ❌ [E101] Router node 'classify' has routes as list; must be dict
      Fix: Change routes to dict mapping: {'route_name': 'target_node'}

   ❌ [E102] Router prompt schema uses field 'category'; must be 'intent' or 'tone'
      Fix: Add 'intent' field to schema (available: sentiment). Framework requires 'intent' or 'tone' for routing.

   ⚠ [W101] Router node 'classify' missing default_route
      Fix: Add default_route: 'fallback_node' for unhandled classifications

   ⚠ [W301] Graph has interrupt nodes but no checkpointer config
      Fix: Add checkpointer section: {type: memory}

❌ parallel-processor.yaml (batch processing)

   ❌ [E201] Map node 'process_items' missing required field 'over'
      Fix: Add 'over' field: over: "{state.list_field}" to specify list to iterate over

   ❌ [E203] Map node 'process_items' missing required field 'node'
      Fix: Add nested 'node' field with prompt and state_key for processing each item

   ❌ [E205] Map node 'process_items' should not have top-level 'prompt' field
      Fix: Move 'prompt' field into nested 'node' configuration

   ⚠ [W201] Map node 'process_items' 'over' field should reference state list
      Fix: Use state reference: over: "{state.items}"

❌ human-feedback.yaml (interactive workflow)

   ❌ [E301] Interrupt node 'ask_feedback' missing required field 'resume_key'
      Fix: Add 'resume_key' field: resume_key: user_input_variable to store user response

   ❌ [E302] Interrupt node 'ask_feedback' missing 'prompt' or 'message' field
      Fix: Add either 'prompt' field (for LLM-generated question) or 'message' field (for static text)

   ❌ [E303] Interrupt node 'ask_feedback' state_key 'question' not declared in state section
      Fix: Add 'question' to state section: state: question: str

   ⚠ [W301] Graph with interrupt nodes missing checkpointer configuration
      Fix: Add checkpointer section: checkpointer: {type: memory} or {type: sqlite, path: 'checkpoints.db'}

❌ research-agent.yaml (tool-using agent)

   ❌ [E401] Agent node 'researcher' references undefined tool 'analyze_docs'
      Fix: Define tool 'analyze_docs' in tools section or use one of: search_web, websearch

   ⚠ [W401] Agent node 'code_analyzer' has no tools configured
      Fix: Add 'tools' field with list of tool names: tools: [tool1, tool2]
```

This gives users actionable feedback based on battle-tested pattern knowledge!
