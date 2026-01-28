# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.3] - 2026-01-28

### Fixed
- Agent nodes now respect `prompts_relative` and `prompts_dir` config
- Map nodes now respect `prompts_relative` for sub-node prompts
- LLM nodes properly inherit top-level prompt settings
- GraphConfig checks top-level `prompts_relative`/`prompts_dir` before `defaults` block

### Changed
- Refactored `create_agent_node` to use `defaults` dict pattern (consistent with other factories)
- `effective_defaults` now built once at top of `compile_node()` for all node types

### Added
- `tests/unit/test_prompts_relative.py` - 6 tests for prompt config propagation

## [0.4.2] - 2026-01-28

### Breaking Changes
- **FR-013: Demo reorganization** - Demo graphs and prompts moved to `examples/demos/`
  - `graphs/*.yaml` → `examples/demos/{name}/graph.yaml`
  - `prompts/{demo}/` → `examples/demos/{demo}/prompts/`
  - `scripts/demo.sh` → `examples/demos/demo.sh`
  - `DEFAULT_GRAPH` now points to `examples/demos/yamlgraph/graph.yaml`

### Changed
- Demo graphs now use `prompts_relative: true` with co-located prompts
- Updated all tests to use new demo paths
- Linter now correctly resolves `prompts_relative` paths

### Added
- `examples/demos/` directory structure with 14 self-contained demos
- TDD tests in `tests/integration/test_demo_structure.py`

### Removed
- Empty `graphs/` directory (demos moved to `examples/demos/`)
- Demo prompts from global `prompts/` directory

## [0.4.1] - 2026-01-28

### Breaking Changes
- Removed `yamlgraph/builder.py` module
- Removed `build_graph()` from public API

### Changed
- Export `load_and_compile` directly from `yamlgraph` package
- Updated tests to use `load_and_compile()` instead of `build_graph()`

### Added
- New `[npc]` optional dependency group with `python-multipart`

## [0.4.0] - 2026-01-28

### Breaking Changes
- **FR-012: Legacy CLI Removal** (~1,190 lines deleted)
  - Removed `yamlgraph list-runs` command
  - Removed `yamlgraph resume` command
  - Removed `yamlgraph trace` command
  - Removed `yamlgraph export` command
  - Removed `YamlGraphDB` class (use LangGraph checkpointers instead)
  - Removed `build_resume_graph()` function
  - Removed `run_pipeline()` function
  - Removed `yamlgraph/cli/commands.py` and `yamlgraph/cli/validators.py`
  - Removed `yamlgraph/storage/database.py`

### Changed
- **FR-012-0**: `yamlgraph graph run --thread` now uses graph's configured checkpointer
- Refactored `examples/yamlgraph_gen` to use `load_and_compile()` directly
- Updated docs to reflect modern API (`load_and_compile()` vs deprecated `build_graph()`)

### Migration Guide
```python
# Before (deprecated)
from yamlgraph.builder import build_graph
graph = build_graph().compile()

# After (recommended)
from yamlgraph.graph_loader import load_and_compile
graph = load_and_compile("graphs/my-graph.yaml").compile()

# State persistence: use checkpointers in graph.yaml
# checkpointer:
#   type: sqlite
#   path: ~/.yamlgraph/checkpoints.db
```

## [0.3.33] - 2026-01-28

### Added
- **FR-010: Auto-detect Loop Nodes for skip_if_exists**
  - Automatically detect nodes in graph cycles at load time
  - Auto-apply `skip_if_exists: false` to loop nodes (eliminates common footgun)
  - Explicit `skip_if_exists` in YAML overrides auto-detection
  - New `detect_loop_nodes()` and `apply_loop_node_defaults()` functions
  - 16 unit tests for loop detection and auto-application

## [0.3.32] - 2026-01-28

### Added
- **FR-009: JSON Schema Export for IDE Support**
  - New `yamlgraph schema export` CLI command for JSON Schema generation
  - New `yamlgraph schema path` to get bundled schema location
  - Export Pydantic-based schema for VS Code YAML extension support
  - Bundled `graph-v1.json` schema in package
  - New `get_schema_path()` function in public API
  - 22 unit tests for schema export functionality

## [0.3.31] - 2026-01-28

