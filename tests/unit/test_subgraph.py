"""Unit tests for subgraph node functionality.

TDD tests for the subgraph feature:
- create_subgraph_node function
- SubgraphNodeConfig schema
- Circular reference detection
- State mapping modes
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestSubgraphNodeConfig:
    """Tests for SubgraphNodeConfig schema validation."""

    def test_valid_invoke_mode_config(self):
        """Valid config with invoke mode and mappings."""
        from yamlgraph.models.graph_schema import SubgraphNodeConfig

        config = SubgraphNodeConfig(
            type="subgraph",
            graph="subgraphs/child.yaml",
            mode="invoke",
            input_mapping={"query": "user_input"},
            output_mapping={"result": "analysis"},
        )
        assert config.mode == "invoke"
        assert config.graph == "subgraphs/child.yaml"

    def test_valid_direct_mode_config(self):
        """Valid config with direct mode (no mappings)."""
        from yamlgraph.models.graph_schema import SubgraphNodeConfig

        config = SubgraphNodeConfig(
            type="subgraph",
            graph="subgraphs/child.yaml",
            mode="direct",
        )
        assert config.mode == "direct"
        assert config.input_mapping == {}
        assert config.output_mapping == {}

    def test_default_mode_is_invoke(self):
        """Mode defaults to 'invoke' when not specified."""
        from yamlgraph.models.graph_schema import SubgraphNodeConfig

        config = SubgraphNodeConfig(
            type="subgraph",
            graph="child.yaml",
        )
        assert config.mode == "invoke"

    def test_rejects_non_yaml_graph_path(self):
        """Rejects graph paths that don't end in .yaml or .yml."""
        from pydantic import ValidationError

        from yamlgraph.models.graph_schema import SubgraphNodeConfig

        with pytest.raises(ValidationError) as exc_info:
            SubgraphNodeConfig(
                type="subgraph",
                graph="child.json",
            )
        assert "YAML file" in str(exc_info.value)

    def test_rejects_mappings_with_direct_mode(self):
        """Direct mode does not allow input/output mappings."""
        from pydantic import ValidationError

        from yamlgraph.models.graph_schema import SubgraphNodeConfig

        with pytest.raises(ValidationError) as exc_info:
            SubgraphNodeConfig(
                type="subgraph",
                graph="child.yaml",
                mode="direct",
                input_mapping={"foo": "bar"},
            )
        assert "direct" in str(exc_info.value).lower()

    def test_accepts_yml_extension(self):
        """Accepts .yml extension for graph path."""
        from yamlgraph.models.graph_schema import SubgraphNodeConfig

        config = SubgraphNodeConfig(
            type="subgraph",
            graph="child.yml",
        )
        assert config.graph == "child.yml"

    def test_accepts_checkpointer_override(self):
        """Accepts optional checkpointer override."""
        from yamlgraph.models.graph_schema import SubgraphNodeConfig

        config = SubgraphNodeConfig(
            type="subgraph",
            graph="child.yaml",
            checkpointer="memory",
        )
        assert config.checkpointer == "memory"


