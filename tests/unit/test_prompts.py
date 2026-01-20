"""Tests for yamlgraph.utils.prompts module.

TDD: Red phase - write tests before implementation.
"""

from pathlib import Path

import pytest


class TestResolvePromptPath:
    """Tests for resolve_prompt_path function."""

    def test_resolve_standard_prompt(self, tmp_path: Path):
        """Should resolve prompt in standard prompts/ directory."""
        from yamlgraph.utils.prompts import resolve_prompt_path

        # Create temp prompt file
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "greet.yaml"
        prompt_file.write_text("system: Hello\nuser: Hi {name}")

        result = resolve_prompt_path("greet", prompts_dir=prompts_dir)

        assert result == prompt_file
        assert result.exists()

    def test_resolve_nested_prompt(self, tmp_path: Path):
        """Should resolve nested prompt like map-demo/generate_ideas."""
        from yamlgraph.utils.prompts import resolve_prompt_path

        # Create nested prompt structure
        prompts_dir = tmp_path / "prompts"
        nested_dir = prompts_dir / "map-demo"
        nested_dir.mkdir(parents=True)
        prompt_file = nested_dir / "generate_ideas.yaml"
        prompt_file.write_text("system: Generate\nuser: {topic}")

        result = resolve_prompt_path("map-demo/generate_ideas", prompts_dir=prompts_dir)

        assert result == prompt_file

    def test_resolve_external_example_prompt(self, tmp_path: Path, monkeypatch):
        """Should resolve external example like examples/storyboard/expand_story."""
        from yamlgraph.utils.prompts import resolve_prompt_path

        # Create external example structure: {parent}/prompts/{basename}.yaml
        example_dir = tmp_path / "examples" / "storyboard"
        prompts_subdir = example_dir / "prompts"
        prompts_subdir.mkdir(parents=True)
        prompt_file = prompts_subdir / "expand_story.yaml"
        prompt_file.write_text("system: Expand\nuser: {story}")

        # Change to tmp_path so relative paths resolve correctly
        monkeypatch.chdir(tmp_path)

        # Standard prompts dir doesn't have it, should fall back to external
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir(exist_ok=True)

        result = resolve_prompt_path(
            "examples/storyboard/expand_story",
            prompts_dir=prompts_dir,
        )

        assert result.resolve() == prompt_file.resolve()

    def test_resolve_nonexistent_raises(self, tmp_path: Path):
        """Should raise FileNotFoundError for missing prompt."""
        from yamlgraph.utils.prompts import resolve_prompt_path

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="Prompt not found"):
            resolve_prompt_path("nonexistent", prompts_dir=prompts_dir)

    def test_resolve_uses_default_prompts_dir(self):
        """Should use PROMPTS_DIR from config when not specified."""
        from yamlgraph.utils.prompts import resolve_prompt_path

        # This should find the real greet.yaml in prompts/
        result = resolve_prompt_path("greet")

        assert result.exists()
        assert result.name == "greet.yaml"


class TestLoadPrompt:
    """Tests for load_prompt function."""

    def test_load_existing_prompt(self, tmp_path: Path):
        """Should load and parse YAML prompt file."""
        from yamlgraph.utils.prompts import load_prompt

        # Create temp prompt file
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test.yaml"
        prompt_file.write_text("system: You are helpful\nuser: Hello {name}")

        result = load_prompt("test", prompts_dir=prompts_dir)

        assert result["system"] == "You are helpful"
        assert result["user"] == "Hello {name}"

    def test_load_prompt_with_schema(self, tmp_path: Path):
        """Should load prompt with inline schema section."""
        from yamlgraph.utils.prompts import load_prompt

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "structured.yaml"
        prompt_file.write_text("""
system: Analyze content
user: "{content}"
schema:
  name: Analysis
  fields:
    summary:
      type: str
      description: Brief summary
""")

        result = load_prompt("structured", prompts_dir=prompts_dir)

        assert "schema" in result
        assert result["schema"]["name"] == "Analysis"

    def test_load_nonexistent_raises(self, tmp_path: Path):
        """Should raise FileNotFoundError for missing prompt."""
        from yamlgraph.utils.prompts import load_prompt

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            load_prompt("missing", prompts_dir=prompts_dir)

    def test_load_real_generate_prompt(self):
        """Should load the real generate.yaml from prompts/."""
        from yamlgraph.utils.prompts import load_prompt

        result = load_prompt("generate")

        assert "system" in result
        assert "user" in result


