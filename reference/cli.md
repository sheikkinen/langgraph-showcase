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
yamlgraph graph {run,list,info,validate,lint,mermaid} ...
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

**Examples:**
```bash
# Basic run with variables
yamlgraph graph run graphs/showcase.yaml -v topic=AI -v style=casual

# With thread ID for resumable sessions
yamlgraph graph run graphs/interview.yaml -t session-123

# Full output for debugging
yamlgraph graph run graphs/reflexion-demo.yaml -v topic="climate" -f

# Export results
yamlgraph graph run graphs/git-report.yaml -v input="What changed?" -e
```

### graph list

List available graphs in the workspace.

```bash
yamlgraph graph list
```

### graph info

Show structure and metadata of a graph.

```bash
yamlgraph graph info <graph_path>
```

**Example:**
```bash
yamlgraph graph info graphs/router-demo.yaml
```

### graph validate

Validate graph YAML against schema.

```bash
yamlgraph graph validate <graph_paths...>
```

**Example:**
```bash
yamlgraph graph validate graphs/*.yaml
```

### graph lint

Lint graph for common issues (missing state keys, unused tools, etc.).

```bash
yamlgraph graph lint <graph_paths...>
```

**Example:**
```bash
yamlgraph graph lint graphs/showcase.yaml graphs/router-demo.yaml
```

### graph mermaid

Generate Mermaid diagram from graph definition.

```bash
yamlgraph graph mermaid <graph_path>
```

**Example:**
```bash
yamlgraph graph mermaid graphs/reflexion-demo.yaml
```

---

## yamlgraph list-runs

List recent pipeline runs from checkpoint storage.

```bash
yamlgraph list-runs [--limit N]
```

---

## yamlgraph resume

Resume a paused pipeline (typically after interrupt node).

```bash
yamlgraph resume --thread-id <thread_id> [--value <value>]
```

**Example:**
```bash
# Resume with user input
yamlgraph resume --thread-id session-123 --value "Alice"
```

---

## yamlgraph trace

Show execution trace for debugging.

```bash
yamlgraph trace [--verbose]
```

Requires LangSmith to be configured (`LANGSMITH_API_KEY`).

---

## yamlgraph export

Export run results to JSON file.

```bash
yamlgraph export --thread-id <thread_id> [--output <path>]
```

**Example:**
```bash
yamlgraph export --thread-id abc123 --output results.json
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
