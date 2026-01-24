"""Pytest configuration for e2e tests."""

import pytest


def pytest_configure(config):
    """Register e2e marker."""
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end (deselect with '-m \"not e2e\"')"
    )


def pytest_collection_modifyitems(config, items):
    """Skip e2e tests unless explicitly requested."""
    if config.getoption("-m") and "e2e" in config.getoption("-m"):
        # e2e tests explicitly requested, don't skip
        return

    skip_e2e = pytest.mark.skip(
        reason="E2E tests skipped by default. Run with: pytest -m e2e"
    )
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_e2e)
