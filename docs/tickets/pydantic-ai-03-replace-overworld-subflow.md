# Ticket: Replace the Junjo Overworld Subflow with a Pydantic AI Agent

## Outcome

Replace the Junjo overworld decision flow with a Pydantic AI overworld agent
that selects and executes a real function tool from freshly prepared world
state.

The Junjo root graph remains temporarily. It invokes one overworld agent turn
through an adapter, leaving all three gameplay modes on their final agent
architecture before the root graph is replaced.

## Design

Create a dedicated `OverworldContext` dataclass and use it as the overworld
agent's Pydantic AI dependency type. Preparation should include relevant
rolling and long-term memory, goals, current player and party state, the
explored map, known transitions and provisional connected regions, and the
current screenshot.

The overworld agent owns a `tools/registry.py` built with `FunctionToolset`.
Use Pydantic AI toolset filtering for capabilities that are not legal in the
current state.

Every selectable capability has its own tool package with `interface.py` for
the actual Pydantic AI tool and `service.py` for business logic. Tool-specific
boundary models live beside that tool when needed. There is no `actions/`
directory and no monolithic `tools.py`.

The registry should cover navigation, direct interaction, item and party
management, the Sokoban solver, goal changes, long-term-memory changes, and
map annotations.

The model chooses a tool and its semantic arguments in one tool call. Remove
the separate tool selector and secondary argument prompts. Navigation remains
an agent tool while route planning, emulator movement, interruption handling,
and map observation remain deterministic service work.

Run one agent-selected overworld action, observe its result, update memory and
the HTML background as appropriate, and return to the root loop. If the action
enters battle or text mode, the next root iteration routes to that completed
mode runner.

## Completion

- Overworld decisions use a typed `OverworldContext` and real Pydantic AI
  function tools.
- Tools are composed through the registry and split into per-tool interface
  and service modules.
- Goal and long-term-memory mutation are overworld tools.
- The selector prompt and secondary tool-argument calls are removed.
- The Junjo root reaches the overworld runner through one temporary adapter.
- The old overworld graph, state, conditions, and nodes are removed.
- Overworld actions, tool filtering, mode transitions, and background updates
  are covered by relevant tests.
