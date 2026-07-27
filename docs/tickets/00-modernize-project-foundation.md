# Prerequisite Ticket: Modernize the Project Foundation

## Outcome

Establish a clean Python 3.13 baseline for v2 before any behavioral work. The
repository should have current quality tooling, current dependencies except
PyBoy, a reproducible default ROM patch, a useful root `AGENTS.md`, and a fully
green validation suite.

**Priority:** P0

**Blocks:** Every other v2 implementation ticket

## Scope

- Preserve the existing unstaged change lowering Ruff's McCabe limit from 20
  to 10.
- Refactor every resulting `C901` violation; do not suppress or weaken the
  limit.
- Update Ruff to the latest Python-3.13-compatible release and fix the newly
  reported issues.
- Add ty, configure it for the whole first-party project, and fix its
  diagnostics with narrow exceptions only.
- Replace the stale pre-commit configuration with the modern baseline from
  `../pokemon-speedrun-optimizer`, adapted to this repository.
- Make the uv lock the single source of Ruff, ty, and pre-commit tool versions.
- Update every direct and transitive dependency to its latest selected
  Python-3.13-compatible release except PyBoy.
- Pin PyBoy exactly to 2.6.0 in this ticket. The Python 3.14 prerequisite owns
  the coordinated update to PyBoy 2.6.1.
- Replace the default Yellow Legacy ROM with the maintainer's personal
  bug-fixed build through a distributable patch.
- Add a root `AGENTS.md`.
- Create fresh v2 emulator and backup fixtures where the test suite requires
  them.
- Run all static checks, tests, ROM verification, and bounded emulator smoke
  tests.

## Key Decisions

### Tooling

Use uv-backed local pre-commit hooks for project tools so local commands,
pre-commit, and the lockfile cannot drift. Reuse the sibling project's generic
file-hygiene coverage, including merge-conflict, syntax, private-key,
line-ending, large-file, and protected-branch checks, without copying its
project-specific rules.

Declare `pytest` and ty directly. Replace the `dotenv` wrapper with
`python-dotenv` because that is the package the source imports. Remove the
Poetry-based Ruff version-check script.

### Dependency boundary

P0 deliberately ends on:

- Python `>=3.13,<3.14`;
- Ruff targeting `py313`; and
- PyBoy exactly 2.6.0.

Review direct dependency caps before refreshing the lock so “update all”
actually selects current releases. Record any package that cannot use its
latest Python-3.13-compatible version and the concrete conflict.

### ROM distribution

Do not commit a ROM. Track a BPS patch outside the ignored `resources/`
directory, plus documentation containing:

- the exact base release/build;
- base and target sizes and SHA-256 hashes;
- patch tool and application command; and
- the expected output path, normally `resources/ylegacy.gbc`.

Applying the patch to the documented base must reproduce the personal target
byte-for-byte. The application should detect a missing or incorrect default ROM
and provide a useful setup error. Deliberate custom `--rom-path` use should
remain supported under a documented policy.

### `AGENTS.md`

Document:

- the uv, Ruff, ty, pytest, and pre-commit commands;
- McCabe 10 and the no-broad-suppressions policy;
- repository layout and the role of `resources/pokeyellow`;
- ROM, ignored-fixture, credential, and external-call safety;
- the temporary P0 PyBoy pin;
- the prohibition on starting the indefinite gameplay loop during validation;
  and
- the requirement to preserve unrelated worktree changes.

## Out of Scope

- Python 3.14 and PyBoy 2.6.1.
- Any v2 feature or architecture ticket.
- Junjo removal, telemetry redesign, or memory redesign.
- CI setup.
- Live billable model calls.
- Committing ROMs, emulator states, RAM saves, databases, generated proprietary
  assets, or credentials.

## Acceptance Criteria

- [ ] McCabe complexity 10 is configured and all `C901` violations are fixed.
- [ ] Ruff is current for Python 3.13 and passes formatting and linting.
- [ ] ty is declared, configured, and passes on first-party source and tests.
- [ ] Pre-commit uses the modern adapted baseline and uv-locked project tools.
- [ ] Two consecutive all-files pre-commit runs pass without further edits.
- [ ] PyBoy is exactly 2.6.0; all other dependencies are updated as specified.
- [ ] The lockfile is reproducible and passes its consistency check.
- [ ] The tracked ROM patch reproduces the documented personal target exactly.
- [ ] No ROM or private runtime artifact is tracked.
- [ ] Required v2 emulator fixtures can be recreated from the documented ROM
      and emulator stack.
- [ ] A root `AGENTS.md` and updated README describe the final P0 setup.
- [ ] The complete test suite and bounded emulator/application smoke checks
      pass without live model calls.

## References

- [Ruff documentation](https://docs.astral.sh/ruff/)
- [ty documentation](https://docs.astral.sh/ty/)
- [uv dependency management](https://docs.astral.sh/uv/)
- [pre-commit documentation](https://pre-commit.com/)
- [PyBoy documentation](https://docs.pyboy.dk/)
