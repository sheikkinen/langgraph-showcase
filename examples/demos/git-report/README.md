# Git Report Agent

AI agent with git tools for repository analysis.

## Usage

```bash
yamlgraph graph run examples/demos/git-report/graph.yaml \
  --var input="What changed recently?"
```

More queries:

```bash
yamlgraph graph run examples/demos/git-report/graph.yaml \
  --var input="Summarize the last 20 commits"

yamlgraph graph run examples/demos/git-report/graph.yaml \
  --var input="Who are the main contributors?"
```

## What It Does

1. Takes a natural language query about the git repository
2. Agent decides which tools to use
3. Executes git commands and analyzes output
4. Returns human-readable report

## Tools Available

| Tool | Command | Description |
|------|---------|-------------|
| `recent_commits` | `git log --oneline -n {count}` | List recent commits |
| `commit_details` | `git show {hash}` | Show commit details |
| `file_changes` | `git diff --stat HEAD~{n}` | Show changed files |

## Key Concepts

- **`type: agent`** - ReAct agent with tool access
- **Tool selection** - LLM decides which tools to call
- **`max_iterations`** - Limit tool call loops

## Agent Configuration

```yaml
nodes:
  analyze:
    type: agent
    prompt: analyze
    tools: [recent_commits, commit_details, file_changes]
    max_iterations: 8
```

## Learning Path

After [reflexion](../reflexion/). This shows tool-using agents. Next: [interview](../interview/) for human-in-the-loop.
