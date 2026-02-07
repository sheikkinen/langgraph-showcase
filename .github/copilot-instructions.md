# GitHub Copilot Instructions - YAMLGraph

Getting started: See `reference/getting-started.md` for a comprehensive overview of the YAMLGraph framework, its core files, key patterns, and essential rules.

## Core Technologies
- **LangGraph**: Pipeline orchestration with state management
- **Pydantic v2**: Structured, validated LLM outputs
- **YAML Prompts**: Declarative prompt templates with Jinja2 support
- **Jinja2**: Advanced template engine for complex prompts
- **Multi-Provider LLMs**: Anthropic, Mistral, OpenAI, Replicate, xAI, LM Studio
- **Checkpointers**: Memory, SQLite, and Redis for state persistence
- **LangSmith**: Observability and tracing

### Conventions
- Term 'backward compatibility' is a key indicator for a refactoring need. Use `DeprecationError` to mark old APIs.
- Code quality tools: `ruff`, `vulture`, `radon`, `pylint --disable=all --enable=duplicate-code .`, `jscpd .`
- No heredoc for Python scripts
- Run shell scripts with redirect to log file. Analyze logs separately.

## Quick Reference

See these canonical sources for patterns:
- **Getting Started**: `reference/getting-started.md` (core patterns, node types, CLI)
- **Architecture**: `ARCHITECTURE.md` (design philosophy, state, 3-layer pattern)
- **Dev Commands**: `CLAUDE.md` (testing, linting, running examples)
- **Prompts**: `reference/prompt-yaml.md` (Jinja2, schemas)
- **Graphs**: `reference/graph-yaml.md` (node config, edges, routing)

## The 10 Commandments

1. **Thou shalt research before coding** — Let infinite agents explore deep and wide; distill their wisdom into constraints, for the cheapest code is unwritten code.
2. **Thou shalt demonstrate with example** — Never explain abstractly; show working code:
   ```bash
   yamlgraph graph run graphs/hello.yaml --var name="World" --var style="enthusiastic"
   ```

3. **Thou shalt not utter code in vain** — Keep configuration separate and validated, for code is logic and config is truth.
4. **Thou shalt honor existing patterns** — Don't reinvent; check how it's done elsewhere in the codebase.
5. **Thou shalt sanctify thy outputs with types** — All outputs use Pydantic models; no untyped dicts.
6. **Thou shalt bear witness of thy errors** — Expose them, don't hide; run `ruff check . && ruff format .` before committing.
7. **Thou shalt be faithful to TDD** — Red-Green-Refactor; run `pytest` with every change. No bug shall be fixed unless first condemned by a failing test.
8. **Thou shalt kill all entropy** — Split modules before they bloat (< 400 lines); feed the dead to `vulture`; burn duplicates with `jscpd`; sanctify the living with `radon cc -a .`.
9. **Thou shalt RTFM and document** — Check `examples/` and `reference/` first; update them to keep sync.
10. **Thou shalt covet transparency** — Every change gets a `CHANGELOG.md` entry; bump `pyproject.toml` version.

May CI judge swiftly,
may metrics speak truth,
may agents explore without restraint,
and may we commit only what survives the fire.

Or fail fast in CI, sinner.
