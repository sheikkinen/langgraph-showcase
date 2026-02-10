"""Tests for Phase 6.5: Generic Report Schema.

Tests for flexible GenericReport model that works for most analysis/summary tasks.
"""

import pytest
from pydantic import ValidationError


class TestGenericReportSchema:
    """Tests for GenericReport model."""

    @pytest.mark.req("REQ-YG-030")
    def test_generic_report_exists(self):
        """GenericReport model is importable."""
        from yamlgraph.models.schemas import GenericReport

        assert GenericReport is not None

    @pytest.mark.req("REQ-YG-030")
    def test_minimal_report(self):
        """Report works with just title and summary."""
        from yamlgraph.models.schemas import GenericReport

        report = GenericReport(
            title="Test Report",
            summary="A brief summary of findings.",
        )

        assert report.title == "Test Report"
        assert report.summary == "A brief summary of findings."

    @pytest.mark.req("REQ-YG-030")
    def test_report_with_sections(self):
        """Sections field accepts arbitrary dict content."""
        from yamlgraph.models.schemas import GenericReport

        report = GenericReport(
            title="Report",
            summary="Summary",
            sections={
                "overview": "First section content",
                "details": {"nested": "data", "count": 42},
                "items": ["a", "b", "c"],
            },
        )

        assert report.sections["overview"] == "First section content"
        assert report.sections["details"]["count"] == 42
        assert len(report.sections["items"]) == 3

    @pytest.mark.req("REQ-YG-030")
    def test_report_with_findings(self):
        """Findings field is list of strings."""
        from yamlgraph.models.schemas import GenericReport

        report = GenericReport(
            title="Report",
            summary="Summary",
            findings=["Finding 1", "Finding 2", "Finding 3"],
        )

        assert len(report.findings) == 3
        assert "Finding 1" in report.findings

    @pytest.mark.req("REQ-YG-030")
    def test_report_with_recommendations(self):
        """Recommendations field is list of strings."""
        from yamlgraph.models.schemas import GenericReport

        report = GenericReport(
            title="Report",
            summary="Summary",
            recommendations=["Action 1", "Action 2"],
        )

        assert len(report.recommendations) == 2

    @pytest.mark.req("REQ-YG-030")
    def test_report_with_metadata(self):
        """Metadata field accepts arbitrary key-value data."""
        from yamlgraph.models.schemas import GenericReport

        report = GenericReport(
            title="Report",
            summary="Summary",
            metadata={
                "author": "Test Author",
                "version": 1.0,
                "tags": ["a", "b"],
            },
        )

        assert report.metadata["author"] == "Test Author"
        assert report.metadata["version"] == 1.0

    @pytest.mark.req("REQ-YG-030")
    def test_defaults_are_empty(self):
        """Optional fields default to empty collections."""
        from yamlgraph.models.schemas import GenericReport

        report = GenericReport(title="Report", summary="Summary")

        assert report.sections == {}
        assert report.findings == []
        assert report.recommendations == []
        assert report.metadata == {}

    @pytest.mark.req("REQ-YG-030")
    def test_title_is_required(self):
        """Title field is required."""
        from yamlgraph.models.schemas import GenericReport

        with pytest.raises(ValidationError) as exc_info:
            GenericReport(summary="Summary")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("title",) for e in errors)

    @pytest.mark.req("REQ-YG-030")
    def test_summary_is_required(self):
        """Summary field is required."""
        from yamlgraph.models.schemas import GenericReport

        with pytest.raises(ValidationError) as exc_info:
            GenericReport(title="Title")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("summary",) for e in errors)

    @pytest.mark.req("REQ-YG-030")
    def test_model_serializes_to_dict(self):
        """Report serializes to dictionary."""
        from yamlgraph.models.schemas import GenericReport

        report = GenericReport(
            title="Test",
            summary="Summary",
            findings=["A", "B"],
        )

        data = report.model_dump()

        assert data["title"] == "Test"
        assert data["summary"] == "Summary"
        assert data["findings"] == ["A", "B"]

    @pytest.mark.req("REQ-YG-030")
    def test_model_serializes_to_json(self):
        """Report serializes to JSON string."""
        import json

        from yamlgraph.models.schemas import GenericReport

        report = GenericReport(title="Test", summary="Summary")

        json_str = report.model_dump_json()
        data = json.loads(json_str)

        assert data["title"] == "Test"


class TestGenericReportUseCases:
    """Verify GenericReport works for common analysis patterns."""

    @pytest.mark.req("REQ-YG-030")
    def test_git_analysis_report(self):
        """GenericReport works for git analysis output."""
        from yamlgraph.models.schemas import GenericReport

        report = GenericReport(
            title="Git Repository Analysis",
            summary="Analysis of recent activity in the repository.",
            sections={
                "commit_summary": "15 commits in last 7 days",
                "authors": ["alice", "bob", "carol"],
            },
            findings=[
                "High activity in src/core module",
                "No tests for new features",
                "Breaking changes in v2.0",
            ],
            recommendations=[
                "Add tests for recent changes",
                "Review breaking changes before release",
            ],
            metadata={
                "repo": "langgraph-showcase",
                "analyzed_at": "2024-01-01T00:00:00",
            },
        )

        assert "Git Repository" in report.title
        assert len(report.findings) == 3
        assert report.metadata["repo"] == "langgraph-showcase"

    @pytest.mark.req("REQ-YG-030")
    def test_api_analysis_report(self):
        """GenericReport works for API analysis output."""
        from yamlgraph.models.schemas import GenericReport

        report = GenericReport(
            title="API Performance Report",
            summary="Performance analysis of API endpoints.",
            sections={
                "latency": {"p50": 45, "p95": 120, "p99": 250},
                "errors": {"rate": 0.02, "top_errors": ["500", "429"]},
            },
            findings=["High latency on /search endpoint"],
            recommendations=["Add caching for /search"],
        )

        assert report.sections["latency"]["p95"] == 120
