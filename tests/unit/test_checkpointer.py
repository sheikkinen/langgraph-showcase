"""Tests for native LangGraph checkpointer integration."""

from pathlib import Path

import pytest


class TestGetCheckpointer:
    """Tests for get_checkpointer() function."""

    @pytest.mark.req("REQ-YG-026")
    def test_returns_sqlite_saver_instance(self, tmp_path: Path):
        """Should return a SqliteSaver instance."""
        from langgraph.checkpoint.sqlite import SqliteSaver

        from yamlgraph.storage.checkpointer import get_checkpointer

        db_path = tmp_path / "test.db"
        checkpointer = get_checkpointer(db_path)

        assert isinstance(checkpointer, SqliteSaver)

    @pytest.mark.req("REQ-YG-026")
    def test_creates_database_file(self, tmp_path: Path):
        """Should create the database file on first use."""
        from yamlgraph.storage.checkpointer import get_checkpointer

        db_path = tmp_path / "test.db"
        assert not db_path.exists()

        checkpointer = get_checkpointer(db_path)
        # Access connection to trigger file creation
        _ = checkpointer

        # File created when connection is made
        assert db_path.exists()

    @pytest.mark.req("REQ-YG-026")
    def test_uses_default_path_when_none(self, monkeypatch, tmp_path: Path):
        """Should use DATABASE_PATH when db_path is None."""
        from yamlgraph.storage.checkpointer import get_checkpointer

        # Monkeypatch the default path
        default_db = tmp_path / "default.db"
        monkeypatch.setattr("yamlgraph.storage.checkpointer.DATABASE_PATH", default_db)

        checkpointer = get_checkpointer(None)
        assert checkpointer is not None

    @pytest.mark.req("REQ-YG-026")
    def test_accepts_string_path(self, tmp_path: Path):
        """Should accept string path as well as Path."""
        from yamlgraph.storage.checkpointer import get_checkpointer

        db_path = str(tmp_path / "test.db")
        checkpointer = get_checkpointer(db_path)

        assert checkpointer is not None


class TestCheckpointerWithGraph:
    """Tests for using checkpointer with a LangGraph StateGraph."""

    @pytest.mark.req("REQ-YG-026")
    def test_graph_compiles_with_checkpointer(self, tmp_path: Path):
        """Graph should compile when checkpointer is provided."""
        from typing import TypedDict

        from langgraph.graph import END, StateGraph

        from yamlgraph.storage.checkpointer import get_checkpointer

        class SimpleState(TypedDict, total=False):
            value: str

        def node_fn(state: SimpleState) -> dict:
            return {"value": "updated"}

        workflow = StateGraph(SimpleState)
        workflow.add_node("test", node_fn)
        workflow.set_entry_point("test")
        workflow.add_edge("test", END)

        checkpointer = get_checkpointer(tmp_path / "test.db")
        graph = workflow.compile(checkpointer=checkpointer)

        assert graph is not None

    @pytest.mark.req("REQ-YG-026")
    def test_state_persists_with_thread_id(self, tmp_path: Path):
        """State should persist when using thread_id in config."""
        from typing import TypedDict

        from langgraph.graph import END, StateGraph

        from yamlgraph.storage.checkpointer import get_checkpointer

        class CounterState(TypedDict, total=False):
            count: int

        def increment(state: CounterState) -> dict:
            return {"count": state.get("count", 0) + 1}

        workflow = StateGraph(CounterState)
        workflow.add_node("increment", increment)
        workflow.set_entry_point("increment")
        workflow.add_edge("increment", END)

        checkpointer = get_checkpointer(tmp_path / "test.db")
        graph = workflow.compile(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": "test-thread-1"}}

        # First invocation
        result1 = graph.invoke({"count": 0}, config)
        assert result1["count"] == 1

        # State should be retrievable
        state = graph.get_state(config)
        assert state.values["count"] == 1

    @pytest.mark.req("REQ-YG-026")
    def test_get_state_history_returns_checkpoints(self, tmp_path: Path):
        """get_state_history() should return checkpoint history."""
        from typing import TypedDict

        from langgraph.graph import END, StateGraph

        from yamlgraph.storage.checkpointer import get_checkpointer

        class StepState(TypedDict, total=False):
            step: int

        def step1(state: StepState) -> dict:
            return {"step": 1}

        def step2(state: StepState) -> dict:
            return {"step": 2}

        workflow = StateGraph(StepState)
        workflow.add_node("step1", step1)
        workflow.add_node("step2", step2)
        workflow.set_entry_point("step1")
        workflow.add_edge("step1", "step2")
        workflow.add_edge("step2", END)

        checkpointer = get_checkpointer(tmp_path / "test.db")
        graph = workflow.compile(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": "history-test"}}
        graph.invoke({}, config)

        # Get history
        history = list(graph.get_state_history(config))

        # Should have multiple checkpoints (one per step + initial)
        assert len(history) >= 2

        # Most recent first
        assert history[0].values["step"] == 2


class TestGetStateHistory:
    """Tests for get_state_history helper function."""

    @pytest.mark.req("REQ-YG-026")
    def test_returns_list_of_snapshots(self, tmp_path: Path):
        """get_state_history should return list of StateSnapshot."""
        from typing import TypedDict

        from langgraph.graph import END, StateGraph

        from yamlgraph.storage.checkpointer import get_checkpointer, get_state_history

        class TestState(TypedDict, total=False):
            data: str

        def node(state: TestState) -> dict:
            return {"data": "done"}

        workflow = StateGraph(TestState)
        workflow.add_node("test", node)
        workflow.set_entry_point("test")
        workflow.add_edge("test", END)

        checkpointer = get_checkpointer(tmp_path / "test.db")
        graph = workflow.compile(checkpointer=checkpointer)

        thread_id = "history-helper-test"
        config = {"configurable": {"thread_id": thread_id}}
        graph.invoke({}, config)

        history = get_state_history(graph, thread_id)

        assert isinstance(history, list)
        assert len(history) >= 1

    @pytest.mark.req("REQ-YG-026")
    def test_empty_history_for_unknown_thread(self, tmp_path: Path):
        """Should return empty list for non-existent thread."""
        from typing import TypedDict

        from langgraph.graph import END, StateGraph

        from yamlgraph.storage.checkpointer import get_checkpointer, get_state_history

        class TestState(TypedDict, total=False):
            data: str

        def node(state: TestState) -> dict:
            return {"data": "done"}

        workflow = StateGraph(TestState)
        workflow.add_node("test", node)
        workflow.set_entry_point("test")
        workflow.add_edge("test", END)

        checkpointer = get_checkpointer(tmp_path / "test.db")
        graph = workflow.compile(checkpointer=checkpointer)

        history = get_state_history(graph, "non-existent-thread")

        assert history == []
