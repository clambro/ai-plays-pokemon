# Ticket: Replace Animation Polling with ROM Control Boundaries

## Dependency and Decision Gate

The existing ROM text-event system has established PyBoy execution hooks,
instruction-signature validation, owner-thread callbacks, and asynchronous event
delivery as coordination primitives for battle, overworld dialog, and transient
item text. This ticket extends that approach to non-text control boundaries.

The intended end state has no animation checker. Before migrating callers,
however, a small prototype must prove that shared ROM boundaries cover the
application's actual overworld, menu, naming, and bespoke-screen workflows. If
that requires per-screen hooks or cannot distinguish requested input from idle
polling, stop and reassess the design rather than expanding it into a model of
the entire ROM.

## Outcome

Remove screen-stability polling from emulator input and application dispatch.
Replace it with fast, deterministic coordination based on the ROM reaching its
next meaningful control boundary after an input.

The result should wait for what the game is doing, not for five periodically
sampled screenshots to happen to look alike. Ordinary menu input should complete
quickly, long animations and scripted movement should not return early, and
continuous cosmetic animation should not prevent progress.

## Current Problem

`Emulator.wait_for_animation_to_finish()` samples `GameState` every 150 ms and
returns after five observations with unchanged screen tiles, map, player
coordinates, and facing direction. A successful wait therefore costs at least
roughly 750 ms, and longer whenever an unrelated visual change resets the count.
The dispatcher performs this wait twice before selecting a gameplay handler.

The method is not actually detecting animation completion. Its callers use it as
one generic barrier for several unrelated operations:

- one-tile overworld movement and collisions;
- menu cursor movement and submenu transitions;
- battle turns containing animation, text, HUD updates, and forced choices;
- warps, field moves, ledges, spinners, and other scripted movement; and
- immediate custom interfaces such as naming and map or status screens.

These operations do not share a visual definition of completion. Stable pixels
can occur before the ROM has finished, while blinking or ambient animation can
continue after the ROM is ready for input.

## Investigation Findings

### Observe shared control boundaries, not individual animations

The ROM converges on a small number of engine-level boundaries used by the
application's supported workflows:

- the existing text-event system reports standard dialog input and lifecycle
  transitions, although closure and battle-exit events are not necessarily
  settled completion boundaries;
- `HandleMenuInput` covers the standard start, bag, party, battle, list, and
  choice menus;
- the overworld loop exposes when external control has returned after movement,
  map scripts, warps, battles, and simulated input; and
- the player-step completion path exposes precise intermediate movement needed
  while observing spinners.

Naming is the only bespoke interface currently automated directly enough to
justify a dedicated readiness boundary if the standard boundaries do not cover
it. Other immediate bespoke interfaces may use a short, deterministic render
fence only after the prototype proves that their operation is bounded.

Do not hook move animations, field-move effects, battle transitions, or other
individual visual routines. A battle action may execute several animations with
text, damage, EXP, fainting, switching, and menus between them. The correct
terminal condition is the next decision boundary, not any particular animation
returning.

### Progress events are not necessarily terminal boundaries

Several useful ROM events occur before the application may safely continue:

- `wWalkCounter` reaching zero updates the player's tile before step effects,
  random battles, poison, warps, and map scripts have all resolved;
- `INTERACTION_CLOSED` marks a text-display lifecycle transition, after which a
  surrounding script may continue; and
- the current `BATTLE_ENDED` hook clears battle variables before sound, palette,
  map restoration, and post-battle control flow have completed.

These events may be retained as progress or domain-transition markers, but a
button operation must continue until a real input or decision boundary follows.

The current dialog drivers do not yet enforce that rule. Battle dialog stops on
`BATTLE_ENDED`, and ordinary dialog stops on `INTERACTION_CLOSED`. The duplicate
dispatcher waits currently mask those early returns. Both drivers must converge
on the subsequent decision-ready boundary before the dispatcher waits can be
removed.

### A universal joypad hook is the wrong abstraction

Many ROM input loops poll the low-level joypad routines extremely frequently.
Hooking every poll would impose Python callback overhead on hot ROM loops and
would still not distinguish a meaningful decision from input used only to skip
an effect.

Use a few low-frequency, named engine boundaries with validated instruction
signatures. All ROM and WRAM addresses remain confined to parser modules.

### ROM evidence behind the proposed boundaries

The local Yellow Legacy decompilation establishes the following control flow.
These are investigation findings and candidate convergence points, not a mandate
to use the first convenient instruction as the final hook:

