# Ticket: Replace the Junjo Overworld Subflow with a Pydantic AI Agent

## Outcome

Replace the internal Junjo overworld graph with one Pydantic AI agent decision
that selects and executes a real function tool.

The root Junjo graph remains temporarily and invokes the overworld runner
through one adapter node, matching the battle and text agents. Each overworld
run executes exactly one tool and returns to the root graph.

This ticket covers the existing overworld subflow only. Root-level behavior
such as goal updates, long-term-memory management, background refresh,
iteration finalization, and mode routing remains unchanged until the root
migration.

## Overworld Preparation

Before calling the agent:

1. Load the explored map for the current location.
2. Update revealed terrain and other deterministic screen information.
3. Capture the initial game state and screenshot.
4. Build the prompt and the tools available from that prepared state.

Map loading and revealed-terrain updates are deterministic preparation, not
agent tools. Nearby sprite and sign descriptions are agent decisions and must
not remain separate automatic model calls.

`OverworldContext` contains the live `AgentState`, emulator dependency, and
prepared current map needed by the tools. The map is local context for the
overworld run rather than a second durable source of truth.

## Agent and Tools

The agent receives the screenshot, explored map, accessible coordinates,
exploration candidates, map boundaries, inventory, player state, goals, and
relevant memory. It briefly narrates its decision and calls exactly one
available tool.

Every tool has its own package with `interface.py` for the Pydantic AI
boundary and `service.py` for deterministic behavior. Tool-specific guidance
belongs in the tool interface. Preserve the useful instructions from the
prompts replaced by the migration.

The registry contains:

- press buttons;
- navigate;
- swap the first Pokémon;
- use an item;
- solve the current Sokoban puzzle;
- update nearby sprite descriptions; and
- update nearby sign descriptions.

Initial availability is derived from prepared state:

- button input is always available;
- navigation is unavailable while biking;
- party reordering requires more than one party member;
- item use requires a non-empty inventory;
- Sokoban requires a visible boulder and goal plus access to Strength;
- sprite updates require at least one sprite within the existing two-step
  distance; and
- sign updates require at least one sign within the existing two-step
  distance.

The sprite and sign tools expose the eligible entities and allow the agent to
persist useful description changes through the existing map-entity boundary.
They replace the two automatic entity-update model requests. The deterministic
terrain update remains in preparation.

Each tool validates fresh emulator state before acting. Model narration is
written to rolling memory, and token and cost usage continue through the
shared usage boundary.

## Scope

Keep the agent to one executed tool per overworld run until the Junjo subgraph
has been removed. Then allow non-movement tools to continue within the same
agent run while tools that move the player end the run.

Defer:

- goal and long-term-memory tools;
- root graph replacement;
- iteration-semantic changes;
- common runner abstractions;
- connected-component and warp work; and
- broader emulator or navigation changes.

## Staged Implementation Plan

Each stage leaves the application working.

### 1. Replace action selection and routing

Replace the selector plus its five routed action nodes with one Pydantic AI
decision using the corresponding function tools. Remove the secondary
argument requests and their obsolete prompts and schemas while preserving the
deterministic services and fixtures.

Keep the existing map-loading and map-update portion of the Junjo subgraph
temporarily. Keep the agent limited to one tool call.

This stage is complete.

### 2. Replace automatic entity updates with tools

Add separate sprite-update and sign-update tools. Register each only when the
prepared map contains an eligible entity within the existing two-step
distance. Move the relevant update instructions and entity choices into their
tool interfaces and reuse the existing persistence behavior.

Keep revealed-terrain updates deterministic. Delete the automatic sprite and
sign model calls, and their obsolete node-specific code, alongside the tool
migration.

This stage is complete.

### 3. Remove the overworld Junjo subgraph

Move map loading and deterministic terrain refresh into an ordinary preparation
stage at the start of the overworld runner. The prepared map belongs on the
overworld context before the agent and its conditional toolset are built.

Invoke the resulting overworld adapter directly from the root graph as already
done for battle and text, then delete the obsolete load-map and update-map node
wrappers, overworld graph, and subflow.

Use `AgentState` directly in `OverworldContext`, retain the prepared map on the
context, and remove the duplicated overworld state and store.

Preserve the single-tool turn boundary and all root-graph behavior.

This stage is complete.

### 4. Enable the overworld agent loop

Allow the agent to use multiple non-movement tools within one run. Mark tools
that move the player so their successful execution ends the run; do not infer
movement by comparing maps or game states. Keep the initial instructions and
tool definitions stable for prompt caching, and return fresh observations
through tool results when the agent continues.

Do not impose an arbitrary request limit. Preserve the existing outer workflow
boundary when a movement tool ends the agent run.

### 5. Final cleanup

Review the completed branch for prompt parity, conditional tool availability,
map preparation, entity persistence, mode transitions, rolling-memory output,
and usage accounting. Remove obsolete references and delete this ticket when
the migration is complete.

Defer broad workflow documentation and visualization changes until the root
graph migration can describe the finished orchestration.
