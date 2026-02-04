# Web Research Agent

AI agent that researches topics using web search.

## Prerequisites

```bash
pip install yamlgraph[websearch]
```

Requires `TAVILY_API_KEY` or similar search provider.

## Usage

```bash
yamlgraph graph run examples/demos/web-research/graph.yaml \
  --var topic="Latest developments in AI agents"
```

## What It Does

1. Takes a research topic
2. Agent searches the web for information
3. Synthesizes findings into a report

## Tools

| Tool | Description |
|------|-------------|
| `search_web` | Search web for current information |

## Key Concepts

- **`type: python`** tool - Custom Python function as tool
- **External API** - Calls Tavily/similar search API
- **Agent synthesis** - Combines multiple sources

## Tool Configuration

```yaml
tools:
  search_web:
    type: python
    module: examples.shared.websearch
    function: search_web
    description: "Search the web for current information"
```

## Related

- [codegen/](../../codegen/) - More complex agent with 24 tools
- [git-report](../git-report/) - Agent with shell tools