- `resources/pokeyellow/home/overworld.asm` runs `OverworldLoop`, checks
  `wWalkCounter`, and only calls `JoypadOverworld` when ordinary walking is not
  in progress. After a completed step it still performs step counting, Safari
  checks, poison and blackout handling, random-battle checks, warp checks, and
  map scripts. A safe overworld terminal event must be on the far side of that
  processing, when non-simulated external input is genuinely available again.
  The investigated symbols are `OverworldLoop` at `00:023c` and
  `JoypadOverworld` at `00:0c74`.
- `resources/pokeyellow/engine/overworld/advance_player_sprite.asm` decrements
  `wWalkCounter` and updates map coordinates when it reaches zero. This is the
  precise candidate for a player-step progress event, but it is deliberately
  not the final action boundary. `_AdvancePlayerSprite` is at `3c:410c`.
- `resources/pokeyellow/home/window.asm` implements `HandleMenuInput_`.
  Entering the function is too early to mean that a rendered menu is ready: it
  still places the cursor and calls `Delay3` before polling. A control-ready
  event must represent the prepared input loop, while an accepted-input event
  can be taken from its key-pressed path without hooking every joypad poll. The
  investigated symbols are `HandleMenuInput_` at `00:3ab6`, `.loop2` at
  `00:3acd`, and `.keyPressed` at `00:3afe`. The existing text recorder's entry
  hook may remain useful for detecting that a menu opened without being
  sufficient to synchronize consecutive menu inputs.
- `resources/pokeyellow/engine/menus/naming_screen.asm` has explicit input-loop
  and post-button return points. Those provide a contained special boundary if
  naming cannot use the shared menu behavior. Its investigated input-loop
  symbol is at `01:6466`.
- `resources/pokeyellow/engine/items/town_map.asm` demonstrates why not every
  custom screen should receive hooks. It has its own blinking input loop, but
  ordinary cursor changes can be observed after their bounded render update.
  Its investigated input-loop symbol is at `1c:4fe0`.
- `resources/pokeyellow/engine/battle/core.asm` may call
  `PlayMoveAnimation` repeatedly during one turn. Its animation return therefore
  cannot be an action-completion boundary. Even the explicit
  `MoveAnimation.animationFinished` symbol at `1e:4dc9` is therefore the wrong
  abstraction for this ticket.
- `resources/pokeyellow/engine/battle/end_of_battle.asm` clears battle variables
  before waiting for sound, whitening the palette, and returning through battle
  initialization to restore overworld state. `BATTLE_ENDED` is consequently a
  transition marker rather than permission to capture the next observation. The
  existing hook at `EndOfBattle.resetVariables` is `04:7ca1`.
- `UpdateSprites` is called across unrelated overworld, text, and menu paths. It
  is a rendering helper, not a semantic convergence point, and should not become
  a universal completion hook.
- `Delay3` exists because the background map is transferred in thirds across
  three frames. This supports a short explicit render fence for immediate
  bespoke screens; it does not justify a general elapsed-time or pixel-stability
  rule.

PyBoy invokes execution hooks synchronously inside the worker's rendered
`tick()`. Hook callbacks should only record compact facts. The worker should
publish a boundary or capture an observation after the containing tick has
finished so the CPU-side transition and rendered frame cannot be confused.
The numeric locations above came from the investigated required-ROM symbol file;
the implementation must still derive and validate instruction signatures rather
than treating symbols or this prose as runtime authority.

### Current production-call audit

Animation settling is still used by:

- application dispatch, which waits twice before handler selection;
- overworld navigation, spinner exploration, Pikachu-facing adjustments, HM
  use, the general overworld button tool, and the Sokoban solver;
- deterministic start-menu, inventory, party, and Pokémon-swapping workflows;
- battle menu navigation; and
- text-menu button input and automated naming.

Post-confirmation battle and standard-dialog resolution already use the ROM text
driver. Their transcript behavior should remain intact, but their terminal
policy must be tightened so transition markers do not expose an unfinished
screen. The remaining work is principally emulator coordination plus an audit of
deterministic input callers, not a rewrite of battle or navigation.

## Scope Constraint

This ticket must not become a model of every interactive routine in the ROM.
The completed system should reuse the existing text hooks and add only the
few control hooks needed for:

1. accepted input and readiness in the standard-menu engine, if the existing
   menu hook cannot represent both safely;
