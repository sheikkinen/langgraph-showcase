"""Tests for FR-008: TypedDict Code Generation.

Enables exporting the dynamically-built TypedDict state class to a
Python file for IDE autocomplete and static type checking.
"""

import pytest

from yamlgraph.models.state_builder import generate_typeddict_code


class TestGenerateTypedDictCode:
    """Tests for generate_typeddict_code function."""

    @pytest.mark.req("REQ-YG-037", "REQ-YG-044")
    def test_generates_basic_typeddict(self):
        """Basic graph config produces valid TypedDict code."""
        config = {
            "name": "interview",
            "state": {"response": "str", "complete": "bool"},
            "nodes": {"greet": {"type": "llm", "state_key": "greeting"}},
        }

        code = generate_typeddict_code(config)

        assert "class InterviewState(TypedDict, total=False):" in code
        assert "response: str" in code
        assert "complete: bool" in code
        assert "greeting: Any" in code  # from state_key

    @pytest.mark.req("REQ-YG-037", "REQ-YG-044")
    def test_includes_typing_imports(self):
        """Generated code includes necessary typing imports."""
        config = {"name": "simple", "nodes": {}}

        code = generate_typeddict_code(config)

        assert "from typing import" in code
        assert "TypedDict" in code
        assert "Any" in code

    @pytest.mark.req("REQ-YG-037", "REQ-YG-044")
    def test_includes_generation_comment(self):
        """Generated code includes auto-generation comment."""
        config = {"name": "test", "nodes": {}}

        code = generate_typeddict_code(config, source_path="graphs/test.yaml")

        assert "Auto-generated" in code
        assert "graphs/test.yaml" in code

    @pytest.mark.req("REQ-YG-037", "REQ-YG-044")
    def test_handles_all_type_mappings(self):
        """All YAML types map to Python types correctly."""
        config = {
            "name": "types",
            "state": {
                "s": "str",
                "i": "int",
                "f": "float",
                "b": "bool",
                "l": "list",
                "d": "dict",
            },
            "nodes": {},
        }

        code = generate_typeddict_code(config)

        assert "s: str" in code
        assert "i: int" in code
        assert "f: float" in code
        assert "b: bool" in code
        assert "l: list" in code
        assert "d: dict" in code

    @pytest.mark.req("REQ-YG-037", "REQ-YG-044")
    def test_extracts_agent_fields(self):
        """Agent nodes add input and _tool_results fields."""
        config = {
            "name": "agent_graph",
            "nodes": {"researcher": {"type": "agent", "state_key": "result"}},
        }

        code = generate_typeddict_code(config)

        assert "input: str" in code
        assert "_tool_results: list" in code

    @pytest.mark.req("REQ-YG-037", "REQ-YG-044")
    def test_extracts_router_fields(self):
        """Router nodes add _route field."""
        config = {
            "name": "router_graph",
            "nodes": {"classify": {"type": "router", "state_key": "tone"}},
        }

        code = generate_typeddict_code(config)

        assert "_route: str" in code

    @pytest.mark.req("REQ-YG-037", "REQ-YG-044")
    def test_class_name_from_graph_name(self):
        """Class name is derived from graph name."""
        config = {"name": "my-awesome-graph", "nodes": {}}

        code = generate_typeddict_code(config)

        assert "class MyAwesomeGraphState" in code

    @pytest.mark.req("REQ-YG-037", "REQ-YG-044")
    def test_handles_missing_name(self):
        """Uses default name when graph name is missing."""
        config = {"nodes": {}}

        code = generate_typeddict_code(config)

        assert "class GraphState" in code

    @pytest.mark.req("REQ-YG-037", "REQ-YG-044")
    def test_generated_code_is_valid_python(self):
        """Generated code can be compiled without syntax errors."""
        config = {
            "name": "valid",
            "state": {"data": "str"},
            "nodes": {"process": {"type": "llm", "state_key": "output"}},
        }

        code = generate_typeddict_code(config)

        # Should compile without raising SyntaxError
        compile(code, "<test>", "exec")

    @pytest.mark.req("REQ-YG-037", "REQ-YG-044")
    def test_excludes_base_fields_by_default(self):
        """Base fields are excluded by default to reduce noise."""
        config = {"name": "minimal", "state": {"custom": "str"}, "nodes": {}}

        code = generate_typeddict_code(config)

        # Should NOT include infrastructure fields
        assert "thread_id:" not in code
        assert "current_step:" not in code
        assert "_loop_counts:" not in code
        # But should include custom fields
        assert "custom: str" in code

    @pytest.mark.req("REQ-YG-037", "REQ-YG-044")
    def test_includes_base_fields_when_requested(self):
        """Can include base fields if explicitly requested."""
        config = {"name": "full", "nodes": {}}

        code = generate_typeddict_code(config, include_base_fields=True)

        assert "thread_id: str" in code
        assert "current_step: str" in code


class TestGenerateTypedDictCodeDocstrings:
    """Tests for docstring generation."""

    @pytest.mark.req("REQ-YG-037", "REQ-YG-044")
    def test_includes_class_docstring(self):
        """Generated class includes a docstring."""
        config = {"name": "documented", "nodes": {}}

        code = generate_typeddict_code(config)

        assert '"""State for documented graph."""' in code

    @pytest.mark.req("REQ-YG-037", "REQ-YG-044")
    def test_field_comments_from_state_key(self):
        """Fields from state_key are commented with node source."""
        config = {
            "name": "commented",
            "nodes": {"analyzer": {"type": "llm", "state_key": "analysis"}},
        }

        code = generate_typeddict_code(config)

        # Field should indicate it comes from a node
        assert "analysis:" in code
