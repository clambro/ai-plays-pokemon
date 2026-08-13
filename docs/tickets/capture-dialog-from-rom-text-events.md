# Ticket: Capture Dialog from ROM Text Events

## Outcome

Replace timing-based dialog observation with one emulator-level text-event
recorder driven by the ROM's own text engine. Battle, text, and overworld tools
must consume the same ordered event stream so completed dialog is retained even
when it pauses unpredictably, advances automatically, scrolls, or disappears
before the next gameplay handler runs.

The rendered screen remains useful for screenshots, menus, naming screens, and
current-state observations. It must no longer be the authority for deciding
when standard dialog is complete or for reconstructing dialog from transient
animation frames.

## Current Failures

`DialogReader` observes periodically sampled `GameState` objects and treats
visual stability, cursor detection, and line-prefix comparisons as evidence
about the ROM's text state. The battle and text handlers then add their own
timing rules on top:

- battle can stop after roughly three quarters of a second without a visual
  change even though automatically progressing battle text has not finished;
- the blinking cursor can be absent during a sampling window even though the
  ROM is waiting for input;
- EXP-bar and HUD redraws can briefly leave the dialog border in place while
  replacing its contents, causing valid-looking corrupted text to be retained;
- the text handler uses cursor sampling and fixed sleeps to decide whether to
  advance or close dialog; and
- the overworld action-button tool reads only the final visible dialog box,
  even though item-pickup messages can disappear before that read occurs.

These are not tuning problems. A stationary screen is not a semantic text
boundary, and a visible dialog border does not prove that its interior still
contains dialog.

## Validated ROM Behavior

Standard message-box dialog across battle and overworld converges on the common
text engine in `resources/pokeyellow/home/text.asm` and
`resources/pokeyellow/home/text_script.asm`. Dynamic player, rival, trainer,
Pokémon, item, and move names and numeric values are resolved by that engine
before their character IDs are placed in the WRAM tile map.

The following execution points expose the semantics that visual sampling is
currently guessing:

- `NextTextCommand` reads the next command. When it points to `TX_END`, the
  current text program has completed and the current page can be captured
  before its caller redraws the screen. `TX_END` is a page/text-program
  boundary, not necessarily the end of the surrounding interaction.
- `WaitForTextScrollButtonPress` is the shared manual-input loop. It is called
  both by `ManualTextScroll` and directly by `DisplayTextID` after ordinary NPC
  and sign dialog. Observing `ManualTextScroll` alone would miss those direct
  final waits.
- `_ContTextNoPause` and `TextCommand_SCROLL` are the destructive automatic
  scroll paths. The completed page must be captured before either routine moves
  and clears its rows.
- `TextCommand_PAUSE` waits up to 30 frames and then continues automatically.
  Its silence must not be interpreted as completion and it requires no input.
- `TextCommand_WAIT_BUTTON`, `TextCommand_PROMPT_BUTTON`, `<PROMPT>`, `<CONT>`,
  paragraphs, and pages eventually enter the shared button-wait loop when they
  require input.
- `HandleMenuInput` marks a real interactive menu boundary. Dialog automation
  must stop and leave the choice to the applicable gameplay agent.
- the completed `CloseTextDisplay` path marks the end of an ordinary overworld
  text interaction after the window and map display have been restored.
- battle menu/input and battle-exit paths provide corresponding battle decision
  and completion boundaries.

Visible item pickups confirm why the recorder must operate below the handler
layer. `PickUpItem` hides the object, sets
`wDoNotWaitForButtonPressAfterDisplayingText`, prints the found-item text, and
returns to `DisplayTextID`. That flag skips the normal final button wait;
`HoldTextDisplayOpen` retains the box only while the initiating A button remains
held and then closes it. A `TX_END` event occurs while the complete message is
still in WRAM even if no later handler ever sees the box.

`TX_START_ASM` can execute arbitrary assembly, so implementing a second static
interpreter for ROM text scripts would not be reliable. Runtime hooks observe
the actual resolved behavior, including nested `PrintText` calls made by those
scripts.

