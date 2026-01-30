# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**YAMLGraph** is a YAML-first framework for building LLM pipelines using LangGraph. The key insight: 60-80% of AI workflows can be defined entirely in YAML (graphs + prompts + schemas) without writing Python code. Built on LangGraph with multi-provider LLM support (Anthropic, Mistral, OpenAI).

## Development Process

Before implementing any feature or fix:

### 1. Research First
- Analyze existing solutions and alternatives
- Check if the problem is already solved elsewhere in the codebase
- Review similar patterns in `examples/` and `reference/`

### 2. Plan Before Coding
- Create an implementation plan (feature request or issue)
- Define acceptance criteria upfront
- Estimate effort realistically

### 3. Critical Review
- Plans need multiple iterations
- Challenge assumptions: "Is this the right approach?"
- Get feedback before writing code

### 4. Reflect: Is This Really Needed?
- Documenting patterns is cheaper than new code
- Showing alternatives without implementation often suffices
- Ask: "Does this belong in YAMLGraph, or is it a deployment/application concern?"

> **Example**: URL-based prompt loading was proposed as a 2-day feature. After reflection, we realized documenting deployment patterns (volume mounts, git-sync, ConfigMaps) solved the same problem without adding framework complexity. See `reference/prompt-deployment.md`.

## Development Commands

### Environment Setup
```bash
# Install in development mode
pip install -e ".[dev]"

# Install with optional features
pip install -e ".[dev,redis,websearch,storyboard]"
```

### Testing
```bash
# Fast unit tests (no coverage report)
pytest tests/unit/ -q --no-cov

# All tests with coverage
pytest tests/ -q

# Specific test file
pytest tests/unit/test_graph_loader.py -v

# Run single test
pytest tests/unit/test_graph_loader.py::test_load_graph_config -v

# Integration tests (require API keys)
pytest tests/integration/ -v

# Coverage HTML report
pytest tests/ --cov=yamlgraph --cov-report=html
# Then open htmlcov/index.html
```

### Linting
```bash
# Check code style
ruff check yamlgraph/

# Auto-fix issues
ruff check --fix yamlgraph/

# Format code
ruff format yamlgraph/
```

### Running Examples
```bash
# CLI execution
yamlgraph graph run graphs/showcase.yaml --var topic="AI" --var style=casual

# List available graphs
yamlgraph graph list

# Validate graph schema
yamlgraph graph validate graphs/*.yaml

# Lint graphs for common issues
yamlgraph graph lint graphs/*.yaml

# Show graph info
yamlgraph graph info graphs/router-demo.yaml
```

## Architecture Overview

### Three-Layer Pattern

YAMLGraph uses a strict separation of concerns:

```
┌─────────────────────────────────┐
│  Presentation (Python CLI/API)  │  ← Args, colors, REPL, HTTP routes
├─────────────────────────────────┤
│  Logic (YAML Graphs)            │  ← LLM calls, routing, state, checkpoints
├─────────────────────────────────┤
│  Side Effects (Python Tools)    │  ← External APIs, file I/O, shell commands
└─────────────────────────────────┘
```

**When building new features:**
- Put LLM orchestration in YAML graphs (`graphs/*.yaml`)
- Put reusable prompts in YAML templates (`prompts/*.yaml`)
- Put external integrations in Python tools (`yamlgraph/tools/` or `examples/*/nodes/`)

### Core Compilation Pipeline

```
YAML file → load_graph_config() → GraphConfig (Pydantic)
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
            build_state_class()  parse_tools()   compile_graph()
                    │                 │                 │
                    ▼                 ▼                 ▼
            Dynamic TypedDict   Tool Registry    StateGraph (LangGraph)
                                                       │
                                              graph.compile()
                                                       │
                                                       ▼
                                              CompiledGraph
```

**Key files:**
- `graph_loader.py` (~385 lines): Orchestrates entire compilation
- `node_factory/` modules: Creates node functions by type (llm, router, map, agent, etc.)
- `models/state_builder.py`: Generates dynamic TypedDict from graph YAML
- `executor.py`: Unified `execute_prompt()` interface for all LLM calls

### Node Execution Flow

Every node follows this pattern (implemented in `node_factory/`):

1. **Pre-checks**: `check_requirements()` verifies required state keys exist
2. **Loop protection**: `check_loop_limit()` prevents infinite cycles
3. **Resume support**: `skip_if_exists` check for checkpointing
4. **Execution**: `execute_prompt()` or custom logic
5. **Return**: Dict with state updates (never mutate state directly)

### Dynamic State Management

**No manual state classes needed.** State is auto-generated from YAML:

