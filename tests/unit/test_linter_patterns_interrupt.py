"""Tests for interrupt pattern linter validations."""

from yamlgraph.linter.patterns.interrupt import (
    check_interrupt_checkpointer,
    check_interrupt_node_structure,
    check_interrupt_patterns,
    check_interrupt_state_declarations,
)


class TestInterruptNodeStructure:
    """Test interrupt node structural validation."""

    def test_valid_interrupt_with_prompt(self):
        """Should pass valid interrupt structure with prompt."""
        node_config = {
            "type": "interrupt",
            "prompt": "ask_question",
            "resume_key": "user_answer",
        }

        issues = check_interrupt_node_structure("ask_user", node_config)
        assert len(issues) == 0

    def test_valid_interrupt_with_message(self):
        """Should pass valid interrupt structure with message."""
        node_config = {
            "type": "interrupt",
            "message": "What is your answer?",
            "resume_key": "user_input",
        }

        issues = check_interrupt_node_structure("ask_user", node_config)
        assert len(issues) == 0

    def test_missing_resume_key(self):
        """Should error when resume_key is missing."""
        node_config = {"type": "interrupt", "prompt": "ask_question"}

        issues = check_interrupt_node_structure("ask_user", node_config)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].code == "E301"
        assert "missing required field 'resume_key'" in issues[0].message

    def test_missing_prompt_and_message(self):
        """Should error when both prompt and message are missing."""
        node_config = {"type": "interrupt", "resume_key": "user_answer"}

        issues = check_interrupt_node_structure("ask_user", node_config)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].code == "E302"
        assert "missing 'prompt' or 'message' field" in issues[0].message

    def test_has_both_prompt_and_message(self):
        """Should warn when both prompt and message are present."""
        node_config = {
            "type": "interrupt",
            "prompt": "ask_question",
            "message": "What is your answer?",
            "resume_key": "user_answer",
        }

        issues = check_interrupt_node_structure("ask_user", node_config)
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert issues[0].code == "W302"
        assert "has both 'prompt' and 'message' fields" in issues[0].message


class TestInterruptStateDeclarations:
    """Test interrupt node state declaration validation."""

    def test_valid_state_declarations(self):
        """Should pass when state_key and resume_key are declared."""
        node_config = {
            "type": "interrupt",
            "prompt": "ask_question",
            "state_key": "question",
            "resume_key": "answer",
        }
        graph = {"state": {"question": "str", "answer": "str"}}

        issues = check_interrupt_state_declarations("ask_user", node_config, graph)
        assert len(issues) == 0

    def test_missing_state_key_declaration(self):
        """Should error when state_key is not declared in state section."""
        node_config = {
            "type": "interrupt",
            "prompt": "ask_question",
            "state_key": "question",
            "resume_key": "answer",
        }
        graph = {
            "state": {
                "answer": "str"
                # Missing "question"
            }
        }

        issues = check_interrupt_state_declarations("ask_user", node_config, graph)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].code == "E303"
        assert "state_key 'question' not declared" in issues[0].message

    def test_missing_resume_key_declaration(self):
        """Should error when resume_key is not declared in state section."""
        node_config = {
            "type": "interrupt",
            "message": "What is your answer?",
            "resume_key": "user_input",
        }
        graph = {
            "state": {
                # Missing "user_input"
            }
        }

        issues = check_interrupt_state_declarations("ask_user", node_config, graph)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].code == "E303"
        assert "resume_key 'user_input' not declared" in issues[0].message

    def test_no_state_key_no_error(self):
        """Should pass when state_key is not specified (optional field)."""
        node_config = {
            "type": "interrupt",
            "message": "What is your answer?",
            "resume_key": "user_input",
        }
        graph = {"state": {"user_input": "str"}}

        issues = check_interrupt_state_declarations("ask_user", node_config, graph)
        assert len(issues) == 0


