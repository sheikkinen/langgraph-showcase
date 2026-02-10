"""Tests for yamlgraph.executor module."""

import pytest

from yamlgraph.executor_base import format_prompt
from yamlgraph.utils.prompts import load_prompt


class TestLoadPrompt:
    """Tests for load_prompt function."""

    @pytest.mark.req("REQ-YG-014")
    def test_load_existing_prompt(self):
        """Should load an existing prompt file."""
        prompt = load_prompt("generate")
        assert "system" in prompt
        assert "user" in prompt

    @pytest.mark.req("REQ-YG-014")
    def test_load_analyze_prompt(self):
        """Should load analyze prompt."""
        prompt = load_prompt("analyze")
        assert "system" in prompt
        assert "{content}" in prompt["user"]

    @pytest.mark.req("REQ-YG-014")
    def test_load_nonexistent_prompt(self):
        """Should raise FileNotFoundError for missing prompt."""
        with pytest.raises(FileNotFoundError):
            load_prompt("nonexistent_prompt")


class TestFormatPrompt:
    """Tests for format_prompt function."""

    @pytest.mark.req("REQ-YG-014")
    def test_format_single_variable(self):
        """Should format single variable."""
        template = "Hello, {name}!"
        result = format_prompt(template, {"name": "World"})
        assert result == "Hello, World!"

    @pytest.mark.req("REQ-YG-014")
    def test_format_multiple_variables(self):
        """Should format multiple variables."""
        template = "Topic: {topic}, Style: {style}"
        result = format_prompt(template, {"topic": "AI", "style": "casual"})
        assert result == "Topic: AI, Style: casual"

    @pytest.mark.req("REQ-YG-014")
    def test_format_empty_variables(self):
        """Should handle empty variables dict."""
        template = "No variables here"
        result = format_prompt(template, {})
        assert result == "No variables here"

    @pytest.mark.req("REQ-YG-014")
    def test_format_missing_variable_raises(self):
        """Should raise KeyError for missing variable."""
        template = "Hello, {name}!"
        with pytest.raises(KeyError):
            format_prompt(template, {})

    @pytest.mark.req("REQ-YG-014")
    def test_format_with_numbers(self):
        """Should handle numeric variables."""
        template = "Count: {word_count}"
        result = format_prompt(template, {"word_count": 300})
        assert result == "Count: 300"


class TestPromptExecutorGraphRelative:
    """Tests for PromptExecutor with graph-relative prompts."""

    @pytest.mark.req("REQ-YG-014")
    def test_execute_with_graph_path_and_prompts_relative(self, tmp_path):
        """Executor should resolve prompts relative to graph when configured."""
        from unittest.mock import MagicMock, patch

        from yamlgraph.executor import PromptExecutor

        # Create graph-relative prompt structure
        graph_dir = tmp_path / "questionnaires" / "audit"
        prompts_dir = graph_dir / "prompts"
        prompts_dir.mkdir(parents=True)

        # Create colocated prompt
        prompt_file = prompts_dir / "opening.yaml"
        prompt_file.write_text(
            """
system: You are an audit assistant.
user: Generate opening for {questionnaire_name}.
"""
        )

        graph_path = graph_dir / "graph.yaml"
        graph_path.touch()  # Just needs to exist for path resolution

        # Mock LLM to avoid actual API calls
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Welcome to the audit.")

        executor = PromptExecutor()

        with patch.object(executor, "_get_llm", return_value=mock_llm):
            # Should find prompts/opening.yaml relative to graph_path
            result = executor.execute(
                prompt_name="prompts/opening",
                variables={"questionnaire_name": "Financial Audit"},
                graph_path=graph_path,
                prompts_relative=True,
            )

        assert result == "Welcome to the audit."
        mock_llm.invoke.assert_called_once()

    @pytest.mark.req("REQ-YG-014")
    def test_execute_with_prompts_dir_override(self, tmp_path):
        """Executor should use explicit prompts_dir when provided."""
        from unittest.mock import MagicMock, patch

        from yamlgraph.executor import PromptExecutor

        # Create prompts in explicit directory
        prompts_dir = tmp_path / "my_prompts"
        prompts_dir.mkdir()

        prompt_file = prompts_dir / "greeting.yaml"
        prompt_file.write_text(
            """
system: You are helpful.
user: Say hello to {name}.
"""
        )

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Hello!")

        executor = PromptExecutor()

        with patch.object(executor, "_get_llm", return_value=mock_llm):
            result = executor.execute(
                prompt_name="greeting",
                variables={"name": "World"},
                prompts_dir=prompts_dir,
            )

        assert result == "Hello!"

    @pytest.mark.req("REQ-YG-014")
    def test_execute_prompt_function_passes_path_params(self, tmp_path):
        """execute_prompt() should accept and forward path params."""
        from unittest.mock import MagicMock, patch

        from yamlgraph.executor import execute_prompt

        # Create test prompt
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "test.yaml").write_text(
            """
system: Test system.
user: Test {msg}.
"""
        )

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="OK")

        with patch("yamlgraph.executor.get_executor") as mock_get:
            mock_executor = MagicMock()
            mock_executor.execute.return_value = "OK"
            mock_get.return_value = mock_executor

            execute_prompt(
                prompt_name="test",
                variables={"msg": "hello"},
                prompts_dir=prompts_dir,
            )

            # Verify path params were forwarded
            mock_executor.execute.assert_called_once()
            call_kwargs = mock_executor.execute.call_args.kwargs
            assert call_kwargs["prompts_dir"] == prompts_dir
