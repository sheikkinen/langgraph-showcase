"""Unit tests for graph linter.

TDD: Red-Green-Refactor approach.
"""

from pathlib import Path

import pytest
import yaml

from yamlgraph.linter import (
    LintIssue,
    lint_graph,
)
from yamlgraph.linter.checks import (
    check_edge_coverage,
    check_node_types,
    check_prompt_files,
    check_state_declarations,
    check_tool_references,
)
from yamlgraph.linter.graph_linter import LintResult

# --- Fixtures ---


@pytest.fixture
def temp_graph_dir(tmp_path):
    """Create a temp directory with prompts folder."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    return tmp_path


def write_graph(tmp_path: Path, content: dict) -> Path:
    """Helper to write a graph YAML file."""
    graph_path = tmp_path / "test-graph.yaml"
    with open(graph_path, "w") as f:
        yaml.dump(content, f)
    return graph_path


def write_prompt(tmp_path: Path, name: str, content: str = "system: Test\nuser: Test"):
    """Helper to create a prompt file."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(exist_ok=True)

    # Handle nested prompts like "code-analysis/analyzer"
    parts = name.split("/")
    if len(parts) > 1:
        subdir = prompts_dir / parts[0]
        subdir.mkdir(exist_ok=True)
        prompt_path = subdir / f"{parts[1]}.yaml"
    else:
        prompt_path = prompts_dir / f"{name}.yaml"

    with open(prompt_path, "w") as f:
        f.write(content)


# --- Test LintIssue and LintResult models ---


class TestLintModels:
    """Test Pydantic models for lint results."""

    def test_lint_issue_creation(self):
        issue = LintIssue(
            severity="error",
            code="E001",
            message="Missing state declaration",
        )
        assert issue.severity == "error"
        assert issue.code == "E001"
        assert issue.fix is None

    def test_lint_issue_with_fix(self):
        issue = LintIssue(
            severity="warning",
            code="W001",
            message="Unused tool",
            fix="Remove tool 'unused_tool' from tools section",
        )
        assert issue.fix is not None

    def test_lint_result_valid(self):
        result = LintResult(
            file="test.yaml",
            issues=[],
            valid=True,
        )
        assert result.valid is True
        assert len(result.issues) == 0

    def test_lint_result_with_errors(self):
        issues = [
            LintIssue(severity="error", code="E001", message="Test error"),
        ]
        result = LintResult(
            file="test.yaml",
            issues=issues,
            valid=False,
        )
        assert result.valid is False
        assert len(result.issues) == 1


# --- Test check_state_declarations ---


