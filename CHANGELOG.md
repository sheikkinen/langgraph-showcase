# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.15] - 2026-01-22

### Fixed
- **Graph linter now supports `defaults.prompts_dir`** - Previously only checked top-level `prompts_dir`, now also checks `defaults.prompts_dir` section for custom prompt directories

### Removed
- **Innovation Matrix example** - Moved to separate [innovation-matrix](https://github.com/sheikki/innovation-matrix) repository

## [0.3.14] - 2026-01-22

### Added
- **Demo script now lints all graphs first** - `scripts/demo.sh` runs `graph lint` on all core graphs before executing demos

### Fixed
- **Graph linter now respects `prompts_dir` config** - Previously always looked in `prompts/`, now uses:
  - Graph's `prompts_dir` setting when present
  - Default `prompts/` folder otherwise
  - Fix suggestions show correct path based on config
- **Added missing node types to linter** - Now recognizes: `agent`, `interrupt`, `llm`, `map`, `passthrough`, `python`, `router`, `subgraph`

## [0.3.13] - 2026-01-21

### Changed
- **Refactored graph_commands.py into modules** - Split 541-line file into focused modules
  - `graph_commands.py` (243 lines) - Core commands: run, list, info, dispatch
  - `graph_mermaid.py` (107 lines) - Mermaid diagram generation
  - `graph_validate.py` (230 lines) - Validation and linting commands
  - All modules under 250 lines (limit: 400)

- **Added debug logging to prompt resolution** - `resolve_prompt_path()` now logs:
  - Which resolution path was chosen (graph-relative, prompts_dir, default, fallback)
  - All tried paths on failure for easier debugging

- **Documented sync/async design pattern** in ARCHITECTURE.md
  - Explains sync-first with async wrappers approach
  - Rationale for current structure vs async-first alternative

### Fixed
- Ruff B904/B905 lint errors in examples (raise from err, zip strict)

### Removed
- Redundant `scripts/test_interrupt_fix.py` (covered by integration tests)

## [0.3.12] - 2026-01-21

### Changed
- **DRY refactor of executor modules** - Extracted shared code to `executor_base.py`
  - New `prepare_messages()` helper eliminates 3x duplicated prompt loading logic
  - Shared `format_prompt()` and `is_retryable()` functions
  - `executor.py` and `executor_async.py` now import from base module
  - Cleaner separation of sync/async concerns

### Added
- **Documentation for error/errors design pattern**
  - `state_builder.py` - Explains `error` (singular, overwrite) vs `errors` (plural, accumulator)
  - `tool_nodes.py` - Clarifies nested tool result `error` is not state-level
  - `llm_nodes.py` - Notes `errors` uses add reducer for accumulation

## [0.3.11] - 2026-01-21

### Changed
- **Refactored node_factory into package** - Split 768-line monolith into focused modules
  - `base.py` (90 lines) - `resolve_class`, `get_output_model_for_node`
  - `llm_nodes.py` (208 lines) - `create_node_function`
  - `streaming.py` (72 lines) - `create_streaming_node`
  - `tool_nodes.py` (90 lines) - `create_tool_call_node`
  - `control_nodes.py` (147 lines) - `create_interrupt_node`, `create_passthrough_node`
  - `subgraph_nodes.py` (220 lines) - `create_subgraph_node`, state mapping helpers
  - All modules under 230 lines (limit: 400)
  - Public API unchanged via `__init__.py` re-exports

## [0.3.10] - 2026-01-21

### Added
- **redis-simple checkpointer type** - Plain Redis support for Upstash/Fly.io (FR add-simple-redis-checkpointer)
  - New `SimpleRedisCheckpointer` class using standard Redis commands (GET, SET, SCAN, DEL)
  - No Redis Stack (RediSearch, RedisJSON) requirement
  - Uses `orjson` for secure JSON serialization (no pickle)
  - Supports both sync and async Redis operations
  - Stores only latest checkpoint per thread (no history)
  - New optional dependency: `pip install yamlgraph[redis-simple]`

- **Async checkpointer factory** - New `get_checkpointer_async()` function
  - Properly initializes async checkpointers with `await saver.asetup()`
  - Deprecated `async_mode=True` parameter on `get_checkpointer()`
  - Added `shutdown_checkpointers()` for graceful cleanup

### Fixed
- **Async Redis checkpointer bug** (FR fix-async-redis-checkpointer)
  - `AsyncRedisSaver.from_conn_string()` returns context manager, not saver instance
  - Sync Redis now uses direct instantiation: `RedisSaver(redis_url=url)`
  - Async Redis uses `get_checkpointer_async()` for proper initialization
  - `compile_graph_async()` is now properly async

### Changed
- `compile_graph_async()` changed from sync to async function
- `load_and_compile_async()` now awaits `compile_graph_async()`

## [0.3.8] - 2026-01-20

### Added
- **interrupt_output_mapping for subgraphs** (FR-006) - Expose child state during interrupts
  - New `interrupt_output_mapping` field in subgraph node config
  - Maps child state → parent when subgraph hits an interrupt node
  - Uses LangGraph's internal `__pregel_send` to update parent state before interrupt propagates
  - `output_mapping` still used for normal completion (reaches END)
  - 3 integration tests for interrupt output mapping
  - See [reference/subgraph-nodes.md](reference/subgraph-nodes.md#interrupt-output-mapping-fr-006)

## [0.3.7] - 2026-01-20

### Added
- **interrupt_output_mapping for subgraphs** (FR-006) - Expose child state during interrupts
  - New `interrupt_output_mapping` field in subgraph node config
  - Maps child state → parent when subgraph hits an interrupt node
  - `output_mapping` still used for normal completion (reaches END)
  - `__interrupt__` marker auto-forwarded to parent graph
  - See [reference/subgraph-nodes.md](reference/subgraph-nodes.md#interrupt-output-mapping-fr-006)

### Fixed
- **prompts_relative + prompts_dir** - When both are set, prompts_dir is now resolved relative to graph_path.parent
  - Fixed `yamlgraph/utils/prompts.py` resolve_prompt_path() to combine graph_path.parent with prompts_dir
  - New resolution order: graph-relative + prompts_dir takes precedence over standalone prompts_dir
  - Added `test_prompts_relative_with_prompts_dir_combines_paths()` regression test
  - All 16 unit tests and 2 integration tests pass

## [0.3.6] - 2026-01-20

### Fixed
- **prompts_relative bug** - Complete fix for graph-relative prompt resolution
  - `node_factory.create_node_function()` now passes path params to executor
  - `create_interrupt_node()` now accepts and forwards path params
  - `graph_loader._compile_node()` extracts prompts config from defaults
  - Integration test verifies path params forwarded to `execute_prompt()`

## [0.3.5] - 2026-01-20

### Fixed
- **prompts_relative bug (partial)** - Added path params to executor API
  - Added `graph_path`, `prompts_dir`, `prompts_relative` params to `execute_prompt()`
  - Added same params to `PromptExecutor.execute()` method
  - 3 new unit tests for executor path resolution

## [0.3.4] - 2026-01-20

### Fixed
- Ruff linter compliance: 17 style fixes across test files
  - Combined nested `with` statements (SIM117)
  - Combined nested `if` statements (SIM102)
  - Removed unused variables (F841)
  - Removed whitespace in blank lines (W293)

## [0.3.3] - 2026-01-20

### Added
- **Graph-Relative Prompts** (FR-A) - Colocate prompts with graphs
  - `defaults.prompts_relative: true` resolves prompts relative to graph file
  - `defaults.prompts_dir: path/to/prompts` explicit prompts directory
  - Enables clean multi-graph project structures
  - See [reference/graph-yaml.md](reference/graph-yaml.md#defaults)
- **JSON Extraction** (FR-B) - Auto-extract JSON from LLM responses
  - Node-level `parse_json: true` extracts JSON from markdown code blocks
  - `extract_json()` utility in `yamlgraph.utils`
  - Cascading extraction: raw → ```json``` → ```...``` → `{...}` pattern
  - See [reference/graph-yaml.md](reference/graph-yaml.md#type-llm---standard-llm-node)
- Integration test for colocated prompts
- 22 new unit tests for FR-A and FR-B

### Changed
- `resolve_prompt_path()` accepts `graph_path` and `prompts_relative` params
- `create_node_function()` threads graph_path for relative resolution
- `load_prompt()` and `load_prompt_path()` support new resolution options

## [0.3.2] - 2026-01-20

### Added
- **NPC Encounter Web API** - HTMX-powered web UI for running NPC encounters
  - FastAPI backend with session persistence (`examples/npc/api/`)
  - Session adapter pattern for stateless servers with checkpointer state
  - MemorySaver default, RedisSaver via `REDIS_URL` env var
  - Interrupt detection and resume with `Command(resume=input)`
  - Map node output parsing (`{'_map_index': N, 'value': '...'}`)
  - HTML templates with HTMX fragments
  - Integration tests (20 passing)
- **Web UI + API Reference** - `reference/web-ui-api.md`
  - Architecture diagram, directory structure
  - Session adapter, routes, HTMX templates patterns
  - Interrupt handling and checkpointer options
- **Application Layer Pattern** in ARCHITECTURE.md
  - Three-layer architecture: Presentation → Logic → Side Effects
  - API integration patterns with example code

### Changed
- NPC example graphs now use `mistral` provider (was `anthropic`)

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
