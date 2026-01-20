# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2026-01-20

### Added
- **ARCHITECTURE.md** - Internal architecture guide for core developers
  - Design philosophy (YAML-first, dynamic state)
  - Module architecture diagrams
  - Extension points (adding node types, LLM providers, tool types)
  - Testing strategy and code quality rules
- **CLI Reference** - `reference/cli.md` with complete command documentation
- **Subgraph Nodes Reference** - `reference/subgraph-nodes.md` with state mapping patterns
- **Documentation Index** - Comprehensive reference/README.md with reading order
- **Reading Order Guide** - Beginner → Intermediate → Advanced path in main README

### Changed
- Reorganized reference documentation with structured tables
- Updated graph-yaml.md with all 9 node types documented
- Added websearch tool documentation to graph-yaml.md
- Fixed broken link: `docs/tools-langsmith.md` → `reference/langsmith-tools.md`
- Fixed outdated path: `graphs/impl-agent.yaml` → `examples/codegen/impl-agent.yaml`
- Renamed getting-started.md to clarify it's for AI coding assistants
- Added link to ARCHITECTURE.md from main README

### Fixed
- Accurate line counts in ARCHITECTURE.md file reference table

## [0.3.0] - 2026-01-19

### Added
- **Subgraph Nodes** for composing graphs from other YAML graphs
  - New `type: subgraph` node embeds child graphs
  - Two modes: `mode: invoke` (explicit state mapping) or `mode: direct` (shared schema)
  - Input/output mapping: `{parent_key: child_key}`, `"auto"`, or `"*"`
  - Thread ID propagation for checkpointer continuity
  - Circular reference detection with clear error messages
  - Nested subgraphs supported (graphs within graphs)
  - See demo: `graphs/subgraph-demo.yaml`

### Changed
- Moved impl-agent to `examples/codegen/` as self-contained example
  - Tools: `examples/codegen/tools/` (13 analysis tools)
  - Prompts: `examples/codegen/prompts/`
  - Graph: `examples/codegen/impl-agent.yaml`
  - Tests: `examples/codegen/tests/` (16 test files)
  - Run: `yamlgraph graph run examples/codegen/impl-agent.yaml`
- Updated ruff linting rules: added B (bugbear), C4 (comprehensions), UP (pyupgrade), SIM (simplify)
- Removed dead code: `log_execution`, `set_executor`, `get_checkpointer_for_graph`, `log_with_context`

## [0.2.0] - 2026-01-19

### Added
- **Interrupt Nodes** for human-in-the-loop workflows
  - New `type: interrupt` node pauses graph execution
  - Resume with `Command(resume={...})` providing user input
  - See [reference/interrupt-nodes.md](reference/interrupt-nodes.md)
- **Checkpointer Factory** with Redis support
  - Configure checkpointers in YAML: `memory`, `sqlite`, `redis`
  - Async variants: `redis_async`, `memory` (for async)
  - Environment variable expansion in connection strings
  - Optional dependency: `pip install yamlgraph[redis]`
  - See [reference/checkpointers.md](reference/checkpointers.md)
- **Async Executor** for web framework integration
  - `run_graph_async()` - Run graphs with interrupt handling
  - `compile_graph_async()` - Compile with async checkpointer
  - `load_and_compile_async()` - Load YAML and compile async
  - See [reference/async-usage.md](reference/async-usage.md)
- **Streaming Support** for real-time token output
  - `execute_prompt_streaming()` - Async generator yielding chunks
  - `stream: true` node config for YAML-defined streaming
  - `create_streaming_node()` factory function
  - See [reference/streaming.md](reference/streaming.md)
- FastAPI integration example (`examples/fastapi_interview.py`)
- Interview demo graph (`graphs/interview-demo.yaml`)
- 51 new unit tests (891 total, 86% coverage)

### Changed
- `executor_async.py` expanded with graph execution APIs
- `node_factory.py` supports `type: interrupt` and `stream: true`
- `graph_loader.py` integrates checkpointer factory

## [0.1.4] - 2026-01-18

### Added
- Implementation Agent expanded to **14 tools** for comprehensive code analysis
  - `git_blame` - Get author, date, commit for specific lines
  - `git_log` - Get recent commits for a file
  - `syntax_check` - Validate Python code syntax
  - `get_imports` - Extract all imports from a Python file
  - `get_dependents` - Find files that import a given module