2. accepted input and restored control in the overworld loop;
3. player-step progress for spinner observation; and
4. naming readiness only if required by the automated naming tool.

Some concepts may share one executable location and some may require separate
accepted-input and ready locations. The expected total is approximately four to
six new executable hooks, with six as the investigation's upper bound.

Immediate bespoke interfaces that only need their completed WRAM-to-VRAM update
may use a short deterministic frame fence derived from the ROM's rendering
cycle. This policy must be selected from the current control domain rather than
used as a timeout when no recognized event arrives. Bespoke screens do not
receive one hook each.

If implementation requires more than roughly six new hook addresses, begins
naming individual animations or maps, or requires tool-specific knowledge in the
event recorder, stop and reconsider the design. That indicates the work has
crossed from observing shared engine behavior into reimplementing the ROM.

### Expected change size

The expected implementation is one small control-event type and waiter, one
input-correlation state machine, approximately four to six hook definitions, a
narrow spinner-observation path, caller migration, and deletion of the old
polling code. The investigation estimate is roughly 300–600 lines of production
code before deletions, plus focused tests. It should not approach thousands of
lines.

That estimate is not permission to satisfy a line budget with a compressed or
implicit design. It is an architectural warning: a much larger implementation
almost certainly means the shared-boundary premise has failed.

## Design

### Separate control coordination from dialog ownership

Reuse the ROM text recorder's validated hook installation and owner-thread
callback structure, but do not make ordinary button waiting drain the text-event
journal. A control wait must never consume dialog before the transcript driver
claims it.

Add a separate transient control-boundary waiter, or an event hub with independent
sequence cursors. Control events are coordination state only. Do not persist or
log them.

The high-level button operation owns semantic completion. The worker still needs
a narrow raw button-pulse primitive for drivers such as standard-dialog
advancement, where the driver itself consumes the resulting sequence of events.
Removing the public `wait_for_animation` switch must not force those internal
pulses through a second competing waiter.

### Correlate each input with its result

A button operation should:

1. record the current control-event sequence;
2. schedule one short deliberate button pulse;
3. observe that the ROM processed that input;
4. ignore progress and transition markers; and
5. complete at the first applicable decision-ready boundary produced after the
   accepted input.

Correlation is required because the idle overworld repeatedly reaches its input
loop. Waiting for the next unqualified overworld event could otherwise complete
before the queued input was consumed.

The operation must also prevent one held button from bleeding into the next
interface. Prefer the shortest pulse already demonstrated to register reliably
rather than using a long hold as an implicit timing delay.

The exact accepted-input hook locations must be selected and verified during a
small prototype. The likely shape is a high-level key-processed path such as the
standard menu's key-pressed branch, or a domain boundary that can inspect the
ROM's already-resolved joypad state while an input operation is pending. Do not
solve correlation by permanently emitting an event from every low-level
`Joypad` or `JoypadLowSensitivity` call.

An idle ready event that occurs after the sequence watermark but before the ROM
has seen the requested button must not satisfy the operation. Conversely, once
the button has been accepted, the operation may pass through several progress,
text, transition, or rendering events before reaching its terminal boundary.

### Control boundaries

Keep the event vocabulary small and caller-oriented. The expected concepts are:

- overworld control ready;
- standard menu ready;
- player step completed; and
- existing text input, menu, battle, and interaction transitions supplied by the
  text-event work.

The driver, not the hook callback, decides which event is terminal for the
current action. For example, a step-completed event is observable progress during
a spinner, while a later non-simulated overworld-ready event is terminal.

The intended terminal policy is:

| Input context | Completion condition |
| --- | --- |
| Standard dialog | Next text-input decision, prepared menu, prepared special interface, battle decision, or restored overworld control; closure alone is only progress |
| Ordinary movement or collision | Next external decision boundary after accepted input, normally overworld ready |
| Warp, ledge, spinner, or scripted movement | Next external decision boundary after all forced input ends |
| Standard menu | Prepared menu input, resulting text decision, prepared special interface, battle decision, or restored overworld control |
| Confirmed battle action | Next battle decision, post-catch naming decision, or restored overworld control; `BATTLE_ENDED` alone is only progress |
| Immediate bespoke interface | Accepted input plus its proven bounded render-frame fence, or the next shared decision boundary |

Do not expose this table as lists of hook names that every tool must understand.
Ordinary callers should retain a simple button API whose emulator-level driver
selects the policy from the current control domain. Spinner traversal is the one
known caller that needs an explicit intermediate-observation option.

