# Ticket: Enforce Import Discipline

## Outcome

Keep dependencies pointed from orchestration toward implementation and place
shared code with the layer that owns it. Preserve the repository's existing,
explicit import style and application behavior.

## Principles

- Treat circular imports as an ownership or dependency-direction problem.
  Resolve the underlying relationship instead of hiding it with lazy imports,
  runtime indirection, import ordering, or lint suppressions.
- Code belongs at the narrowest layer that owns it. Helpers used only by a
  feature's tools belong with those tools rather than at the feature root.
- Higher-level orchestration may depend on lower-level services and schemas;
  lower-level modules must not depend back on the orchestration that consumes
  them.
- `TYPE_CHECKING` imports follow the same dependency direction as runtime
  imports.
- Keep imports explicit. Do not introduce wildcard imports or `__all__`.
- Do not add package initializers, facade modules, or custom import rules merely
  to enforce an arbitrary spelling of an otherwise clear import.
- A package initializer is appropriate only when it provides necessary package
  behavior or a genuinely useful, coherent package API.

## Work

- Audit dependency direction one concrete cycle or inversion at a time.
- Move clearly misplaced modules to the layer that owns them and update their
  import paths.
- Start with `agent/`: tool-only battle and overworld helpers should live under
  their respective `tools` directories.
- Leave unrelated absolute-versus-relative import choices and package layout
  alone unless they cause a real ownership problem.
- Use Ruff's existing import checks. Add an architectural rule only when there
  is a concrete boundary worth enforcing and the rule cannot be expressed by
  ordinary module ownership.

## Done When

- Tool-only helpers live with their tools and all consumers use the new paths.
- No dependency cycle is concealed by indirection, ordering, or suppression.
- The resulting dependency direction is explainable in terms of ownership,
  without initializer or facade boilerplate.
- Ruff, ty, and the relevant tests pass with unchanged behavior.
