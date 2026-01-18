"""Tests for code-analysis graph."""

from pathlib import Path


class TestCodeAnalysisGraphStructure:
    """Tests for code-analysis.yaml graph structure."""

    def test_graph_file_exists(self):
        """Graph file should exist."""
        graph_path = Path("graphs/code-analysis.yaml")
        assert graph_path.exists(), "graphs/code-analysis.yaml not found"

    def test_graph_loads_successfully(self):
        """Graph should load without errors."""
        from yamlgraph.graph_loader import load_and_compile

        graph = load_and_compile("graphs/code-analysis.yaml")
        assert graph is not None

    def test_graph_has_required_nodes(self):
        """Graph should have run_analysis and generate_recommendations nodes."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config("graphs/code-analysis.yaml")
        assert "run_analysis" in config.nodes
        assert "generate_recommendations" in config.nodes

    def test_graph_has_analysis_tools(self):
        """Graph should define analysis tools."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config("graphs/code-analysis.yaml")
        tools = config.tools

        # Should have at least these tools
        expected_tools = ["run_ruff", "run_tests", "run_bandit"]
        for tool in expected_tools:
            assert tool in tools, f"Missing tool: {tool}"


class TestCodeAnalysisPrompts:
    """Tests for code-analysis prompts."""

    def test_analyzer_prompt_exists(self):
        """Analyzer prompt should exist."""
        prompt_path = Path("prompts/code-analysis/analyzer.yaml")
        assert prompt_path.exists(), "prompts/code-analysis/analyzer.yaml not found"

    def test_recommend_prompt_exists(self):
        """Recommend prompt should exist."""
        prompt_path = Path("prompts/code-analysis/recommend.yaml")
        assert prompt_path.exists(), "prompts/code-analysis/recommend.yaml not found"

    def test_analyzer_prompt_has_system_and_user(self):
        """Analyzer prompt should have system and user sections."""
        import yaml

        with open("prompts/code-analysis/analyzer.yaml") as f:
            prompt = yaml.safe_load(f)

        assert "system" in prompt, "Missing system prompt"
        assert "user" in prompt, "Missing user prompt"

    def test_recommend_prompt_has_system_and_user(self):
        """Recommend prompt should have system and user sections."""
        import yaml

        with open("prompts/code-analysis/recommend.yaml") as f:
            prompt = yaml.safe_load(f)

        assert "system" in prompt, "Missing system prompt"
        assert "user" in prompt, "Missing user prompt"


class TestCodeAnalysisTools:
    """Tests for shell tool commands."""

    def test_ruff_tool_command_valid(self):
        """Ruff tool should have valid command structure."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config("graphs/code-analysis.yaml")
        ruff_tool = config.tools.get("run_ruff", {})

        assert "command" in ruff_tool
        assert "ruff" in ruff_tool["command"]

    def test_tests_tool_command_valid(self):
        """Tests tool should have valid command structure."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config("graphs/code-analysis.yaml")
        tests_tool = config.tools.get("run_tests", {})

        assert "command" in tests_tool
        assert "pytest" in tests_tool["command"]

    def test_bandit_tool_command_valid(self):
        """Bandit tool should have valid command structure."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config("graphs/code-analysis.yaml")
        bandit_tool = config.tools.get("run_bandit", {})

        assert "command" in bandit_tool
        assert "bandit" in bandit_tool["command"]


class TestCodeAnalysisCompilation:
    """Tests for graph compilation."""

    def test_graph_compiles_with_checkpointer(self):
        """Graph should compile with SQLite checkpointer."""
        from langgraph.checkpoint.sqlite import SqliteSaver

        from yamlgraph.graph_loader import load_and_compile

        graph = load_and_compile("graphs/code-analysis.yaml")

        with SqliteSaver.from_conn_string(":memory:") as checkpointer:
            compiled = graph.compile(checkpointer=checkpointer)
            assert compiled is not None

    def test_graph_has_entry_point(self):
        """Graph should have START -> run_analysis edge."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config("graphs/code-analysis.yaml")

        # Find edge from START
        start_edges = [e for e in config.edges if e.get("from") == "START"]
        assert len(start_edges) > 0, "No edge from START"
        assert start_edges[0]["to"] == "run_analysis"
