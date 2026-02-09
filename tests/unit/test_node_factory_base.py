"""Tests for node_factory.base — resolve_class fallback and get_output_model_for_node (REQ-YG-045).

Covers:
- Short-name resolution via yamlgraph.models.schemas (L30-37)
- get_output_model_for_node priority: explicit model → inline schema → None
"""

import pytest

from yamlgraph.node_factory.base import get_output_model_for_node, resolve_class

# ---------------------------------------------------------------------------
# resolve_class — short-name fallback
# ---------------------------------------------------------------------------


class TestResolveClassShortName:
    """Short names without dots try yamlgraph.models.schemas."""

    def test_short_name_resolves_generic_report(self):
        """'GenericReport' resolves via schemas module."""
        from yamlgraph.models.schemas import GenericReport

        cls = resolve_class("GenericReport")
        assert cls is GenericReport

    def test_short_name_resolves_pipeline_error(self):
        """'PipelineError' resolves via schemas module."""
        from yamlgraph.models.schemas import PipelineError

        cls = resolve_class("PipelineError")
        assert cls is PipelineError

    def test_short_name_not_in_schemas_raises(self):
        """Short name not found in schemas raises ValueError."""
        with pytest.raises(ValueError, match="Invalid class path"):
            resolve_class("CompletelyFakeModel")

    def test_dotted_path_still_works(self):
        """Full dotted path bypasses short-name logic."""
        cls = resolve_class("yamlgraph.models.schemas.GenericReport")
        from yamlgraph.models.schemas import GenericReport

        assert cls is GenericReport


# ---------------------------------------------------------------------------
# get_output_model_for_node — priority chain
# ---------------------------------------------------------------------------


class TestGetOutputModelForNode:
    """Tests for the three-level resolution: explicit → inline schema → None."""

    def test_explicit_output_model_resolved(self):
        """Priority 1: explicit output_model in node config."""
        node_config = {
            "output_model": "yamlgraph.models.schemas.GenericReport",
            "prompt": "some_prompt",
        }

        result = get_output_model_for_node(node_config)

        from yamlgraph.models.schemas import GenericReport

        assert result is GenericReport

    def test_explicit_output_model_short_name(self):
        """Priority 1: short name also works for output_model."""
        node_config = {"output_model": "GenericReport", "prompt": "some_prompt"}

        result = get_output_model_for_node(node_config)

        from yamlgraph.models.schemas import GenericReport

        assert result is GenericReport

    def test_inline_schema_from_prompt(self, tmp_path):
        """Priority 2: inline schema in prompt YAML."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "analyze.yaml"
        prompt_file.write_text(
            "system: You are an analyst.\n"
            "user: Analyze {topic}\n"
            "schema:\n"
            "  name: AnalysisResult\n"
            "  fields:\n"
            "    summary:\n"
            "      type: str\n"
            "      description: Brief summary\n"
        )

        node_config = {"prompt": "analyze"}

        result = get_output_model_for_node(node_config, prompts_dir=prompts_dir)

        assert result is not None
        assert result.__name__ == "AnalysisResult"

    def test_no_model_returns_none(self, tmp_path):
        """Priority 3: no output_model and no schema → None."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "simple.yaml"
        prompt_file.write_text("system: Hi\nuser: Hello {name}\n")

        node_config = {"prompt": "simple"}

        result = get_output_model_for_node(node_config, prompts_dir=prompts_dir)

        assert result is None

    def test_no_prompt_no_model_returns_none(self):
        """Neither prompt nor output_model → None."""
        node_config = {"state_key": "something"}

        result = get_output_model_for_node(node_config)

        assert result is None

    def test_missing_prompt_file_returns_none(self, tmp_path):
        """Prompt file doesn't exist → gracefully returns None (deferred error)."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        node_config = {"prompt": "does_not_exist"}

        result = get_output_model_for_node(node_config, prompts_dir=prompts_dir)

        assert result is None

    def test_graph_relative_prompt_resolution(self, tmp_path):
        """With prompts_relative=True, prompts resolve relative to graph_path."""
        graph_dir = tmp_path / "project"
        prompts_dir = graph_dir / "prompts"
        prompts_dir.mkdir(parents=True)
        graph_file = graph_dir / "graph.yaml"
        graph_file.touch()

        prompt_file = prompts_dir / "eval.yaml"
        prompt_file.write_text(
            "system: Eval\nuser: Evaluate\n"
            "schema:\n"
            "  name: EvalResult\n"
            "  fields:\n"
            "    score:\n"
            "      type: float\n"
            "      description: Score 0-1\n"
        )

        node_config = {"prompt": "prompts/eval"}

        result = get_output_model_for_node(
            node_config,
            graph_path=graph_file,
            prompts_relative=True,
        )

        assert result is not None
        assert result.__name__ == "EvalResult"
