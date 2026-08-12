# Ticket: Separate Persistent Map Terrain from Entity Overlays

## Outcome

Persist the stable background of each explored map independently from transient
player and sprite positions. Compose the current player, Pikachu, sprites,
signs, and warps onto that background only when producing an observation or
calculating behavior that depends on the current entities.

The explored-map terrain must have one durable source of truth. A rendered
screen containing temporary entity glyphs must not become that source.

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
cache of current emulator state. Also decide how existing map rows containing
embedded entity glyphs will be repaired: migration, normalization where the
underlying tile is recoverable, or deliberate regeneration of explored maps.

## Scope

- Expose or construct an entity-free classified background observation.
- Persist only durable background terrain in map tile storage.
- Compose current entities onto terrain at the presentation boundary.
- Make routing account for current blocking sprites without treating stale
  historical positions as terrain.
- Preserve discovered entity identities and other durable structural metadata.
- Remove stale player, Pikachu, and sprite glyphs when a map is revisited from
  a non-overlapping viewport.
- Handle same-map Fly and other same-map relocation mechanisms explicitly.
- Define and implement a safe transition for existing persisted map data.
- Keep screen-relative and map-relative coordinate conversion in one clear
  layer.

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
  position; and
- loading or regenerating map data created before this change.

## Acceptance Criteria

- [ ] Persisted terrain contains no player, Pikachu, or ordinary sprite glyphs.
- [ ] A composed current map contains exactly one player at the live emulator
      coordinate.
- [ ] Same-map Fly cannot leave a duplicate player at the departure location.
- [ ] Moving and removed sprites cannot leave stale routing obstacles.
- [ ] Current blocking sprites still affect routing where appropriate.
- [ ] Signs, warps, and discovery state remain available without
      being embedded as accidental terrain state.
- [ ] Existing persisted maps are migrated, normalized, or deliberately
      regenerated with an explicit policy.
- [ ] Prompt maps and current ASCII screens remain faithful to the live state.
