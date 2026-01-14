"""Tests for showcase.models.state module."""


from showcase.models import create_initial_state


class TestCreateInitialState:
    """Tests for create_initial_state function."""

    def test_basic_creation(self):
        """Basic state creation with required fields."""
        state = create_initial_state(topic="test topic")
        assert state["topic"] == "test topic"
        assert state["style"] == "informative"
        assert state["word_count"] == 300

    def test_custom_parameters(self):
        """State creation with custom parameters."""
        state = create_initial_state(
            topic="AI",
            style="casual",
            word_count=500,
            thread_id="custom123",
        )
        assert state["topic"] == "AI"
        assert state["style"] == "casual"
        assert state["word_count"] == 500
        assert state["thread_id"] == "custom123"

    def test_auto_generated_thread_id(self):
        """Thread ID should be auto-generated if not provided."""
        state = create_initial_state(topic="test")
        assert state["thread_id"] is not None
        assert len(state["thread_id"]) == 16  # 16 hex chars for better uniqueness

    def test_initial_values_are_none(self):
        """Pipeline outputs should be None initially."""
        state = create_initial_state(topic="test")
        assert state["generated"] is None
        assert state["analysis"] is None
        assert state["final_summary"] is None
        assert state["error"] is None

    def test_initial_step_is_init(self):
        """Current step should be 'init' initially."""
        state = create_initial_state(topic="test")
        assert state["current_step"] == "init"


class TestShowcaseStateTypedDict:
    """Tests for ShowcaseState TypedDict."""

    def test_state_is_dict(self):
        """State should be a dict."""
        state = create_initial_state(topic="test")
        assert isinstance(state, dict)

    def test_state_allows_updates(self):
        """State should allow field updates."""
        state = create_initial_state(topic="test")
        state["current_step"] = "generate"
        state["error"] = "Test error"
        assert state["current_step"] == "generate"
        assert state["error"] == "Test error"
