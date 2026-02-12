"""Requirement traceability enforcement.

Every test must be linked to a requirement via @pytest.mark.req("REQ-CALC-XXX").
See docs/RTM-guide.md for the full methodology.
"""

import pytest


def pytest_collection_modifyitems(config, items):
    """Reject tests that lack a @pytest.mark.req marker."""
    missing = [item.nodeid for item in items if "req" not in item.keywords]
    if missing:
        raise pytest.UsageError(
            f"\n{'=' * 60}\n"
            f"REQUIREMENT TRACEABILITY VIOLATION\n"
            f"{'=' * 60}\n"
            f"{len(missing)} test(s) missing @pytest.mark.req:\n\n"
            + "\n".join(f"  - {n}" for n in missing)
            + f"\n\nSee docs/RTM-guide.md\n{'=' * 60}\n"
        )
