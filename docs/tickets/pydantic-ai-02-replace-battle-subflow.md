# Ticket: Replace the Junjo Battle Subflow with a Pydantic AI Agent

## Outcome

Replace the complete Junjo battle subflow with a Pydantic AI battle agent that
stays inside a local battle loop until the application no longer classifies
the current screen as battle mode.

The Junjo root graph remains temporarily. It invokes the new battle runner
through one adapter, and the application remains runnable while the text and
overworld handlers still use Junjo.

## Existing Behavior

The current subflow handles one battle action per top-level workflow:

1. At the standard `FIGHT / PKMN / ITEM / RUN` menu, it calculates the legal
   move, switch, ball, and run choices.
2. One model call selects an indexed semantic action.
3. Junjo routes that choice to the corresponding deterministic menu service.
4. A separate model-driven button handler covers forced switches, special
   battles, and other irregular screens.
5. Subsequent battle dialog is advanced and recorded deterministically.
6. Control returns to the root graph.

The migration should preserve the useful battle mechanics while replacing the
Junjo routing and separate action-selection response with real Pydantic AI
tool calls.

## Design

Create a dedicated `BattleContext` dataclass and use it as the battle agent's
Pydantic AI dependency type. Prepare the context and initial agent input once
at battle entry. The input contains the relevant memory, goals, player
information, and initial battle and screen state; it is not rebuilt between
actions.

The battle agent owns a `tools/registry.py` built with `FunctionToolset`.
Keep the registered tool definitions stable throughout the battle. The current
observation tells the model which actions and arguments are legal, and tool
services validate requests against fresh emulator state before acting. This
avoids changing tool schemas between requests and breaking prompt-cache reuse.

Use stable references for tool arguments: move slot for fighting, party slot
for switching, and ball type for throwing a ball. Each returned observation
lists the currently legal values. An empty list makes that action unavailable
without removing or rewriting its tool definition. If a request is no longer
legal when its service reads fresh state, perform no emulator input and return
the rejection with the refreshed observation.

Every selectable tool has its own package with `interface.py` for the actual
Pydantic AI function tool and `service.py` for battle mechanics. Tool-specific
models remain inside the tool package when needed. There is no `actions/`
directory and no single `tools.py`.

The battle handler should be organized around the agent, context preparation,
local runner, temporary Junjo adapter, and tool packages:

```text
battle_handler/
├── agent.py
├── context.py
├── prepare.py
├── prompts.py
├── run.py
├── node.py
└── tools/
    ├── registry.py
    ├── fight/
    ├── switch_pokemon/
    ├── throw_ball/
    ├── run/
    └── press_buttons/
```

The local runner starts one Pydantic AI run for the complete battle. Within
that run it:

1. sends the prepared static input and initial observation;
2. lets the agent select and execute a real function tool;
3. deterministically advances battle dialog and waits for the next decision
   point;
4. refreshes the displayed state;
5. returns the updated battle state, screen state, and screenshot from the
   tool for the agent's next decision; and
6. continues until the application no longer classifies the screen as battle
   mode.

The toolset should cover fighting, switching, throwing a ball, running, and
constrained input for irregular battle screens. Tool interfaces expose
semantic choices; services translate them into deterministic emulator input.

Tool results form the changing portion of the battle conversation. Each result
describes the completed action and supplies a fresh observation for the next
model request. Normal battle dialog remains deterministic and should not
consume a separate model call.

Keep the conversation append-only and cache-friendly. Stable instructions,
tool definitions, and initial input stay at the beginning; changing state is
appended only through tool results. Use a stable battle-agent prompt cache key,
keep image detail settings consistent, and inspect cache-read and cache-write
usage while tuning. Do not rebuild the full prompt, change tool schemas, or
re-send rolling memory between actions.

At the ordinary trainer or wild battle menu, the returned observation
identifies the currently legal semantic actions and arguments. Constrained
button input covers screens that the semantic services do not understand.
Tool services must resolve semantic choices against fresh state instead of
trusting menu indices captured before the model call.

The local loop ends when battle mode exits, not solely when the ROM battle flag
is cleared. In particular, the naming screen shown after catching a Pokémon is
text mode even though the battle flag may remain set.

The complete battle remains one top-level rolling-memory iteration. Individual
actions and captured dialog append to the current block, which already streams
live log changes to the HTML background. The runner must also refresh the full
displayed game state during the local loop because control may not return to
the root graph for several actions.

Introducing Pydantic AI also requires small shared integrations outside the
battle handler:

- add the OpenAI-enabled Pydantic AI dependency;
- instrument Pydantic AI through the existing Logfire setup; and
- feed Pydantic AI response usage through the existing token and
  `genai-prices` cost totals.

The existing save-state integration tests for fighting, switching, throwing a
ball, and running should remain attached to their deterministic services.

## Implementation Order

Start by routing only the existing generic battle fallback through a Pydantic
AI agent with the `press_buttons` function tool. Keep Junjo and the existing
semantic battle routes around this narrow slice so the application remains
runnable while the shared agent, context, multimodal input, telemetry, usage,
registry, and tool-service boundaries are established.

Once that path is sound, move orchestration into the whole-battle runner and
add the semantic tools against the stable registry. Remove the old Junjo
battle graph only after the new runner owns every battle path.

## Completion

- A battle is handled by the Pydantic AI battle agent without returning to the
  root graph between actions.
- The agent uses a typed `BattleContext`, a stable registry, and real
  function tools with separate interface and service modules.
- The Junjo root reaches the battle runner through one temporary adapter.
- The old battle graph, state, conditions, handlers, and nodes are removed.
- Battle behavior, legal-action validation, loop termination, and background
  updates are covered by relevant tests.
