# MCP Server

Expose YAMLGraph graphs as tools for Copilot and other MCP-compatible AI assistants.

## Setup

### 1. Install MCP dependency

```bash
pip install -e ".[mcp]"
```

### 2. Configure VS Code

The workspace `.mcp.json` is pre-configured:

```json
{
  "mcpServers": {
    "yamlgraph": {
      "command": ".venv/bin/python3",
      "args": ["yamlgraph/mcp_server.py"],
      "env": {}
    }
  }
}
```

VS Code discovers this automatically. The server starts on demand via stdio transport.

## Tools

### `yamlgraph_list_graphs`

Lists all discovered graphs with names, descriptions, and required variables.

**Parameters:** None

**Example response:**
```json
[
  {
    "name": "hello-world",
    "description": "Simple greeting generator demonstrating basic LLM usage",
    "required_vars": ["name", "style"]
  },
  {
    "name": "code-analysis",
    "description": "Automated code quality analysis",
    "required_vars": ["path", "package"]
  }
]
```

### `yamlgraph_run_graph`

Run a graph by name, passing required variables.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `graph` | string | Yes | Graph name (from `yamlgraph_list_graphs`) |
| `vars` | object | No | Input variables for the graph |

**Example call:**
```json
{
  "graph": "code-analysis",
  "vars": {
    "path": "yamlgraph/",
    "package": "yamlgraph"
  }
}
```

## Graph Discovery

The server scans these glob patterns at startup:

- `examples/demos/*/graph.yaml`
- `examples/*/graph.yaml`

Paths are resolved relative to the project root. Any graph.yaml in a scanned directory is automatically available as an MCP tool.

### Adding a Graph

Place a `graph.yaml` in any scanned directory. The server reads `name`, `description`, and `state` fields from the YAML header:

```yaml
name: my-workflow
description: Does something useful
state:
  input_path: str
  output_format: str
```

The `state` keys become `required_vars` in the tool listing.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: mcp` | `pip install -e ".[mcp]"` |
| `ModuleNotFoundError: yamlgraph` | Ensure `.mcp.json` uses `.venv/bin/python3` |
| Graph not listed | Verify path matches a scan pattern |
| Timeout errors | Graph execution exceeds 120s default; check `config.timeout` in graph YAML |
