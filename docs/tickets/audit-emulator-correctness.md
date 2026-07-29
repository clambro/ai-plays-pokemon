# Ticket: Audit Emulator Correctness Against the ROM

## Outcome

Verify that the emulator integration reads and controls the supported Pokémon
Yellow Legacy ROM exactly as the game implements it. Correct confirmed mistakes
and leave the code's non-obvious assumptions traceable to the relevant assembly
labels or routines.

This is a correctness audit, not an emulator rewrite. Preserve the existing
public behavior and architecture unless the ROM proves that behavior wrong.

## Sources of Truth

Audit the exact ROM build used by this project against:

1. `resources/pokeyellow/pokeyellow.sym` and `pokeyellow.map`;
2. the corresponding assembly under `resources/pokeyellow`;
3. bounded observations from the running ROM and existing save-state fixtures;
4. `../pokemon-speedrun-optimizer` as a source of known edge cases and useful
   cross-checks.

The speedrun project is not authoritative where its ROM, patch, or purpose
differs. Do not rely on generic Pokémon Red/Blue/Yellow documentation when the
local Yellow Legacy assembly can answer the question directly.

## Audit Scope

### Memory parsing

- Verify every hardcoded address, structure size, offset, terminator, bitfield,
  enum value, byte order, and coordinate conversion in `emulator/parsers`.
- Pay particular attention to similarly named or overlapping WRAM fields,
  scratch fields whose meaning changes by game state, and values that are only
  valid during part of a transition.
- Audit player, party, PC, inventory, battle, map, screen, sprite, sign, and
  warp parsing, including Yellow Legacy additions.
- Check that parsers handle title screens, menus, transitions, scripted events,
  fainting and send-out sequences, Safari battles, and other partially
  initialized states without interpreting unrelated memory as valid gameplay
  state.
- Compare duplicated lookup tables and tile classifications with the exact ROM
  data rather than assuming the original game's values still apply.

Initial high-risk areas include battle-type and status fields, active-versus-
stored Pokémon layouts, current-map dimension fields, sprite visibility and
movement flags, collision pointers, dialog detection, and special warp records.
These are leads to investigate, not assumed defects.

### Emulator control

- Verify PyBoy construction, frame ticking, rendering and sound pacing, button
  press/release duration, save/load behavior, and worker-thread ownership
  against the supported PyBoy version.
- Audit every timing or screen-stability heuristic used to wait for movement,
  animations, menus, and text. Distinguish deliberate real-time pacing from
  waits that are attempting to infer a ROM state the assembly exposes directly.
- Check deterministic input sequences in navigation, text handling, and battle
  tools for hidden menu-position, animation, disabled-move, forced-switch, or
  transient-state assumptions.
- Preserve the small real-time pacing delay required to prevent PyBoy audio
  catch-up unless a better verified mechanism replaces it.

### Map and screen semantics

- Trace coordinate systems from ROM map blocks and sprite state through screen
  projection and explored-map persistence.
- Verify collision, elevation pairs, ledges, spinners, Cut, Surf, Strength,
  boulder holes, pressure plates, map connections, signs, sprites, Pikachu, and
  warps against the routines that actually govern movement.
- Verify text decoding, dialog-box recognition, cursor handling, page
  transitions, menu cursors, and the shared dialog reader against the tilemap
  and text-engine assembly.

## Implementation Approach

- Keep a concise audit ledger mapping each reviewed Python assumption to its ROM
  symbol or routine and the result: confirmed, corrected, or intentionally
  heuristic. This ledger should make later ROM or PyBoy upgrades reviewable
  without becoming a second implementation guide.
- Centralize repeated memory addresses and record their assembly symbol names.
  Prefer checking addresses against the generated symbol file during
  development; do not make normal application startup depend on the decomp
  checkout.
- Fix confirmed defects in focused changes. Do not bundle speculative cleanup
  or broad schema/API redesign into the audit.
- Add regression coverage for actual findings and important ROM boundaries.
  Tests should assert observable game-state or control behavior, not mirror
  implementation details. Reuse ignored save-state fixtures carefully and
  never modify the originals in place.
- When behavior cannot be proven statically, use a small bounded probe against
  a copied state and document what was observed. Do not launch the gameplay
  loop or make model calls.

## Out of Scope

- Reimplementing battle mechanics in Python.
- Replacing PyBoy.
- General agent, memory, map-routing, or package-structure refactors.
- Expanding the parsed game state merely because more ROM fields are available.
- Fixing behavior in the speedrun project.

## Done When

- Every emulator parser and deterministic emulator-control path has been traced
  to the exact ROM/PyBoy behavior it depends on.
- Confirmed parsing, timing, and input-sequence mistakes are corrected.
- Non-obvious addresses and heuristics identify the symbols or routines that
  justify them.
- Important transient and special states no longer produce confidently wrong
  structured state.
- The audit ledger records coverage and any deliberately unresolved heuristic.
- Focused regression tests cover real findings, and the existing static and
  test suites pass.
