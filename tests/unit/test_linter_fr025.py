"""FR-025: Linter cross-reference & semantic checks.

TDD Red-Green-Refactor.
Dual-sided fixture-based tests: each check gets _pass.yaml and _fail.yaml.
"""

from pathlib import Path

import pytest

from yamlgraph.linter import lint_graph
from yamlgraph.linter.checks_semantic import (
    check_cross_references,
    check_edge_types,
    check_error_handling,
    check_expression_syntax,
    check_passthrough_nodes,
    check_tool_call_nodes,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "linter"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def issue_codes(issues):
    """Extract issue codes from a list of LintIssue."""
    return [i.code for i in issues]


def lint_codes(path: Path) -> list[str]:
    """Lint a fixture file, return issue codes."""
    result = lint_graph(path, project_root=path.parent)
    return issue_codes(result.issues)


# ===========================================================================
# Phase 1 — Cross-reference checks (E006, E008)
# ===========================================================================


class TestCheckCrossReferences:
    """Edge from/to and loop_limits reference existing nodes."""

    # --- E006: edge endpoints ---

    @pytest.mark.req("REQ-YG-053")
    def test_edge_refs_pass(self):
        """All edge from/to targets reference real nodes — no issue."""
        issues = check_cross_references(FIXTURES / "edge_refs_pass.yaml")
        codes = issue_codes(issues)
        assert "E006" not in codes

    @pytest.mark.req("REQ-YG-053")
    def test_edge_refs_fail(self):
        """Edge 'from' references typo node 'genrate' — E006 raised."""
        issues = check_cross_references(FIXTURES / "edge_refs_fail.yaml")
        codes = issue_codes(issues)
        assert "E006" in codes
        e006 = [i for i in issues if i.code == "E006"]
        assert any("genrate" in i.message for i in e006)

    # --- E008: loop_limits keys ---

    @pytest.mark.req("REQ-YG-053")
    def test_loop_limits_pass(self):
        """loop_limits keys match real nodes — no issue."""
        issues = check_cross_references(FIXTURES / "loop_limits_pass.yaml")
        codes = issue_codes(issues)
        assert "E008" not in codes

    @pytest.mark.req("REQ-YG-053")
    def test_loop_limits_fail(self):
        """loop_limits references 'critiqu' — E008 raised."""
        issues = check_cross_references(FIXTURES / "loop_limits_fail.yaml")
        codes = issue_codes(issues)
        assert "E008" in codes
        e008 = [i for i in issues if i.code == "E008"]
        assert any("critiqu" in i.message for i in e008)


# ===========================================================================
# Phase 2 — Passthrough & tool_call node checks (E601, E701, E702)
# ===========================================================================


class TestCheckPassthroughNodes:
    """Passthrough node must have output field."""

    @pytest.mark.req("REQ-YG-053")
    def test_passthrough_pass(self):
        """Passthrough with output field — no issue."""
        issues = check_passthrough_nodes(FIXTURES / "passthrough_pass.yaml")
        codes = issue_codes(issues)
        assert "E601" not in codes

    @pytest.mark.req("REQ-YG-053")
    def test_passthrough_fail(self):
        """Passthrough without output — E601 raised."""
        issues = check_passthrough_nodes(FIXTURES / "passthrough_fail.yaml")
        codes = issue_codes(issues)
        assert "E601" in codes
        e601 = [i for i in issues if i.code == "E601"]
        assert any("transform" in i.message for i in e601)


class TestCheckToolCallNodes:
    """tool_call node must have tool and args fields."""

    @pytest.mark.req("REQ-YG-053")
    def test_tool_call_pass(self):
        """tool_call with tool + args — no issue."""
        issues = check_tool_call_nodes(FIXTURES / "tool_call_pass.yaml")
        codes = issue_codes(issues)
        assert "E701" not in codes
        assert "E702" not in codes

    @pytest.mark.req("REQ-YG-053")
    def test_tool_call_fail_missing_tool(self):
        """tool_call without tool — E701 raised."""
        issues = check_tool_call_nodes(FIXTURES / "tool_call_fail.yaml")
        codes = issue_codes(issues)
        assert "E701" in codes

    @pytest.mark.req("REQ-YG-053")
    def test_tool_call_fail_missing_args(self):
        """tool_call without args — E702 raised."""
        issues = check_tool_call_nodes(FIXTURES / "tool_call_fail.yaml")
        codes = issue_codes(issues)
        assert "E702" in codes


# ===========================================================================
# Phase 3 — Expression syntax checks (W801, W007)
# ===========================================================================


class TestCheckExpressionSyntax:
    """Validate condition/variable expression syntax."""

    # --- W801: condition with braces ---

    @pytest.mark.req("REQ-YG-053")
    def test_condition_syntax_pass(self):
        """Bare-name condition — no issue."""
        issues = check_expression_syntax(FIXTURES / "condition_syntax_pass.yaml")
        codes = issue_codes(issues)
        assert "W801" not in codes

    @pytest.mark.req("REQ-YG-053")
    def test_condition_syntax_fail(self):
        """Condition uses {state.score} — W801 raised."""
        issues = check_expression_syntax(FIXTURES / "condition_syntax_fail.yaml")
        codes = issue_codes(issues)
        assert "W801" in codes

    # --- W007: variable missing state. prefix ---

    @pytest.mark.req("REQ-YG-053")
    def test_variable_expr_pass(self):
        """{state.name} in variable — no issue."""
        issues = check_expression_syntax(FIXTURES / "variable_expr_pass.yaml")
        codes = issue_codes(issues)
        assert "W007" not in codes

    @pytest.mark.req("REQ-YG-053")
    def test_variable_expr_fail(self):
        """{name} without state. prefix — W007 raised."""
        issues = check_expression_syntax(FIXTURES / "variable_expr_fail.yaml")
        codes = issue_codes(issues)
        assert "W007" in codes

    # --- W014: {state.X} references undeclared field ---

    @pytest.mark.req("REQ-YG-069")
    def test_state_ref_undeclared_pass(self):
        """All {state.X} refs resolve to known fields — no W014."""
        issues = check_expression_syntax(FIXTURES / "state_ref_undeclared_pass.yaml")
        codes = issue_codes(issues)
        assert "W014" not in codes

    @pytest.mark.req("REQ-YG-069")
    def test_state_ref_undeclared_fail(self):
        """{state.unknown_field} not in known state — W014 raised."""
        issues = check_expression_syntax(FIXTURES / "state_ref_undeclared_fail.yaml")
        codes = issue_codes(issues)
        assert "W014" in codes
        w014 = [i for i in issues if i.code == "W014"]
        assert any("unknown_field" in i.message for i in w014)


# ===========================================================================
# Phase 4 — Error handling & edge type checks (E010, E802)
# ===========================================================================


class TestCheckErrorHandling:
    """on_error: fallback must have fallback config."""

    @pytest.mark.req("REQ-YG-053")
    def test_fallback_pass(self):
        """fallback with config — no issue."""
        issues = check_error_handling(FIXTURES / "fallback_pass.yaml")
        codes = issue_codes(issues)
        assert "E010" not in codes

    @pytest.mark.req("REQ-YG-053")
    def test_fallback_fail(self):
        """fallback without config — E010 raised."""
        issues = check_error_handling(FIXTURES / "fallback_fail.yaml")
        codes = issue_codes(issues)
        assert "E010" in codes
        e010 = [i for i in issues if i.code == "E010"]
        assert any("generate" in i.message for i in e010)


class TestCheckEdgeTypes:
    """Conditional edges must have list 'to'."""

    @pytest.mark.req("REQ-YG-053")
    def test_conditional_edge_pass(self):
        """Conditional edge with list to — no issue."""
        issues = check_edge_types(FIXTURES / "conditional_edge_pass.yaml")
        codes = issue_codes(issues)
        assert "E802" not in codes

    @pytest.mark.req("REQ-YG-053")
    def test_conditional_edge_fail(self):
        """Conditional edge with string to — E802 raised."""
        issues = check_edge_types(FIXTURES / "conditional_edge_fail.yaml")
        codes = issue_codes(issues)
        assert "E802" in codes


# ===========================================================================
# Integration: full lint_graph picks up new checks
# ===========================================================================


class TestLintGraphIntegration:
    """Verify lint_graph orchestrator runs all new checks."""

    @pytest.mark.req("REQ-YG-053")
    def test_integration_edge_refs_fail(self):
        """lint_graph catches E006 from fixture."""
        codes = lint_codes(FIXTURES / "edge_refs_fail.yaml")
        assert "E006" in codes

    @pytest.mark.req("REQ-YG-053")
    def test_integration_loop_limits_fail(self):
        """lint_graph catches E008 from fixture."""
        codes = lint_codes(FIXTURES / "loop_limits_fail.yaml")
        assert "E008" in codes

    @pytest.mark.req("REQ-YG-053")
    def test_integration_passthrough_fail(self):
        """lint_graph catches E601 from fixture."""
        codes = lint_codes(FIXTURES / "passthrough_fail.yaml")
        assert "E601" in codes

    @pytest.mark.req("REQ-YG-053")
    def test_integration_tool_call_fail(self):
        """lint_graph catches E701 and E702."""
        codes = lint_codes(FIXTURES / "tool_call_fail.yaml")
        assert "E701" in codes
        assert "E702" in codes

    @pytest.mark.req("REQ-YG-053")
    def test_integration_condition_syntax_fail(self):
        """lint_graph catches W801."""
        codes = lint_codes(FIXTURES / "condition_syntax_fail.yaml")
        assert "W801" in codes

    @pytest.mark.req("REQ-YG-053")
    def test_integration_variable_expr_fail(self):
        """lint_graph catches W007."""
        codes = lint_codes(FIXTURES / "variable_expr_fail.yaml")
        assert "W007" in codes

    @pytest.mark.req("REQ-YG-053")
    def test_integration_fallback_fail(self):
        """lint_graph catches E010."""
        codes = lint_codes(FIXTURES / "fallback_fail.yaml")
        assert "E010" in codes

    @pytest.mark.req("REQ-YG-053")
    def test_integration_conditional_edge_fail(self):
        """lint_graph catches E802."""
        codes = lint_codes(FIXTURES / "conditional_edge_fail.yaml")
        assert "E802" in codes

    @pytest.mark.req("REQ-YG-053")
    def test_integration_all_pass_fixtures_clean(self):
        """All _pass fixtures produce no errors from new checks."""
        pass_fixtures = sorted(FIXTURES.glob("*_pass.yaml"))
        assert (
            len(pass_fixtures) == 11
        ), f"Expected 11 pass fixtures, got {len(pass_fixtures)}"
        new_codes = {
            "E006",
            "E008",
            "E601",
            "E701",
            "E702",
            "W801",
            "W007",
            "W014",
            "E010",
            "E011",
            "E802",
            "W012",
        }
        for fixture in pass_fixtures:
            codes = lint_codes(fixture)
            overlap = new_codes & set(codes)
            assert not overlap, f"{fixture.name} unexpectedly raised {overlap}"
