# Ticket: Replace the Junjo Text Subflow with a Pydantic AI Agent

## Outcome

Replace the Junjo text subflow with a local text runner that owns the complete
interaction. Ordinary dialog is deterministic: read it, advance it, record it,
and return without calling a model if the interaction ends. A Pydantic AI
agent is created only when the game presents a decision such as a menu,
yes/no question, naming screen, or other actionable text state.

The Junjo root graph remains temporarily. It invokes the new text runner
through one adapter, leaving the application runnable while the overworld
handler still uses Junjo.

## Design

Create a dedicated `TextContext` dataclass containing the live agent state and
emulator dependency. The entry game state and screenshot are static run inputs,
not context fields. Tools read fresh observations from the emulator and return
them without mutating the context.

The runner first observes the game and distinguishes between:

- text mode having ended;
- an ordinary dialog box with no decision on screen; and
- an actionable text screen.

It drains ordinary dialog with the shared dialog reader and appends the
captured text to rolling memory. If that closes the interaction, the runner
returns without constructing an agent. If it exposes a decision, the captured
dialog becomes part of the context available to the agent.

The agent is built once for the remaining interaction with a fixed
`FunctionToolset`. Its initial prompt and screenshot remain static. Each tool
result supplies the fresh screenshot, onscreen text, action result, and any
dialog produced by the action. State-dependent legality is checked inside the
tool services rather than by rebuilding or filtering the tools between model
steps.

Initial tools are:

- `press_buttons`, for menus, questions, the title screen, and other direct
  text-screen input; and
- `assign_name`, which lets the model choose a name while deterministic code
  validates it and navigates the naming grid.

Every selectable tool has its own package with `interface.py` for the Pydantic
AI boundary and `service.py` for deterministic behavior. Tool-specific models
are added only when plain typed parameters are insufficient.

The model's ordinary response text is recorded as reasoning. Captured dialog
is also retained in rolling memory because it remains relevant after the
interaction. Detailed tool results stay inside the agent conversation. The
HTML background is refreshed as the interaction advances.

As in the battle agent, the prompt tells the model to make one tool call in
each response. Do not force `tool_choice` or retry a text-only final response.
If the model ends its run while a decision remains, the next root iteration
routes back into the text runner and tries again naturally.

## Implementation Plan

1. **Establish the actionable-text agent.**
   Add `TextContext`, a temporary root-graph adapter, and a Pydantic AI agent
   with the `press_buttons` tool. Replace the generic raw structured-output
   decision while retaining the existing deterministic dialog and naming
   behavior. Keep the one-text-action boundary initially so this first slice
   can establish the agent pattern without also changing the interaction
   lifecycle. Remove the superseded Junjo text graph, subflow, state,
   conditions, and wrapper nodes.

1.5. **Clarify the initial game state.**
   Remove game state and screenshot fields from both `BattleContext` and
   `TextContext`. Contexts contain live dependencies only. Capture the entry
   observation as local agent-run input, and keep fresh observations returned
   by tools local rather than storing them back on the context.

2. **Migrate naming into the toolset.**
   Replace the separate naming model call with an `assign_name` function tool.
   Preserve the deterministic cursor navigation and uniqueness checks, and
   keep the existing navigation tests with the service they cover. Build both
   text tools into one stable registry and let their services reject requests
   that do not match the current screen.

3. **Close the local interaction loop.**
   Move ordinary dialog advancement ahead of agent construction so dialog-only
   interactions make no model call. Once a decision is reached, keep one agent
   conversation alive across subsequent decisions. After each tool action,
   drain and record ordinary dialog, refresh the context and HTML background,
   and either return the next actionable observation to the agent or end when
   text mode exits or control moves to battle.

4. **Remove the old implementation and update documentation.**
   Delete the remaining raw text prompts, response schemas, handlers, and
   obsolete routing code. Update the workflow and architecture documentation
   to show the deterministic dialog path and conditional text agent, then
   remove this completed ticket.
