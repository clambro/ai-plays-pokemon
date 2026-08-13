# Ticket: Replace Animation Polling with ROM Control Boundaries

## Dependency and Decision Gate

This is a dedicated follow-up to
[`Capture Dialog from ROM Text Events`](capture-dialog-from-rom-text-events.md).
Do not begin it until that ticket is complete and its event-driven behavior has
worked reliably in real gameplay across battle, overworld dialog, and transient
item text.

The completed text ticket should establish whether PyBoy execution hooks,
instruction-signature validation, owner-thread callbacks, and asynchronous event
delivery are reliable enough to use as emulator coordination primitives. If that
premise does not hold in practice, reassess this ticket rather than extending the
hook system.

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

- the text-event driver established by the prerequisite ticket reports standard
  dialog input and completion boundaries;
- `HandleMenuInput` covers the standard start, bag, party, battle, list, and
  choice menus;
- the overworld loop exposes when external control has returned after movement,
  map scripts, warps, battles, and simulated input; and
- the player-step completion path exposes precise intermediate movement needed
  while observing spinners.

Naming is the only bespoke interface currently automated directly enough to
justify a dedicated readiness boundary if the standard boundaries do not cover
its completion.

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

### A universal joypad hook is the wrong abstraction

Many ROM input loops poll the low-level joypad routines extremely frequently.
Hooking every poll would impose Python callback overhead on hot ROM loops and
would still not distinguish a meaningful decision from input used only to skip
an effect.

Use a few low-frequency, named engine boundaries with validated instruction
signatures. All ROM and WRAM addresses remain confined to parser modules.

## Scope Constraint

This ticket must not become a model of every interactive routine in the ROM.
The expected addition is approximately four to six executable hook locations:

1. the existing text and standard-menu boundaries;
2. one overworld control-ready boundary;
3. one player-step progress boundary for spinner observation; and
4. a naming readiness boundary only if required by the automated naming tool.

Immediate bespoke interfaces that only need their completed WRAM-to-VRAM update
use a short deterministic frame fence derived from the ROM's rendering cycle.
They do not receive one hook per screen.

If implementation requires more than roughly six new hook addresses, begins
naming individual animations or maps, or requires tool-specific knowledge in the
event recorder, stop and reconsider the design. That indicates the work has
crossed from observing shared engine behavior into reimplementing the ROM.

## Design

### Separate control coordination from dialog ownership

Reuse the prerequisite ticket's validated hook installation and owner-thread
callback structure, but do not make ordinary button waiting drain the text-event
journal. A control wait must never consume dialog before the transcript driver
claims it.

Add a separate transient control-boundary waiter, or an event hub with independent
sequence cursors. Control events are coordination state only. Do not persist or
log them.

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

## Implementation Sequence

### Stage 1: Replace overworld movement polling

Add correlated control waiting with the overworld-ready and player-step events.
Migrate navigation, ordinary overworld button input, ledges, HM use, scripted
movement, and spinner observation. Preserve existing text capture and map-update
behavior. Callers outside this stage continue using the existing behavior.

### Stage 2: Replace standard menu input polling

Make standard-menu readiness safe for immediate subsequent input and migrate the
battle, inventory, party, naming, and text-screen menu workflows. Use the bounded
render fence for immediate bespoke interfaces rather than adding screen-specific
hooks.

### Stage 3: Remove the stability heuristic

Replace the dispatcher's duplicate settling waits with the established gameplay
boundary invariant. Remove `wait_for_animation_to_finish`, the
`wait_for_animation` button argument, `DialogReader` integration left solely for
animation observation, and all remaining callers.

Each stage is a self-contained commit. At the end of every stage, each caller
must use either the complete new behavior for its domain or the unchanged prior
behavior; do not leave a workflow split across both coordination systems.

## Out of Scope

- Hooking every joypad poll, animation, move, item, map, or custom screen.
- Building a general interpreter for ROM control flow.
- Reconstructing screenshots or gameplay state inside hook callbacks.
- Changing dialog transcript ownership established by the prerequisite ticket.
- Changing agent prompts, prompt caching, rolling memory, or iteration boundaries.
- Patching or rebuilding the ROM.

## Validation

Use focused unit coverage for the event-correlation state machine and bounded
integration scenarios for the actual ROM boundaries. Automated tests must not
read files under `resources/`.

Verify at least:

- an ordinary menu cursor press can be followed immediately by another press;
- a collision and a successful one-tile move both return at overworld readiness;
- a warp or random encounter does not return at the intermediate step event;
- Cut and Surf return at the resulting text, menu, battle, or overworld boundary;
- a long spinner retains intermediate map observations and stops only when
  simulated movement releases control;
- battle completion does not expose the whiteout or partially restored overworld;
- ambient cursor, sprite, or tile animation cannot prevent progress;
- text generated by an emulator action remains available to the text-event
  consumer exactly once; and
- screenshots returned after a boundary show the corresponding current interface.

## Acceptance Criteria

- [ ] The prerequisite ROM-text event system has first proved reliable in real
      gameplay.
- [ ] No production caller uses screen stability to infer completion.
- [ ] `wait_for_animation_to_finish` and its polling constants are removed.
- [ ] Dispatcher selection occurs at a semantic gameplay boundary without two
      arbitrary settling waits.
- [ ] Button operations cannot complete on an unrelated idle-loop event or bleed
      a held input into the next interface.
- [ ] Standard menus and ordinary movement complete materially faster than the
      former 750 ms minimum wait.
- [ ] Long battle, warp, field-move, and scripted sequences do not return at an
      intermediate animation or transition marker.
- [ ] Spinner traversal preserves its intermediate observations and map updates.
- [ ] Control waiting cannot consume or duplicate text events.
- [ ] Hook addresses and memory interpretation remain confined to parsers and are
      guarded by instruction signatures.
- [ ] The implementation stays within the small shared-boundary scope rather than
      adding hooks for individual animations or custom screens.