class TestCreateSubgraphNode:
    """Tests for create_subgraph_node function."""

    @pytest.fixture
    def child_graph_yaml(self, tmp_path: Path) -> Path:
        """Create a minimal child graph YAML file."""
        child_yaml = tmp_path / "subgraphs" / "child.yaml"
        child_yaml.parent.mkdir(parents=True, exist_ok=True)
        child_yaml.write_text(
            """
version: "1.0"
name: child
state:
  input_text: str
  output_text: str
nodes:
  process:
    type: llm
    prompt: test
    state_key: output_text
edges:
  - {from: START, to: process}
  - {from: process, to: END}
"""
        )
        return child_yaml

    @pytest.fixture
    def parent_graph_path(self, tmp_path: Path) -> Path:
        """Return path to parent graph (for relative resolution)."""
        return tmp_path / "parent.yaml"

    def test_creates_callable_node_invoke_mode(
        self, child_graph_yaml: Path, parent_graph_path: Path
    ):
        """Creates a callable node function in invoke mode."""
        from yamlgraph.node_factory import create_subgraph_node

        config = {
            "type": "subgraph",
            "mode": "invoke",
            "graph": "subgraphs/child.yaml",
            "input_mapping": {"parent_input": "input_text"},
            "output_mapping": {"result": "output_text"},
        }

        node = create_subgraph_node(
            "test_subgraph",
            config,
            parent_graph_path=parent_graph_path,
        )
        assert callable(node)

    def test_raises_file_not_found_for_missing_graph(self, parent_graph_path: Path):
        """Raises FileNotFoundError when subgraph doesn't exist."""
        from yamlgraph.node_factory import create_subgraph_node

        config = {
            "type": "subgraph",
            "graph": "nonexistent.yaml",
        }

        with pytest.raises(FileNotFoundError) as exc_info:
            create_subgraph_node(
                "test_subgraph",
                config,
                parent_graph_path=parent_graph_path,
            )
        assert "nonexistent.yaml" in str(exc_info.value)

    def test_resolves_path_relative_to_parent(
        self, child_graph_yaml: Path, parent_graph_path: Path
    ):
        """Graph path is resolved relative to parent graph file."""
        from yamlgraph.node_factory import create_subgraph_node

        config = {
            "type": "subgraph",
            "graph": "subgraphs/child.yaml",  # Relative path
        }

        # Should resolve to tmp_path/subgraphs/child.yaml
        node = create_subgraph_node(
            "test_subgraph",
            config,
            parent_graph_path=parent_graph_path,
        )
        assert callable(node)


class TestSubgraphStateMapping:
    """Tests for state mapping between parent and child."""

    @pytest.fixture
    def mock_compiled_graph(self):
        """Create a mock compiled graph."""
        mock = MagicMock()
        mock.invoke.return_value = {"output_text": "result from child"}
        return mock

    def test_maps_input_state_explicit(self, mock_compiled_graph):
        """Explicit input mapping transforms parent state to child input."""
        from yamlgraph.node_factory import _map_input_state

        parent_state = {"query": "hello", "context": "world", "other": "ignored"}
        input_mapping = {"query": "user_input", "context": "conversation"}

        child_input = _map_input_state(parent_state, input_mapping)

        assert child_input == {"user_input": "hello", "conversation": "world"}
        assert "other" not in child_input

    def test_maps_input_state_auto(self, mock_compiled_graph):
        """Auto mapping copies all parent state fields."""
        from yamlgraph.node_factory import _map_input_state

        parent_state = {"query": "hello", "context": "world"}

        child_input = _map_input_state(parent_state, "auto")

        assert child_input == {"query": "hello", "context": "world"}
        assert child_input is not parent_state  # Should be a copy

    def test_maps_input_state_full(self, mock_compiled_graph):
        """Star mapping passes entire state (same reference)."""
        from yamlgraph.node_factory import _map_input_state

        parent_state = {"query": "hello", "context": "world"}

        child_input = _map_input_state(parent_state, "*")

        assert child_input is parent_state

    def test_maps_output_state_explicit(self):
        """Explicit output mapping transforms child output to parent updates."""
        from yamlgraph.node_factory import _map_output_state

        child_output = {"analysis": "done", "meta": {"count": 1}, "internal": "ignored"}
        output_mapping = {"result": "analysis", "metadata": "meta"}

        parent_updates = _map_output_state(child_output, output_mapping)

        assert parent_updates == {"result": "done", "metadata": {"count": 1}}
        assert "internal" not in parent_updates


