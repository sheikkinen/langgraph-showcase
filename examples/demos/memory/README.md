# Memory Agent Demo

Multi-turn code review assistant with conversation memory.

## Usage

```bash
yamlgraph graph run examples/demos/memory/graph.yaml \
  --var input="Show recent commits"
```

## What It Does

1. Agent analyzes git repository
2. Maintains conversation history across turns
3. Can reference previous queries in follow-up questions

## Key Concepts

- **Conversation memory** - Messages accumulated in state
- **`messages`** reducer - Appends rather than replaces
- **Multi-turn context** - LLM sees full conversation history

## Tools

- `git_log` - Recent commits
- `git_diff` - File changes
- `git_show` - Commit details

## Difference from git-report

| Aspect | git-report | memory |
|--------|------------|--------|
| Memory | Single turn | Multi-turn |
| Use case | One-shot queries | Conversations |
| State | Fresh each run | Accumulates |

## Learning Path

Extension of [git-report](../git-report/) with memory. See also [interview](../interview/) for human-in-the-loop with memory.
