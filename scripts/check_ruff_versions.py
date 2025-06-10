import re
import subprocess
import sys
from pathlib import Path

import yaml
from loguru import logger


def main() -> None:
    """Check that the installed Ruff version matches the pre-commit Ruff version."""
    installed = _get_installed_ruff_version()
    precommit = _get_precommit_ruff_version()

    if installed != precommit:
        logger.error(
            "Ruff versions do not match!",
            installed_version=installed,
            precommit_version=precommit,
        )
        sys.exit(1)

    logger.success(f"Ruff versions match: {installed}")
    sys.exit(0)


def _get_installed_ruff_version() -> str:
    result = subprocess.run(["ruff", "--version"], capture_output=True, text=True, check=False)  # noqa: S603, S607
    if result.returncode != 0:
        logger.error("Error: Could not get installed Ruff version")
        sys.exit(1)
    match = re.search(r"ruff (\d+\.\d+\.\d+)", result.stdout)
    if not match:
        logger.error("Error: Could not parse Ruff version from output")
        sys.exit(1)
    return match.group(1)


def _get_precommit_ruff_version() -> str:
    with Path(".pre-commit-config.yaml").open() as f:
        config = yaml.safe_load(f)

    for repo in config["repos"]:
        if repo["repo"] == "https://github.com/astral-sh/ruff-pre-commit":
            return repo["rev"].lstrip("v")

    logger.error("Error: Could not find Ruff in pre-commit config")
    sys.exit(1)


if __name__ == "__main__":
    main()