class TestCircularReferenceDetection:
    """Tests for circular subgraph reference detection."""

    def test_detects_direct_self_reference(self, tmp_path: Path):
        """Detects A → A cycle (graph references itself)."""
        from yamlgraph.node_factory import create_subgraph_node

        # Create a graph that references itself
        self_ref = tmp_path / "self.yaml"
        self_ref.write_text(
            """
version: "1.0"
name: self-referencing
state:
  data: str
nodes:
  recurse:
    type: subgraph
    graph: self.yaml
edges:
  - {from: START, to: recurse}
  - {from: recurse, to: END}
"""
        )

        config = {"type": "subgraph", "graph": "self.yaml"}

        with pytest.raises(ValueError) as exc_info:
            create_subgraph_node("test", config, parent_graph_path=self_ref)

        assert "Circular" in str(exc_info.value)

    def test_detects_indirect_cycle(self, tmp_path: Path):
        """Detects A → B → A cycle."""
        from yamlgraph.node_factory import create_subgraph_node

        # Create A that references B
        graph_a = tmp_path / "a.yaml"
        graph_a.write_text(
            """
version: "1.0"
name: graph-a
state:
  data: str
nodes:
  call_b:
    type: subgraph
    graph: b.yaml
edges:
  - {from: START, to: call_b}
  - {from: call_b, to: END}
"""
        )

        # Create B that references A
        graph_b = tmp_path / "b.yaml"
        graph_b.write_text(
            """
version: "1.0"
name: graph-b
state:
  data: str
nodes:
  call_a:
    type: subgraph
    graph: a.yaml
edges:
  - {from: START, to: call_a}
  - {from: call_a, to: END}
"""
        )

        config = {"type": "subgraph", "graph": "b.yaml"}

        with pytest.raises(ValueError) as exc_info:
            create_subgraph_node("test", config, parent_graph_path=graph_a)

        error_msg = str(exc_info.value)
        assert "Circular" in error_msg
        assert "a.yaml" in error_msg

    def test_allows_diamond_pattern(self, tmp_path: Path):
        """Allows diamond pattern: A→B, A→C, B→D, C→D (not circular)."""
        from yamlgraph.node_factory import create_subgraph_node

        # Create D (leaf)
        graph_d = tmp_path / "d.yaml"
        graph_d.write_text(
            """
version: "1.0"
name: graph-d
state:
  data: str
nodes:
  process:
    type: llm
    prompt: test
    state_key: data
edges:
  - {from: START, to: process}
  - {from: process, to: END}
"""
        )

        # Create B that references D
        graph_b = tmp_path / "b.yaml"
        graph_b.write_text(
            """
version: "1.0"
name: graph-b
state:
  data: str
nodes:
  call_d:
    type: subgraph
    graph: d.yaml
edges:
  - {from: START, to: call_d}
  - {from: call_d, to: END}
"""
        )

        # Create C that also references D
        graph_c = tmp_path / "c.yaml"
        graph_c.write_text(
            """
version: "1.0"
name: graph-c
state:
  data: str
nodes:
  call_d:
    type: subgraph
    graph: d.yaml
edges:
  - {from: START, to: call_d}
  - {from: call_d, to: END}
"""
        )

        # This should NOT raise (diamond is valid)
        config_b = {"type": "subgraph", "graph": "b.yaml"}
        config_c = {"type": "subgraph", "graph": "c.yaml"}

        # Both should succeed (D is referenced twice but no cycle)
        parent_path = tmp_path / "a.yaml"
        node_b = create_subgraph_node("call_b", config_b, parent_graph_path=parent_path)
        node_c = create_subgraph_node("call_c", config_c, parent_graph_path=parent_path)

        assert callable(node_b)
        assert callable(node_c)


class TestThreadIdPropagation:
    """Tests for thread ID propagation to child graphs."""

    def test_propagates_thread_id_from_config(self):
        """Thread ID is propagated as parent_thread:node_name."""
        from yamlgraph.node_factory import _build_child_config

        parent_config = {"configurable": {"thread_id": "main-123"}}
        node_name = "summarizer"

        child_config = _build_child_config(parent_config, node_name)

        assert child_config["configurable"]["thread_id"] == "main-123:summarizer"

    def test_creates_thread_id_when_parent_has_none(self):
        """Creates thread ID from node name when parent has none."""
        from yamlgraph.node_factory import _build_child_config

        parent_config = {"configurable": {}}
        node_name = "summarizer"

        child_config = _build_child_config(parent_config, node_name)

        assert child_config["configurable"]["thread_id"] == "summarizer"

    def test_preserves_other_config_values(self):
        """Other config values are preserved in child config."""
        from yamlgraph.node_factory import _build_child_config

        parent_config = {
            "configurable": {"thread_id": "main", "other": "value"},
            "tags": ["test"],
        }
        node_name = "child"

        child_config = _build_child_config(parent_config, node_name)

        assert child_config["configurable"]["other"] == "value"
        assert child_config["tags"] == ["test"]


