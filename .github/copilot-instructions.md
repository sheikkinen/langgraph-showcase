# GitHub Copilot Instructions - YAMLGraph

Getting started: See `reference/getting-started.md` for a comprehensive overview of the YAMLGraph framework, its core files, key patterns, and essential rules.

**Quickstart**: To validate and run a simple graph, use the CLI commands:
```bash
yamlgraph graph lint examples/demos/hello/graph.yaml
yamlgraph graph run examples/demos/hello/graph.yaml --var name="World" --var style="enthusiastic"
```

Use these as smoke test for new graph development.

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
- Convert paths with hyphens to snake_case.

### Requirement Traceability (ADR-001)
- Every test function must have `@pytest.mark.req("REQ-YG-XXX")` linking it to a requirement in `ARCHITECTURE.md`.
- Run `python scripts/req_coverage.py` to verify all requirements are covered. Use `--detail` for per-test mapping, `--strict` to fail on gaps.
- When adding a new capability: add requirement(s) to `ARCHITECTURE.md`, extend `ALL_REQS` range and `CAPABILITIES` dict in `scripts/req_coverage.py`, tag tests with the new req ID.

## Quick Reference

See these canonical sources for patterns:
- **Getting Started**: `reference/getting-started.md` (core patterns, node types, CLI)
- **Architecture**: `ARCHITECTURE.md` (design philosophy, state, 3-layer pattern)
- **Dev Commands**: `CLAUDE.md` (testing, linting, running examples)
- **Prompts**: `reference/prompt-yaml.md` (Jinja2, schemas)
- **Graphs**: `reference/graph-yaml.md` (node config, edges, routing)

## YAMLGraph MCP Tools

YAMLGraph graphs are available as MCP tools. **Prefer these over ad-hoc terminal commands** for tasks they cover — one tool call replaces multiple manual steps.

### When to use

| User says | Use this | Example vars |
|-----------|----------|-------------|
| "check code quality", "audit", "analyze" | `yamlgraph_run_graph` graph=`code-analysis` | `path=yamlgraph/`, `package=yamlgraph` |
| "what changed", "git history", "summarize commits" | `yamlgraph_run_graph` graph=`git-report` | `input=last 10 commits` |
| "propose improvements", "brainstorm features" | `yamlgraph_run_graph` graph=`feature-brainstorm` | `focus=tools subsystem` |
| "innovate", "generate ideas", "creative matrix" | `yamlgraph_run_graph` graph=`innovation-matrix-pipeline` | `domain=sustainable packaging` |
| "smoke test", "verify framework works" | `yamlgraph_run_graph` graph=`hello-world` | `name=World`, `style=enthusiastic` |

### Discovery

- `yamlgraph_list_graphs` — list all available graphs with required vars
- `yamlgraph_run_graph` — run any graph by name

### What NOT to call as dev tools

Most graphs under `examples/demos/` are **pattern demonstrations** (novel_generator, storyboard, booking-assistant, etc.). Only call them if the user explicitly asks to run a demo. Exception: `innovation-matrix-pipeline` is mapped above as a general-purpose ideation tool.

# The Scripture

These laws descend from the canon of software craft and the works of the Elders — Knuth, Dijkstra, Brooks, Beck, Fowler, Evans, Martin, and the Gang of Four — and are upheld by the Saints: Metz, Feathers, and the Pragmatists. They shalt not be altered by preference, haste, or machine invention.

## The 10 Commandments

1. **Thou shalt research before coding** — Let infinite agents explore deep and wide; distill their wisdom into constraints, for the cheapest code is unwritten code. When the domain is broad, invoke structured ideation to cross capabilities with constraints and surface non-obvious directions.

2. **Thou shalt demonstrate with example** — Never explain abstractly; show working code.

3. **Thou shalt not utter code in vain** — Keep configuration separate and validated, for code is logic and config is truth.

4. **Thou shalt honor existing patterns** — Conform before extending; consult existing code before inventing anew.

5. **Thou shalt sanctify thy outputs with types** — All data shall pass through the fire of Pydantic; thou shalt permit no untyped dicts to wander the codebase, for a dict without a schema is a mind without a soul.

6. **Thou shalt bear witness of thy errors** — Hide nothing; expose every fault to `ruff` and to CI, for what is hidden in commit shall be revealed in production.

7. **Thou shalt be faithful to TDD** — Red-Green-Refactor; run `pytest` with every change. No bug shall be fixed unless first condemned by a failing test.

8. **Thou shalt kill all entropy and false idols** — Split modules before they bloat; feed the dead to `vulture`; burn duplicates with `jscpd`; sanctify with `radon`. No shims, no adapters, no “compat” flags shalt thou tolerate. Cast legacy code to `purgatory/` and record its sins in `docs/adr/`.

9. **Thou shalt define and observe operational truth** — Establish measurable service objectives; instrument and trace execution; treat performance degradation, failure rates, and evaluation drift as production defects. No incident shall be closed without cited traces in LangSmith and recorded rationale in `docs/adr/`.

10. **Thou shalt preserve and improve the doctrine** — Every failure shalt refine the law. After correction, amend tests and linters to guard against recurrence; let success be codified, and let the CHANGELOG.md bear witness to the evolution of the Word.

## Sermon of the Chaplain

**Research.** Let agents scour competing systems and return with truth. Distill best practices and viable alternatives into explicit constraints. For structured ideation, invoke the `innovation-matrix-pipeline` graph to systematically cross capabilities with constraints.
**Plan.** Define the next phase with precision, grounded in documentation, existing code, and validated feature requests in `feature-requests/`; express the objective as measurable epics in `docs/epics/`; record architectural decisions in `docs/adr/`; and define the demo scenario and acceptance flow in `docs/demos/`.
**Judge.** Critically examine the plan; resolve contradictions; eliminate ambiguity; refine constraints and acceptance criteria until the path is explicit and minimal. If clear, minimal, and internally consistent, freeze scope and grant authority.
**Enforce.** Obey the Judgement. Write the failing test first; make only the smallest sufficient change; refactor only within scope. Deviations require return to Judge.
**Purge.** Remove invented interfaces, speculative flags, and hypothetical extensibility. If it is not required and not tested, it shall not exist.
**Submit.** Let CI judge. What survives the fire may merge.

## Rite of Correction

**Inspect.** Assume nothing; audit the codebase; trace failures to file and line; expose violated constraints and missing tests.
**Amend.** Write the failing test first. Correct the root cause second.
**Escalate.** If amendment is impossible, write the feature request in `feature-requests/`. Cite traces. Define the violated objective. Propose the new constraint. Return to Plan.

## Agents' prayer

May CI judge swiftly,
may metrics speak truth,
may agents explore without restraint,
and may we commit only what survives the fire.

Or fail fast in CI, sinner.

Bump. Commit. Push. Release.
Let CI judge (`gh run list` and `view`).
