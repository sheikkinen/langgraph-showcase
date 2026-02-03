"""Tests for questionnaire handlers - TDD: Write tests first."""

from pathlib import Path


class TestAppendMessages:
    """Test message management functions."""

    def test_append_user_message(self) -> None:
        """Add user message to empty messages list."""
        from tools.handlers import append_user_message

        state = {"user_message": "Hello", "messages": []}
        result = append_user_message(state)

        assert result["messages"] == [{"role": "user", "content": "Hello"}]

    def test_append_user_message_preserves_existing(self) -> None:
        """Append to existing messages."""
        from tools.handlers import append_user_message

        state = {
            "user_message": "Second",
            "messages": [{"role": "assistant", "content": "First"}],
        }
        result = append_user_message(state)

        assert len(result["messages"]) == 2
        assert result["messages"][1] == {"role": "user", "content": "Second"}

    def test_append_user_message_none_messages(self) -> None:
        """Handle None messages list."""
        from tools.handlers import append_user_message

        state = {"user_message": "Hello", "messages": None}
        result = append_user_message(state)

        assert result["messages"] == [{"role": "user", "content": "Hello"}]

    def test_append_assistant_message(self) -> None:
        """Add assistant response to messages."""
        from tools.handlers import append_assistant_message

        state = {"response": "Hi there!", "messages": []}
        result = append_assistant_message(state)

        assert result["messages"] == [{"role": "assistant", "content": "Hi there!"}]


class TestPruneMessages:
    """Test message pruning for context limits."""

    def test_prune_under_limit(self) -> None:
        """Don't prune if under limit."""
        from tools.handlers import prune_messages

        messages = [{"role": "user", "content": f"msg{i}"} for i in range(5)]
        state = {"messages": messages}
        result = prune_messages(state, max_messages=20)

        assert len(result["messages"]) == 5

    def test_prune_over_limit(self) -> None:
        """Prune keeps first 2 + most recent."""
        from tools.handlers import prune_messages

        messages = [{"role": "user", "content": f"msg{i}"} for i in range(25)]
        state = {"messages": messages}
        result = prune_messages(state, max_messages=10)

        assert len(result["messages"]) == 10
        # First 2 preserved
        assert result["messages"][0]["content"] == "msg0"
        assert result["messages"][1]["content"] == "msg1"
        # Most recent preserved
        assert result["messages"][-1]["content"] == "msg24"


class TestDetectGaps:
    """Test gap detection for missing required fields."""

    def test_all_fields_present(self) -> None:
        """No gaps when all required fields have values."""
        from tools.handlers import detect_gaps

        schema = {
            "fields": [
                {"id": "title", "required": True},
                {"id": "priority", "required": True},
            ]
        }
        extracted = {"title": "My Feature", "priority": "high"}
        state = {"schema": schema, "extracted": extracted, "probe_count": 0}

        result = detect_gaps(state)

        assert result["gaps"] == []
        assert result["has_gaps"] is False
        assert result["probe_count"] == 1

    def test_missing_required_field(self) -> None:
        """Detect missing required field."""
        from tools.handlers import detect_gaps

        schema = {
            "fields": [
                {"id": "title", "required": True},
                {"id": "priority", "required": True},
            ]
        }
        extracted = {"title": "My Feature"}
        state = {"schema": schema, "extracted": extracted, "probe_count": 0}

        result = detect_gaps(state)

        assert result["gaps"] == ["priority"]
        assert result["has_gaps"] is True

    def test_empty_string_counts_as_missing(self) -> None:
        """Empty string is treated as missing."""
        from tools.handlers import detect_gaps

        schema = {"fields": [{"id": "title", "required": True}]}
        extracted = {"title": ""}
        state = {"schema": schema, "extracted": extracted, "probe_count": 0}

        result = detect_gaps(state)

        assert result["gaps"] == ["title"]
        assert result["has_gaps"] is True

    def test_optional_fields_ignored(self) -> None:
        """Optional fields don't create gaps."""
        from tools.handlers import detect_gaps

        schema = {
            "fields": [
                {"id": "title", "required": True},
                {"id": "notes", "required": False},
            ]
        }
        extracted = {"title": "My Feature"}
        state = {"schema": schema, "extracted": extracted, "probe_count": 0}

        result = detect_gaps(state)

        assert result["gaps"] == []
        assert result["has_gaps"] is False

    def test_probe_count_increments(self) -> None:
        """Probe count increments each call."""
        from tools.handlers import detect_gaps

        schema = {"fields": []}
        state = {"schema": schema, "extracted": {}, "probe_count": 5}

        result = detect_gaps(state)

        assert result["probe_count"] == 6


class TestApplyCorrections:
    """Test correction merging from recap."""

    def test_apply_corrections(self) -> None:
        """Merge corrections into extracted data."""
        from tools.handlers import apply_corrections

        state = {
            "extracted": {"title": "Old Title", "priority": "low"},
            "recap_action": {"corrections": {"title": "New Title"}},
            "correction_count": 0,
        }

        result = apply_corrections(state)

        assert result["extracted"]["title"] == "New Title"
        assert result["extracted"]["priority"] == "low"  # Unchanged
        assert result["correction_count"] == 1

    def test_apply_corrections_ignores_none(self) -> None:
        """None values in corrections are ignored."""
        from tools.handlers import apply_corrections

        state = {
            "extracted": {"title": "Keep This"},
            "recap_action": {"corrections": {"title": None}},
            "correction_count": 0,
        }

        result = apply_corrections(state)

        assert result["extracted"]["title"] == "Keep This"


class TestStoreRecapSummary:
    """Test recap summary storage."""

    def test_store_recap_summary(self) -> None:
        """Store response as recap_summary."""
        from tools.handlers import store_recap_summary

        state = {"response": "Here is your summary..."}
        result = store_recap_summary(state)

        assert result["recap_summary"] == "Here is your summary..."


class TestSaveToFile:
    """Test file saving."""

    def test_save_creates_file(self, tmp_path: Path, monkeypatch) -> None:
        """Save creates markdown file in outputs directory."""
        from tools.handlers import save_to_file

        # Change CWD to tmp_path
        monkeypatch.chdir(tmp_path)

        state = {
            "extracted": {
                "title": "Test Feature",
                "priority": "high",
                "summary": "A test summary",
                "problem": "The problem",
                "proposed_solution": "The solution",
            },
            "analysis": {
                "analysis": "Good request",
                "strengths": ["Clear"],
                "concerns": ["None"],
                "recommendation": "proceed",
            },
        }

        result = save_to_file(state)

        assert result["complete"] is True
        assert "outputs" in result["output_path"]
        assert Path(result["output_path"]).exists()

        content = Path(result["output_path"]).read_text()
        assert "# Feature Request: Test Feature" in content
        assert "**Priority:** HIGH" in content

    def test_save_slugifies_title(self, tmp_path: Path, monkeypatch) -> None:
        """Title is slugified for filename."""
        from tools.handlers import save_to_file

        monkeypatch.chdir(tmp_path)

        state = {
            "extracted": {"title": "Add Special! @#$ Characters"},
            "analysis": {},
        }

        result = save_to_file(state)

        # Should have slugified filename (special chars become dashes)
        assert "add-special" in result["output_path"]
        assert "characters" in result["output_path"]
