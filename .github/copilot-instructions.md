# GitHub Copilot Instructions - YAMLGraph

Getting started: See `reference/getting-started.md` for a comprehensive overview of the YAMLGraph framework, its core files, key patterns, and essential rules.

## Development Process

1. **Research First** - Analyze alternatives before proposing implementation
2. **Plan** - Create implementation plan before coding
3. **Critical Review** - Plans need multiple iterations; challenge assumptions
4. **Reflect** - Is this really needed? Documenting patterns or using existing solutions is cheaper than new code

> "The cheapest code is the code you don't write."

## Core Technologies
- **LangGraph**: Pipeline orchestration with state management
- **Pydantic v2**: Structured, validated LLM outputs
- **YAML Prompts**: Declarative prompt templates with Jinja2 support
- **Jinja2**: Advanced template engine for complex prompts
- **Multi-Provider LLMs**: Anthropic, Mistral, OpenAI, Replicate, xAI, LM Studio
- **Checkpointers**: Memory, SQLite, and Redis for state persistence
- **LangSmith**: Observability and tracing

- Term 'backward compatibility' is a key indicator for a refactoring need in this project. Use DeprecationError to mark old APIs while refactoring.

- use ruff, vulture, radon, pylint --disable=all --enable=duplicate-code ., jscpd .

## Essential Rules

### 1. YAML Prompts with Jinja2 Support
- **ALL prompts MUST be in YAML files** under `prompts/`
- Never hardcode prompts in Python
- Use shared `execute_prompt()` from `yamlgraph.executor`
- Use `load_prompt()` and `resolve_prompt_path()` from `yamlgraph.utils.prompts`
- **Simple templates**: Use `{variable}` for basic substitution
- **Advanced templates**: Use Jinja2 syntax for loops, conditionals, filters
  - Loops: `{% for item in items %}...{% endfor %}`
  - Conditionals: `{% if condition %}...{% endif %}`
  - Filters: `{{ text[:50] }}`, `{{ items | join(", ") }}`
- Template engine auto-detects: `{{` or `{%` triggers Jinja2 mode

### 2. Multi-Provider LLM Factory
- **Use factory**: `from yamlgraph.utils.llm_factory import create_llm`
- **Never import providers directly** in nodes (use factory)
- **Provider selection**: Parameter > YAML metadata > env var > default
- **Caching**: Factory handles LLM instance caching
- Supported: `"anthropic"`, `"mistral"`, `"openai"`, `"replicate"`, `"xai"`, `"lmstudio"`

### 3. Pydantic for All Outputs
- All LLM outputs use Pydantic models in `yamlgraph/models/schemas.py`
- Or define inline schemas in YAML prompt files (preferred for graph-specific outputs)
- Define fields with `Field(description="...")`
- Inherit from `pydantic.BaseModel`

### 4. LangGraph State Pattern
- State is dynamically generated from YAML graph config (no manual state.py needed)
- Built via `build_state_class()` from `yamlgraph.models.state_builder`
- Nodes return `dict` with partial updates
- Never mutate state directly

### 5. Error Handling
Error handling is built into `graph_loader.py` for YAML-defined nodes.
For custom Python nodes:
```python
from yamlgraph.models import PipelineError

try:
    result = execute_prompt(...)
    return {"field": result, "current_step": "node_name"}
except Exception as e:
    error = PipelineError.from_exception(e, node="node_name")
    errors = list(state.get("errors") or [])
    errors.append(error)
    return {"errors": errors, "current_step": "node_name"}
```

### 6. Code Quality
- **Module size**: < 400 lines (max 500)
- **TDD**: Red-Green-Refactor with tests for all changes
- **KISS**: Prefer clarity over cleverness
- **Type hints**: On ALL functions
- **Python 3.11+**: Use `|` for unions

### 7. Logging
- Use `logging.getLogger(__name__)`
- User-facing prints with emojis: 📝 🔍 📊 ✓ ✗ 🚀 💾

## Anti-Patterns

❌ Hardcoded prompts → ✅ YAML templates
❌ Untyped dicts → ✅ Pydantic models
❌ Direct state mutation → ✅ Return update dicts
❌ Silent exceptions → ✅ `PipelineError.from_exception()`
❌ Files > 400 lines → ✅ Refactor into modules
❌ Skip tests → ✅ TDD red-green-refactor

## Reminder

The Zeroth Law. A robot may not harm humanity, or, by inaction, allow humanity to come to harm.
