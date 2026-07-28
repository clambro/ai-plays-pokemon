# Development Guide

## Environment and Commands

This project uses Python 3.14 and `uv` for dependency management. Run project
tools through the locked environment:

```bash
uv sync --all-groups
uv run ruff check --fix .
uv run ruff format .
uv run ty check
uv run python -m pytest
uv run python -m pytest path/to/test_file.py
uv run pre-commit run --all-files
```

Run the application with `uv run python -m main`, following the options
documented in the README. Do not start it as a validation step: it launches the
indefinite gameplay loop and may make billable model calls. Emulator smoke tests
must be explicitly bounded.

The project targets standard GIL-enabled Python `>=3.14,<3.15`. PyBoy is pinned
exactly because emulator changes can affect existing save states.

## Quality Rules

- Fix lint and type errors at their source. Add narrow suppressions only for
  unavoidable third-party issues, with a nearby explanation.
- Prefer module-level functions for stateless operations. Do not use classes
  solely to copy one call's arguments onto `self`, expose one public method, or
  namespace static helpers. Keep per-call inputs explicit in function
  signatures, but preserve existing shared service clients at module scope
  instead of threading them through unrelated callers.
- Use classes when state, identity, lifecycle, invariants, polymorphism, or a
  framework contract makes them useful. Test classes may also group a large
  test module when that grouping materially improves comprehension.
- Use Google-style docstrings. Document caller-relevant semantics, mutation,
  side effects, returns, and failures; keep obvious operations concise. Do not
  use Sphinx directives.
- Use Pydantic models at I/O and validation boundaries. Prefer standard-library
  dataclasses for internal structured data.
- Establish the source of truth, ownership, and lifecycle before adding state
  or abstractions. Do not duplicate authoritative data for a view, put loading
  or presentation policy in domain records, or let cached state become another
  authority; keep persistence and workflow transitions in the coordinating
  service.
- Tests must protect externally observable behavior or stable domain rules and
  survive internal refactors that preserve that behavior. Do not add tests that
  merely mirror implementation details such as private helpers, internal call
  sequences, exact wiring, or timing constants. Prefer real integration
  coverage for component interactions and focused unit tests for substantive
  pure algorithms. Repository policy tests are appropriate when they
  deliberately enforce a project convention.
- Keep changes focused and preserve unrelated worktree changes.

## Repository Layout

- `agent/`: the current Junjo workflow, nodes, and overworld/text/battle
  subflows.
- `emulator/`: PyBoy lifecycle, game-state snapshots, and ROM-memory parsers.
- `overworld_map/`: explored-map state, persistence integration, and prompt
  formatting.
- `memory/`: goals, rolling-memory compaction, and long-term memory behavior.
- `database/`: SQLite models and repositories.
- `llm/`: model definitions and provider access.
- `streaming/`: the HTML background server and view models.
- `common/`: shared settings, enums, schemas, constants, and utilities.
- `docs/`: current design documentation and the ordered v2 tickets.

## ROMs, Fixtures, and External Effects

ROMs are proprietary local inputs and must never be committed. The default ROM
is expected at `resources/ylegacy.gbc`; distributable repository changes use a
patch plus hashes and application instructions, not a ROM image.

Save states, RAM saves, backups, databases, output folders, generated game
assets, `.env` files, and credentials are also local artifacts. Do not add them
to Git, copy them into tracked paths, or overwrite them casually. Some
integration tests depend on ignored emulator fixtures that are not present in a
fresh clone.

Do not make live model calls, send telemetry, access paid services, or contact
other external systems during validation unless the task explicitly requires
it. Never expose API keys or runtime data in logs, patches, or tool output.

## Workflow

Read the relevant implementation, tests, documentation, and ticket before
editing. Use the smallest meaningful validation for the change, then run the
full static and test suite when the task reaches that stage. The complete suite
must avoid live model calls and the indefinite gameplay loop.

Do not commit, push, create pull requests, or alter branches unless the user
explicitly asks. Before any requested commit, inspect the staged diff and keep
unrelated user changes out of it.