```yaml
# graphs/example.yaml
nodes:
  generate:
    state_key: generated  # ← Creates state.generated field automatically
  analyze:
    state_key: analysis   # ← Creates state.analysis field automatically
```

State builder (`models/state_builder.py`) scans all `state_key` fields and generates a TypedDict at runtime.

## Critical Rules

### 1. YAML Prompts Only (Never Hardcode)

**All prompts MUST live in `prompts/*.yaml`:**

```python
# ❌ WRONG - Never hardcode prompts
llm.invoke("Write a summary of {topic}")

# ✅ CORRECT - Use YAML prompts
from yamlgraph.executor import execute_prompt
result = execute_prompt("summarize", {"topic": topic})
```

**Template syntax:**
- Simple: `{variable}` for basic substitution
- Advanced: Jinja2 auto-detected when `{{` or `{%` present
  - Loops: `{% for item in items %}...{% endfor %}`
  - Conditionals: `{% if condition %}...{% endif %}`
  - Filters: `{{ text[:50] }}`, `{{ items | join(", ") }}`

### 2. Multi-Provider LLM Factory (Never Import Directly)

```python
# ❌ WRONG - Direct provider import
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-3")

# ✅ CORRECT - Use factory
from yamlgraph.utils.llm_factory import create_llm
llm = create_llm(provider="anthropic")
```

**Provider selection priority:** Function parameter > YAML metadata > `PROVIDER` env var > default (`anthropic`)

### 3. Pydantic for All LLM Outputs

**Option A: Inline schema in YAML prompt (preferred for graph-specific outputs):**
```yaml
# prompts/analyze.yaml
schema:
  name: Analysis
  fields:
    summary: {type: str, description: "Brief summary"}
    key_points: {type: list[str], description: "Main points"}
```

**Option B: Python model in `yamlgraph/models/schemas.py` (for shared schemas):**
```python
from pydantic import BaseModel, Field

class Analysis(BaseModel):
    summary: str = Field(description="Brief summary")
    key_points: list[str] = Field(description="Main points")
```

### 4. State Updates (Never Mutate)

```python
# ❌ WRONG - Direct mutation
def node_fn(state):
    state["key"] = value
    return state

# ✅ CORRECT - Return update dict
def node_fn(state):
    return {"key": value}
```

LangGraph merges the returned dict into state.

### 5. Error Handling Pattern

```python
from yamlgraph.models import PipelineError

try:
    result = execute_prompt(...)
    return {"state_key": result}
except Exception as e:
    error = PipelineError.from_exception(e, node="node_name")
    errors = list(state.get("errors") or [])
    errors.append(error)
    return {"errors": errors}
```

For YAML-defined nodes, error handling is automatic via `on_error: skip|retry|fail|fallback`.

## Extension Points

### Adding a New Node Type

1. **Define constant** in `yamlgraph/constants.py`:
   ```python
   class NodeType(StrEnum):
       MY_NODE = "my_node"
   ```

2. **Create factory** in `yamlgraph/node_factory/` (choose appropriate module):
   ```python
   def create_my_node(node_name: str, node_config: dict, state_class: type) -> Callable:
       def node_fn(state: dict) -> dict:
           # Implementation
           return {"result_key": result}
       return node_fn
   ```

3. **Register** in `graph_loader.py` `_compile_node()`:
   ```python
   elif node_type == NodeType.MY_NODE:
       node_fn = create_my_node(node_name, node_config, state_class)
   ```

4. **Add tests** in `tests/unit/test_my_node.py`
5. **Document** in `reference/graph-yaml.md`

### Adding a New LLM Provider

1. **Update** `yamlgraph/config.py`:
   ```python
   DEFAULT_MODELS = {
       "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
       "mistral": os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
       "openai": os.getenv("OPENAI_MODEL", "gpt-4o"),
       "replicate": os.getenv("REPLICATE_MODEL", "ibm-granite/granite-4.0-h-small"),
       "xai": os.getenv("XAI_MODEL", "grok-4-1-fast-reasoning"),
       "lmstudio": os.getenv("LMSTUDIO_MODEL", "qwen2.5-coder-7b-instruct"),
       "my_provider": os.getenv("MY_PROVIDER_MODEL", "my-model"),
   }
   ```

2. **Update** `yamlgraph/utils/llm_factory.py`:
   ```python
   elif selected_provider == "my_provider":
       from langchain_my_provider import ChatMyProvider
       llm = ChatMyProvider(model=selected_model, temperature=temperature)
   ```

3. **Add dependency** to `pyproject.toml` (optional extra recommended)
4. **Update docs** in `reference/graph-yaml.md`

### Adding a New Tool Type

