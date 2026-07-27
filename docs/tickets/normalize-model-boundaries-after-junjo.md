# Ticket: Normalize Model Boundaries After Junjo

## Outcome

Remove incidental Pydantic usage from internal application state after Junjo no
longer owns the workflow. Use standard-library dataclasses for trusted domain
data and reserve Pydantic for boundaries that perform validation,
serialization, or schema generation.

This is an architectural cleanup. It must not change gameplay behavior.

## Dependency

Do this after the final Junjo removal ticket. Until then, Junjo's Pydantic
`BaseState` models validate and serialize their complete nested state trees,
which makes an honest separation unnecessarily awkward.

## Model Boundary

Pydantic belongs at explicit boundaries such as:

- model responses and tool schemas;
- settings and environment input;
- database create, update, and read DTOs;
- HTTP and streaming payloads; and
- dedicated persisted snapshot formats.

Standard-library dataclasses belong in trusted internal code, including agent
contexts and state, memory aggregates, emulator snapshots produced by parsers,
map-domain objects, coordinates, solver state, provider configuration, and
internal operation results.

Boundary models must not become the application's domain models. Convert
between validated payloads and internal values at the boundary, then pass the
internal representation through the rest of the application.

## Work

- Audit the remaining Pydantic models by responsibility rather than by file or
  naming convention.
- Convert internal models to `dataclasses.dataclass` without redesigning their
  surrounding gameplay logic.
- Introduce small, explicit boundary conversions where external and internal
  representations differ.
- Remove domain dependencies on database DTOs, provider payloads, and other
  boundary schemas.
- Use `slots=True` by default and `frozen=True` for immutable value objects.
- Do not use `pydantic.dataclasses.dataclass`.
- Keep boundary schemas focused on parsing, validation, serialization, and
  schema generation; keep behavior in domain code.
- Update `AGENTS.md` and the architecture documentation to reflect the final
  boundary.

## Done When

- Internal domain and workflow state use standard-library dataclasses.
- Every remaining Pydantic model has a concrete boundary or framework reason
  to exist.
- Boundary DTOs do not leak into internal aggregates.
- No hidden Pydantic coercion is required for ordinary domain operations.
- Static checks and the test suite pass with unchanged gameplay behavior.