## Design

### Emulator-owned event recorder

Register low-frequency PyBoy execution hooks once, after the initial save state
has been loaded and before the worker begins normal ticking. Keep the recorder
and its journal beside the thread-owned PyBoy instance rather than in an agent
or gameplay domain.

Each relevant hook appends a small immutable event with:

- a monotonic sequence number;
- the emulator frame number;
- the event kind;
- a stable snapshot of the standard dialog page, when one exists; and
- enough control metadata to distinguish pending input, completed input,
  automatic progression, menu input, interaction closure, and battle exit.

The journal is transient coordination state, not gameplay history. Once an
event has been consumed, the resulting dialog belongs in the applicable tool
result and rolling memory. Do not persist the journal or log dialog content.

PyBoy invokes hook callbacks synchronously from `tick()` on the existing owner
thread. Callbacks must copy only the small amount of state needed for the event,
must never block, and must never invoke asynchronous emulator operations.
Expose an asynchronous worker API that waits for or drains journal events
without blocking the owner thread.

### Stable page capture

Capture a standard message box only when its raw WRAM border and window state
are valid at one of the semantic boundaries above. Decode the dialog rows from
the character IDs written by the text engine at that moment. Do not construct a
complete `GameState` inside a hook and do not retain later VRAM/HUD frames as
dialog.

The transcript reducer should retain the existing useful behavior of removing a
line repeated by two-row scrolling, while deduplicating identical snapshots
produced by nested text programs or adjacent semantic hooks. It must not use
line prefixes, elapsed silence, or arbitrary animation stability to decide
whether a page is complete.

Special interfaces that do not use the standard message box—naming, status,
town-map, slot-machine, and other custom layouts—remain ordinary current-screen
observations. The recorder should not reinterpret every `PlaceString` call as
dialog.

### Input lifecycle

Observe both the active loop and the exit of
`WaitForTextScrollButtonPress`. This handles a save state restored in the middle
of a wait and prevents an additional A press when the initiating held button
already satisfied the wait before Python consumed the event.

The consumer presses A only when the latest ordered events still describe an
unresolved standard-dialog wait. Use a short deliberate pulse and then wait for
the ROM's wait-exit or subsequent semantic event. Never press through
`HandleMenuInput` or another decision interface automatically.

Several hook events may occur during one emulated frame—for example, wait
entry, wait exit, scroll, and text end. Preserve their order and process the
complete available batch before deciding to send input.

Elapsed time must not become a text-completion rule.

### Consumption and ownership

The application has one serial gameplay workflow, so one runtime consumer
cursor can claim text events exactly once. Take or advance that cursor at the
same deterministic action boundary that owns the resulting dialog. Events
already included in an overworld tool result must not be repeated when control
passes to the text handler, while later pages from the still-open interaction
must remain available to that handler.

### Domain integration

Battle actions should begin observing before the final confirming input, retain
all pages produced while attacks, damage, EXP, fainting, switching, capture, or
escape resolves, advance only explicit ROM button waits, and return when the
next battle input interface is ready or battle state exits. HUD and EXP redraws
produce no text event and therefore cannot corrupt the transcript.

The text handler should use the same driver for ordinary dialog. It should stop
at menus, yes/no questions, naming and other special screens, battle entry, or
ordinary interaction closure, leaving those decisions to the existing agent
and dispatcher.

Overworld emulator-input tools should claim any text events caused by their
actions, even when the standard dialog has already closed. This includes action
button interactions, visible and hidden item pickups, field and inventory item
messages, and scripted interactions reached during deterministic movement.
Remove the current special case that attempts to recover an item message only
from the final visible `GameState`.

Audit all deterministic emulator-input tools so ephemeral text is neither lost
nor duplicated. Do not make every tool understand ROM hooks; expose one shared
transcript/driver API from the emulator layer.

## ROM Hook Safety

