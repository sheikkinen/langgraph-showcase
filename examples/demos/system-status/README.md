# System Status Demo

Demonstrates `type: tool` nodes for deterministic shell command execution.

## What It Does

1. **Gathers system metrics** using 6 parallel tool nodes:
   - `df -h` - Disk usage
   - `memory_pressure` - Memory statistics  
   - `sysctl -n vm.loadavg` - Load average
   - `uptime` - System uptime
   - `ps aux -r | head -15` - Top CPU processes
   - `ps aux -m | head -15` - Top memory processes

2. **Analyzes with LLM** to diagnose performance issues

## Usage

```bash
yamlgraph graph run examples/demos/system-status/graph.yaml \
  --var complaint="my system is running a bit slow - what could be the issue"
```

Custom complaints:

```bash
yamlgraph graph run examples/demos/system-status/graph.yaml \
  --var complaint="Chrome is freezing and fan is loud"

yamlgraph graph run examples/demos/system-status/graph.yaml \
  --var complaint="disk space warning keeps appearing"
```

## Key Pattern: `type: tool` vs `type: agent`

| Aspect | `type: tool` (this demo) | `type: agent` |
|--------|--------------------------|---------------|
| Decision | Deterministic - always runs | LLM decides which tools |
| Use case | Known data gathering | Exploratory analysis |
| Control | Full control over execution | LLM autonomy |
| Cost | Cheaper (no tool selection LLM call) | More LLM calls |

## Pipeline

```
START → get_disk → get_memory → get_load → get_uptime → get_top_cpu → get_top_mem → analyze → END
```

Each tool node gathers one piece of system info, then the `analyze` LLM node receives all data.

## Output

Returns structured diagnosis:

```json
{
  "diagnosis": "High memory pressure from Chrome...",
  "key_findings": ["...", "...", "..."],
  "recommendations": ["...", "...", "..."],
  "priority_action": "Close unused Chrome tabs",
  "severity": "medium"
}
```

## macOS Notes

- `memory_pressure` may not be available on all systems (uses `on_error: skip`)
- All commands are macOS-specific
- Variables are sanitized with `shlex.quote()` to prevent injection