- Patch-style output format in implementation plans
  - Changes now include actual code: `file:LINE ACTION | after: context | code: ...`
  - Supports ADD, MODIFY, CREATE, DELETE actions
- 33 new tests for Phase 4-6 tools

### Changed
- Analyze prompt now includes git context guidance
- Single-line references in output (e.g., `shell.py:38` not `:1-50`)
- Structured discovery output (no narrative paragraphs)

## [0.1.3] - 2026-01-18

### Added
- Implementation Agent (`graphs/impl-agent.yaml`) for code analysis
  - Analyzes codebases and generates implementation plans
  - 9 tools: AST analysis, text search, jedi semantic analysis
  - Detects existing implementations before suggesting changes
- Code analysis tools subpackage (`yamlgraph.tools.analysis`)
  - `get_module_structure` - AST-based structure extraction
  - `read_lines`, `search_in_file`, `search_codebase` - text search
  - `find_refs`, `get_callers`, `get_callees` - jedi semantic analysis
  - `list_package_modules` - package module discovery
- `analysis` optional dependency group (`pip install yamlgraph[analysis]`)
- Reference documentation for impl-agent (`reference/impl-agent.md`)

### Changed
- Refactored analysis tools into `examples/codegen/tools/` as self-contained example
- Agent nodes now support `max_iterations` config (default 10)

## [0.1.2] - 2026-01-18

### Added
- Graph linter (`yamlgraph graph lint`) for static analysis of YAML graphs
  - Checks: missing state declarations, undefined tools, missing prompts, unreachable nodes, invalid node types
  - Error codes: E001-E005 (errors), W001-W003 (warnings)
- Feature Brainstormer meta-graph (`graphs/feature-brainstorm.yaml`)
  - Analyzes YAMLGraph codebase and proposes new features
  - Uses web search for competitive analysis
  - Outputs prioritized roadmap
- Web search tool (`type: websearch`) with DuckDuckGo integration
- `websearch` optional dependency group (`pip install yamlgraph[websearch]`)
- Sample `web-research.yaml` graph demonstrating web search agent

## [0.1.1] - 2026-01-17

### Added
- `demo.sh` script to run all demos with single command
- Pydantic schema validation for graph configuration (`GraphConfigSchema`, `NodeConfig`, `EdgeConfig`)
- Compile-time validation of condition expressions in edges
- `sorted_add` reducer for guaranteed ordering in map node fan-in
- Consolidated expression resolution in `expressions.py` module
- Comprehensive unit tests for conditions, routing, and expressions
- Security section in README documenting shell injection protection

### Changed
- State is now dynamically generated from YAML config (no manual `state.py` needed)
- Map node results are automatically sorted by `_map_index` during collection
- Config paths (`prompts/`, `graphs/`, `outputs/`, `.env`) now resolve from current working directory instead of package install location

### Removed
- `output_key` node config field - use `state_key` instead
- `should_continue()` routing function - use expression-based conditions
- Legacy `continue`/`end` condition keywords - use expression conditions like `field > value`
- Legacy `mermaid` CLI command - use `graph info` for graph visualization
- `get_graph_mermaid()`, `print_graph_mermaid()`, `export_graph_png()` functions
- `PROJECT_ROOT` config constant - use `WORKING_DIR` instead

### Fixed
- Map node ordering now guaranteed regardless of parallel execution timing
- README architecture documentation updated to reflect dynamic state generation
- `.env` file now correctly loaded from current directory when installed via `pip install yamlgraph`

## [0.1.0] - 2026-01-17

### Added
- YAML-based graph definition with `graphs/*.yaml`
- YAML prompt templates with Jinja2 support
- Multi-provider LLM support (Anthropic, Mistral, OpenAI)
- Node types: `llm`, `router`, `agent`, `tool`, `python`, `map`
- Expression-based conditional routing
- Loop limits with automatic termination
- Map nodes for parallel fan-out/fan-in processing
- Agent nodes with tool calling
- Shell tool execution with `shlex.quote()` sanitization
- SQLite state persistence and checkpointing
- LangSmith integration for observability
- CLI commands: `graph run`, `graph list`, `graph info`, `graph validate`
- Resume support for interrupted pipelines
- JSON export of pipeline runs
- Animated storyboard demo with image generation

### Security
- Shell command variables sanitized with `shlex.quote()`
- Prompt input sanitization for dangerous patterns
- No use of `eval()` for expression evaluation