### Establish the initial boundary once

Correlation applies to a button operation because the waiter can be armed before
the input is sent. The application's first dispatch has no preceding requested
input: a fresh run follows the manual startup interval, while a restored backup
may have been captured during error handling rather than at a clean boundary.

Perform one explicit bootstrap wait after startup or state restoration that
accepts the next recognized ready boundary without requiring input correlation.
After that, every migrated handler and tool must return at a decision-ready
boundary, so ordinary dispatcher iterations can classify the current state
without waiting again.

The bootstrap must use the same shared boundaries as normal coordination. It is
not a one-off stability check, elapsed delay, or permission to add title-screen
and transition-specific hooks.

### Preserve spinner observations

Navigation currently observes intermediate `GameState` snapshots while a spinner
moves the player through several tiles. Removing animation polling must not reduce
map discovery or lose the spinner route.

Record exact player-step events while a navigation operation has requested
intermediate observation. Capture the corresponding state at the end of the
emulator tick, outside the hook callback, before the next tick advances the ROM.
Do not construct a complete `GameState` inside every permanent hook invocation.

### Keep rendered observations fresh

ROM control state and the rendered screenshot do not always become current at the
same CPU instruction. Deliver semantic boundaries after the worker has completed
the containing emulator tick. Where a bespoke interface performs only a bounded
background transfer, use its deterministic render-frame fence before capturing a
screenshot.

Do not reintroduce visual comparison, elapsed silence, or repeated `GameState`
sampling as a completion rule.

### Failure behavior and ROM coupling

This application supports one required ROM build. Coupling a small hook table to
that build is intentional. As with the existing text recorder, every new
executable address must have a short expected instruction signature checked
before hook installation. A mismatch is a startup error; silently falling back
to screen polling or pretending to support an unrelated ROM is not acceptable.

The main risks are not the number of callbacks but incorrect event correlation,
choosing a progress marker as a terminal boundary, and publishing an observation
before the containing frame renders. Those risks must be exercised directly in
the prototype and integration scenarios below.

## Implementation Sequence

Each review slice is one self-contained commit reviewed before proceeding. At
the end of a slice, every migrated caller must use the complete new behavior
for its assigned scope; callers assigned to later slices remain entirely on the
existing path.

### Stage 1: Replace overworld movement polling

First prove the core mechanism on the required ROM before changing callers:

- arm a pending operation before injecting a short button pulse;
- observe that the ROM accepted the requested button rather than an unrelated
  idle-loop event;
- reach genuine overworld readiness after a move or collision;
- reach prepared standard-menu input after opening the start menu; and
- capture a screenshot only after the containing rendered tick is complete.

If the prototype succeeds, retain the minimal control coordinator, the
validated overworld hook, and the prepared-menu boundary needed when an
overworld action opens the start menu. Overworld readiness must exclude walking,
simulated input, ignored input, NPC movement, door movement, and other
ROM-controlled player movement. Correlated input within an already-open menu
remains Stage 2 work.

Complete the migration through the following self-contained review slices:

1. **Basic overworld button input.** Migrate only the agent-facing overworld
   button tool. Cover ordinary directional movement, collisions, short button
   sequences, action-button dialog, random-battle handoff, and opening the start
   menu. Stop a sequence when control leaves the overworld so remaining buttons
   cannot bleed into text, battle, or menu input. Control coordination may
   observe existing text events but must leave them available to the text-event
   consumer exactly once.
2. **Ordinary navigation.** Migrate routine path traversal, rotation, collision
   handling, and Pikachu-facing adjustments. Leave HMs, forced movement,
   spinners, and Sokoban on the existing animation-settling path.
3. **Forced overworld transitions.** Migrate ledges, warps, Cut, Surf, and other
   scripted movement. Coordinate through the final external decision boundary
   rather than an intermediate coordinate update.
4. **Spinner traversal.** Add the validated player-step progress hook and return
   ordered end-of-tick step observations while waiting for final overworld
   readiness. Preserve the existing spinner route and map-discovery updates.
5. **Sokoban movement.** Migrate the solver after ordinary and forced movement
   have established the complete overworld operation semantics.

Preserve existing text capture and map-update behavior throughout these slices.
Menu, naming, battle-menu, and generic text callers continue using the unchanged
animation-settling path until Stage 2.

