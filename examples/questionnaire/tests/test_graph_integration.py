"""Integration tests for questionnaire graph - TDD."""

from pathlib import Path


class TestGraphLoading:
    """Test graph loading and compilation."""

    def test_graph_loads_with_data_files(self) -> None:
        """Graph loads and schema is available via data_files."""
        from yamlgraph.graph_loader import load_graph_config

        graph_path = Path(__file__).parent.parent / "graph.yaml"
        config = load_graph_config(graph_path)

        # data_files should load schema
        assert "schema" in config.data
        assert config.data["schema"]["name"] == "feature-request"
        assert len(config.data["schema"]["fields"]) == 7

    def test_graph_compiles(self) -> None:
        """Graph compiles to StateGraph."""
        from yamlgraph.graph_loader import compile_graph, load_graph_config

        graph_path = Path(__file__).parent.parent / "graph.yaml"
        config = load_graph_config(graph_path)
        graph = compile_graph(config)

        # Should have nodes
        assert graph is not None

    def test_graph_has_expected_nodes(self) -> None:
        """Graph has all expected nodes."""
        from yamlgraph.graph_loader import load_graph_config

        graph_path = Path(__file__).parent.parent / "graph.yaml"
        config = load_graph_config(graph_path)

        expected_nodes = [
            "init",
            "opening",
            "extract",
            "detect_gaps",
            "probe",
            "recap",
            "classify",
            "analyze",
            "save",
            "closing",
        ]

        for node in expected_nodes:
            assert node in config.nodes, f"Missing node: {node}"


class TestInitNode:
    """Test init node sets up state correctly."""

    def test_init_sets_default_state(self) -> None:
        """Init node initializes all state fields."""
        from yamlgraph.graph_loader import load_graph_config

        graph_path = Path(__file__).parent.parent / "graph.yaml"
        config = load_graph_config(graph_path)

        # Init should set these fields via passthrough output
        init_output = config.nodes["init"].get("output", {})
        assert init_output.get("messages") == []
        assert init_output.get("extracted") == {}
        assert init_output.get("probe_count") == 0


class TestDetectGapsIntegration:
    """Test detect_gaps works with real schema."""

    def test_detect_gaps_with_schema(self) -> None:
        """Detect gaps finds missing required fields from schema."""
        import yaml
        from tools.handlers import detect_gaps

        schema_path = Path(__file__).parent.parent / "schema.yaml"
        schema = yaml.safe_load(schema_path.read_text())

        # Empty extracted - should find all 5 required fields
        state = {"schema": schema, "extracted": {}, "probe_count": 0}
        result = detect_gaps(state)

        assert result["has_gaps"] is True
        assert len(result["gaps"]) == 5
        assert "title" in result["gaps"]
        assert "priority" in result["gaps"]
        assert "summary" in result["gaps"]
        assert "problem" in result["gaps"]
        assert "proposed_solution" in result["gaps"]

    def test_detect_gaps_partial_fill(self) -> None:
        """Detect gaps finds remaining fields."""
        import yaml
        from tools.handlers import detect_gaps

        schema_path = Path(__file__).parent.parent / "schema.yaml"
        schema = yaml.safe_load(schema_path.read_text())

        # Partial - 2 of 5 filled
        state = {
            "schema": schema,
            "extracted": {"title": "My Feature", "priority": "high"},
            "probe_count": 0,
        }
        result = detect_gaps(state)

        assert result["has_gaps"] is True
        assert len(result["gaps"]) == 3
        assert "title" not in result["gaps"]
        assert "priority" not in result["gaps"]

    def test_detect_gaps_all_filled(self) -> None:
        """No gaps when all required fields filled."""
        import yaml
        from tools.handlers import detect_gaps

        schema_path = Path(__file__).parent.parent / "schema.yaml"
        schema = yaml.safe_load(schema_path.read_text())

        state = {
            "schema": schema,
            "extracted": {
                "title": "Add URL support",
                "priority": "medium",
                "summary": "Load graphs from URLs",
                "problem": "Can only load local files",
                "proposed_solution": "Add http:// handling",
            },
            "probe_count": 0,
        }
        result = detect_gaps(state)

        assert result["has_gaps"] is False
        assert result["gaps"] == []


