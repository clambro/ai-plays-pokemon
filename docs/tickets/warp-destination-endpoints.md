# Ticket: Make Warp Destinations Coordinate-Aware

## Outcome

Retain the destination warp index already present in normal ROM warp records
and use it to resolve each normal warp's destination coordinate directly from
the loaded ROM. Replace the adjacency-based single/double classification with
the actual per-record activation rule so prompts and route execution know
whether a warp activates on entry or requires another directional step.

Retain the bounded strip and coordinate alignment of each outdoor map
connection as well. A cardinal connection does not make every tile along that
edge a valid transition point.

Together, the parsed record identifies:

```text
(source map, source coordinate)
    -> (destination map, destination coordinate)
```

This ticket does not persist a transition graph. That belongs with the future
global route planner, which will have an actual consumer for observed and
scripted transitions.

## ROM Findings

The Yellow decomp defines each normal warp as four bytes:

```text
source Y
source X
zero-based destination warp index
destination map ID
```

Before stage 1, the parser ignored byte 2. The destination coordinate is
resolved by loading the indexed warp record from the destination map and using
that record's source Y/X coordinate. The game performs the equivalent lookup
in `LoadDestinationWarpPosition`.

### Warp activation

The ROM has no single/double-warp distinction. `CheckWarpsNoCollision` matches
each warp record independently. A matching record activates immediately when
`IsPlayerStandingOnDoorTileOrWarpTile` recognizes the tile under the player.
Otherwise, `ExtraWarpCheck` requires either an outward-facing map-edge movement
or a direction whose tile in front appears in the corresponding warp-carpet
table.

Before stage 1, the parser instead joined every pair of Manhattan-adjacent
records and guessed the entry direction from the pair orientation and whether
its row or column was zero. This produced both false pairs and false
directions:

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

The ROM also contains an inaccessible Celadon City record at `(19, 39)` that
points to Celadon Mart 5F. No current tile or directional input activates it,
and the Celadon City script does not enable it later. It is vestigial raw data,
not an application-level "inactive warp," so actionable warp parsing excludes
it.

Resolution should read the exact loaded ROM through its banked map headers, as
the game does, rather than introducing a second generated source of truth.

### Outdoor map connections

The four connection records copied into WRAM contain more than the connected
map ID. Each 11-byte `map_connection_struct` also carries the source and
destination strip pointers, strip length, connected-map width, Y/X alignment,
and view pointer. Before stage 2, the parser retained only the map ID, and
`get_map_boundary_tiles()` consequently advertised every accessible cell on
that edge as an exit.

Connection availability must be limited to the strip encoded by the ROM and
must preserve the coordinate alignment needed to map a source boundary cell to
its destination coordinate. For example, Saffron City's north connection to
Route 5 occupies columns 10 through 29; column 0 is on the north edge but is not
a Route 5 exit.

Relevant code and decomp sources include:

- `emulator/parsers/map.py` (`parse_map_state`);
- `agent/overworld/tools/navigate/utils.py` (`get_map_boundary_tiles`);
- `resources/pokeyellow/macros/ram.asm` (`map_connection_struct`); and
- `resources/pokeyellow/macros/scripts/maps.asm` (`connection`).

## Scope

- Add the destination warp index to the parsed warp representation.
- Replace `WarpType` and adjacency-based pairing with per-record activation
  metadata: step-on, up, down, left, or right.
- Resolve activation using the loaded map blocks, tileset blockset, tileset
  door/warp IDs, directional warp-carpet IDs, and the map-specific branch in
  `ExtraWarpCheck`.
- Keep adjacent records independent even when they share an activation
  direction or destination.
- Resolve normal destination coordinates from the destination map's indexed
  warp record in the loaded ROM.
- Leave dynamic destinations and invalid destination indices unresolved.
- Parse and retain each outdoor connection's valid source strip and coordinate
  alignment instead of reducing it to a connected map ID.
- Use those bounds when advertising reachable map-edge exits, and preserve the
  source-to-destination coordinate mapping for later route execution.
- Update prompts to include a resolved coordinate only when the destination map
  is already known, and give the exact per-warp entry instruction. Remove the
  single/double-warp explanation.

## Prompt Visibility

Destination indices and resolved coordinates are parser data. A resolved
coordinate becomes prompt-visible only when the existing `known_map_ids` set
already considers its destination map known. An unvisited destination keeps
the existing generic exploration description. No additional policy or
provenance layer is needed for this ticket.

## Special Cases

Normal indexed lookup does not cover:

- destination map `0xff`/dynamic `wLastMap`;
- dungeon holes and special warp tables;
- outdoor map connections;
- scripted map changes;
- Fly, blackout, Dig, Escape Rope, and special placements.

These cases remain unresolved here. Their observed endpoints can be added with
the global route planner, when the application has somewhere useful to store
and consume them.

## Out of Scope

- Revealing complete unexplored maps.
- Persisting connected-component IDs.
- Assuming all doors, ladders, or holes are reciprocal.
- Persisting observed transitions, timestamps, or provenance.
- Building a transition-observer or endpoint-visibility policy subsystem.
- Building the global route planner; that belongs to
  [`provisional-map-regions-and-routing.md`](provisional-map-regions-and-routing.md).

## Staged Implementation Plan

Each stage is a self-contained commit that leaves the project valid and
establishes the inputs needed by the next stage.

1. **Parse actionable warp activation** (`fcd7433`). Retain the destination warp
   index, replace `WarpType` and adjacency pairing with one working activation
   instruction per independent record, exclude inaccessible raw records, and
   update model-facing instructions.
2. **Model bounded outdoor connections** (`fbfe411`). Parse each connection's
   valid source strip and coordinate alignment, advertise only valid boundary
   exits, and preserve source-to-destination coordinate mapping.
3. **Resolve normal warp destination coordinates.** Read the destination map's
   indexed warp record from the loaded ROM, retain its coordinate on `Warp`,
   leave dynamic or invalid destinations unresolved, and include the coordinate
   in the existing warp description when the destination map is already known.

## Validation

Cover normal record parsing, destination index bounds, per-record activation,
ROM lookup against known decomp examples, dynamic exits, outdoor connections,
and destination visibility for known versus unvisited maps. Outdoor connection
coverage must verify bounded strips and coordinate alignment, including
Saffron City's north Route 5 connection at columns 10 through 29 and the
rejection of column 0. Activation coverage must include the independent Celadon
Mansion 2F stairs, the shared Celadon City entrance, both directions through
the Route 11 gate, and a genuine map-edge exit.

## Acceptance Criteria

- [ ] Normal parsed warps retain their zero-based destination warp index.
- [ ] Adjacent warp records remain independent and carry their own activation
      rule and destination.
- [ ] Step-on, map-edge, and directional warp-carpet activation match the ROM.
- [ ] Normal destination coordinates resolve correctly for the configured ROM.
- [ ] Dynamic destinations and invalid destination indices remain unresolved.
- [ ] Outdoor connections retain their ROM-defined strip bounds and coordinate
      alignment.
- [ ] Navigation advertises only boundary cells that belong to the relevant
      connection strip.
- [ ] Prompts include a resolved coordinate for known destination maps without
      revealing it for unvisited maps.
- [ ] Prompts and route execution use exact entry directions and no longer rely
      on a single/double-warp heuristic.
