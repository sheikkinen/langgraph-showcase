# Feature Request: JSON Schema Export for IDE Support

**Priority:** LOW  
**Type:** Feature  
**Status:** Proposed  
**Effort:** 2 days  
**Requested:** 2026-01-28

## Summary

Export the graph YAML schema as a JSON Schema file for IDE autocompletion and in-editor validation of `graph.yaml` files.

## Problem

YamlGraph has robust Pydantic validation in `graph_schema.py` (NodeConfig, SubgraphNodeConfig, etc.), but this only runs at graph load time. When editing `graph.yaml` files:

1. **No autocompletion** - Users must consult docs for valid node types, edge syntax
2. **No inline validation** - Typos like `typ: llm` or `stat_key: result` aren't caught until execution
3. **No documentation on hover** - Field descriptions aren't surfaced in the editor

VS Code with YAML Language Server (redhat.vscode-yaml) supports JSON Schema for YAML files, enabling rich editing experience.

## Proposed Solution

### CLI Command

```bash
# Export JSON Schema to file
yamlgraph schema export --output schemas/graph-schema.json

# Print to stdout
yamlgraph schema export

# Include in package distribution
yamlgraph schema path  # Prints path to bundled schema
```

### Generated Schema (excerpt)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://yamlgraph.dev/schemas/graph-v1.json",
  "title": "YamlGraph Graph Configuration",
  "description": "Schema for YamlGraph graph.yaml files",
  "type": "object",
  "required": ["version", "nodes", "edges"],
  "properties": {
    "version": {
      "type": "string",
      "const": "1.0",
      "description": "Graph schema version"
    },
    "name": {
      "type": "string",
      "description": "Human-readable graph name"
    },
    "nodes": {
      "type": "object",
      "additionalProperties": {
        "$ref": "#/definitions/NodeConfig"
      }
    },
    "edges": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/EdgeConfig"
      }
    },
    "checkpointer": {
      "$ref": "#/definitions/CheckpointerConfig"
    }
  },
  "definitions": {
    "NodeConfig": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "enum": ["llm", "router", "map", "agent", "python", "interrupt", "passthrough", "subgraph", "tool"],
          "description": "Node type determines execution behavior"
        },
        "prompt": {
          "type": "string",
          "description": "Prompt template name (required for llm, router, agent)"
        },
        "state_key": {
          "type": "string",
          "description": "State key to store node output"
        },
        "on_error": {
          "type": "string",
          "enum": ["skip", "fail", "retry", "fallback"],
          "description": "Error handling strategy"
        }
      }
    }
  }
}
```

### VS Code Integration

Users add to `.vscode/settings.json`:

```json
{
  "yaml.schemas": {
    "https://yamlgraph.dev/schemas/graph-v1.json": ["**/graph.yaml", "**/graphs/*.yaml"]
  }
}
```

Or with local schema:

```json
{
  "yaml.schemas": {
    "./schemas/graph-schema.json": ["**/graph.yaml"]
  }
}
```

### Implementation

Use Pydantic's JSON Schema export:

```python
# yamlgraph/cli/schema_commands.py

def cmd_schema_export(args: Namespace) -> None:
    """Export graph schema as JSON Schema."""
    from yamlgraph.models.graph_schema import GraphConfig
    
    schema = GraphConfig.model_json_schema()
    
    # Add $schema and $id
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["$id"] = "https://yamlgraph.dev/schemas/graph-v1.json"
    
    if args.output:
        Path(args.output).write_text(json.dumps(schema, indent=2))
        print(f"✅ Schema exported to {args.output}")
    else:
        print(json.dumps(schema, indent=2))
```

### Bundled Schema

Include pre-generated schema in package:

```
yamlgraph/
├── schemas/
│   └── graph-v1.json
```

Accessible via:
```python
from yamlgraph import get_schema_path
print(get_schema_path())  # /path/to/yamlgraph/schemas/graph-v1.json
```

## Acceptance Criteria

- [ ] `yamlgraph schema export` outputs JSON Schema
- [ ] `--output` flag writes to file
- [ ] `yamlgraph schema path` prints bundled schema location
- [ ] Schema validates all node types (llm, router, map, agent, python, interrupt, passthrough, subgraph)
- [ ] Schema includes property descriptions from Pydantic Field
- [ ] Schema includes enum values for type, on_error, etc.
- [ ] Works with VS Code YAML extension (redhat.vscode-yaml)
- [ ] Bundled schema included in PyPI package
- [ ] Tests for schema export command
- [ ] Documentation with VS Code setup instructions

## Alternatives Considered

### 1. SchemaStore.org Submission (Future Enhancement)
Submit schema to schemastore.org for automatic recognition. Requires stable public URL first.

### 2. VS Code Extension (Rejected)
Build dedicated YamlGraph extension. Overkill when YAML Language Server + JSON Schema works.

### 3. In-Editor Language Server (Rejected)
Build LSP server for YamlGraph YAML. Much higher effort for similar benefit.

## Related

- `yamlgraph/models/graph_schema.py` - Pydantic models to export
- `yamlgraph graph validate` - CLI validation (works, but post-hoc)
- VS Code YAML extension: https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml
