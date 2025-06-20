import sys
from importlib.metadata import version
from pathlib import Path

import yaml
from loguru import logger


def main() -> None:
    """
    Check that the installed Ruff version matches the pre-commit Ruff version. Ignore the patch
    version. Only the major and minor versions matter for compatibility.
    """
    installed = version("ruff")
    installed = ".".join(installed.split(".")[:2])
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


def _get_precommit_ruff_version() -> str:
    with Path(".pre-commit-config.yaml").open() as f:
        config = yaml.safe_load(f)

    for repo in config["repos"]:
        if repo["repo"] == "https://github.com/astral-sh/ruff-pre-commit":
            version = repo["rev"].lstrip("v")
            return ".".join(version.split(".")[:2])

    logger.error("Error: Could not find Ruff in pre-commit config")
    sys.exit(1)


if __name__ == "__main__":
    main()
