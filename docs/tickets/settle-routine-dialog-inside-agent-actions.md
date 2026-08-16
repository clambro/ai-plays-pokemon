# Ticket: Settle Routine Dialog Inside Agent Actions

## Outcome

Keep routine dialog inside the agent action that caused it. After an overworld
or battle action produces ordinary text, deterministic code should read and
advance that text, record it in the same rolling-memory iteration, and return
the transcript and resulting state to the same agent conversation.

The text handler remains responsible for screens that require a decision, such
as menus, yes/no questions, naming screens, and other custom interfaces. It also
remains the fallback when the dispatcher encounters text that was not produced
by an active agent tool, such as after restoring a save in the middle of an
interaction.

## Current Problem

When the overworld agent presses the action button to speak to an NPC, the
accepted button stops at `TEXT_INPUT_READY`. The overworld tool captures only
dialog that has already closed, so an ordinary open conversation causes the
overworld runner to finalize its iteration and return to the dispatcher.

The dispatcher then starts the text handler. Its deterministic preparation step
reads and advances the conversation, records the transcript in a separate
iteration, and returns without constructing a text agent when no decision
remains. The dispatcher subsequently starts a new overworld-agent conversation.

One ordinary interaction is therefore split across:

1. an overworld-agent action;
2. a deterministic text-handler iteration; and
3. a new overworld-agent run for the next decision.

This separates the decision to interact from the resulting text in rolling
memory and discards useful local conversation continuity. The model must make a
new response after seeing the transcript, but that response does not require a
new handler or Pydantic AI conversation when control has returned to the same
gameplay domain.

## Investigation Findings

### The emulator already exposes the required boundary

The ROM text-event driver already advances explicit text waits and stops at
semantic boundaries. `advance_text_dialog()` stops when ordinary interaction
closes or reaches a menu, special interface, overworld transition, or battle
boundary. No new ROM hook, screen polling, timing delay, or prompt instruction
is required.

Do not make `press_overworld_button()` silently drain dialog. Button input must
continue to report the exact decision boundary reached after accepted input.
Whether a standard dialog is safe to advance is agent workflow policy, not an
input primitive.

### Battle actions already demonstrate the intended lifecycle

Battle semantic tools perform their selected input and then call
`complete_battle_action()`. That completion path invokes the ROM-event dialog
driver, records the resulting battle text, captures a fresh observation, and
returns it to the same battle-agent conversation. The battle runner leaves only
when the resulting state no longer belongs to battle.

This is the behavior overworld interactions should adopt. Battle must still be
included in the implementation audit because its settlement policy is currently
separate from the text and overworld paths. In particular, direct button input
has special handling for an already-open menu, and the early return when an
action has already left battle must be checked to ensure final dialog events
remain owned and consumed exactly once.

### Dialog settlement is distributed across several owners

Current responsibilities are divided among:

- overworld tool completion, which consumes only completed interactions;
- text-handler preparation, which drains an ordinary open interaction;
- text-tool completion, which drains text produced by a menu decision;
- battle-tool completion, which drains battle resolution text;
- battle button handling, which separately captures text preceding a menu; and
- field-move and Sokoban services, which advance specific dialog sequences
  internally.

The ROM mechanics may retain distinct overworld and battle terminal policies,
but the agent-level decision about whether to advance routine text, preserve an
interactive screen, record a transcript, and refresh the observation should
have one clear owner.

## Design

Extract routine-dialog settlement from the text handler into a shared
agent-level utility. The emulator continues to own ROM-event collection and
mechanical advancement; the shared agent utility owns workflow policy, memory
recording, and background publication.

After an agent tool performs its domain action, settlement should:

1. inspect the current control boundary and game state;
2. advance only an ordinary dialog that requires no choice;
3. stop before any menu, yes/no question, naming screen, custom interface, or
   other decision;
4. retain all transcript text exactly once;
5. record that transcript before the current iteration is finalized; and
6. capture the screenshot and state only after settlement reaches its terminal
   boundary.

The domain tool then returns its ordinary action result, captured transcript,
and fresh observation through its existing result format.

### Overworld behavior

Make overworld tool completion settle ordinary dialog before returning its
result. If the interaction closes and external overworld control returns, the
overworld runner remains alive and the same agent conversation receives the
NPC's text before choosing its next action.

If settlement reaches a real decision or another gameplay domain, return the
fresh terminal observation and let the overworld runner exit normally. The
dispatcher can then route a menu to the text handler or a battle to the battle
handler.

This should apply consistently to routine dialog produced by direct interaction,
navigation, and other overworld tools. Services that deliberately complete a
larger deterministic sequence, such as confirmed field moves, may continue to
drive the required sequence themselves; the shared completion path must simply
find nothing left to consume.

### Battle behavior

Preserve the existing battle-agent experience: move resolution, item results,
switching text, experience gains, fainting text, and similar routine output are
drained and returned inside the same battle conversation.

Audit battle completion against the shared ownership rule rather than replacing
its battle-specific stop conditions mechanically. A standard battle menu is a
decision boundary and must remain visible. End-of-battle and post-catch
transitions must deliver their final transcript exactly once before control
passes to the overworld or text handler.

### Text-handler behavior

The text handler continues to own actual text-domain decisions. Before creating
its agent, it may use the same shared settlement utility to drain routine text
encountered directly by the dispatcher. If no decision remains, it returns
without a model call as it does today.

Do not inject routine transcripts into a new text-agent conversation merely
because text appeared. The handler boundary should represent the need for a
different decision maker, not the existence of a dialog box.

## Iteration and Conversation Semantics

