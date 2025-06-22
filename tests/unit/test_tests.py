"""Meta-test file to ensure that all tests have the correct markers and are in the right folders."""

import ast
from pathlib import Path
from typing import Any, TypeGuard

import pytest
from pydantic import BaseModel


@pytest.fixture(scope="session", autouse=True)
def valid_markers(pytestconfig: pytest.Config) -> set[str]:
    """Retrieve valid markers from pytest.ini."""
    ini_markers = pytestconfig._getini("markers")
    if not isinstance(ini_markers, list) or not all(isinstance(m, str) for m in ini_markers):
        raise ValueError(
            f"Invalid pytest configuration. Markers must be a list of strings. Got: {ini_markers}",
        )
    return {str(marker).split(":")[0].strip() for marker in ini_markers}


@pytest.mark.unit
def test_all_tests_have_marker(valid_markers: set[str]) -> None:
    """Test that all tests in have exactly one marker that matches the test's parent folder."""
    errors = []
    total_tests = 0
    for filepath in Path().glob("**/tests/**/test_*.py"):
        test_functions = _get_test_functions_with_markers(filepath, valid_markers)
        total_tests += len(test_functions)
        for func in test_functions:
            if not func.markers:
                errors.append(f"{filepath}:{func.name} is missing a required pytest marker")
                continue
            if len(func.markers) > 1:
                errors.append(
                    f"{filepath}:{func.name} has multiple pytest markers"
                    f" ({', '.join(func.markers)})",
                )
                continue
            marker = func.markers.pop()
            if marker != func.parent_folder:
                errors.append(
                    f"{filepath}:{func.name} has a marker that does not match its parent"
                    f" folder: ({marker} != {func.parent_folder})",
                )
                continue
    if errors:
        pytest.fail("Errors found in the marker meta-test:\n" + "\n".join(errors))


class _TestFunctionParams(BaseModel):
    """Parameters for a test function."""

    name: str
    markers: set[str]
    parent_folder: str


def _get_test_functions_with_markers(
    filepath: Path,
    valid_markers: set[str],
) -> list[_TestFunctionParams]:
    """Get all test functions and test methods with markers from a file."""
    with filepath.open(encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)

    return [
        _TestFunctionParams(
            name=node.name,
            markers=_extract_markers(node.decorator_list, valid_markers),
            parent_folder=filepath.parent.name,
        )
        for node in tree.body
        if _is_valid_test_function(node)
    ]


def _extract_markers(decorator_list: list[ast.expr], valid_markers: set[str]) -> set[str]:
    """Extract Pytest markers from a list of attributes."""
    markers = set()
    for decorator in decorator_list:
        if (
            isinstance(decorator, ast.Attribute)
            and isinstance(decorator.value, ast.Attribute)
            and decorator.value.attr == "mark"
            and decorator.attr in valid_markers
        ):
            markers.add(decorator.attr)
    return markers


def _is_valid_test_function(node: Any) -> TypeGuard[ast.FunctionDef | ast.AsyncFunctionDef]:  # noqa: ANN401
    """Check if a node is a valid test function."""
    is_function = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    return is_function and node.name.startswith("test_")