1. **Create parser** in `yamlgraph/tools/my_tool.py`:
   ```python
   from langchain_core.tools import BaseTool

   def parse_my_tools(tools_config: dict) -> list[BaseTool]:
       tools = []
       for name, config in tools_config.items():
           if config.get("type") == "my_tool":
               tools.append(create_my_tool(name, config))
       return tools
   ```

2. **Register** in `graph_loader.py` `compile_graph()`:
   ```python
   from yamlgraph.tools.my_tool import parse_my_tools
   all_tools.extend(parse_my_tools(config.tools))
   ```

3. **Add tests** in `tests/unit/test_my_tool.py`

## Code Quality Standards

- **Module size**: Target < 400 lines, max 500 (split into submodules if exceeded)
- **TDD**: Red-Green-Refactor approach mandatory
- **Type hints**: Required on all public functions
- **Python 3.11+**: Use `|` for unions, not `Union[]`
- **Logging**: Use `logging.getLogger(__name__)` (user-facing prints use emojis: 📝 🔍 ✓ ✗ 🚀)
- **Deprecation**: Use `DeprecationError` when marking old APIs during refactoring

## Testing Patterns

### Mock LLM for Unit Tests
```python
def test_node_execution(mock_llm, monkeypatch):
    monkeypatch.setattr("yamlgraph.executor.create_llm", lambda **k: mock_llm)
    result = execute_prompt("test", {})
    assert result is not None
```

### Real LLM for Integration Tests
```python
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="No API key")
def test_full_pipeline():
    graph = load_and_compile("graphs/test.yaml")
    result = graph.compile().invoke({"topic": "AI"})
    assert "generated" in result
```

### YAML Fixture Files
```python
def test_router(tmp_path):
    graph_yaml = tmp_path / "test.yaml"
    graph_yaml.write_text("""
version: "1.0"
nodes:
  classify:
    type: router
    ...
""")
    config = load_graph_config(graph_yaml)
```

## Production Application Pattern

See `examples/npc/` for a complete production example, or `examples/demos/` for standalone demos:

```bash
# Run all demos
./examples/demos/demo.sh

# Individual demos: hello, router, reflexion, map, memory, interview, etc.
```

NPC example architecture:

```
┌─────────────────────────────────┐
│  FastAPI + HTMX Frontend        │
├─────────────────────────────────┤
│  Session Adapter (Python)       │  ← Wraps graph with thread_id management
├─────────────────────────────────┤
│  YAMLGraph (encounter-multi.yaml)│  ← Map nodes, interrupt_before
├─────────────────────────────────┤
│  Tools + Prompts                │
└─────────────────────────────────┘
```

Key patterns:
- **Session Adapter**: Clean API over raw graph (`EncounterSession`)
- **Human-in-Loop**: `interrupt_before` + `Command(resume=player_choice)`
- **Map Nodes**: Parallel fan-out with `Send()` for multi-entity processing
- **HTMX Integration**: Server-rendered fragments, minimal JavaScript

## Sync/Async Pattern

The codebase uses **sync-first with async wrappers**:

- `executor.py` + `executor_async.py` (share `executor_base.py`)
- `llm_factory.py` + `llm_factory_async.py` (async wraps sync)

Async modules import from sync, adding only async-specific features (streaming, `asyncio.gather`). This avoids duplication and event loop issues for sync users.

## Anti-Patterns to Avoid

| ❌ Wrong | ✅ Correct |
|---------|-----------|
| Hardcoded prompts in Python | YAML templates in `prompts/` |
| Direct provider imports | `create_llm()` factory |
| Untyped dicts | Pydantic models or inline YAML schemas |
| `state["key"] = value` | `return {"key": value}` |
| Silent exceptions | `PipelineError.from_exception()` |
| Files > 400 lines | Refactor into submodules |
| Skip tests | TDD red-green-refactor |

## Security Notes

- **Shell injection protection**: All user variables sanitized with `shlex.quote()` in `tools/shell.py`
- **No eval()**: Condition expressions parsed with regex only
- **Command templates trusted**: Only YAML config is trusted; all runtime variables are escaped

## Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Anthropic authentication |
| `MISTRAL_API_KEY` | Mistral authentication |
| `OPENAI_API_KEY` | OpenAI authentication |
| `REPLICATE_API_TOKEN` | Replicate authentication |
| `XAI_API_KEY` | xAI Grok authentication |
| `LMSTUDIO_BASE_URL` | LM Studio local server URL |
| `PROVIDER` | Default LLM provider (anthropic/mistral/openai/replicate/xai/lmstudio) |
| `LANGSMITH_TRACING` | Enable LangSmith observability (true/false) |
| `LANGSMITH_PROJECT` | LangSmith project name |
