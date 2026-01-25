"""Tests for agent pattern linter validations."""

from yamlgraph.tools.linter_patterns.agent import (
    check_agent_node_tools,
    check_agent_patterns,
)


class TestAgentNodeTools:
    """Test agent node tool validation."""

    def test_valid_agent_with_defined_tools(self):
        """Should pass when agent references defined tools."""
        node_config = {"type": "agent", "tools": ["search_web", "analyze_code"]}
        graph = {
            "tools": {
                "search_web": {"type": "websearch"},
                "analyze_code": {"type": "shell", "command": "analyze"},
            }
        }

        issues = check_agent_node_tools("research_agent", node_config, graph)
        assert len(issues) == 0

    def test_valid_agent_with_builtin_tools(self):
        """Should pass when agent references built-in tools."""
        node_config = {"type": "agent", "tools": ["websearch"]}
        graph = {
            "tools": {}  # No custom tools defined
        }

        issues = check_agent_node_tools("research_agent", node_config, graph)
        assert len(issues) == 0

    def test_agent_with_no_tools_warning(self):
        """Should warn when agent node has no tools."""
        node_config = {
            "type": "agent",
            "tools": [],  # Empty tools list
        }
        graph = {"tools": {"search_web": {"type": "websearch"}}}

        issues = check_agent_node_tools("research_agent", node_config, graph)
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert issues[0].code == "W401"
        assert "has no tools configured" in issues[0].message

    def test_agent_missing_tools_field_warning(self):
        """Should warn when agent node has no tools field."""
        node_config = {
            "type": "agent"
            # No tools field
        }
        graph = {"tools": {"search_web": {"type": "websearch"}}}

        issues = check_agent_node_tools("research_agent", node_config, graph)
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert issues[0].code == "W401"
        assert "has no tools configured" in issues[0].message

    def test_agent_references_undefined_tool(self):
        """Should error when agent references undefined tool."""
        node_config = {"type": "agent", "tools": ["search_web", "undefined_tool"]}
        graph = {
            "tools": {
                "search_web": {"type": "websearch"}
                # "undefined_tool" not defined
            }
        }

        issues = check_agent_node_tools("research_agent", node_config, graph)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].code == "E401"
        assert "references undefined tool 'undefined_tool'" in issues[0].message
        assert "search_web" in issues[0].fix  # Should suggest available tools

    def test_agent_mixed_valid_and_invalid_tools(self):
        """Should report errors for invalid tools but allow valid ones."""
        node_config = {
            "type": "agent",
            "tools": ["websearch", "defined_tool", "undefined_tool"],
        }
        graph = {
            "tools": {
                "defined_tool": {"type": "shell", "command": "echo"}
                # "undefined_tool" not defined
            }
        }

        issues = check_agent_node_tools("research_agent", node_config, graph)
        assert len(issues) == 1  # Only the undefined tool should error
        assert issues[0].severity == "error"
        assert issues[0].code == "E401"
        assert "undefined_tool" in issues[0].message


class TestAgentPatternsIntegration:
    """Test agent pattern validation integration."""

    def test_valid_agent_graph(self, tmp_path):
        """Should pass valid agent graph."""
        graph_content = """
tools:
  search_web:
    type: websearch
    provider: duckduckgo
nodes:
  research:
    type: agent
    prompt: research/prompt
    tools: [search_web]
    state_key: result
"""
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text(graph_content)

        issues = check_agent_patterns(graph_file)
        assert len(issues) == 0

    def test_invalid_agent_graph_no_tools(self, tmp_path):
        """Should warn when agent has no tools."""
        graph_content = """
tools:
  search_web:
    type: websearch
nodes:
  research:
    type: agent
    prompt: research/prompt
    # No tools field
    state_key: result
"""
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text(graph_content)

        issues = check_agent_patterns(graph_file)
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert issues[0].code == "W401"

    def test_invalid_agent_graph_undefined_tools(self, tmp_path):
        """Should error when agent references undefined tools."""
        graph_content = """
tools:
  search_web:
    type: websearch
nodes:
  research:
    type: agent
    prompt: research/prompt
    tools: [search_web, undefined_tool]
    state_key: result
"""
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text(graph_content)

        issues = check_agent_patterns(graph_file)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].code == "E401"
        assert "undefined_tool" in issues[0].message

    def test_mixed_nodes_validates_only_agents(self, tmp_path):
        """Should only validate agent nodes, ignore others."""
        graph_content = """
tools:
  search_web:
    type: websearch
nodes:
  llm_node:
    type: llm
    prompt: hello
  router_node:
    type: router
    routes: {"pos": "handle_pos"}
  agent_node:
    type: agent
    prompt: research/prompt
    tools: [search_web]
    state_key: result
"""
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text(graph_content)

        issues = check_agent_patterns(graph_file)
        # Should only validate the agent_node
        assert len(issues) == 0  # All valid