Settlement must occur before the originating runner calls
`complete_iteration()`. The action reasoning, action result, and resulting
dialog then form one durable memory block.

When settlement returns to the same gameplay domain, the next model response is
a new decision iteration inside the existing Pydantic AI conversation. It cannot
be the same model response because the model must first receive the newly read
text. The change removes the redundant handler activation and conversation
restart; it does not ask deterministic code to choose the model's next action.

## Out of Scope

- Removing the text handler or text agent.
- Automatically selecting menu entries or answering questions.
- Adding prompts that tell the model what an NPC said or what choice to make.
- Adding ROM hooks, modifying the ROM, or restoring screen-stability polling.
- Combining distinct overworld and battle terminal conditions merely to create
  one universal emulator method.
- Changing the rule that one model decision produces one iteration.

## Implementation Plan

Execute these stages one at a time. Each stage includes its associated tests and
documentation so that code, verified behavior, and the documented architecture
remain aligned throughout the work.

### Stage 1: Establish the shared settlement boundary

Create a shared agent-level routine-dialog utility using module-level functions
and a small internal result record containing the transcript and terminal
observation. Move ordinary-dialog classification, background publication,
rolling-memory recording, and pending-event claiming behind this boundary while
retaining distinct ordinary-text and battle emulator drivers.

Extend battle dialog advancement to accept the same pre-input publication
callback already supported by ordinary text. This is an agent-facing API
alignment over the existing ROM event driver, not a new hook or polling path.

Add focused tests for plain-text advancement, protected decision screens,
exactly-once transcript recording, post-settlement observation capture, and the
no-op case where a larger deterministic service already consumed its dialog.
Update the shared-runtime and dialog-ownership portions of `docs/workflow.md` to
describe the new boundary.

### Stage 2: Migrate text handling without changing its domain behavior

Replace the duplicated settlement logic in text-tool completion and text-handler
preparation with the shared utility. Preserve the text agent's ownership of
menus, yes/no questions, naming screens, and custom interfaces. Preserve the
dispatcher fallback that drains an already-open ordinary dialog without a model
call, including its deterministic memory iteration.

Add text-path tests for ordinary fallback, dialog following a text-agent choice,
and untouched decision screens. Update the text-runner documentation alongside
the migration so it distinguishes fallback settlement from genuine text-domain
decisions.

### Stage 3: Settle overworld dialog inside the originating action

Make overworld tool completion invoke shared settlement before constructing its
result. Because every overworld tool uses this completion path, the behavior
will apply to direct interaction, navigation, inventory and party actions, goal
tools, and Sokoban. Field-move and puzzle services that intentionally finish a
larger deterministic sequence may retain that responsibility; shared completion
must safely find nothing left to consume.

Add tests proving that ordinary NPC and sign text is returned to the current
overworld conversation, recorded in the originating memory block, and followed
by a distinct model-decision iteration without restarting the local
conversation. Also cover menu and trainer-battle handoff boundaries and verify
that returned screenshots represent the terminal state. Update the overworld
workflow and memory/display documentation in the same stage.

### Stage 4: Unify and audit battle transcript ownership

Route battle transcript recording through the shared utility without replacing
the battle-specific emulator stop conditions. Preserve the special handling for
direct button input that has already reached a rendered menu. Replace the
current post-battle early return with terminal pending-event settlement so final
battle and capture text is claimed once without starting a driver that could
wait after control has already changed domains.

Add tests for normal turn resolution, direct menu input, battle exit to the
overworld, capture exit to the naming screen, and empty pending-event journals.
Update the battle workflow documentation with the resulting ownership and
handoff semantics.

After Stage 4, run the full static-analysis and test suite. This is final
verification of the staged work rather than a separate implementation stage.

## Validation

After the staged implementation and automated validation pass, use bounded live
playtesting to check observable workflow behavior:

- speaking to an NPC whose dialog closes normally;
- reading a sign whose dialog closes normally;
- speaking to an NPC whose dialog leads to a yes/no menu;
- triggering a trainer conversation that proceeds into battle;
- resolving a normal battle turn back to the battle menu;
- ending a battle and returning to the overworld;
- catching a Pokemon and reaching the naming decision; and
- restoring or dispatching while an ordinary dialog is already open.

During live playtesting, verify that each transcript is complete and appears
exactly once, that menus and other decisions are never advanced automatically,
and that every returned screenshot depicts the terminal state reported with it.

## Acceptance Criteria

- [ ] Ordinary overworld dialog is settled by the tool action that caused it.
- [ ] A completed NPC or sign interaction returns to the same overworld-agent
      conversation without activating the text handler.
- [ ] The originating action and its transcript are recorded in the same
      rolling-memory iteration.
- [ ] The next model decision remains a distinct iteration even when the local
      Pydantic AI conversation continues.
- [ ] Menus, yes/no questions, naming screens, and custom interfaces remain
      untouched for the text agent.
- [ ] Trainer dialog can transition cleanly from the overworld action into the
      battle handler.
- [ ] Battle actions continue to return routine resolution text to the same
      battle-agent conversation.
- [ ] Final battle and capture text is retained exactly once across transitions
      to the overworld or naming handler.
- [ ] Text-handler entry can still drain ordinary dialog encountered outside an
      originating tool action without making an unnecessary model call.
- [ ] Dialog events have one clear consumer and cannot be duplicated or lost
      across handler boundaries.
- [ ] Fresh screenshots and game state are captured only after deterministic
      settlement completes.
- [ ] No new ROM hooks, polling delays, or prompt instructions are introduced.
