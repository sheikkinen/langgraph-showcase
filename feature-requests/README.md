# YamlGraph Feature Requests

Feature requests from questionnaire-api integration work.

## Priority Summary

| Feature | Priority | Complexity | Impact |
|---------|----------|------------|--------|
| [Graph-relative prompts](graph-relative-prompts.md) | HIGH | Medium | Enables clean multi-graph projects |
| [JSON extraction](json-extraction.md) | MEDIUM | Low | Reduces boilerplate in handlers |
| [Runtime prompt interpolation](runtime-prompt-interpolation.md) | LOW | High | Enables reusable subgraphs with dynamic prompts |

## Context

These requests emerged from building a multi-questionnaire system where:
- Each questionnaire has its own graph + prompts + schema
- A common interview flow pattern is shared across questionnaires
- Graphs live in `questionnaires/{name}/` directories
- Prompts are questionnaire-specific

## Quick Wins

1. **Graph-relative prompts** - Most impactful, moderate effort
2. **JSON extraction** - Small feature, eliminates common boilerplate

## Can Wait

3. **Runtime prompt interpolation** - Nice to have, current workaround acceptable
