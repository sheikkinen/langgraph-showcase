# Test Case: Agent + Tools Pattern

**Status:** ✅ Tested

## Request

```
Create a research agent that can search the web for information
```

## Reference

Compare with `graphs/web-research.yaml`

## Validation Commands

```bash
cd examples/yamlgraph_gen

# Generate
python run_generator.py -o outputs/agent-test \
  'Create a research agent that can search the web for information'

# Structural checks
grep -A10 "type: agent" outputs/agent-test/graph.yaml
grep -A5 "tools:" outputs/agent-test/graph.yaml
grep "type: websearch" outputs/agent-test/graph.yaml

# Execute
source ../../.env && cd outputs/agent-test && \
yamlgraph graph run graph.yaml --var 'query=quantum computing latest advances'
```

## Success Criteria

- [x] Agent node has type: agent with tools: list
- [x] Websearch tool defined with type: websearch
- [x] max_iterations set
- [x] Prompt exists for agent node
- [x] Execution calls websearch and returns results

## Tool Types Supported

| Tool Type | Status | Notes |
|-----------|--------|-------|
| websearch | ✅ | Built-in DuckDuckGo, works |
| python | ⚠️ | Stubs generated, not functional |
| shell | ❌ | Not implemented in generator |

## Results

### Generated Structure

```yaml
tools:
  search_web:
    type: websearch
    provider: duckduckgo
    max_results: 5
    description: "Search the web for information"

nodes:
  research:
    type: agent
    prompt: research
    state_key: research_result
    tools:
      - search_web
    max_iterations: 3
```

### Execution Output

Successfully executed:
- Agent ran 3 iterations
- Made 7 web searches
- Synthesized research summary

### Issues Found

| Issue | Description | Severity |
|-------|-------------|----------|
| Custom tools | Python tool stubs are not functional | Medium |
