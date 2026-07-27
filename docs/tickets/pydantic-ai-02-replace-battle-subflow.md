# Ticket: Replace the Junjo Battle Subflow with a Pydantic AI Agent

## Outcome

Replace the complete Junjo battle subflow with a Pydantic AI battle agent that
stays inside a local battle loop until the ROM reports that battle mode has
ended.

The Junjo root graph remains temporarily. It invokes the new battle runner
through one adapter, and the application remains runnable with the completed
text migration.

**Depends on:**

- [`pydantic-ai-01-replace-text-subflow.md`](pydantic-ai-01-replace-text-subflow.md)

## Design

Create a dedicated `BattleContext` dataclass and use it as the battle agent's
Pydantic AI dependency type. Each decision receives freshly prepared battle
state, parsed text, relevant memory, and only the dependencies required by
battle tools.

The battle agent owns a `tools/registry.py` built with `FunctionToolset`.
Filter the registered toolset against the current battle state so the model
sees only legal capabilities.

Every selectable tool has its own package with `interface.py` for the actual
Pydantic AI function tool and `service.py` for battle mechanics. Tool-specific
models remain inside the tool package when needed. There is no `actions/`
directory and no single `tools.py`.

The local runner repeatedly:

1. waits for battle state to settle;
2. observes and prepares a fresh `BattleContext`;
3. runs one real agent tool decision;
4. executes the selected tool service;
5. refreshes displayed state; and
6. re-observes until battle mode exits.

The toolset should cover fighting, switching, throwing a ball, running, and
constrained input for irregular battle screens. Tool interfaces expose
semantic choices; services translate them into deterministic emulator input.

## Completion

- A battle is handled by the Pydantic AI battle agent without returning to the
  root graph between actions.
- The agent uses a typed `BattleContext`, a filtered registry, and real
  function tools with separate interface and service modules.
- The Junjo root reaches the battle runner through one temporary adapter.
- The old battle graph, state, conditions, handlers, and nodes are removed.
- Battle behavior, legal-tool exposure, loop termination, and background
  updates are covered by relevant tests.
