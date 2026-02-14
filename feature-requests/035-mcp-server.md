# Plan: YAMLGraph MCP Server

**Status**: Draft
**Date**: 2026-02-14

## Motivation

YAMLGraph encapsulates repeating LLM processing tasks in YAML graphs. We have 20+ working graphs covering code analysis, git reporting, beautification, feature brainstorming, and more. Yet in our daily Copilot workflow, we never use them — instead reinventing the same multi-step processes via ad-hoc terminal commands each session.

The Model Context Protocol (MCP) makes YAMLGraph graphs available as first-class Copilot tools. When Copilot can call `yamlgraph_run_graph` directly, it reaches for graphs naturally because they're in its tool palette.

## Location Decision

**Core (`yamlgraph/mcp_server.py`)** — not an example.

The MCP server is an API surface for YAMLGraph, like the CLI (`yamlgraph/cli/`). It exposes existing core functionality (graph loading, compilation, execution) through MCP protocol. It belongs alongside:
- `yamlgraph/cli/` — CLI interface (CAP-09)
- `examples/openai_proxy/` — example of *using* YAMLGraph (not core)

The Tier 2 workflow graphs (`req-audit`, `changelog-draft`, `file-health`) belong in `examples/demos/` — they're *applications* of YAMLGraph, not core.

## RTM: New Capability & Requirements

### CAP-19: MCP Server Interface

| Requirement | Description | Module |
|-------------|-------------|--------|
| REQ-YG-066 | MCP server with stdio transport: expose `yamlgraph_list_graphs` and `yamlgraph_run_graph` tools via MCP protocol | `mcp_server` |
| REQ-YG-067 | Graph discovery: scan configured directories for `graph.yaml`, parse headers for name/description/state schema | `mcp_server` |
| REQ-YG-068 | Graph invocation via MCP: compile and invoke any discovered graph with vars, return structured result JSON | `mcp_server` |

### RTM Updates Required

| Document | Change |
|----------|--------|
| `ARCHITECTURE.md` | Add CAP-19 section, REQ-YG-066–068 rows to requirements table |
| `scripts/req_coverage.py` | Add CAP-19 to CAPABILITIES dict, extend ALL_REQS range to 68 |

## Architecture

```
.mcp.json → yamlgraph/mcp_server.py → load_graph_config + compile_graph + invoke
                                     ↓
                              structured JSON result
```

- **Transport**: stdio (same as Forge MCP server pattern)
- **SDK**: `mcp` v1.12.2 (already installed globally; add to `pyproject.toml` `[mcp]` extras)
- **Runtime**: Reuses existing `yamlgraph.graph_loader` pipeline — zero new runtime code

## Server Design

### Tools Exposed

| Tool | Purpose |
|------|---------|
| `yamlgraph_list_graphs` | List available graphs with descriptions and required vars |
| `yamlgraph_run_graph` | Run any graph by path with `--var` params, return result dict |

### Tool Schema

```json
{
  "yamlgraph_run_graph": {
    "graph": "examples/demos/code-analysis/graph.yaml",
    "vars": {
      "path": "yamlgraph/",
      "package": "yamlgraph"
    }
  }
}
```

### Graph Discovery

The server scans configured directories for `graph.yaml` files at startup, parsing YAML headers (`name`, `description`, `state`) to populate tool descriptions and parameter schemas.

Default scan paths:
- `examples/demos/*/graph.yaml`
- `examples/*/graph.yaml`
- `workflows/*/graph.yaml` (for dev-workflow graphs)

## Candidate Graphs

### Tier 1 — Existing (immediate value, zero new YAML)

| Graph | Copilot Use Case |
|-------|-------------------|
| `demos/code-analysis` | "Analyze yamlgraph/ for quality issues" — ruff, radon, vulture, coverage, bandit |
| `demos/git-report` | "What changed in the last 10 commits?" — agent with git tools |
| `beautify` | "Generate HTML infographic for this graph" — graph.yaml → visual docs |
| `demos/feature-brainstorm` | "Propose improvements for the tools subsystem" — self-analyzing agent |
| `demos/run-analyzer` | "Analyze my last failed LangSmith run" — post-mortem agent |

### Tier 2 — New (high-value dev workflow graphs)

| Graph | Copilot Use Case | Description |
|-------|-------------------|-------------|
| `workflows/req-audit` | "Cross-check req IDs vs tests" | Parse ARCHITECTURE.md + grep tests → diff report |
| `workflows/changelog-draft` | "Draft CHANGELOG entry" | git log → structured summary |
| `workflows/file-health` | "Check file sizes & complexity" | Commandment 8 audit as a graph |

## TDD: Tests First (Commandment 7)

### Test File: `tests/unit/test_mcp_server.py`

| Test | Marker | What it proves |
|------|--------|----------------|
| `test_discover_graphs_finds_yaml` | REQ-YG-067 | Finds graph.yaml files in scan dirs, parses headers |
| `test_discover_graphs_empty_dir` | REQ-YG-067 | Empty/missing dir returns empty list |
| `test_discover_graphs_parses_state` | REQ-YG-067 | Extracts state vars as parameter schema |
| `test_list_tools_schema` | REQ-YG-066 | Tool list includes correct names and input schemas |
| `test_run_graph_hello` | REQ-YG-068 | Invokes hello graph via MCP, returns greeting in result |
| `test_run_graph_missing` | REQ-YG-068 | Missing graph returns error, doesn't crash server |
| `test_run_graph_with_vars` | REQ-YG-068 | Vars passed through to graph state correctly |
| `test_run_graph_timeout` | REQ-YG-068 | Graph timeout produces error result, not hang |