class TestGraphRelativePrompts:
    """Tests for graph-relative prompt resolution (FR-A)."""

    def test_resolve_prompt_relative_to_graph(self, tmp_path: Path):
        """Should resolve prompt relative to graph file location."""
        from yamlgraph.utils.prompts import resolve_prompt_path

        # Create graph structure with colocated prompts
        # questionnaires/audit/graph.yaml
        # questionnaires/audit/prompts/opening.yaml
        graph_dir = tmp_path / "questionnaires" / "audit"
        prompts_dir = graph_dir / "prompts"
        prompts_dir.mkdir(parents=True)

        graph_file = graph_dir / "graph.yaml"
        graph_file.write_text("name: audit")

        prompt_file = prompts_dir / "opening.yaml"
        prompt_file.write_text("system: Welcome\nuser: Start audit")

        # Resolve relative to graph
        result = resolve_prompt_path(
            "prompts/opening",
            graph_path=graph_file,
            prompts_relative=True,
        )

        assert result == prompt_file
        assert result.exists()

    def test_resolve_prompt_explicit_prompts_dir(self, tmp_path: Path):
        """Should use explicit prompts_dir when specified."""
        from yamlgraph.utils.prompts import resolve_prompt_path

        # Create shared prompts directory
        shared_prompts = tmp_path / "shared" / "prompts"
        shared_prompts.mkdir(parents=True)

        prompt_file = shared_prompts / "greet.yaml"
        prompt_file.write_text("system: Hello\nuser: Hi")

        result = resolve_prompt_path(
            "greet",
            prompts_dir=shared_prompts,
        )

        assert result == prompt_file

    def test_prompts_dir_overrides_relative(self, tmp_path: Path):
        """Explicit prompts_dir should override prompts_relative."""
        from yamlgraph.utils.prompts import resolve_prompt_path

        # Create both graph-relative and explicit prompts
        graph_dir = tmp_path / "graphs"
        graph_dir.mkdir()
        graph_file = graph_dir / "test.yaml"
        graph_file.write_text("name: test")

        # Graph-relative prompt (should NOT be used)
        graph_prompts = graph_dir / "prompts"
        graph_prompts.mkdir()
        (graph_prompts / "greet.yaml").write_text("system: Graph local")

        # Explicit prompts dir (should be used)
        explicit_dir = tmp_path / "explicit"
        explicit_dir.mkdir()
        explicit_prompt = explicit_dir / "greet.yaml"
        explicit_prompt.write_text("system: Explicit")

        result = resolve_prompt_path(
            "greet",
            prompts_dir=explicit_dir,  # Explicit takes precedence
            graph_path=graph_file,
            prompts_relative=True,
        )

        assert result == explicit_prompt

    def test_relative_resolution_without_graph_path_raises(self, tmp_path: Path):
        """Should raise if prompts_relative=True but no graph_path."""
        from yamlgraph.utils.prompts import resolve_prompt_path

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "greet.yaml").write_text("system: Hi")

        with pytest.raises(ValueError, match="graph_path required"):
            resolve_prompt_path(
                "greet",
                prompts_relative=True,
                # graph_path not provided
            )

    def test_relative_resolution_nested_prompt(self, tmp_path: Path):
        """Should resolve nested prompts relative to graph."""
        from yamlgraph.utils.prompts import resolve_prompt_path

        # questionnaires/phq9/graph.yaml
        # questionnaires/phq9/prompts/extract/fields.yaml
        graph_dir = tmp_path / "questionnaires" / "phq9"
        prompts_dir = graph_dir / "prompts" / "extract"
        prompts_dir.mkdir(parents=True)

        graph_file = graph_dir / "graph.yaml"
        graph_file.write_text("name: phq9")

        prompt_file = prompts_dir / "fields.yaml"
        prompt_file.write_text("system: Extract\nuser: {text}")

        result = resolve_prompt_path(
            "prompts/extract/fields",
            graph_path=graph_file,
            prompts_relative=True,
        )

        assert result == prompt_file

    def test_prompts_relative_with_prompts_dir_combines_paths(self, tmp_path: Path):
        """When BOTH prompts_relative and prompts_dir are set, combine them.

        Bug: prompts_dir should be resolved RELATIVE to graph_path.parent
        when prompts_relative=True, not as an absolute/CWD-relative path.

        Structure:
            questionnaires/audit/
                graph.yaml (with prompts_relative: true, prompts_dir: prompts)
                prompts/
                    opening.yaml

        Expected: "opening" resolves to questionnaires/audit/prompts/opening.yaml
        """
        from yamlgraph.utils.prompts import resolve_prompt_path

        # Create the structure
        graph_dir = tmp_path / "questionnaires" / "audit"
        prompts_dir = graph_dir / "prompts"
        prompts_dir.mkdir(parents=True)

        graph_file = graph_dir / "graph.yaml"
        graph_file.write_text("name: audit")

        prompt_file = prompts_dir / "opening.yaml"
        prompt_file.write_text("system: Welcome\nuser: Start audit")

        # This should resolve to questionnaires/audit/prompts/opening.yaml
        # Note: prompts_dir is a RELATIVE path "prompts", not an absolute path
        result = resolve_prompt_path(
            "opening",
            prompts_dir="prompts",  # Relative path!
            graph_path=graph_file,
            prompts_relative=True,
        )

        # Should resolve to the prompt colocated with the graph
        assert result == prompt_file
        assert result.exists()


class TestLoadPromptPath:
    """Tests for load_prompt_path (returns Path + parsed content)."""

    def test_load_prompt_path_returns_both(self, tmp_path: Path):
        """Should return both path and parsed content."""
        from yamlgraph.utils.prompts import load_prompt_path

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "dual.yaml"
        prompt_file.write_text("system: Test\nuser: Hello")

        path, content = load_prompt_path("dual", prompts_dir=prompts_dir)

        assert path == prompt_file
        assert content["system"] == "Test"
