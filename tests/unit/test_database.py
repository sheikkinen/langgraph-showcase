"""Tests for showcase.storage.database module."""



from showcase.models import create_initial_state


class TestShowcaseDB:
    """Tests for ShowcaseDB class."""

    def test_db_initialization(self, temp_db):
        """Database should initialize successfully."""
        assert temp_db.db_path.exists()

    def test_save_and_load_state(self, temp_db, sample_state):
        """State should be saved and loaded correctly."""
        thread_id = sample_state["thread_id"]
        temp_db.save_state(thread_id, sample_state, status="completed")
        
        loaded = temp_db.load_state(thread_id)
        assert loaded is not None
        assert loaded["topic"] == sample_state["topic"]
        assert loaded["thread_id"] == thread_id

    def test_load_nonexistent_state(self, temp_db):
        """Loading nonexistent state should return None."""
        result = temp_db.load_state("nonexistent")
        assert result is None

    def test_update_existing_state(self, temp_db, empty_state):
        """Updating existing state should work."""
        thread_id = empty_state["thread_id"]
        
        # Save initial state
        temp_db.save_state(thread_id, empty_state, status="running")
        
        # Update state
        empty_state["current_step"] = "generate"
        temp_db.save_state(thread_id, empty_state, status="completed")
        
        # Load and verify
        loaded = temp_db.load_state(thread_id)
        assert loaded["current_step"] == "generate"

    def test_list_runs_empty(self, temp_db):
        """List runs should return empty list when no runs."""
        runs = temp_db.list_runs()
        assert runs == []

    def test_list_runs_with_data(self, temp_db):
        """List runs should return saved runs."""
        state1 = create_initial_state(topic="test1", thread_id="thread1")
        state2 = create_initial_state(topic="test2", thread_id="thread2")
        
        temp_db.save_state("thread1", state1, status="completed")
        temp_db.save_state("thread2", state2, status="running")
        
        runs = temp_db.list_runs()
        assert len(runs) == 2
        thread_ids = [r["thread_id"] for r in runs]
        assert "thread1" in thread_ids
        assert "thread2" in thread_ids

    def test_list_runs_limit(self, temp_db):
        """List runs should respect limit parameter."""
        for i in range(5):
            state = create_initial_state(topic=f"test{i}", thread_id=f"thread{i}")
            temp_db.save_state(f"thread{i}", state)
        
        runs = temp_db.list_runs(limit=3)
        assert len(runs) == 3

    def test_delete_run(self, temp_db, empty_state):
        """Delete run should remove the state."""
        thread_id = empty_state["thread_id"]
        temp_db.save_state(thread_id, empty_state)
        
        result = temp_db.delete_run(thread_id)
        assert result is True
        
        loaded = temp_db.load_state(thread_id)
        assert loaded is None

    def test_delete_nonexistent_run(self, temp_db):
        """Deleting nonexistent run should return False."""
        result = temp_db.delete_run("nonexistent")
        assert result is False

    def test_serialize_state_with_pydantic(self, temp_db, sample_state):
        """State with Pydantic models should serialize correctly."""
        thread_id = sample_state["thread_id"]
        temp_db.save_state(thread_id, sample_state)
        
        loaded = temp_db.load_state(thread_id)
        # Pydantic models should be dicts after serialization
        assert isinstance(loaded["generated"], dict)
        assert loaded["generated"]["title"] == "Test Article"