class TestCheckStateDeclarations:
    """Test detection of missing state declarations."""

    def test_valid_state_declaration(self, temp_graph_dir):
        """Graph with proper state declaration should pass."""
        graph = {
            "version": "1.0",
            "name": "test",
            "state": {"path": "str", "count": "int"},
            "nodes": {
                "step1": {
                    "type": "llm",
                    "prompt": "test",
                    "state_key": "output",
                }
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        write_prompt(temp_graph_dir, "test")
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_state_declarations(graph_path, temp_graph_dir)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_missing_state_for_prompt_variable(self, temp_graph_dir):
        """Prompt using {path} without state declaration should error."""
        graph = {
            "version": "1.0",
            "name": "test",
            # No state declaration!
            "nodes": {
                "step1": {
                    "type": "llm",
                    "prompt": "test",
                    "state_key": "output",
                }
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        # Create prompt that uses {path} variable
        write_prompt(temp_graph_dir, "test", "system: Analyze\nuser: Check {path}")
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_state_declarations(graph_path, temp_graph_dir)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) >= 1
        assert any("path" in i.message for i in errors)

    def test_missing_state_for_shell_tool_variable(self, temp_graph_dir):
        """Shell tool NOT used by agent, using {path} without state declaration should error."""
        graph = {
            "version": "1.0",
            "name": "test",
            # No state declaration for 'path'!
            "tools": {
                "run_check": {
                    "type": "shell",
                    "command": "ruff check {path}",
                    "description": "Run ruff",
                }
            },
            "nodes": {
                "step1": {
                    "type": "llm",  # LLM node, not agent - must have state for tool vars
                    "prompt": "test",
                    "state_key": "output",
                }
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        write_prompt(temp_graph_dir, "test")
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_state_declarations(graph_path, temp_graph_dir)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) >= 1
        assert any("path" in i.message for i in errors)

    def test_agent_tool_variables_not_required_in_state(self, temp_graph_dir):
        """Shell tools used by agents get variables from LLM, not state."""
        graph = {
            "version": "1.0",
            "name": "test",
            # No state declaration for 'path' - but that's OK for agent tools
            "tools": {
                "run_check": {
                    "type": "shell",
                    "command": "ruff check {path}",
                    "description": "Run ruff",
                }
            },
            "nodes": {
                "step1": {
                    "type": "agent",  # Agent node - LLM provides tool args
                    "prompt": "test",
                    "tools": ["run_check"],
                    "state_key": "output",
                }
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        write_prompt(temp_graph_dir, "test")
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_state_declarations(graph_path, temp_graph_dir)
        errors = [i for i in issues if i.severity == "error"]
        # No errors because agent tools get variables from LLM
        assert len(errors) == 0


# --- Test check_tool_references ---


class TestCheckToolReferences:
    """Test detection of undefined tool references."""

    def test_valid_tool_reference(self, temp_graph_dir):
        """Node referencing defined tool should pass."""
        graph = {
            "version": "1.0",
            "name": "test",
            "tools": {
                "my_tool": {
                    "type": "shell",
                    "command": "echo hello",
                    "description": "Test tool",
                }
            },
            "nodes": {
                "step1": {
                    "type": "agent",
                    "prompt": "test",
                    "tools": ["my_tool"],
                    "state_key": "output",
                }
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        write_prompt(temp_graph_dir, "test")
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_tool_references(graph_path)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_undefined_tool_reference(self, temp_graph_dir):
        """Node referencing undefined tool should error."""
        graph = {
            "version": "1.0",
            "name": "test",
            "tools": {
                "defined_tool": {
                    "type": "shell",
                    "command": "echo hello",
                    "description": "Test tool",
                }
            },
            "nodes": {
                "step1": {
                    "type": "agent",
                    "prompt": "test",
                    "tools": ["undefined_tool"],  # This doesn't exist!
                    "state_key": "output",
                }
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        write_prompt(temp_graph_dir, "test")
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_tool_references(graph_path)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) >= 1
        assert any("undefined_tool" in i.message for i in errors)

    def test_unused_tool_warning(self, temp_graph_dir):
        """Defined but unused tool should warn."""
        graph = {
            "version": "1.0",
            "name": "test",
            "tools": {
                "used_tool": {
                    "type": "shell",
                    "command": "echo used",
                    "description": "Used tool",
                },
                "unused_tool": {
                    "type": "shell",
                    "command": "echo unused",
                    "description": "Unused tool",
                },
            },
            "nodes": {
                "step1": {
                    "type": "agent",
                    "prompt": "test",
                    "tools": ["used_tool"],  # unused_tool not used
                    "state_key": "output",
                }
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        write_prompt(temp_graph_dir, "test")
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_tool_references(graph_path)
        warnings = [i for i in issues if i.severity == "warning"]
        assert len(warnings) >= 1
        assert any("unused_tool" in i.message for i in warnings)


# --- Test check_prompt_files ---


class TestCheckPromptFiles:
    """Test detection of missing prompt files."""

    def test_valid_prompt_exists(self, temp_graph_dir):
        """Node with existing prompt file should pass."""
        graph = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "step1": {
                    "type": "llm",
                    "prompt": "my_prompt",
                    "state_key": "output",
                }
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        write_prompt(temp_graph_dir, "my_prompt")
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_prompt_files(graph_path, temp_graph_dir)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_missing_prompt_file(self, temp_graph_dir):
        """Node with missing prompt file should error."""
        graph = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "step1": {
                    "type": "llm",
                    "prompt": "nonexistent_prompt",
                    "state_key": "output",
                }
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        # Don't create the prompt file!
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_prompt_files(graph_path, temp_graph_dir)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) >= 1
        assert any("nonexistent_prompt" in i.message for i in errors)

    def test_nested_prompt_path(self, temp_graph_dir):
        """Nested prompt paths like 'code-analysis/analyzer' should work."""
        graph = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "step1": {
                    "type": "llm",
                    "prompt": "code-analysis/analyzer",
                    "state_key": "output",
                }
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        write_prompt(temp_graph_dir, "code-analysis/analyzer")
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_prompt_files(graph_path, temp_graph_dir)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_custom_prompts_dir(self, temp_graph_dir):
        """Graph with custom prompts_dir should resolve prompts correctly."""
        # Create custom prompts directory
        custom_dir = temp_graph_dir / "custom" / "prompts"
        custom_dir.mkdir(parents=True)
        (custom_dir / "my_prompt.yaml").write_text("system: Test\nuser: Test")

        graph = {
            "version": "1.0",
            "name": "test",
            "prompts_dir": "custom/prompts",
            "nodes": {
                "step1": {
                    "type": "llm",
                    "prompt": "my_prompt",
                    "state_key": "output",
                }
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_prompt_files(graph_path, temp_graph_dir)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_prompts_dir_in_defaults(self, temp_graph_dir):
        """Graph with prompts_dir in defaults section should resolve correctly."""
        # Create custom prompts directory
        custom_dir = temp_graph_dir / "my" / "prompts"
        custom_dir.mkdir(parents=True)
        (custom_dir / "test_prompt.yaml").write_text("system: Test\nuser: Test")

        graph = {
            "version": "1.0",
            "name": "test",
            "defaults": {
                "prompts_dir": "my/prompts",
            },
            "nodes": {
                "step1": {
                    "type": "llm",
                    "prompt": "test_prompt",
                    "state_key": "output",
                }
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_prompt_files(graph_path, temp_graph_dir)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0


# --- Test check_edge_coverage ---


class TestCheckEdgeCoverage:
    """Test detection of unreachable nodes."""

    def test_all_nodes_reachable(self, temp_graph_dir):
        """All nodes connected should pass."""
        graph = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "step1": {"type": "llm", "prompt": "test", "state_key": "a"},
                "step2": {"type": "llm", "prompt": "test", "state_key": "b"},
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "step2"},
                {"from": "step2", "to": "END"},
            ],
        }
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_edge_coverage(graph_path)
        warnings = [i for i in issues if i.severity == "warning"]
        assert len(warnings) == 0

    def test_unreachable_node(self, temp_graph_dir):
        """Node not in any edge should warn."""
        graph = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "step1": {"type": "llm", "prompt": "test", "state_key": "a"},
                "orphan": {
                    "type": "llm",
                    "prompt": "test",
                    "state_key": "b",
                },  # Not connected!
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_edge_coverage(graph_path)
        warnings = [i for i in issues if i.severity == "warning"]
        assert len(warnings) >= 1
        assert any("orphan" in i.message for i in warnings)

    def test_no_path_to_end(self, temp_graph_dir):
        """Node without path to END should warn."""
        graph = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "step1": {"type": "llm", "prompt": "test", "state_key": "a"},
                "dead_end": {"type": "llm", "prompt": "test", "state_key": "b"},
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "dead_end"},
                # dead_end has no edge to END!
                {"from": "step1", "to": "END"},
            ],
        }
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_edge_coverage(graph_path)
        warnings = [i for i in issues if i.severity == "warning"]
        assert len(warnings) >= 1
        assert any("dead_end" in i.message for i in warnings)


# --- Test check_node_types ---


class TestCheckNodeTypes:
    """Test detection of invalid node types."""

    def test_valid_node_types(self, temp_graph_dir):
        """Valid node types should pass."""
        graph = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "a": {"type": "llm", "prompt": "test", "state_key": "a"},
                "b": {
                    "type": "router",
                    "prompt": "test",
                    "routes": {},
                    "state_key": "b",
                },
                "c": {"type": "agent", "prompt": "test", "tools": [], "state_key": "c"},
                "d": {"type": "map", "prompt": "test", "state_key": "d"},
                "e": {
                    "type": "python",
                    "module": "test",
                    "function": "fn",
                    "state_key": "e",
                },
            },
            "edges": [
                {"from": "START", "to": "a"},
                {"from": "a", "to": "END"},
            ],
        }
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_node_types(graph_path)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_invalid_node_type(self, temp_graph_dir):
        """Invalid node type should error."""
        graph = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "step1": {
                    "type": "invalid_type",  # Not a valid type!
                    "prompt": "test",
                    "state_key": "output",
                }
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        graph_path = write_graph(temp_graph_dir, graph)

        issues = check_node_types(graph_path)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) >= 1
        assert any("invalid_type" in i.message for i in errors)


# --- Test full lint_graph function ---


class TestLintGraph:
    """Test the main lint_graph entry point."""

    def test_valid_graph_passes(self, temp_graph_dir):
        """A well-formed graph should pass linting."""
        graph = {
            "version": "1.0",
            "name": "test",
            "description": "A test graph",
            "state": {"input": "str"},
            "nodes": {
                "step1": {
                    "type": "llm",
                    "prompt": "test",
                    "state_key": "output",
                }
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        write_prompt(temp_graph_dir, "test")
        graph_path = write_graph(temp_graph_dir, graph)

        result = lint_graph(graph_path, temp_graph_dir)
        assert result.valid is True
        errors = [i for i in result.issues if i.severity == "error"]
        assert len(errors) == 0

    def test_multiple_issues_detected(self, temp_graph_dir):
        """Graph with multiple issues should report all."""
        graph = {
            "version": "1.0",
            "name": "test",
            # Missing description (warning)
            # Missing state for {path} (error)
            "tools": {
                "unused": {"type": "shell", "command": "echo", "description": "x"},
            },
            "nodes": {
                "step1": {
                    "type": "invalid",  # Invalid type (error)
                    "prompt": "missing_prompt",  # Missing file (error)
                    "tools": ["undefined"],  # Undefined tool (error)
                    "state_key": "output",
                },
                "orphan": {  # Unreachable (warning)
                    "type": "llm",
                    "prompt": "test",
                    "state_key": "orphan",
                },
            },
            "edges": [
                {"from": "START", "to": "step1"},
                {"from": "step1", "to": "END"},
            ],
        }
        graph_path = write_graph(temp_graph_dir, graph)

        result = lint_graph(graph_path, temp_graph_dir)
        assert result.valid is False
        assert len(result.issues) >= 3  # At least 3 issues
