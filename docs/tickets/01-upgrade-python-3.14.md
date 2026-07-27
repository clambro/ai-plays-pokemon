# Prerequisite Ticket: Upgrade to Python 3.14

## Outcome

Move the clean P0 baseline to standard GIL-enabled CPython 3.14, update PyBoy
to 2.6.1, adopt the useful modern typing syntax, and leave every quality gate
green before v2 feature work begins.

**Priority:** P1  
**Depends on:** [`00-modernize-project-foundation.md`](00-modernize-project-foundation.md)  
**Blocks:** Every v2 feature ticket

## Scope

- Change the project requirement to `>=3.14,<3.15`.
- Update uv, Ruff, ty, pre-commit, README, and `AGENTS.md` to agree on Python
  3.14.
- Target `py314` in Ruff.
- Update PyBoy from 2.6.0 to exactly 2.6.1 and keep the declared range below
  2.7.
- Re-resolve the P0 dependency set for Python 3.14.
- Audit runtime annotation consumers under Python 3.14's deferred annotation
  semantics, especially Pydantic, structured LLM schemas, Junjo, and
  SQLAlchemy.
- Remove unnecessary quoted forward references.
- Replace legacy `TypeVar` and assignment-style type aliases where Python
  3.14 syntax is clearer.
- Keep `TypeGuard` or use `TypeIs` according to actual narrowing semantics,
  not as a mechanical modernization.
- Regenerate fresh v2 emulator fixtures under Python 3.14/PyBoy 2.6.1.
- Run the full validation suite without external model calls.

## Key Decisions

The sibling `pokemon-speedrun-optimizer` already establishes the intended
version boundary:

```toml
requires-python = ">=3.14,<3.15"
pyboy = ">=2.6.1,<2.7"

[tool.ruff]
target-version = "py314"
```

Use standard CPython, not the free-threaded `3.14t` build. Do not move to
PyBoy 2.7 or select a later 2.6 patch implicitly.

Python 3.14 provides native deferred annotations. Do not add
`from __future__ import annotations` across the repository or preserve older
typing spellings for an interpreter the project no longer supports.

Modernize types only where readability improves. Framework-specific fixes must
remain narrowly scoped; removing Junjo or redesigning models belongs to their
own tickets.

## Out of Scope

- Free-threaded Python, subinterpreters, template strings, and unrelated 3.14
  features.
- Provider, telemetry, memory, or orchestration redesign.
- PyBoy 2.7 or later.
- Live model calls or the autonomous gameplay loop.

## Acceptance Criteria

- [ ] Project metadata and the lock target Python `>=3.14,<3.15`.
- [ ] Ruff targets `py314`; ty and developer docs agree on Python 3.14.
- [ ] PyBoy resolves exactly to 2.6.1 with the declared range below 2.7.
- [ ] All dependencies install from the locked environment.
- [ ] Pydantic, structured-output schemas, Junjo, SQLAlchemy, and other runtime
      annotation consumers work under deferred annotations.
- [ ] Unnecessary quoted references, the legacy Pydantic model `TypeVar`, and
      genuine type aliases use appropriate modern syntax.
- [ ] Narrowing helpers retain correct behavior.
- [ ] No blanket future-annotations import or broad checker suppression is
      introduced.
- [ ] Fresh v2 emulator states and backup round trips pass.
- [ ] Ruff, ty, pre-commit, and the complete automated suite pass without live
      external effects.

## References

- [What's New in Python 3.14](https://docs.python.org/3.14/whatsnew/3.14.html)
- [Porting to Python 3.14](https://docs.python.org/3.14/whatsnew/3.14.html#porting-to-python-3-14)
- [PEP 649](https://peps.python.org/pep-0649/)
- [PEP 749](https://peps.python.org/pep-0749/)
- [`annotationlib`](https://docs.python.org/3.14/library/annotationlib.html)

