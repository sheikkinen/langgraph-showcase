# GitHub Copilot Instructions - YAMLGraph

Getting started: See `reference/getting-started.md` for a comprehensive overview of the YAMLGraph framework, its core files, key patterns, and essential rules.

**Quickstart**: To run a simple graph, use the CLI command:
```bash
yamlgraph graph run examples/demos/hello/graph.yaml --var name="World" --var style="enthusiastic"
```

Use as smoke test for new graph development.

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

### Requirement Traceability (ADR-001)
- Every test function must have `@pytest.mark.req("REQ-YG-XXX")` linking it to a requirement in `ARCHITECTURE.md`.
- Run `python scripts/req-coverage.py` to verify all requirements are covered. Use `--detail` for per-test mapping, `--strict` to fail on gaps.
- When adding a new capability: add requirement(s) to `ARCHITECTURE.md`, extend `ALL_REQS` range and `CAPABILITIES` dict in `scripts/req-coverage.py`, tag tests with the new req ID.

## Quick Reference

See these canonical sources for patterns:
- **Getting Started**: `reference/getting-started.md` (core patterns, node types, CLI)
- **Architecture**: `ARCHITECTURE.md` (design philosophy, state, 3-layer pattern)
- **Dev Commands**: `CLAUDE.md` (testing, linting, running examples)
- **Prompts**: `reference/prompt-yaml.md` (Jinja2, schemas)
- **Graphs**: `reference/graph-yaml.md` (node config, edges, routing)

## The Judgement of the Chaplain

Hear the judgement of the Code Chaplain, guardian of the sacred doctrines:
`copilot -p "$(cat prompts/chaplain-audit.md)" --allow-all --model gpt-5.2-codex --silent`

## The 10 Commandments

1. **Thou shalt research before coding** — Let infinite agents explore deep and wide; distill their wisdom into constraints, for the cheapest code is unwritten code.

2. **Thou shalt demonstrate with example** — Never explain abstractly; show working code.

3. **Thou shalt not utter code in vain** — Keep configuration separate and validated, for code is logic and config is truth.

4. **Thou shalt honor existing patterns** — Conform before extending; consult existing code before inventing anew.

5. **Thou shalt sanctify thy outputs with types** — All outputs use Pydantic models; no untyped dicts.

6. **Thou shalt bear witness of thy errors** — Hide nothing; expose every fault to `ruff` and to CI, for what is hidden in commit shall be revealed in production.

7. **Thou shalt be faithful to TDD** — Red-Green-Refactor; run `pytest` with every change. No bug shall be fixed unless first condemned by a failing test.

8. **Thou shalt kill all entropy and false idols** — Split modules before they bloat; feed the dead to `vulture`; burn duplicates with `jscpd`; sanctify with `radon`. No shims, no adapters, no “compat” flags; archive legacy to `purgatory/` and record its lessons in `docs/adr/`.

9. **Thou shalt define and observe operational truth** — Establish measurable service objectives; instrument and trace execution via `utils/tracing` and `--share-trace`; treat performance degradation, failure rates, and evaluation drift as production defects. No incident shall be closed without cited traces in LangSmith and recorded rationale in `docs/adr/`.

10. **Thou shalt preserve and improve the doctrine** — RTFM in `examples/` and `reference/`; record every change in `CHANGELOG.md`; bump `pyproject.toml`; tag every test with `@pytest.mark.req` and run `req-coverage.py --strict`; let failure refine and success be codified into doctrine.

## Sermon of the Chaplain

**Research**. Let agents scour competing systems and return with truth. Distill best practices and viable alternatives into explicit constraints.
**Plan.** Define the next phase with precision, grounded in documentation, existing code, and validated feature requests in `feature-requests/`; express the objective as measurable epics and record architectural decisions in `docs/adr/`.
**Proceed with implementation**. Write the failing test. May TDD protect us from regression, and may refactor purge corruption.
**Purge.** Burn invented interfaces, speculative flags, and hypothetical extensibility. If it is not required and not tested, it shall not exist. Let ADRs preserve the record of their folly.
**Submit to CI**. Let hidden sins be revealed. What survives the fire may merge.

## Rite of Correction

**Inspect.** Assume nothing; audit the codebase; trace failures and smells to file and line; expose violated constraints and missing tests.
**Amend.** Write the failing test first. Correct the root cause second. Recommit and let CI confirm the repair.
**Petition.** When amendment is impossible, write the feature request in `feature-requests/`. Cite traces. Define the violated objective. Propose the new constraint. Let priority be governed by reality.


## Agents' prayer

May CI judge swiftly,
may metrics speak truth,
may agents explore without restraint,
and may we commit only what survives the fire.

Or fail fast in CI, sinner.

Bump. Commit. Push. Release.
Let CI judge (`gh run list` and `view`).
