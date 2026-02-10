"""Tests for deprecation module.

TDD tests for DeprecationError and deprecation utilities.
"""

import pytest


class TestDeprecationError:
    """Tests for DeprecationError exception."""

    @pytest.mark.req("REQ-YG-034")
    def test_deprecation_error_exists(self):
        """DeprecationError should be importable."""
        from yamlgraph.cli.deprecation import DeprecationError

        assert issubclass(DeprecationError, Exception)

    @pytest.mark.req("REQ-YG-034")
    def test_deprecation_error_message(self):
        """DeprecationError should include replacement command."""
        from yamlgraph.cli.deprecation import DeprecationError

        err = DeprecationError(
            old_command="route",
            new_command="graph run graphs/router-demo.yaml --var message=...",
        )

        assert "route" in str(err)
        assert "graph run" in str(err)
        assert "deprecated" in str(err).lower()

    @pytest.mark.req("REQ-YG-034")
    def test_deprecation_error_has_attributes(self):
        """DeprecationError should expose old and new commands."""
        from yamlgraph.cli.deprecation import DeprecationError

        err = DeprecationError(
            old_command="refine",
            new_command="graph run graphs/reflexion-demo.yaml",
        )

        assert err.old_command == "refine"
        assert err.new_command == "graph run graphs/reflexion-demo.yaml"


class TestDeprecatedCommand:
    """Tests for deprecated_command decorator/helper."""

    @pytest.mark.req("REQ-YG-034")
    def test_deprecated_command_exists(self):
        """deprecated_command should be importable."""
        from yamlgraph.cli.deprecation import deprecated_command

        assert callable(deprecated_command)

    @pytest.mark.req("REQ-YG-034")
    def test_deprecated_command_raises(self):
        """deprecated_command should raise DeprecationError."""
        from yamlgraph.cli.deprecation import DeprecationError, deprecated_command

        with pytest.raises(DeprecationError) as exc_info:
            deprecated_command(
                "route",
                "graph run graphs/router-demo.yaml --var message=...",
            )

        assert "route" in str(exc_info.value)

    @pytest.mark.req("REQ-YG-034")
    def test_deprecated_command_with_mapping(self):
        """deprecated_command should format with variable mapping."""
        from yamlgraph.cli.deprecation import DeprecationError, deprecated_command

        with pytest.raises(DeprecationError) as exc_info:
            deprecated_command(
                "refine --topic X",
                "graph run graphs/reflexion-demo.yaml --var topic=X",
            )

        assert "topic=X" in str(exc_info.value)


class TestCommandMappings:
    """Tests for deprecated command mappings."""

    @pytest.mark.req("REQ-YG-034")
    def test_get_replacement_for_route(self):
        """Should return replacement for route command."""
        from yamlgraph.cli.deprecation import get_replacement_command

        result = get_replacement_command("route", {"message": "hello"})
        assert "graph run" in result
        assert "router-demo.yaml" in result
        assert "message=hello" in result

    @pytest.mark.req("REQ-YG-034")
    def test_get_replacement_for_refine(self):
        """Should return replacement for refine command."""
        from yamlgraph.cli.deprecation import get_replacement_command

        result = get_replacement_command("refine", {"topic": "AI"})
        assert "graph run" in result
        assert "reflexion-demo.yaml" in result
        assert "topic=AI" in result

    @pytest.mark.req("REQ-YG-034")
    def test_get_replacement_unknown_command(self):
        """Unknown command returns None."""
        from yamlgraph.cli.deprecation import get_replacement_command

        result = get_replacement_command("unknown", {})
        assert result is None