### Added
- **FR-008: TypedDict Code Generation for IDE Support**
  - New `yamlgraph graph codegen <graph.yaml>` CLI command
  - Generates TypedDict Python code from graph state configuration
  - Options: `--output/-o FILE` to write to file, `--include-base` to include base fields
  - Auto-generates class name from graph name (e.g., `hello-world` → `HelloWorldState`)
  - Includes docstrings and generation comments
  - 13 unit tests for codegen functionality

## [0.3.30] - 2026-01-27

### Changed
- Version bump for PyPI release via GitHub Actions

## [0.3.29] - 2026-01-27

### Added
- **LM Studio Provider Support**
  - New `lmstudio` provider for local LLM inference via LM Studio
  - Uses OpenAI-compatible API with custom `base_url`
  - No API key required (local server)
  - Config: `LMSTUDIO_BASE_URL`, `LMSTUDIO_MODEL`
  - Default model: `qwen2.5-coder-7b-instruct`
  - 8 unit tests for provider integration

## [0.3.28] - 2026-01-27

### Added
- **RAG Tool Demo Fixes & Script**
  - Fixed `examples/rag/graph.yaml` structure: flat YAML (not nested `graph:`), proper `from/to` edges
  - Added `rag_retrieve_node()` state-based wrapper for `type: python` nodes
  - Fixed `prompts/answer.yaml` schema format (`schema:` with `name/fields`)
  - Added `examples/rag/demo.sh` script for one-command demo execution
  - Added `vectorstore/` to `.gitignore`

### Fixed
- **Code Duplication Reduction** (0.3.27 continuation)
  - Core yamlgraph: 2.17% → 0.71% duplication
  - Extracted `build_skip_error_state()` helper to `error_handlers.py`
  - Moved `Chunk` dataclass to `examples/book_translator/models.py`
  - Simplified `storyboard/replicate_tool.py` to re-export from shared

## [0.3.27] - 2026-01-27

### Fixed
- **FR-007: JSON Key Type Coercion for Schema Coding Dicts**
  - Root cause: JSON serialization (Redis checkpointer) converts integer dict keys to strings, causing silent Jinja2 lookup failures
  - Fix: Added `normalize_coding_keys()` to convert integer keys to strings during schema loading
  - Applied in both `build_pydantic_model()` and `build_pydantic_model_from_json_schema()`
  - Ensures coding dicts survive checkpoint round-trips consistently

## [0.3.26] - 2026-01-26

### Fixed
- **CI Test Fixes**
  - Fixed 15 failing unit tests in CI by mocking `load_prompt` instead of requiring external prompt files
  - `test_agent_nodes.py`: Added autouse fixture to mock load_prompt
  - `test_conversation_memory.py`: Added autouse fixture to mock load_prompt
  - `test_jinja2_prompts.py`: Use inline template constant instead of loading from file

## [0.3.25] - 2026-01-26

### Fixed
- **Booking Example Cleanup**
  - Removed accidentally copied yamlgraph core library, demo graphs, and demo prompts from `examples/booking/`
  - Fixed `fly.toml` BOOKING_GRAPH_PATH to point to correct file location (`graph.yaml` not `graphs/booking.yaml`)
  - Code formatting fixes (trailing whitespace, import sorting)

## [0.3.24] - 2026-01-26

### Fixed
- **FR-006: Redis Checkpointer Serialization for Subgraph Interrupts**
  - Root cause: `SimpleRedisCheckpointer` failed when serializing LangGraph internal runtime objects (`CallbackManager`, checkpointers) propagated via `__pregel_checkpointer` during subgraph execution
  - Fix: Updated `serializers.py` to skip LangGraph/LangChain internal types that can't be meaningfully serialized
  - Skipped types include: `CallbackManager`, `BaseCheckpointSaver`, `MemorySaver`, `RedisSaver`, `SimpleRedisCheckpointer`, `PregelLoop`, etc.
  - All 51 Redis unit tests pass
  - All 27 subgraph unit/integration tests pass
  - Added TDD test script: `scripts/test_subgraph_interrupt.py`
  - Added test graphs: `graphs/interrupt-parent-redis.yaml`, `graphs/subgraphs/interrupt-child-with-checkpointer-redis.yaml`

## [0.3.23] - 2026-01-25

### Added
- **xAI/Grok LLM Provider Support**
  - Added `xai` provider to multi-provider LLM factory
  - Uses OpenAI-compatible API with `base_url="https://api.x.ai/v1"`
  - Default model: `grok-beta` (configurable via `XAI_MODEL` env var)
  - Updated router demo to use xAI instead of Mistral
  - Added comprehensive tests for xAI provider

