# Ticket: Separate Persistent Map Terrain from Entity Overlays

## Outcome

Persist the stable background of each explored map independently from transient
player and sprite positions. Compose the current player, Pikachu, sprites,
signs, and warps onto that background only when producing an observation or
calculating behavior that depends on the current entities.

The explored-map terrain must have one durable source of truth. A rendered
screen containing temporary entity glyphs must not become that source.
Because composition no longer destroys the underlying terrain value, the
overworld prompt should also identify the terrain tile beneath the player.

## Current Failure

`GameState.get_ascii_screen()` first classifies the background and then overlays
sprites, warps, signs, Pikachu, and the player. `_update_overworld_map_tiles()`
persists this composite screen directly as the explored map.

This leaves stale overlays whenever the next observation does not cover their
old coordinates. The clearest reproduction is:

1. stand on one side of a map and persist the observation;
2. use Fly to return to a different part of that same map;
3. let the newly visible area redraw; and
4. observe that the persisted map contains both the old and new player glyphs.

The same ownership problem affects moving or removed sprites. A stale sprite
glyph can remain outside the refreshed viewport and incorrectly block routing,
even though current sprite state and entity memory already exist separately.

Relevant code:

- `emulator/game_state.py` (`get_ascii_screen` and background classification);
- `overworld_map/service.py` (`_update_overworld_map_tiles` and entity updates);
- `agent/overworld/prompts.py` and `agent/overworld/formatting.py` (map prompt
  composition and rendering);
- `agent/overworld/tools/navigate/utils.py` (routing over persisted tiles); and
- `database/map_memory` and `database/map_entity_memory` (current persistence
  boundaries).

## Investigation

Establish explicit ownership and lifecycle for each layer before choosing the
storage shape:

- stable classified terrain;
- static interaction metadata such as signs and warps;
- current ordinary sprite and boulder positions;
- Pikachu's current position and visibility; and
- the player's current position.

Determine which consumers require a composed view and which require terrain
only. In particular, prompts need a faithful current rendering, while routing
needs stable terrain plus only the current blockers that should affect
movement.

Investigate whether the existing entity-memory tables are sufficient or need
typed position/state persistence. Do not introduce a second authoritative
cache of current emulator state.

Persistence is ephemeral and there are no existing databases that need to be
preserved. Make breaking schema and model changes directly. Do not add database
migrations, compatibility aliases, legacy-row normalization, or fallback logic
for composite maps created before this change. The explicit transition policy
is to start with a fresh database and regenerate explored terrain through normal
gameplay observations.

## Scope

- Expose or construct an entity-free classified background observation.
- Persist only durable background terrain in map tile storage.
- Compose current entities onto terrain at the presentation boundary.
- Report the entity-free terrain tile beneath the player in the overworld
  prompt, separately from the composed player glyph.
- Make routing account for current blocking sprites without treating stale
  historical positions as terrain.
- Preserve discovered entity identities and other durable structural metadata.
- Remove stale player, Pikachu, and sprite glyphs when a map is revisited from
  a non-overlapping viewport.
- Handle same-map Fly and other same-map relocation mechanisms explicitly.
- Change the persistence schema directly and regenerate maps from a fresh
  database; backward compatibility is not required.
- Keep screen-relative and map-relative coordinate conversion in one clear
  layer.

## Staged Commit Plan

Each commit must be internally consistent, independently reviewable, and pass
the validation relevant to its scope before the next commit begins.

### Commit 1: Expose Entity-Free Screen Terrain

- Add an explicit entity-free ASCII terrain observation.
- Build the existing composed ASCII screen from that terrain observation while
  preserving its current output and overlay precedence.
- Centralize map-relative and screen-relative coordinate conversion on the
  screen/viewport boundary.
- Add emulator coverage proving that composed screens are unchanged while the
  terrain observation contains no entity-overlay glyphs.

### Commit 2: Make Entity Memory Discovery-Only

- Represent known sprites, signs, and warps in `OverworldMap` as discovered
  identities rather than cached parser records.
- Continue persisting those identities in `map_entity_memory`.
- Resolve current positions, visibility, labels, and other live state from the
  current `GameState` in prompt formatting, entity updates, tool availability,
  and Sokoban behavior.
- Add focused coverage for discovery, movement, de-rendering/removal, and live
  boulder lookup.

### Commit 3: Persist Terrain and Compose Live Overlays

- Rename and reshape map persistence around terrain directly, without schema
  compatibility code or migration machinery.
- Persist only the entity-free terrain observation and durable blockages.
- Derive prompt maps from terrain plus discovered entities and the current
  player, Pikachu, and sprite state.
- Include the underlying terrain at the live player coordinate in the prompt's
  player-position information.
- Derive navigation traversability from terrain plus only the current blockers
  and structural overlays that affect movement.
- Update exploration, special-tile handling, Sokoban, formatting, and all other
  map consumers to use terrain or a composed view according to their needs.
- Add behavior-level coverage for same-map relocation, distant re-entry,
  moving and removed sprites, current routing blockers, and fresh-database map
  reconstruction.
- Update the mapping documentation and retire this ticket after the full static
  and test suite passes.

## Out of Scope

- Per-warp activation and destination metadata, which is already implemented.
- Global cross-map route planning.
- Persisting unexplored terrain or revealing ROM map data the player has not
  observed.
- Replacing the emulator's live state as the authority for current entities.

## Validation

Use behavior-level coverage that exercises persistence and reconstruction,
rather than tests that restate overlay helper implementations. Include:

- flying from one part of a map back to another part of the same map;
- leaving and re-entering a map through distant entrances;
- a moving sprite whose old and new positions do not share a viewport;
- a removed item or scripted sprite;
- routing around a currently present blocker without retaining its stale
  position;
- reporting the entity-free terrain beneath the player while the composed map
  displays the player glyph; and
- creating and reconstructing explored maps from a fresh database.

## Acceptance Criteria

- [ ] Persisted terrain contains no player, Pikachu, or ordinary sprite glyphs.
- [ ] A composed current map contains exactly one player at the live emulator
      coordinate.
- [ ] The overworld prompt reports the entity-free terrain tile beneath the
      player.
- [ ] Same-map Fly cannot leave a duplicate player at the departure location.
- [ ] Moving and removed sprites cannot leave stale routing obstacles.
- [ ] Current blocking sprites still affect routing where appropriate.
- [ ] Signs, warps, and discovery state remain available without
      being embedded as accidental terrain state.
- [ ] A fresh database creates and reconstructs entity-free explored terrain;
      persisted maps from earlier implementations are deliberately unsupported.
- [ ] Prompt maps and current ASCII screens remain faithful to the live state.
