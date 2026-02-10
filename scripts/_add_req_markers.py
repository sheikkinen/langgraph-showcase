#!/usr/bin/env python3
"""One-shot script to add @pytest.mark.req(...) markers to all test files.

Run from project root:
    python scripts/_add_req_markers.py

This script is idempotent — it skips tests that already have a req marker.
Delete this script after use.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent / "tests"

# ── File stem → list of requirement IDs ──────────────────────────────
# Unit tests
FILE_REQS: dict[str, list[str]] = {
    # Capability 1: Config Loading & Validation
    "test_graph_loader": ["REQ-YG-001", "REQ-YG-002", "REQ-YG-005"],
    "test_graph_schema": ["REQ-YG-002"],
    "test_graph_linter": ["REQ-YG-003"],
    "test_linter_patterns_agent": ["REQ-YG-003"],
    "test_linter_patterns_interrupt": ["REQ-YG-003"],
    "test_linter_patterns_map": ["REQ-YG-003"],
    "test_linter_patterns_router": ["REQ-YG-003"],
    "test_linter_patterns_subgraph": ["REQ-YG-003"],
    "test_cli_helpers": ["REQ-YG-001", "REQ-YG-004"],
    "test_data_loader": ["REQ-YG-001", "REQ-YG-004"],
    "test_empty_yaml_error": ["REQ-YG-004"],
    # Capability 2: Graph Compilation
    "test_node_compiler_branches": ["REQ-YG-007"],
    "test_compile_graph_map": ["REQ-YG-008", "REQ-YG-040"],
    "test_auto_loop_detection": ["REQ-YG-006"],
    "test_loop_detection": ["REQ-YG-006"],
    "test_loops": ["REQ-YG-006"],
    # Capability 3: Node Execution
    "test_node_factory": ["REQ-YG-009", "REQ-YG-045"],
    "test_node_factory_base": ["REQ-YG-045"],
    "test_streaming": ["REQ-YG-009"],
    "test_streaming_resolution": ["REQ-YG-009"],
    # Capability 4: LLM Provider
    "test_llm_factory": ["REQ-YG-010", "REQ-YG-011"],
    "test_llm_factory_async": ["REQ-YG-010", "REQ-YG-011"],
    "test_lmstudio_provider": ["REQ-YG-010"],
    # Capability 5: Prompt Execution
    "test_prompts": ["REQ-YG-012"],
    "test_prompts_relative": ["REQ-YG-012"],
    "test_jinja2_prompts": ["REQ-YG-012", "REQ-YG-013"],
    "test_colocated_prompts": ["REQ-YG-012"],
    "test_executor_base": ["REQ-YG-013", "REQ-YG-031"],
    "test_expressions": ["REQ-YG-013"],
    "test_template": ["REQ-YG-013"],
    "test_format_prompt": ["REQ-YG-013"],
    "test_resolve_node_variables": ["REQ-YG-013"],
    "test_llm_jinja2_state": ["REQ-YG-013"],
    "test_interrupt_jinja2_state": ["REQ-YG-013", "REQ-YG-021"],
    "test_executor": ["REQ-YG-014"],
    "test_executor_retry": ["REQ-YG-014", "REQ-YG-031"],
    "test_executor_async": ["REQ-YG-015"],
    "test_async_executor": ["REQ-YG-015"],
    "test_async_prompt_args": ["REQ-YG-015"],
    "test_async_resolution": ["REQ-YG-015"],
    "test_json_extract": ["REQ-YG-016"],
    "test_json_extract_continuation": ["REQ-YG-016"],
    # Capability 6: Tool & Agent Integration
    "test_tool_call_node": ["REQ-YG-017"],
    "test_tool_call_integration": ["REQ-YG-017"],
    "test_agent_nodes": ["REQ-YG-018"],
    "test_agent_llm_config": ["REQ-YG-018"],
    "test_agent_prompt_formatting": ["REQ-YG-018"],
    "test_shell_tools": ["REQ-YG-019"],
    "test_tool_nodes": ["REQ-YG-019"],
    "test_python_nodes": ["REQ-YG-020"],
    # Capability 7: Routing & Flow Control
    "test_interrupt_node": ["REQ-YG-021"],
    "test_passthrough_node": ["REQ-YG-021"],
    "test_conditions_routing": ["REQ-YG-022", "REQ-YG-023"],
    "test_router": ["REQ-YG-022"],
    "test_router_dict_routing": ["REQ-YG-022"],
    # Capability 8: State Persistence
    "test_state_builder": ["REQ-YG-024"],
    "test_state_builder_map": ["REQ-YG-024", "REQ-YG-040"],
    "test_state_config": ["REQ-YG-024"],
    "test_state_jinja2": ["REQ-YG-024"],
    "test_checkpointer_factory": ["REQ-YG-025"],
    "test_checkpointer": ["REQ-YG-026"],
    "test_simple_redis": ["REQ-YG-026", "REQ-YG-039"],
    "test_conversation_memory": ["REQ-YG-026"],
    # Capability 9: Error Handling
    "test_on_error_skip": ["REQ-YG-027", "REQ-YG-028"],
    "test_reliability": ["REQ-YG-027", "REQ-YG-029"],
    "test_generic_report": ["REQ-YG-030"],
    "test_map_keyerror_context": ["REQ-YG-028", "REQ-YG-040"],
    # Capability 10: CLI Interface
    "test_cli_package": ["REQ-YG-032", "REQ-YG-033"],
    "test_graph_commands": ["REQ-YG-032", "REQ-YG-036"],
    "test_deprecation": ["REQ-YG-034"],
    "test_no_backward_compat": ["REQ-YG-034"],
    "test_legacy_cli_removed": ["REQ-YG-035"],
    # Capability 11: Export & Serialization
    "test_json_schema_export": ["REQ-YG-036"],
    "test_export": ["REQ-YG-038"],
    "test_result_export": ["REQ-YG-038"],
    "test_coding_key_normalization": ["REQ-YG-039"],
    "test_typeddict_codegen": ["REQ-YG-044"],
    # Capability 12: Subgraph & Map
    "test_map_node": ["REQ-YG-040", "REQ-YG-041"],
    "test_subgraph": ["REQ-YG-042"],
    # Capability 13: Utilities
    "test_config": ["REQ-YG-043"],
    "test_constants": ["REQ-YG-043"],
    "test_schema_loader": ["REQ-YG-044"],
    "test_inline_schema": ["REQ-YG-044"],
    "test_logging": ["REQ-YG-046"],
    "test_parsing": ["REQ-YG-046"],
    "test_sanitize": ["REQ-YG-046"],
    # Integration tests
    "test_cli_commands": ["REQ-YG-032"],
    "test_data_files_integration": ["REQ-YG-001"],
    "test_pipeline_flow": ["REQ-YG-005", "REQ-YG-014"],
    "test_providers": ["REQ-YG-010"],
    "test_map_demo": ["REQ-YG-040"],
    "test_python_map_demo": ["REQ-YG-020", "REQ-YG-040"],
    "test_memory_demo": ["REQ-YG-025", "REQ-YG-026"],
    "test_subgraph_integration": ["REQ-YG-042"],
    "test_subgraph_interrupt": ["REQ-YG-021", "REQ-YG-042"],
    # Example / demo tests (tag to their primary capability)
    "test_animated_storyboard": ["REQ-YG-005"],
    "test_demo_structure": ["REQ-YG-001"],
    "test_book_translator_assembler": ["REQ-YG-014"],
    "test_book_translator_glossary": ["REQ-YG-014"],
    "test_book_translator_quality": ["REQ-YG-014"],
    "test_book_translator_splitter": ["REQ-YG-014"],
    "test_feature_brainstorm": ["REQ-YG-014"],
    "test_soul_pattern": ["REQ-YG-005"],
    "test_rag_example": ["REQ-YG-005"],
    "test_issues": ["REQ-YG-014"],
    "test_routes": ["REQ-YG-009"],
    "test_session": ["REQ-YG-026"],
}


def build_marker_line(reqs: list[str], indent: str) -> str:
    """Build the @pytest.mark.req(...) decorator line."""
    if len(reqs) == 1:
        return f'{indent}@pytest.mark.req("{reqs[0]}")\n'
    args = ", ".join(f'"{r}"' for r in reqs)
    return f"{indent}@pytest.mark.req({args})\n"


def ensure_pytest_import(content: str) -> str:
    """Ensure 'import pytest' is present."""
    if re.search(r"^import pytest\b", content, re.MULTILINE):
        return content
    # Add after last import or at top
    # Find the last import line
    lines = content.split("\n")
    last_import_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            last_import_idx = i
    if last_import_idx >= 0:
        lines.insert(last_import_idx + 1, "import pytest")
    else:
        lines.insert(0, "import pytest")
    return "\n".join(lines)


def add_markers_to_file(filepath: Path, reqs: list[str]) -> tuple[int, int]:
    """Add @pytest.mark.req markers to test functions in a file.

    Returns (total_functions, newly_marked).
    """
    content = filepath.read_text()
    lines = content.split("\n")
    new_lines: list[str] = []
    total = 0
    marked = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        # Match test function definitions
        m = re.match(r"^(\s*)(async\s+)?def\s+(test_\w+)\s*\(", line)
        if m:
            total += 1
            indent = m.group(1)
            # Check if previous line(s) already have @pytest.mark.req
            already_marked = False
            for j in range(max(0, len(new_lines) - 5), len(new_lines)):
                if "@pytest.mark.req" in new_lines[j]:
                    already_marked = True
                    break
            if not already_marked:
                marker = build_marker_line(reqs, indent)
                new_lines.append(marker.rstrip("\n"))
                marked += 1
        new_lines.append(line)
        i += 1

    if marked > 0:
        result = "\n".join(new_lines)
        result = ensure_pytest_import(result)
        filepath.write_text(result)

    return total, marked


def main() -> None:
    total_files = 0
    total_functions = 0
    total_marked = 0
    skipped_files: list[str] = []

    for test_dir in [ROOT / "unit", ROOT / "integration"]:
        if not test_dir.exists():
            continue
        for filepath in sorted(test_dir.rglob("test_*.py")):
            stem = filepath.stem
            reqs = FILE_REQS.get(stem)
            if reqs is None:
                skipped_files.append(str(filepath.relative_to(ROOT)))
                continue
            total_files += 1
            funcs, marked = add_markers_to_file(filepath, reqs)
            total_functions += funcs
            total_marked += marked
            if marked > 0:
                print(
                    f"  ✅ {filepath.relative_to(ROOT)}: {marked}/{funcs} marked with {reqs}"
                )
            else:
                print(f"  ⏭️  {filepath.relative_to(ROOT)}: {funcs} already marked")

    print(
        f"\nSummary: {total_marked} markers added across {total_files} files ({total_functions} functions)"
    )
    if skipped_files:
        print(f"\n⚠️  Skipped (no mapping): {skipped_files}")


if __name__ == "__main__":
    main()
