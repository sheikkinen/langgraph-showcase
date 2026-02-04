# CLI Reference

Complete command reference for the `yamlgraph` CLI.

## Commands Overview

```
yamlgraph [-h] {list-runs,resume,trace,export,graph} ...
```

| Command | Description |
|---------|-------------|
| `graph` | Run graphs, list, validate, lint, generate diagrams |
| `list-runs` | List recent pipeline runs |
| `resume` | Resume a paused pipeline |
| `trace` | Show execution trace (requires LangSmith) |
| `export` | Export run results to JSON |

---

## yamlgraph graph

The primary command for running and managing graphs.

```
yamlgraph graph {run,info,validate,lint,codegen} ...
```

### graph run

Run a graph with input variables.

```bash
yamlgraph graph run <graph_path> [options]
```

**Arguments:**
- `graph_path` - Path to graph YAML file

**Options:**
| Flag | Short | Description |
|------|-------|-------------|
| `--var VAR` | `-v` | Set state variable (key=value), repeatable |
| `--thread THREAD` | `-t` | Thread ID for state persistence |
| `--export` | `-e` | Export results to files |
| `--full` | `-f` | Show full output without truncation |
| `--async` | `-a` | Use async execution for parallel map nodes |

**Examples:**
```bash
# Basic run with variables
yamlgraph graph run examples/demos/yamlgraph/graph.yaml -v topic=AI -v style=casual

# Parallel map execution (recommended for Mistral provider)
yamlgraph graph run examples/demos/map/graph.yaml -v topic=AI --async

# With thread ID for resumable sessions
yamlgraph graph run examples/demos/interview/graph.yaml -t session-123

# Full output for debugging
yamlgraph graph run examples/demos/reflexion/graph.yaml -v topic="climate" -f

# Export results
yamlgraph graph run examples/demos/git-report/graph.yaml -v input="What changed?" -e
```

### graph info

Show structure and metadata of a graph.

```bash
yamlgraph graph info <graph_path>
```

**Example:**
```bash
yamlgraph graph info examples/demos/router/graph.yaml
```

### graph validate

Validate graph YAML against schema.

```bash
yamlgraph graph validate <graph_paths...>
```

**Example:**
```bash
yamlgraph graph validate examples/demos/*/graph.yaml
```

### graph lint

Lint graph for common issues (missing state keys, unused tools, etc.).

```bash
yamlgraph graph lint <graph_paths...>
```

**Example:**
```bash
yamlgraph graph lint examples/demos/yamlgraph/graph.yaml examples/demos/router/graph.yaml
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key |
| `MISTRAL_API_KEY` | Mistral API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `PROVIDER` | Default LLM provider (`anthropic`, `mistral`, `openai`) |
| `LANGSMITH_API_KEY` | LangSmith tracing key |
| `LANGSMITH_PROJECT` | LangSmith project name |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