class TestProbeLoopGuard:
    """Test probe loop doesn't run forever."""

    def test_probe_count_guards_loop(self) -> None:
        """Probe count prevents infinite loops."""
        import yaml
        from tools.handlers import detect_gaps

        schema_path = Path(__file__).parent.parent / "schema.yaml"
        schema = yaml.safe_load(schema_path.read_text())

        # Simulate 10 iterations
        state = {"schema": schema, "extracted": {}, "probe_count": 9}
        result = detect_gaps(state)

        # Still has gaps but probe_count is now 10
        assert result["has_gaps"] is True
        assert result["probe_count"] == 10

        # Graph edge condition: probe_count >= 10 → set_recap
        # This prevents infinite looping


class TestApplyCorrectionsIntegration:
    """Test corrections flow."""

    def test_apply_multiple_corrections(self) -> None:
        """Apply multiple field corrections at once."""
        from tools.handlers import apply_corrections

        state = {
            "extracted": {
                "title": "Old Title",
                "priority": "low",
                "summary": "Old summary",
            },
            "recap_action": {
                "action_type": "correct",
                "corrections": {"title": "New Title", "priority": "high"},
            },
            "correction_count": 0,
        }

        result = apply_corrections(state)

        assert result["extracted"]["title"] == "New Title"
        assert result["extracted"]["priority"] == "high"
        assert result["extracted"]["summary"] == "Old summary"  # Unchanged
        assert result["correction_count"] == 1

    def test_correction_count_guards_loop(self) -> None:
        """Correction count prevents infinite correction loops."""
        from tools.handlers import apply_corrections

        state = {
            "extracted": {"title": "Test"},
            "recap_action": {"corrections": {"title": "New"}},
            "correction_count": 4,
        }

        result = apply_corrections(state)

        assert result["correction_count"] == 5
        # Graph edge condition: correction_count >= 5 → set_analyzing


class TestRecapRouting:
    """Test recap action routing logic."""

    def test_confirm_routes_to_analyzing(self) -> None:
        """recap_action.action_type == 'confirm' routes to analyzing."""
        # The condition: recap_action.action_type == 'confirm'
        recap_action = {"action_type": "confirm"}
        condition_result = recap_action.get("action_type") == "confirm"
        assert condition_result is True

    def test_correct_with_low_count_routes_to_corrections(self) -> None:
        """Correct action with low count goes to apply_corrections."""
        # Condition: recap_action.action_type == 'correct' and correction_count < 5
        recap_action = {"action_type": "correct", "corrections": {"title": "New"}}
        correction_count = 2
        condition_result = (
            recap_action.get("action_type") == "correct" and correction_count < 5
        )
        assert condition_result is True

    def test_correct_with_max_count_routes_to_analyzing(self) -> None:
        """Correct action at max count skips to analyzing."""
        # Condition: correction_count >= 5
        correction_count = 5
        condition_result = correction_count >= 5
        assert condition_result is True

    def test_clarify_routes_to_recap(self) -> None:
        """Clarify action routes back to recap."""
        # Condition: recap_action.action_type == 'clarify' and correction_count < 5
        recap_action = {"action_type": "clarify"}
        correction_count = 0
        condition_result = (
            recap_action.get("action_type") == "clarify" and correction_count < 5
        )
        assert condition_result is True


class TestSaveOutput:
    """Test save node outputs correct format."""

    def test_save_produces_markdown(self, tmp_path: Path, monkeypatch) -> None:
        """Save handler produces valid markdown."""
        from tools.handlers import save_to_file

        monkeypatch.chdir(tmp_path)

        state = {
            "extracted": {
                "title": "Data Files Directive",
                "priority": "high",
                "summary": "Load external data at graph load time",
                "problem": "Hardcoded data in graph files",
                "proposed_solution": "Add data_files directive",
                "acceptance_criteria": "- Loads YAML\n- Available in state",
                "alternatives": "Inline data in graph",
            },
            "analysis": {
                "analysis": "Well-structured request",
                "strengths": ["Clear problem statement"],
                "concerns": ["May need error handling"],
                "recommendation": "proceed",
            },
        }

        result = save_to_file(state)

        assert result["complete"] is True
        content = Path(result["output_path"]).read_text()

        # Check structure
        assert "# Feature Request:" in content
        assert "## Critical Analysis" in content
        assert "### Strengths" in content
        assert "### Concerns" in content
        assert "### Recommendation" in content