### Fixed
- **Interview Demo Linting**
  - Fixed missing state declarations for interrupt node `state_key` fields
  - Added `name_question` and `topic_question` to state section

## [0.3.22] - 2026-01-24

### Added
- **YAMLGraph Generator** (`examples/yamlgraph_gen/`)
  - Generate complete YAMLGraph pipelines from natural language descriptions
  - Pattern classification: linear, router, map, interrupt, agent, subgraph
  - Snippet-based assembly with 15+ reusable YAML templates
  - Prompt generation for all nodes in the graph
  - Tool stub generation for agent patterns (websearch, python tools)
  - README generation with usage instructions
  - Built-in linting and validation
  - 64 unit tests + 5 E2E tests
  - Helper script `run_generator.py` for CLI usage

### Fixed
- **Template escaping** in prompts with code examples
  - Use `dict()` syntax instead of `{}` to avoid conflicts with Jinja2/format templates
- **`.env` loading** in `run_generator.py`
  - Load `.env` from project root before yamlgraph imports

## [0.3.21] - 2026-01-23

### Added
- **Book Translator Example** (`examples/book_translator/`)
  - Two-phase splitting: LLM identifies markers, Python splits reliably
  - Parallel chunk translation with map nodes
  - Glossary extraction and consistency across chunks
  - Quality gates with optional human review interrupt
  - Sample Finnish Winter War diary (17KB) and German fairy tale
  - Full test coverage with 4 test files

- **`get_map_result()` helper** in book_translator tools
  - Extract results from map node output without hardcoding `_map_*_sub` keys
  - Decouples tools from internal map node key naming

### Fixed
- Pass `graph_path` to map node sub-nodes for relative prompt resolution

## [0.3.20] - 2026-01-22

### Added
- **`adelete_thread()` and `delete_thread()`** methods in `SimpleRedisCheckpointer`
  - Delete all checkpoints for a given thread ID
  - Uses SCAN to find all keys matching thread pattern
  - Required for session cleanup in applications using Redis checkpointer
  - 3 new unit tests added

## [0.3.19] - 2026-01-22

### Added
- **Tuple dict key serialization** in `SimpleRedisCheckpointer`
  - Tuple keys serialized as `"__tuple__:[json_array]"` strings for orjson compatibility
  - LangGraph checkpoints use tuple keys in `channel_versions` and `versions_seen`
  - New `_stringify_keys()` / `_unstringify_keys()` for recursive key conversion
  - 4 new unit tests for tuple key serialization

## [0.3.18] - 2026-01-22

### Added
- **Function serialization** in `SimpleRedisCheckpointer`
  - Functions/callables serialized as `{"__type__": "function", "value": null}`
  - Allows LangGraph internals that include callables to be checkpointed
  - 3 new unit tests for function serialization

## [0.3.17] - 2026-01-22

### Added
- **ChainMap serialization** in `SimpleRedisCheckpointer`
  - Fixes `TypeError: Cannot serialize <class 'collections.ChainMap'>` when graphs contain ChainMap in state
  - ChainMap serialized as `{"__type__": "chainmap", "value": {...}}`
  - Deserialized back to `ChainMap` instance
  - 2 new unit tests for ChainMap serialization

## [0.3.16] - 2026-01-22

### Added
- **Replicate provider support** - New `replicate` provider using LiteLLM for IBM Granite and other Replicate-hosted models
  - Uses `langchain-litellm` for LangChain integration
  - Requires `REPLICATE_API_TOKEN` in `.env`
  - Default model: `ibm-granite/granite-4.0-h-small`
  - Install with: `pip install -e ".[replicate]"`
- **Cost Router example** - New `examples/cost-router/` demonstrating intelligent query routing
  - Classifies queries as simple/medium/complex using cheap Granite model
  - Routes to appropriate tier: Granite (simple), Mistral (medium), Claude (complex)
  - Demonstrates `parse_json: true` for providers without structured output
- **`costrouter` demo** - Added to `scripts/demo.sh` to showcase multi-provider routing

### Changed
- **`parse_json: true` now bypasses output_model** - When set, skips structured output allowing same prompt to work with providers that don't support `response_format`
- **Suppressed Pydantic serializer warnings** for Replicate provider (langchain-litellm type mismatch)
- **Cleaned up replicate dependencies** - Only `langchain-litellm` needed (includes `litellm`)

### Fixed
- **Removed broken innovation symlink** from demo.sh lint command

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
