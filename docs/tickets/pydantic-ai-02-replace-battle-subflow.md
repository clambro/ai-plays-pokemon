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
Build the toolset from the prepared battle state for each agent run. At a
standard trainer-battle menu, expose fighting and switching only when those
actions are available. Wild battles may additionally expose throwing a ball
and running. Irregular battle screens expose constrained button input instead
of semantic tools. The agent chooses arguments from the supplied player,
inventory, battle, and screen state.

Each exposed tool still validates its request against fresh emulator state
before acting and returns model-visible retry feedback when the request is no
longer valid. Do not duplicate argument validation with a generated prompt
allowlist.

Use stable references for tool arguments: move slot for fighting, party slot
for switching, and ball type for throwing a ball. If a request is no longer
legal when its service reads fresh state, perform no emulator input and return
the rejection through the tool so the agent can choose again.

Every selectable tool has its own package with `interface.py` for the actual
Pydantic AI function tool and `service.py` for battle mechanics. Tool-specific
models remain inside the tool package when needed. There is no `actions/`
directory and no single `tools.py`.

The battle handler should keep agent construction and execution together,
alongside context preparation, the temporary Junjo adapter, and tool packages:

```text
battle_handler/
├── agent.py
├── context.py
├── prepare.py
├── prompts.py
├── node.py
└── tools/
    ├── registry.py
    ├── fight/
    ├── switch_pokemon/
    ├── throw_ball/
    ├── run/
    └── press_buttons/
```

The battle-agent runner starts one Pydantic AI run for the complete battle.
Within that run it:

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

Keep the conversation append-only and cache-friendly. Instructions and initial
input stay at the beginning; changing state is appended only through tool
results. Use a stable battle-agent prompt cache key, keep image detail settings
consistent, and inspect cache-read and cache-write usage while tuning. Do not
re-send rolling memory between actions.

At the ordinary trainer or wild battle menu, the registry exposes only the
semantic capabilities available from the supplied game state. Constrained
button input covers screens that the semantic services do not understand. Tool
services must resolve semantic choices against fresh state instead of trusting
menu indices captured before the model call.

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

Next, add the semantic tools against the stable registry and let the agent
execute exactly one tool call per existing Junjo battle-subflow run.
During this intermediate slice, an invalid tool request returns to the outer
workflow and tries again on its next iteration. Once the agent owns the whole
battle loop, it can retry within the same run. Remove the obsolete Junjo
selector, argument schemas, conditions, and action nodes while retaining the
existing post-action dialog handling.

After committing that intermediate slice, remove the `reason` argument from
every battle tool. Instruct the agent to emit a brief, visible text explanation
alongside each tool call. The runner appends that text to rolling memory before
executing the tool, which also streams it to the HTML background. Tool calls
contain only the arguments needed to perform the action.

Once every battle action runs through the agent, move orchestration into the
whole-battle runner. Remove the remaining Junjo battle wrapper only after the
new runner owns the complete battle lifecycle.

## Completion

- A battle is handled by the Pydantic AI battle agent without returning to the
  root graph between actions.
- The agent uses a typed `BattleContext`, a state-derived registry, and real
  function tools with separate interface and service modules.
- The Junjo root reaches the battle runner through one temporary adapter.
- The old battle graph, state, conditions, handlers, and nodes are removed.
- Battle behavior, legal-action validation, loop termination, and background
  updates are covered by relevant tests.
