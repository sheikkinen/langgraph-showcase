"""Tests for impl-agent discovery schemas."""

import pytest
from pydantic import ValidationError

from yamlgraph.models.impl_agent_schemas import (
    DiscoveryFindings,
    DiscoveryPlan,
    DiscoveryResult,
    DiscoveryTask,
)


class TestDiscoveryTask:
    """Tests for DiscoveryTask model."""

    def test_valid_task(self):
        """Create a valid discovery task."""
        task = DiscoveryTask(
            id=1,
            task="Find websearch function",
            tool="get_structure",
            args={"file_path": "yamlgraph/tools/websearch.py"},
            rationale="Need to locate the target function",
        )
        assert task.id == 1
        assert task.tool == "get_structure"
        assert task.status == "pending"  # default
        assert task.priority == 1  # default

    def test_task_with_all_fields(self):
        """Create task with explicit status and priority."""
        task = DiscoveryTask(
            id=2,
            task="Find callers",
            tool="get_callers",
            args={"function_name": "websearch"},
            rationale="Identify dependencies",
            status="done",
            priority=2,
        )
        assert task.status == "done"
        assert task.priority == 2

    def test_invalid_status(self):
        """Reject invalid status values."""
        with pytest.raises(ValidationError):
            DiscoveryTask(
                id=1,
                task="Test",
                tool="test_tool",
                args={},
                rationale="Test",
                status="invalid_status",
            )

    def test_missing_required_fields(self):
        """Require all mandatory fields."""
        with pytest.raises(ValidationError):
            DiscoveryTask(id=1, task="Test")  # missing tool, args, rationale


class TestDiscoveryResult:
    """Tests for DiscoveryResult model."""

    def test_successful_result(self):
        """Create a successful discovery result."""
        result = DiscoveryResult(
            task_id=1,
            tool="get_structure",
            success=True,
            result={"classes": [], "functions": ["websearch"]},
        )
        assert result.success is True
        assert result.error is None

    def test_failed_result(self):
        """Create a failed discovery result."""
        result = DiscoveryResult(
            task_id=2,
            tool="get_callers",
            success=False,
            result=None,
            error="Function not found",
        )
        assert result.success is False
        assert result.error == "Function not found"

    def test_result_serialization(self):
        """Result can be serialized to dict."""
        result = DiscoveryResult(
            task_id=1,
            tool="find_tests",
            success=True,
            result=["test_websearch.py"],
        )
        data = result.model_dump()
        assert data["task_id"] == 1
        assert data["result"] == ["test_websearch.py"]


class TestDiscoveryPlan:
    """Tests for DiscoveryPlan model."""

    def test_plan_with_multiple_tasks(self):
        """Create a plan with multiple tasks."""
        plan = DiscoveryPlan(
            tasks=[
                DiscoveryTask(
                    id=1,
                    task="Find target",
                    tool="get_structure",
                    args={"file_path": "test.py"},
                    rationale="Locate code",
                ),
                DiscoveryTask(
                    id=2,
                    task="Find callers",
                    tool="get_callers",
                    args={"function_name": "test"},
                    rationale="Find dependencies",
                    priority=2,
                ),
            ]
        )
        assert len(plan.tasks) == 2
        assert plan.tasks[0].priority == 1
        assert plan.tasks[1].priority == 2

    def test_empty_plan(self):
        """Allow empty task list."""
        plan = DiscoveryPlan(tasks=[])
        assert len(plan.tasks) == 0

    def test_plan_serialization(self):
        """Plan can be serialized to dict."""
        plan = DiscoveryPlan(
            tasks=[
                DiscoveryTask(
                    id=1,
                    task="Test",
                    tool="test",
                    args={},
                    rationale="Test",
                )
            ]
        )
        data = plan.model_dump()
        assert "tasks" in data
        assert len(data["tasks"]) == 1


class TestDiscoveryFindings:
    """Tests for DiscoveryFindings model."""

    def test_findings_with_results(self):
        """Create findings with multiple results."""
        findings = DiscoveryFindings(
            results=[
                DiscoveryResult(
                    task_id=1,
                    tool="get_structure",
                    success=True,
                    result={"functions": ["foo"]},
                ),
                DiscoveryResult(
                    task_id=2,
                    tool="get_callers",
                    success=False,
                    result=None,
                    error="Not found",
                ),
            ]
        )
        assert len(findings.results) == 2
        assert findings.results[0].success is True
        assert findings.results[1].success is False

    def test_empty_findings(self):
        """Allow empty results."""
        findings = DiscoveryFindings(results=[])
        assert len(findings.results) == 0

    def test_findings_serialization(self):
        """Findings can be serialized to dict."""
        findings = DiscoveryFindings(
            results=[
                DiscoveryResult(task_id=1, tool="test", success=True, result="data")
            ]
        )
        data = findings.model_dump()
        assert "results" in data
        assert data["results"][0]["success"] is True