### Stage 2: Replace standard menu input polling

Add correlated accepted-input and prepared-input behavior for
`HandleMenuInput`. Prepared menu readiness must occur after cursor placement and
`Delay3`, so a caller may immediately inspect the menu or send the next button.
Keep the existing early `MENU_OPENED` event for text lifecycle detection, but do
not use it as rendered menu readiness.

Add naming readiness only if the prototype demonstrates that the standard
boundaries cannot cover automated naming. Establish an explicit coordinator
policy for immediate bespoke interfaces and verify the bounded render fence on
the actual naming, town-map/status, and Pokédex-style screens used by the
application. If one of those screens performs unbounded work without reaching a
shared boundary, stop rather than silently treating the frame fence as a timeout.

Migrate deterministic start-menu, bag, party, item-use, party-swapping, battle
menu, naming, and generic text-screen button workflows. Make dialog handoff wait
for prepared menu readiness rather than the earlier menu-entry hook. Keep raw
button pulses internal to the dialog/control drivers; migrated callers use the
semantic button operation.

### Stage 3: Remove the stability heuristic

Finish the boundary invariant before deleting the old checker:

- make ordinary dialog continue beyond `INTERACTION_CLOSED` until the next real
  decision-ready domain;
- make battle completion continue beyond `BATTLE_ENDED` through palette, map,
  and post-battle restoration to either naming, another decision, or overworld
  readiness;
- add the one-time startup/restoration bootstrap boundary wait;
- audit every production button and dispatcher caller for a defined completion
  policy; and
- verify that post-boundary `GameState` and screenshots describe the same
  rendered interface.

Then remove both dispatcher settling calls,
`wait_for_animation_to_finish`, the `wait_for_animation` argument, its polling
constants, and any screen-comparison property made dead by the deletion. No
production path may retain screen stability as a fallback.

## Out of Scope

- Hooking every joypad poll, animation, move, item, map, or custom screen.
- Building a general interpreter for ROM control flow.
- Reconstructing screenshots or gameplay state inside hook callbacks.
- Changing dialog transcript ownership established by the ROM text-event system.
- Changing agent prompts, prompt caching, rolling memory, or iteration boundaries.
- Patching or rebuilding the ROM.

## Validation

Use focused unit coverage for the substantive event-correlation rules and reuse
or narrowly extend the repository's existing bounded integration scenarios for
actual ROM behavior. Do not create a separate test that simply mirrors every
hook or line in the policy table. Automated tests must not read files under
`resources/`.

Verify at least:

- an ordinary menu cursor press can be followed immediately by another press;
- a collision and a successful one-tile move both return at overworld readiness;
- a warp or random encounter does not return at the intermediate step event;
- Cut and Surf return at the resulting text, menu, battle, or overworld boundary;
- a long spinner retains intermediate map observations and stops only when
  simulated movement releases control;
- battle completion does not expose the whiteout or partially restored overworld;
- initial dispatch after startup or state restoration waits for one real control
  boundary without using screen stability;
- ambient cursor, sprite, or tile animation cannot prevent progress;
- text generated by an emulator action remains available to the text-event
  consumer exactly once; and
- screenshots returned after a boundary show the corresponding current interface.

## Acceptance Criteria

- [ ] No production caller uses screen stability to infer completion.
- [ ] `wait_for_animation_to_finish` and its polling constants are removed.
- [ ] Dispatcher selection occurs at a semantic gameplay boundary without two
      arbitrary settling waits.
- [ ] Startup and restored states establish that boundary once before the first
      dispatch.
- [ ] Button operations cannot complete on an unrelated idle-loop event or bleed
      a held input into the next interface.
- [ ] Standard menus and ordinary movement complete materially faster than the
      former 750 ms minimum wait.
- [ ] Long battle, warp, field-move, and scripted sequences do not return at an
      intermediate animation or transition marker.
- [ ] `INTERACTION_CLOSED` and `BATTLE_ENDED` remain progress markers rather than
      permission to capture an unfinished observation.
- [ ] Spinner traversal preserves its intermediate observations and map updates.
- [ ] Control waiting cannot consume or duplicate text events.
- [ ] Hook addresses and memory interpretation remain confined to parsers and are
      guarded by instruction signatures.
- [ ] A hook-signature mismatch fails startup; there is no compatibility or
      screen-polling fallback.
- [ ] The implementation stays within the small shared-boundary scope rather than
      adding hooks for individual animations or custom screens.
