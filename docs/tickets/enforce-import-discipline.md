# Ticket: Enforce Package Import Discipline

## Outcome

Give every Python package an explicit public interface and make import paths
communicate package boundaries. This is a structural cleanup and must not
change application behavior.

## Import Rules

- Every importable source directory is a regular package with an
  `__init__.py`.
- Every package `__init__.py` defines `__all__`. Re-export only the names that
  form the package's supported interface; an empty `__all__` is valid.
- Re-exports use relative imports from the package's implementation modules.
- Modules within the same immediate package import each other relatively.
- An import crossing an immediate package boundary must target the other
  package's public namespace rather than one of its implementation modules.
- Standard-library and third-party imports remain absolute.
- `TYPE_CHECKING` imports follow the same boundaries as runtime imports.
- Wildcard imports are never allowed.

For example, a battle tool package may expose `build_fight_tool` from
`fight/__init__.py`. Its `interface.py` may import `.service` directly, while
`tools/registry.py` imports `build_fight_tool` from `.fight`, not
`.fight.interface`.

`__all__` documents the interface but does not enforce it at runtime. Static
checks must reject imports that bypass a package boundary or request a name not
listed by the target package. The check should derive allowed names from
`__all__` rather than maintaining a second allowlist.

## Work

- Add the required package initializers and define the smallest useful public
  surface for each package.
- Convert existing imports to the package-relative and public-boundary rules
  above without moving behavior between modules.
- Remove the blanket Ruff `INP001` ignore and the `F401`/`F403` exemptions for
  `__init__.py`; use explicit `__all__` declarations for intentional
  re-exports.
- Keep Ruff responsible for package presence, valid and sorted `__all__`
  declarations, unused imports, and wildcard imports.
- Add one narrow import-boundary check to pre-commit for the repository-specific
  rules Ruff cannot express. Use Import Linter if its contracts can consume the
  package boundaries without duplicating every export; otherwise use a small
  AST-based check.
- Resolve import cycles by correcting dependency direction or narrowing a
  package interface, not with lazy imports or new runtime indirection.
- Document the import rules in `AGENTS.md`.

## Done When

- Package initializers explicitly describe every supported export.
- Internal imports are relative and cross-package imports use public package
  interfaces.
- Direct imports of another package's implementation modules fail static
  validation.
- Ruff, the import-boundary check, ty, pre-commit, and the test suite pass with
  unchanged behavior.