class TestInterruptCheckpointer:
    """Test interrupt checkpointer validation."""

    def test_graph_without_interrupt_no_checkpointer_needed(self):
        """Should pass when graph has no interrupt nodes."""
        graph = {"nodes": {"llm_node": {"type": "llm", "prompt": "hello"}}}

        issues = check_interrupt_checkpointer(graph)
        assert len(issues) == 0

    def test_graph_with_interrupt_missing_checkpointer(self):
        """Should warn when graph has interrupt nodes but no checkpointer."""
        graph = {
            "nodes": {
                "ask_user": {
                    "type": "interrupt",
                    "message": "Question?",
                    "resume_key": "answer",
                }
            }
        }

        issues = check_interrupt_checkpointer(graph)
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert issues[0].code == "W301"
        assert "missing checkpointer configuration" in issues[0].message

    def test_graph_with_interrupt_valid_checkpointer(self):
        """Should pass when graph has interrupt nodes and valid checkpointer."""
        graph = {
            "checkpointer": {"type": "memory"},
            "nodes": {
                "ask_user": {
                    "type": "interrupt",
                    "message": "Question?",
                    "resume_key": "answer",
                }
            },
        }

        issues = check_interrupt_checkpointer(graph)
        assert len(issues) == 0

    def test_checkpointer_not_dict(self):
        """Should error when checkpointer is not a dict."""
        graph = {
            "checkpointer": "memory",  # Should be dict
            "nodes": {
                "ask_user": {
                    "type": "interrupt",
                    "message": "Question?",
                    "resume_key": "answer",
                }
            },
        }

        issues = check_interrupt_checkpointer(graph)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].code == "E304"
        assert "checkpointer must be a dict" in issues[0].message

    def test_checkpointer_missing_type(self):
        """Should error when checkpointer dict missing type field."""
        graph = {
            "checkpointer": {"path": "checkpoints.db"},  # Missing type
            "nodes": {
                "ask_user": {
                    "type": "interrupt",
                    "message": "Question?",
                    "resume_key": "answer",
                }
            },
        }

        issues = check_interrupt_checkpointer(graph)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].code == "E304"
        assert "missing required 'type' field" in issues[0].message


class TestInterruptPatternsIntegration:
    """Test interrupt pattern validation integration."""

    def test_valid_interrupt_graph(self, tmp_path):
        """Should pass valid interrupt graph."""
        graph_content = """
checkpointer:
  type: memory
state:
  question: str
  answer: str
nodes:
  ask_user:
    type: interrupt
    message: "What is your answer?"
    state_key: question
    resume_key: answer
"""
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text(graph_content)

        issues = check_interrupt_patterns(graph_file)
        assert len(issues) == 0

    def test_invalid_interrupt_graph(self, tmp_path):
        """Should catch multiple interrupt validation issues."""
        graph_content = """
# Missing checkpointer
state:
  answer: str
nodes:
  bad_interrupt:
    type: interrupt
    # Missing resume_key and prompt/message
"""
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text(graph_content)

        issues = check_interrupt_patterns(graph_file)
        # Should have: W301 (missing checkpointer), E301 (missing resume_key), E302 (missing prompt/message)
        error_issues = [i for i in issues if i.severity == "error"]
        warning_issues = [i for i in issues if i.severity == "warning"]

        assert len(error_issues) == 2  # E301, E302
        assert len(warning_issues) == 1  # W301

        error_codes = {issue.code for issue in error_issues}
        assert "E301" in error_codes
        assert "E302" in error_codes
        assert warning_issues[0].code == "W301"

    def test_mixed_nodes_validates_only_interrupts(self, tmp_path):
        """Should only validate interrupt nodes, ignore others."""
        graph_content = """
checkpointer:
  type: memory
state:
  answer: str
nodes:
  llm_node:
    type: llm
    prompt: hello
  router_node:
    type: router
    routes: {"pos": "handle_pos"}
  interrupt_node:
    type: interrupt
    message: "Question?"
    resume_key: answer
"""
        graph_file = tmp_path / "test_graph.yaml"
        graph_file.write_text(graph_content)

        issues = check_interrupt_patterns(graph_file)
        # Should only validate the interrupt_node
        assert len(issues) == 0  # All valid
