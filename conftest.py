"""Enforce unit/integration classification for every collected test."""

import pytest


# Validate before pytest applies its -k/-m selection filters.
@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Require each test's classification marker to match its parent folder."""
    errors = []
    for item in items:
        markers = {mark.name for mark in item.iter_markers()} & {"unit", "integration"}
        if markers != {item.path.parent.name}:
            errors.append(
                f"{item.nodeid}: expected one unit/integration marker matching folder"
                f" {item.path.parent.name!r}, found {sorted(markers)}"
            )
    if errors:
        raise pytest.UsageError("Invalid test classification:\n" + "\n".join(errors))
