# Ticket: Enforce Function-First Structure and Model Discipline

## Outcome

Clean up the surviving v2 code around three repository rules:

1. Prefer module-level functions for stateless operations.
2. Use standard dataclasses for internal domain data and Pydantic at explicit
   I/O/validation boundaries.
3. Standardize production docstrings on Google style.

Classes remain appropriate where they own meaningful state, identity,
lifecycle, invariants, polymorphism, or a framework contract.

## Priority and Dependencies

Land this after the provider, telemetry, critic-removal, and rolling-memory
replacement work so the cleanup targets code that will survive. Land it before
adding substantial new map-domain models.

Junjo-required nodes, subflows, conditions, states, and stores may remain as
framework exceptions until Junjo is removed.

## Function-First Rule

Replace a class with functions when it only:

- copies one call's arguments from `__init__` to `self`;
- is instantiated for one public method;
- acts as a namespace for static helpers; and
- owns no resource, lifecycle, persistent mutation, invariant, or polymorphic
  contract.

Keep dependencies explicit in keyword-friendly function signatures. Do not
replace service objects with mutable globals, a service locator, or a
one-for-one “context” dataclass that merely hides the same arguments.

Retain classes for resource owners such as the emulator and stream server,
stateful multi-step workflows where state protects correctness, framework
contracts, SQLAlchemy models, exceptions, enums, boundary schemas, and domain
dataclasses.

Where useful, separate pure decisions from emulator, database, and provider
effects so the decision can be tested directly. Do not fragment already-clear
code into ceremonial layers.

## Model Boundary Rule

Use Pydantic when runtime parsing, validation, serialization, JSON Schema,
settings loading, OpenAI Structured Outputs, HTTP payloads, database DTOs,
backup snapshots, or a framework contract requires it.

Use `dataclasses.dataclass` for trusted internal values and aggregates such as
coordinates, graph values, solver state, pricing configuration, rolling
memory, and internal operation results.

Defaults for new internal value objects:

- `slots=True`;
- `frozen=True` when immutable/hashable;
- `kw_only=True` when positional construction is unclear; and
- `field(default_factory=...)` for mutable defaults.

Do not use `pydantic.dataclasses.dataclass`. Convert explicitly at the boundary
and reject unknown external fields where appropriate. Avoid duplicate
Pydantic/dataclass representations when no real boundary or shape change
exists.

Boundary schemas should remain behavior-light. Domain algorithms and mutable
workflows belong in internal code.

## Google-Style Docstrings

Configure Ruff with:

```toml
[tool.ruff.lint.pydocstyle]
convention = "google"
```

Remove broad or contradictory pydocstyle ignores. Use narrow exceptions for
tests, generated code, obvious magic methods, and constructors documented by
their class.

Production docstrings should:

- put a concise summary on the opening line;
- use `Args:`, `Returns:`, `Yields:`, and `Raises:` when needed;
- document semantics, units, mutation, side effects, and caller-relevant
  failures;
- avoid repeating type annotations; and
- contain no Sphinx `:param:`, `:return:`, or `:raises:` directives.

One-line docstrings are sufficient for obvious public operations. Delete or
improve filler text that only repeats a symbol's name.

## Enforcement

Add these principles to `AGENTS.md` and a short architecture note. Use Ruff and
a small structural check where the rule is objective—for example, prohibiting
Pydantic dataclasses or Pydantic models in clearly internal model modules.
Class usefulness remains a code-review judgment rather than a brittle AST
guess.

## Out of Scope

- Banning classes, inheritance, or methods.
- Removing Junjo.
- A dependency-injection framework.
- Rewriting gameplay algorithms.
- Producing a catalog of every class or model in the repository.
- Mandatory test docstrings when test names are sufficient.

## Validation

Characterization tests should protect behavior-sensitive conversions. Add
focused tests for pure functions, dataclass equality/mutation semantics,
boundary validation and conversion, Structured Output schema generation, and
the structural checks.

## Acceptance Criteria

- [ ] Stateless one-call service/utility classes are replaced with functions.
- [ ] Every retained service-like class owns a concrete stateful, lifecycle,
      framework, or polymorphic responsibility.
- [ ] Removed service classes are not replaced by mutable globals or parameter
      bags.
- [ ] Internal domain values use standard dataclasses where appropriate.
- [ ] Pydantic is limited to explicit boundaries and framework requirements.
- [ ] Boundary conversion and external-field policy are explicit and tested.
- [ ] `pydantic.dataclasses.dataclass` is absent.
- [ ] Ruff enforces Google-style docstrings.
- [ ] Production code contains no Sphinx-style parameter/return directives.
- [ ] `AGENTS.md` and the architecture note state the rules concisely.
- [ ] Ruff, ty, tests, and pre-commit pass.

## References

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [Ruff pydocstyle settings](https://docs.astral.sh/ruff/settings/#lint_pydocstyle_convention)
- [Python 3.14 dataclasses](https://docs.python.org/3.14/library/dataclasses.html)
- [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/)
