"""Tests for state schema variants and Jinja2 template improvements."""


class TestStateSchemas:
    """Tests for typed state schemas."""

    def test_base_state_has_common_fields(self):
        """BaseState should define common fields."""
        from showcase.models.state import BaseState

        # BaseState should be a TypedDict
        assert hasattr(BaseState, "__annotations__")

        # Common fields
        annotations = BaseState.__annotations__
        assert "thread_id" in annotations
        assert "current_step" in annotations
        assert "errors" in annotations

    def test_content_state_inherits_base_state(self):
        """ContentState should inherit from BaseState."""
        from showcase.models.state import ContentState

        # ContentState has its own fields
        annotations = ContentState.__annotations__
        assert "topic" in annotations
        assert "generated" in annotations
        assert "analysis" in annotations

        # Also has base fields (from BaseState)
        assert "thread_id" in annotations
        assert "current_step" in annotations

    def test_agent_state_has_messages_with_reducer(self):
        """AgentState should have messages field with add reducer."""
        from showcase.models.state import AgentState

        annotations = AgentState.__annotations__
        assert "messages" in annotations
        assert "input" in annotations

    def test_showcase_state_is_alias_for_content_state(self):
        """ShowcaseState should be alias for backward compatibility."""
        from showcase.models.state import ContentState, ShowcaseState

        assert ShowcaseState is ContentState

    def test_router_state_has_route_field(self):
        """RouterState should have routing fields."""
        from showcase.models.state import RouterState

        annotations = RouterState.__annotations__
        assert "message" in annotations
        assert "_route" in annotations

    def test_reflexion_state_has_loop_fields(self):
        """ReflexionState should have loop tracking fields."""
        from showcase.models.state import ReflexionState

        annotations = ReflexionState.__annotations__
        assert "current_draft" in annotations
        assert "critique" in annotations
        assert "_loop_counts" in annotations


class TestJinja2StateAccess:
    """Tests for passing state to Jinja2 templates."""

    def test_format_prompt_accepts_state_parameter(self):
        """format_prompt should accept optional state parameter."""
        from showcase.executor import format_prompt

        template = "Topic: {{ state.topic }}"
        state = {"topic": "AI"}

        result = format_prompt(template, {}, state=state)
        assert result == "Topic: AI"

    def test_jinja2_template_can_access_state_directly(self):
        """Jinja2 templates should access state.field directly."""
        from showcase.executor import format_prompt

        template = """
Topic: {{ state.topic }}
Word count: {{ state.word_count }}
Style: {{ state.style }}
"""
        state = {"topic": "Machine Learning", "word_count": 500, "style": "casual"}

        result = format_prompt(template, {}, state=state)
        assert "Topic: Machine Learning" in result
        assert "Word count: 500" in result
        assert "Style: casual" in result

    def test_jinja2_can_access_both_variables_and_state(self):
        """Templates should access both explicit variables and state."""
        from showcase.executor import format_prompt

        template = "{{ title }} about {{ state.topic }}"
        variables = {"title": "Article"}
        state = {"topic": "Python"}

        result = format_prompt(template, variables, state=state)
        assert result == "Article about Python"

    def test_simple_format_ignores_state(self):
        """Simple {var} templates should ignore state parameter."""
        from showcase.executor import format_prompt

        template = "Topic: {topic}"
        variables = {"topic": "AI"}
        state = {"topic": "IGNORED"}

        result = format_prompt(template, variables, state=state)
        assert result == "Topic: AI"


class TestListPreservation:
    """Tests for preserving list types for Jinja2."""

    def test_resolve_template_preserves_lists(self):
        """resolve_template should return lists as-is."""
        from showcase.node_factory import resolve_template

        state = {"items": ["a", "b", "c"]}
        result = resolve_template("{state.items}", state)

        assert isinstance(result, list)
        assert result == ["a", "b", "c"]

    def test_jinja2_can_iterate_preserved_lists(self):
        """Jinja2 should be able to iterate over lists."""
        from showcase.executor import format_prompt

        template = "{% for item in items %}{{ item }}{% endfor %}"
        variables = {"items": ["a", "b", "c"]}

        result = format_prompt(template, variables)
        assert result == "abc"

    def test_simple_format_stringifies_lists(self):
        """Simple {var} should stringify lists for compatibility."""
        from showcase.executor import format_prompt

        template = "Items: {items}"
        variables = {"items": ["a", "b", "c"]}

        result = format_prompt(template, variables)
        assert result == "Items: a, b, c"

    def test_jinja2_list_filters_work(self):
        """Jinja2 list filters should work on preserved lists."""
        from showcase.executor import format_prompt

        template = "Count: {{ items | length }}, First: {{ items[0] }}"
        variables = {"items": ["x", "y", "z"]}

        result = format_prompt(template, variables)
        assert result == "Count: 3, First: x"


class TestResolveTemplatePreservesTypes:
    """Tests for resolve_template type preservation."""

    def test_preserves_dicts(self):
        """Should preserve dict types."""
        from showcase.node_factory import resolve_template

        state = {"data": {"key": "value"}}
        result = resolve_template("{state.data}", state)

        assert isinstance(result, dict)
        assert result == {"key": "value"}

    def test_preserves_nested_pydantic(self):
        """Should preserve Pydantic models."""
        from pydantic import BaseModel

        from showcase.node_factory import resolve_template

        class Inner(BaseModel):
            value: str

        state = {"inner": Inner(value="test")}
        result = resolve_template("{state.inner}", state)

        assert isinstance(result, Inner)
        assert result.value == "test"

    def test_returns_none_for_missing(self):
        """Should return None for missing paths."""
        from showcase.node_factory import resolve_template

        state = {}
        result = resolve_template("{state.missing}", state)

        assert result is None
