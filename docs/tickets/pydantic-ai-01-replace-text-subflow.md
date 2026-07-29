# Ticket: Replace the Junjo Text Subflow with a Pydantic AI Agent

## Outcome

Replace the complete Junjo text subflow with a Pydantic AI text agent that
stays inside a local interaction loop until text mode exits.

The Junjo root graph remains temporarily. It invokes the new text runner
through one adapter, leaving the application runnable while the overworld
handler still uses Junjo. Follow the context, agent, registry, and per-tool
interface/service boundaries established by the completed battle migration.

## Design

Create a dedicated `TextContext` dataclass and use it as the text agent's
Pydantic AI dependency type. Context preparation should expose only the
current interaction state, relevant memory, screenshot, and dependencies
needed by text tools.

The text agent owns a `tools/registry.py` built with Pydantic AI's
`FunctionToolset`. Every selectable tool has its own package with:

- `interface.py` for the typed function exposed to the agent; and
- `service.py` for the underlying deterministic behavior.

Add tool-specific boundary models only when they are useful. Do not introduce
an `actions/` directory or a monolithic `tools.py`.

The text runner should:

1. observe the current screen;
2. exit when the interaction is over;
3. advance ordinary dialog deterministically when no choice is required;
4. otherwise prepare a fresh `TextContext` and run one real tool decision; and
5. re-observe before continuing.

Initial agent tools should cover constrained button input and name entry.
Their services own emulator mechanics; their interfaces own the model-facing
schema and Google-style documentation.

Keep the HTML background current throughout the local loop rather than only
when control returns to the root graph.

## Completion

- Text interactions run through the Pydantic AI text agent and local loop.
- The agent uses a typed `TextContext`, a tool registry, and real function
  tools with separate interface and service modules.
- Plain dialog remains deterministic.
- The Junjo root reaches the new runner through one temporary adapter.
- The old text graph, state, conditions, and nodes are removed.
- Text behavior, loop termination, tool selection, and background updates are
  covered by relevant tests.
