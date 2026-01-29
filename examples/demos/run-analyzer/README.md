# Run Analyzer Demo

Analyzes previous LangSmith runs for issues and provides recommendations.

## Setup

```bash
# Set LangSmith credentials
export LANGCHAIN_API_KEY=lsv2_...
export LANGCHAIN_ENDPOINT=https://api.smith.langchain.com  # or eu.api.smith.langchain.com
export LANGCHAIN_PROJECT=your-project
```

Or add to `.env` in project root and source it:
```bash
set -a && source ../../.env && set +a
```

## Quick Start

```bash
cd examples/demos/run-analyzer

# Analyze the most recent run
yamlgraph graph run graph.yaml -v mode=latest

# Analyze a specific run by ID
yamlgraph graph run graph.yaml -v run_id=abc-123

# Analyze the most recent failed run
yamlgraph graph run graph.yaml -v mode=last_failed
```

**Note:** Must run from `examples/demos/run-analyzer/` directory for local tool imports to work.

## How It Works

1. **Fetch Run Info** (agent node): Uses LangSmith tools to get run details and errors
2. **Analyze Issues** (LLM node): Identifies root causes and severity
3. **Recommend** (LLM node): Provides actionable recommendations

## Tools

Local tools in `tools/langsmith_tools.py`:
- `get_run_details_tool` - Get status, inputs, outputs, timing
- `get_run_errors_tool` - Get all errors from run and child nodes
- `get_failed_runs_tool` - List recent failed runs
