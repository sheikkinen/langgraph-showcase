"""Tests for agent prompt formatting.

Bug: Agent prompt formatting only replaces {word} and ignores {state.foo} or
Jinja2, so agent prompts can ship unresolved placeholders and silently lose
state-driven variables.
"""

from unittest.mock import MagicMock, patch


class TestAgentPromptFormatting:
    """Tests for agent prompt variable formatting."""

    def test_agent_formats_simple_variables(self) -> None:
        """Agent should format simple {var} placeholders."""
        from yamlgraph.tools.agent import create_agent_node

        captured_messages = []

        def capture_invoke(messages):
            # Capture a copy of messages at call time
            captured_messages.append([m.content for m in messages])
            return MagicMock(content="Done", tool_calls=[])

        with (
            patch("yamlgraph.tools.agent.load_prompt") as mock_load,
            patch("yamlgraph.tools.agent.create_llm") as mock_create_llm,
        ):
            mock_load.return_value = {
                "system": "You are helpful.",
                "user": "Process {input} for {task}",
            }

            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_llm.invoke.side_effect = capture_invoke
            mock_create_llm.return_value = mock_llm

            node_fn = create_agent_node(
                node_name="test_agent",
                node_config={"tools": []},
                tools={},
            )

            # Execute with state containing variables
            node_fn({"input": "test data", "task": "analysis"})

            # Check what was passed to llm.invoke (captured at call time)
            assert len(captured_messages) > 0
            user_message = captured_messages[0][-1]  # Last message is user message

            # Simple variables should be replaced
            assert "test data" in user_message
            assert "analysis" in user_message
            assert "{input}" not in user_message
            assert "{task}" not in user_message

    def test_agent_formats_dot_notation_variables(self) -> None:
        """Agent should format {state.field} style placeholders via Jinja2."""
        from yamlgraph.tools.agent import create_agent_node

        captured_messages = []

        def capture_invoke(messages):
            captured_messages.append([m.content for m in messages])
            return MagicMock(content="Done", tool_calls=[])

        with (
            patch("yamlgraph.tools.agent.load_prompt") as mock_load,
            patch("yamlgraph.tools.agent.create_llm") as mock_create_llm,
        ):
            mock_load.return_value = {
                "system": "You are helpful.",
                # Use Jinja2 syntax for nested access
                "user": "Analyze {{ context.topic }} in {{ context.domain }}",
            }

            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_llm.invoke.side_effect = capture_invoke
            mock_create_llm.return_value = mock_llm

            node_fn = create_agent_node(
                node_name="test_agent",
                node_config={"tools": []},
                tools={},
            )

            # State with nested structure
            node_fn({"context": {"topic": "machine learning", "domain": "healthcare"}})

            assert len(captured_messages) > 0
            user_message = captured_messages[0][-1]

            # Jinja2 should render nested access
            assert (
                "machine learning" in user_message
            ), f"Jinja2 {{{{ context.topic }}}} not replaced. Got: {user_message}"
            assert (
                "healthcare" in user_message
            ), f"Jinja2 {{{{ context.domain }}}} not replaced. Got: {user_message}"

    def test_agent_formats_jinja2_templates(self) -> None:
        """Agent should format Jinja2 {{ state.field }} templates."""
        from yamlgraph.tools.agent import create_agent_node

        captured_messages = []

        def capture_invoke(messages):
            captured_messages.append([m.content for m in messages])
            return MagicMock(content="Done", tool_calls=[])

        with (
            patch("yamlgraph.tools.agent.load_prompt") as mock_load,
            patch("yamlgraph.tools.agent.create_llm") as mock_create_llm,
        ):
            mock_load.return_value = {
                "system": "You are helpful.",
                "user": "Analyze {{ state.topic }} for patterns",
            }

            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_llm.invoke.side_effect = capture_invoke
            mock_create_llm.return_value = mock_llm

            node_fn = create_agent_node(
                node_name="test_agent",
                node_config={"tools": []},
                tools={},
            )

            node_fn({"topic": "AI safety"})

            assert len(captured_messages) > 0
            user_message = captured_messages[0][-1]

            # Jinja2 templates should be rendered
            assert (
                "AI safety" in user_message
            ), f"Jinja2 {{{{ state.topic }}}} not rendered. Got: {user_message}"
            assert "{{ state.topic }}" not in user_message

    def test_agent_consistent_with_format_prompt(self) -> None:
        """Agent formatting should be consistent with format_prompt."""
        from yamlgraph.executor_base import format_prompt

        # Test Jinja2 template with state
        jinja_template = "Analyze {{ state.topic }} with {{ method }}"
        variables = {"method": "deep learning"}
        state = {"topic": "NLP"}

        formatted = format_prompt(jinja_template, variables, state=state)

        # Verify format_prompt works correctly with Jinja2
        assert "NLP" in formatted, "format_prompt should render Jinja2 state"
        assert (
            "deep learning" in formatted
        ), "format_prompt should render vars in Jinja2"

        # Test simple format template
        simple_template = "Analyze {topic} with {method}"
        variables = {"topic": "NLP", "method": "deep learning"}

        simple_formatted = format_prompt(simple_template, variables)

        assert "NLP" in simple_formatted, "format_prompt should render simple vars"
        assert (
            "deep learning" in simple_formatted
        ), "format_prompt should render simple vars"


class TestAgentSystemPromptFormatting:
    """Tests for agent system prompt formatting."""

    def test_agent_formats_system_prompt_jinja2(self) -> None:
        """Agent should format Jinja2 in system prompts too."""
        from yamlgraph.tools.agent import create_agent_node

        captured_messages = []

        def capture_invoke(messages):
            captured_messages.append([m.content for m in messages])
            return MagicMock(content="Done", tool_calls=[])

        with (
            patch("yamlgraph.tools.agent.load_prompt") as mock_load,
            patch("yamlgraph.tools.agent.create_llm") as mock_create_llm,
        ):
            mock_load.return_value = {
                "system": "You specialize in {{ state.domain }}.",
                "user": "Help with {input}",
            }

            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_llm.invoke.side_effect = capture_invoke
            mock_create_llm.return_value = mock_llm

            node_fn = create_agent_node(
                node_name="test_agent",
                node_config={"tools": []},
                tools={},
            )

            node_fn({"input": "code review", "domain": "security"})

            assert len(captured_messages) > 0
            system_message = captured_messages[0][0]

            # System prompt Jinja2 should be rendered
            assert (
                "security" in system_message
            ), f"System prompt Jinja2 not rendered. Got: {system_message}"
