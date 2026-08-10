# Ticket: Make Warp Destinations Coordinate-Aware

## Outcome

Retain the destination warp index already present in normal ROM warp records,
resolve destination coordinates when policy permits, and persist directed
transition endpoints so routing can distinguish multiple entrances to the same
map. Replace the current adjacency-based single/double classification with the
actual per-record activation rule so prompts and route execution know whether a
warp activates on entry or requires another directional step.

The durable fact is:

```text
(source map, source coordinate)
    -> (destination map, destination coordinate)
```

Region/component IDs must not be stored with transitions because regions are
derived from incomplete explored terrain and may change.

## ROM Findings

The Yellow decomp defines each normal warp as four bytes:

```text
source Y
source X
zero-based destination warp index
destination map ID
```

The current parser ignores byte 2. The destination coordinate is resolved by
loading the indexed warp record from the destination map and using that
record's source Y/X coordinate. The game performs the equivalent lookup in
`LoadDestinationWarpPosition`.

### Warp activation

The ROM has no single/double-warp distinction. `CheckWarpsNoCollision` matches
each warp record independently. A matching record activates immediately when
`IsPlayerStandingOnDoorTileOrWarpTile` recognizes the tile under the player.
Otherwise, `ExtraWarpCheck` requires either an outward-facing map-edge movement
or a direction whose tile in front appears in the corresponding warp-carpet
table.

The current parser instead joins every pair of Manhattan-adjacent records and
guesses the entry direction from the pair orientation and whether its row or
column is zero. This produces both false pairs and false directions:

- Celadon Mansion 2F has adjacent stairs at `(1, 6)` and `(1, 7)` with different
  destinations. Their Mansion tiles are immediate warp tiles, so both are
  independent step-on warps.
- Celadon City's adjacent Mansion entrance records are a genuine shared
  entrance whose tiles in front require movement down.
- Route 11 has two vertical pairs leading through opposite sides of a gate.
  The records at column 49 require movement right, while those at column 58
  require movement left. Pair orientation alone cannot distinguish them.

Destination equality is also insufficient because activation is determined by
the current tileset and surrounding tiles, not by the destination record.
Represent activation per warp as step-on or a required direction; do not merge
adjacent records into one semantic entrance.

Relevant decomp sources:

- `resources/pokeyellow/macros/scripts/maps.asm`
- `resources/pokeyellow/ram/wram.asm`
- `resources/pokeyellow/home/overworld.asm`
- `resources/pokeyellow/engine/overworld/player_state.asm`
- `resources/pokeyellow/data/tilesets/door_tile_ids.asm`
- `resources/pokeyellow/data/tilesets/warp_tile_ids.asm`
- `resources/pokeyellow/data/tilesets/warp_carpet_tile_ids.asm`
- `resources/pokeyellow/data/maps/map_header_banks.asm`
- `resources/pokeyellow/data/maps/map_header_pointers.asm`

Resolution may read the exact ROM through its banked map headers or use a table
generated from decomp `warp_event` declarations. A generated table must be
tied to the exact ROM build/checksum.

## Scope

- Add the destination warp index to the parsed warp representation.
- Replace `WarpType` and adjacency-based pairing with per-record activation
  metadata: step-on, up, down, left, or right.
- Resolve activation using the loaded map blocks, tileset blockset, tileset
  door/warp IDs, directional warp-carpet IDs, and the map-specific branch in
  `ExtraWarpCheck`.
- Keep adjacent records independent even when they share an activation
  direction or destination.
- Persist typed known-warp metadata independently of free-form entity
  descriptions, including the activation rule needed for later route execution.
- Persist directed transitions with source/destination endpoints, transition
  kind, provenance, and observation timestamps.
- Allow multiple destinations from one source when scripted or state-dependent
  behavior requires it.
- Observe map changes at the general emulator/action boundary so button presses,
  navigation, scripts, forced movement, and other actions are covered.
- Record the before/after map and player coordinate whenever a map changes.
- Resolve normal destination coordinates from the ROM when the active
  information policy allows it.
- Update prompts to include the destination coordinate when it is agent-visible
  and give the exact per-warp entry instruction. Remove the single/double-warp
  explanation.

Suggested provenance:

- observed;
- ROM-resolved; and
- inferred.

Suggested transition kinds include normal warp, dungeon hole, map connection,
scripted, Fly, Dig/Escape Rope, blackout, and unknown. Transitions remain
directed; never invent a reverse edge.

## Information Policy

Observed mode is the default:

- the destination warp index may be stored internally;
- destination coordinates become prompt-visible only after traversal or other
  discovery; and
- observed before/after endpoints are authoritative.

An optional ROM-informed mode may expose normal warp destinations immediately.
Prompts must not imply those endpoints were personally observed. Inferred
transitions must remain distinguishable from confirmed information.

## Special Cases

Normal indexed lookup does not cover:

- destination map `0xff`/dynamic `wLastMap`;
- dungeon holes and special warp tables;
- outdoor map connections;
- scripted map changes;
- Fly, blackout, Dig, Escape Rope, and special placements.

The general transition observer is the required fallback. Prefer a concrete
observed destination over placeholders such as `OUTSIDE`.

## Out of Scope

- Revealing complete unexplored maps.
- Persisting connected-component IDs.
- Assuming all doors, ladders, or holes are reciprocal.
- Building the global route planner; that belongs to
  [`provisional-map-regions-and-routing.md`](provisional-map-regions-and-routing.md).

## Validation

Cover normal record parsing, destination index bounds, per-record activation,
ROM lookup against known decomp examples, ROM checksum mismatch, transition
observation, directed/non-reciprocal edges, dynamic exits, holes, outdoor
connections, and prompt visibility under both information policies. Activation
coverage must include the independent Celadon Mansion 2F stairs, the shared
Celadon City entrance, both directions through the Route 11 gate, and a genuine
map-edge exit.

## Acceptance Criteria

- [ ] Normal parsed warps retain their zero-based destination warp index.
- [ ] Adjacent warp records remain independent and carry their own activation
      rule and destination.
- [ ] Step-on, map-edge, and directional warp-carpet activation match the ROM.
- [ ] Known warp metadata remains available when a map is not current.
- [ ] Normal destination coordinates resolve correctly for the configured ROM.
- [ ] Observed map changes persist exact directed endpoint pairs.
- [ ] Special and dynamic transitions fall back to observation.
- [ ] Provenance and visibility policy are explicit.
- [ ] Prompts show the most specific permitted destination without leaking full
      map terrain.
- [ ] Prompts and route execution use exact entry directions and no longer rely
      on a single/double-warp heuristic.
- [ ] Stored transitions use coordinates, not provisional region IDs.