## Implementation

### Component 1: MCP Server Core (~150 lines)

**File**: `yamlgraph/mcp_server.py`

```python
# Pseudocode
class YamlGraphMCPServer:
    def __init__(self):
        self.server = Server("yamlgraph")
        self.graph_dirs = [...]

    def discover_graphs(self) -> list[GraphInfo]:
        """Scan dirs for graph.yaml, parse headers."""

    def list_tools(self) -> list[types.Tool]:
        """Return yamlgraph_list_graphs + yamlgraph_run_graph."""

    def call_tool(self, name, args) -> types.TextContent:
        """Load, compile, invoke graph → JSON result."""
```

Key design decisions:
- Compile graphs on-demand (not at startup) to avoid import cost
- Return full result dict as JSON, let Copilot interpret
- Capture stdout/stderr from shell tools, include in result
- Timeout: inherit from graph config or default 120s

### Component 2: Dependencies

**File**: `pyproject.toml`

```toml
[project.optional-dependencies]
mcp = ["mcp>=1.0.0"]
```

### Component 3: MCP Configuration

**File**: `.mcp.json` (workspace root)

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

Note: Uses `.venv/bin/python3` (not system python) to ensure yamlgraph is importable.

### Component 4: Copilot Instructions Update

Add to `.github/copilot-instructions.md`:

```markdown
## YAMLGraph MCP Tools

You have access to YAMLGraph graphs as MCP tools. Use them for repeatable tasks:
- `yamlgraph_run_graph` with graph="demos/code-analysis" for code quality audits
- `yamlgraph_run_graph` with graph="demos/git-report" for git analysis
- `yamlgraph_list_graphs` to discover available graphs
```

## Documentation

### New Reference Doc: `reference/mcp-server.md`

| Section | Content |
|---------|---------|
| Overview | What MCP is, why YAMLGraph exposes it |
| Setup | `.mcp.json` config, venv requirements, VS Code settings |
| Tools | `yamlgraph_list_graphs` and `yamlgraph_run_graph` with schemas |
| Graph Discovery | How graphs are discovered, scan paths, state→schema mapping |
| Usage Examples | Copilot conversation examples showing MCP tool calls |
| Adding Graphs | How to make a graph MCP-visible (just put it in a scanned dir) |
| Troubleshooting | Common issues: venv path, import errors, timeouts |

### Reference Index Update: `reference/README.md`

Add to "Advanced Features" table:

```markdown
| [MCP Server](mcp-server.md) | Expose graphs as Copilot/MCP tools |
```

### Other Doc Updates

| Document | Change |
|----------|--------|
| `ARCHITECTURE.md` | CAP-19 section + REQ-YG-066–068 |
| `CHANGELOG.md` | New entry under next version |
| `CLAUDE.md` | Add MCP server to Architecture Overview |
| `.github/copilot-instructions.md` | Add MCP tools usage section |
| `pyproject.toml` | Add `[mcp]` extras group |
| `scripts/req_coverage.py` | Add CAP-19, extend ALL_REQS to 68 |

## Usage Examples

### Before (ad-hoc terminal commands)
```
User: "check code quality"
→ run ruff → run radon → run vulture → run coverage → read outputs → synthesize
(5 tool calls, ~30s)
```

### After (MCP tool call)
```
User: "check code quality"
→ yamlgraph_run_graph(graph="demos/code-analysis", vars={"path": "yamlgraph/", "package": "yamlgraph"})
→ structured analysis + recommendations (1 tool call)
```

## Implementation Order (Sermon-compliant)

1. Add REQ-YG-066–068 to `ARCHITECTURE.md`
2. Add CAP-19 to `scripts/req_coverage.py`, extend ALL_REQS to 68
3. Add `mcp` to `pyproject.toml` `[mcp]` extras
4. Write failing tests (`tests/unit/test_mcp_server.py`) — red
5. Implement `yamlgraph/mcp_server.py` — green
6. Refactor if needed
7. Create `.mcp.json`
8. Create `reference/mcp-server.md`
9. Update `reference/README.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, `CHANGELOG.md`
10. `pre-commit run --all-files` → submit

## Effort Estimate

| Component | Effort |
|-----------|--------|
| RTM updates (ARCHITECTURE, req_coverage) | 30min |
| Tests (TDD red phase) | 1h |
| MCP server core | ~2h |
| `.mcp.json` + config | 15min |
| `reference/mcp-server.md` | 30min |
| Doc updates (CLAUDE, copilot-instructions, CHANGELOG, README) | 30min |
| Tier 2 graphs (req-audit, changelog-draft, file-health) | ~1h each |
| **Total MVP (server + docs)** | **~5h** |
| **Total with Tier 2 graphs** | **~8h** |

## Decision Points

1. **Graph discovery**: Scan directories vs. explicit whitelist?
   - Recommendation: Scan with configurable dirs, simpler maintenance
2. **Tier 2 priority**: Which new graphs first?
   - Recommendation: req-audit (most repeated manual task)
3. **Error handling**: How to surface graph execution errors?
   - Recommendation: Return error in result JSON, don't crash server

## Dependencies

- `mcp` SDK v1.12.2 (installed globally, need in yamlgraph venv)
- VS Code MCP discovery enabled (already configured)
- No new external dependencies

## References

- Forge MCP server: `/Users/sheikki/Documents/src/forge/forge_mcp_server.py` (345 lines, reference implementation)
- MCP SDK docs: https://modelcontextprotocol.io
- Existing API surface: `examples/openai_proxy/api/app.py`