class TestInterruptOutputMapping:
    """Tests for interrupt_output_mapping feature (FR-006)."""

    def test_schema_accepts_interrupt_output_mapping(self):
        """SubgraphNodeConfig accepts interrupt_output_mapping."""
        from yamlgraph.models.graph_schema import SubgraphNodeConfig

        config = SubgraphNodeConfig(
            type="subgraph",
            graph="child.yaml",
            mode="invoke",
            output_mapping={"final_result": "result"},
            interrupt_output_mapping={"current_phase": "phase"},
        )
        assert config.interrupt_output_mapping == {"current_phase": "phase"}

    def test_schema_default_interrupt_output_mapping_empty(self):
        """interrupt_output_mapping defaults to empty dict."""
        from yamlgraph.models.graph_schema import SubgraphNodeConfig

        config = SubgraphNodeConfig(
            type="subgraph",
            graph="child.yaml",
        )
        assert config.interrupt_output_mapping == {}

    def test_applies_interrupt_mapping_when_subgraph_interrupts(self, tmp_path):
        """interrupt_output_mapping is applied when subgraph returns __interrupt__."""
        from unittest.mock import MagicMock, patch

        from yamlgraph.node_factory import create_subgraph_node

        # Create a minimal child graph file
        child_yaml = tmp_path / "child.yaml"
        child_yaml.write_text(
            """
version: "1.0"
name: child
state:
  phase: str
  result: str
nodes:
  ask_question:
    type: interrupt
    state_key: question
edges:
  - {from: START, to: ask_question}
  - {from: ask_question, to: END}
"""
        )

        parent_path = tmp_path / "parent.yaml"

        config = {
            "type": "subgraph",
            "graph": "child.yaml",
            "mode": "invoke",
            "output_mapping": {"final_result": "result"},
            "interrupt_output_mapping": {"current_phase": "phase"},
        }

        # Mock the compiled subgraph to return an interrupted state
        mock_compiled = MagicMock()
        mock_compiled.invoke.return_value = {
            "phase": "probing",
            "result": None,
            "__interrupt__": (MagicMock(value={"question": "What?"}),),
        }

        with (
            patch("yamlgraph.graph_loader.compile_graph") as mock_compile_graph,
            patch("yamlgraph.graph_loader.load_graph_config") as mock_load,
        ):
            mock_load.return_value = MagicMock()
            mock_state_graph = MagicMock()
            mock_state_graph.compile.return_value = mock_compiled
            mock_compile_graph.return_value = mock_state_graph

            node_fn = create_subgraph_node("demographics", config, parent_path)
            result = node_fn({"user_input": "hello"}, {})

        # Should use interrupt_output_mapping, not output_mapping
        assert "current_phase" in result
        assert result["current_phase"] == "probing"
        # Should NOT have the completion mapping
        assert "final_result" not in result
        # Should forward the interrupt marker
        assert "__interrupt__" in result

    def test_applies_output_mapping_when_subgraph_completes(self, tmp_path):
        """output_mapping is applied when subgraph completes (no __interrupt__)."""
        from unittest.mock import MagicMock, patch

        from yamlgraph.node_factory import create_subgraph_node

        child_yaml = tmp_path / "child.yaml"
        child_yaml.write_text(
            """
version: "1.0"
name: child
state:
  phase: str
  result: str
nodes:
  process:
    type: llm
    prompt: test
    state_key: result
edges:
  - {from: START, to: process}
  - {from: process, to: END}
"""
        )

        parent_path = tmp_path / "parent.yaml"

        config = {
            "type": "subgraph",
            "graph": "child.yaml",
            "mode": "invoke",
            "output_mapping": {"final_result": "result"},
            "interrupt_output_mapping": {"current_phase": "phase"},
        }

        # Mock the compiled subgraph to return a completed state (no __interrupt__)
        mock_compiled = MagicMock()
        mock_compiled.invoke.return_value = {
            "phase": "complete",
            "result": "Analysis done",
            # No __interrupt__ key
        }

        with (
            patch("yamlgraph.graph_loader.compile_graph") as mock_compile_graph,
            patch("yamlgraph.graph_loader.load_graph_config") as mock_load,
        ):
            mock_load.return_value = MagicMock()
            mock_state_graph = MagicMock()
            mock_state_graph.compile.return_value = mock_compiled
            mock_compile_graph.return_value = mock_state_graph

            node_fn = create_subgraph_node("demographics", config, parent_path)
            result = node_fn({"user_input": "hello"}, {})

        # Should use output_mapping, not interrupt_output_mapping
        assert "final_result" in result
        assert result["final_result"] == "Analysis done"
        # Should NOT have the interrupt mapping
        assert "current_phase" not in result