PyBoy 2.7 execution hooks replace one instruction in emulated ROM memory with a
breakpoint, invoke the callback before advancing the program counter, restore
and single-step the original opcode, and then reinstall the hook. They do not
modify the ROM file.

The ignored local decompilation currently provides symbol names and addresses,
but a fresh repository clone does not contain its generated `.sym` file. Runtime
code must therefore keep a tracked hook table and short expected instruction
signatures in the ROM-text parser. The parser owns all ROM and WRAM addresses,
hook interpretation, and standard-page decoding. A signature mismatch is a
startup error; hooking the wrong executable address can corrupt emulation.

## Implementation Sequence

### Stage 1: Add the ROM text-event foundation

Add the ROM-text parser with its hook table, signature checks, callback
interpretation, and standard-page decoding. Add immutable event types, the
worker-owned journal, non-blocking async access, and transcript reducer.
Register hooks during emulator setup. Cover the core reducer and journal logic
without changing agent behavior.

### Stage 2: Replace battle dialog polling

Begin event consumption before each battle tool's final input and drive dialog
until the next input boundary or battle exit. Replace battle's animation
stability and cursor polling while retaining the current tool result, rolling
memory, screenshot, and fresh battle-state behavior.

### Stage 3: Unify text and overworld consumption

Move ordinary text advancement and overworld ephemeral-text capture onto the
same driver. Remove the fixed text-handler sleeps, cursor sampling, and the
overworld final-screen item-message workaround. Audit all emulator-input tools,
remove `DialogReader` once no consumer remains, and delete this completed ticket
in the same stage. Update high-level workflow documentation only if the
implemented architecture changes what that document currently claims.

Each stage must be a self-contained commit with its own relevant validation and
documentation. Do not leave behavior knowingly dependent on changes from a
later stage.

## Out of Scope

- Interpreting ROM text scripts statically in Python.
- Hooking every printed character or every `PlaceString` call.
- Patching or rebuilding the ROM to add a RAM transcript buffer.
- Automatically navigating menus, yes/no choices, naming screens, or custom
  interfaces.
- Treating the event journal as durable gameplay memory.
- Changing prompt-cache keys, agent conversation lifetime, or rolling-memory
  compaction.

## Validation

Use focused behavior-level coverage for the event reducer and consumers rather
than one test per text command or string. Cover:

- automatically progressing text that remains visually stationary longer than
  the old animation threshold;
- a manual page wait followed by exactly one deliberate A press;
- an initiating held A that completes the wait before the event is consumed,
  without sending another A;
- a visible or hidden item message captured at `TX_END` and retained after the
  dialog and object disappear;
- multi-page NPC dialog that scrolls without duplicated lines;
- a yes/no or other menu that is returned to the agent and never
  auto-advanced;
- battle effectiveness, fainting, and EXP text followed by HUD redraws, with no
  corrupted suffix;
- forced battle choices and battle exit;
- ordered multiple events emitted in one frame;
- exactly-once ownership when an interaction crosses from overworld to the text
  handler.

Automated tests must not read files under `resources/`.

## Acceptance Criteria

- [ ] Battle, text, and overworld use one emulator-owned dialog event source.
- [ ] Standard dialog completion and input requirements come from ROM execution
      events, not screen-stability timing or cursor sampling.
- [ ] Automatically advancing text is never ended merely because the screen is
      temporarily unchanged.
- [ ] Manual waits receive one deliberate input only while the ROM remains in
      that wait.
- [ ] Item-pickup text survives after its dialog and world object disappear.
- [ ] Battle transcripts contain complete semantic text and no HUD/EXP redraw
      corruption.
- [ ] Menus and other decisions are never automatically advanced as dialog.
- [ ] Interactions crossing handler boundaries retain every page exactly once.
- [ ] The emulator rejects a ROM whose required hook signatures do not match.
- [ ] No dialog content is emitted to operational logs or persisted in a second
      history store.
- [ ] The old `DialogReader` timing heuristics and overworld final-screen dialog
      workaround are removed once all supported consumers use the recorder.
