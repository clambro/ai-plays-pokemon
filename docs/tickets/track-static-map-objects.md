# Ticket: Track Stateful Static Map Objects

## Outcome

Represent important stationary interactions that are neither sprites nor signs
as a distinct map-entity category. Discover them locally, show the agent where
and how they can be used, and retain their latest observed interaction without
flooding the prompt with scenery, hidden pickups, or repetitive furniture.

This closes progression gaps around Bill's computer, the Vermilion Gym trash
can puzzle, Pokemon Mansion switches, and Cinnabar Gym quiz machines. It also
replaces the special-case Pokemon Center PC presentation with the same coherent
object model.

## Current Failure

The overworld currently understands three persistent map-entity categories:
sprites, signs, and warps. Pokemon Yellow has another interaction path: a
coordinate-bound handler table that the ROM checks before it checks ordinary
sprites and signs.

Bill's computer demonstrates the gap. Bill's House has no sign at the computer
and the computer is not a sprite. The ROM instead associates a special handler
with `(row=4, col=1)`, and that handler only responds when the player stands at
`(row=5, col=1)` facing up. Because the application does not parse or hook this
category, the map reports no object, the agent must guess from the screenshot,
and any resulting text cannot be attributed to persistent entity memory.

The ROM calls all entries in this table hidden objects, but they are not one
agent-facing concept. The same mechanism covers invisible items, visible
progression controls, PCs, slot machines, and flavor scenery. Exposing every
entry would reveal secrets and create severe prompt noise. Game Corner alone
contains 36 slot-machine entries.

## Object Model

Add a distinct `OBJECT` map-entity category for important stationary
interactions handled outside the normal sprite and sign paths. An object has:

- a stable map-local identity;
- map coordinates;
- any required interaction position and facing direction; and
- nullable latest interaction text and its iteration.

Use the object's original index in the ROM table as its map-local identity.
Identity is always qualified by map and entity type.

The ROM's terminology and handler identity are implementation details. The
agent should see a generic static object, not a `hidden object`, handler
address, scripted-object classification, or inferred description that is not
visually available in the game.

## Inclusion Policy

Parse the ROM table as the authoritative source of coordinates and behavior,
then expose only explicitly supported handler families. The initial supported
set is:

- Bill's computer (`BillsHousePC`);
- all Pokemon Mansion statue switches (`Mansion1Script_Switches` through
  `Mansion4Script_Switches`);
- all puzzle trash cans in Vermilion Gym (`GymTrashScript`);
- all Cinnabar Gym quiz machines (`PrintCinnabarQuiz`);
- Pokemon Center PCs (`OpenPokemonCenterPC`); and
- Red's PC (`OpenRedsPC`).

These objects either change progression-relevant world state or provide a
general-purpose player storage interface. The distinction is behavioral, not
based on whether the artwork resembles a poster, computer, statue, or trash
can.

Do not expose:

- hidden items or hidden coins;
- ordinary trash cans and other flavor-only scenery;
- bookshelves, magazines, pictures, display fossils, gym statues, benches, and
  display bicycles;
- slot machines; or
- Cable Club Game Boys and other irrelevant multiplayer interfaces.

Unknown or unsupported handlers must remain hidden from the agent. They must
not crash gameplay.

The Team Rocket poster in the Celadon Game Corner is already an ordinary ROM
background event and therefore remains a sign. Its discovery and interaction
memory must continue through the existing sign path. Do not duplicate it as an
object merely because it is visually a poster. Flavor-only posters represented
through the special handler table remain excluded.

## Discovery and Presentation

Follow the same locality rules as other map entities. An object becomes known
only when its coordinate has appeared in the observed screen, and the routine
prompt includes only known objects in the player's current connected region.
Do not reveal objects elsewhere on the map merely because their records exist
in the ROM.

Give objects their own map glyph and compact prompt section rather than calling
them signs. Each note should provide the object's map-qualified ID, coordinate,
latest interaction when present, and a concrete legal interaction position
when direction matters.

For example, Bill's computer should communicate that the player must stand at
`(row=5, col=1)`, face up, and press the action button. Pokemon Mansion
switches, Cinnabar quiz machines, and Pokemon Center PCs also require the
player to face up. Vermilion Gym puzzle cans may be approached from any legal
adjacent position.

An object without interaction memory may receive the same restrained
encouragement used for an untried sprite or sign. Do not add global instructions
requiring every object to be visited, and do not expose internal claims about
what the object will do.

## Interaction Recording

Hook the ROM after it has matched a supported static object and before it runs
that object's handler. Attribute the ensuing literal dialog to the
map-qualified object ID and pass completed interactions through the existing
map-entity memory workflow.

Preserve the existing interaction rule: an interaction exists only when it
produces text. Pressing the action button from an invalid direction, or opening
an interface without observable text, must not create an empty interaction.
The latest recorded text is historical evidence with an iteration stamp, not a
claim that the object's response can never change.

Object discovery and interaction persistence are separate. Discovering an
object creates its nullable entity-memory record; a later completed dialog
updates that record. Persistence failure must degrade with a warning rather
than terminate the gameplay loop.

## PC Consolidation

Represent Pokemon Center PCs and Red's PC through `OBJECT`. Their ROM records
already provide exact coordinates and activation behavior, so they should
replace the tileset-specific `PC_TILE` recognition and the special PC note
currently inserted into the sprite section.

The completed implementation must have one source of truth for PC discovery
and presentation. It must not show both a terrain-derived PC and an object at
the same coordinate.

## Persistence

Store object discovery and latest interaction alongside existing map-entity
memory using the new entity type. Continue to persist only entity-free terrain;
object glyphs and positions are composed at the map-view boundary.

No backward-compatibility migration is required during development. Existing
test databases may be regenerated when the entity type and PC representation
change.

## Out of Scope

- Exposing all ROM hidden-object records.
- Revealing hidden item or coin locations.
- Recording every flavor-text surface in the game.
- Classifying objects for the agent as switches, scripts, items, or other ROM
  implementation types.
- Treating the Celadon Game Corner poster as an object instead of a sign.
- Automating object activation or solving the Vermilion and Cinnabar puzzles
  deterministically.
- Adding an exhaustive walkthrough or progression database.

## Validation

Use domain and integration coverage for entity discovery, handler filtering,
activation constraints, and interaction attribution. Do not add tests that
assert exact prompt prose or formatting.

Cover at least:

- Bill's computer appearing at `(row=4, col=1)` only after local observation,
  with `(row=5, col=1)` and facing up as its valid interaction position;
- Bill's computer dialog being attributed to its object memory;
- all fifteen Vermilion Gym puzzle cans remaining distinct and retaining their
  individual latest interactions;
- Pokemon Mansion switches and Cinnabar quiz machines exposing their required
  approach direction;
- Pokemon Center and Red's PCs using the object path without duplicate PC
  presentation;
- hidden items, hidden coins, ordinary trash, scenery, and slot machines not
  appearing as objects;
- the Game Corner poster remaining discoverable and recordable as a sign;
- an invalid-direction attempt producing no empty interaction record;
- an unknown handler remaining undisclosed without interrupting gameplay; and
- object overlays never becoming persisted terrain.

## Acceptance Criteria

- [ ] `OBJECT` is a distinct map-entity type with map-qualified, stable
      identity.
- [ ] Supported objects are sourced from the ROM's coordinate-bound handler
      records rather than inferred from prompt memory or screenshots.
- [ ] Objects are discovered only through locally observed coordinates and are
      shown only in the current connected region.
- [ ] Bill's computer, Pokemon Mansion switches, Vermilion Gym puzzle cans,
      Cinnabar Gym quiz machines, Pokemon Center PCs, and Red's PC are exposed.
- [ ] Required interaction positions and facing directions are concrete and
      correct.
- [ ] Hidden pickups, flavor scenery, slot machines, and multiplayer terminals
      are not exposed.
- [ ] Unknown handlers fail closed and cannot crash the application.
- [ ] Completed object dialog is persisted with its iteration; attempts that
      produce no text create no interaction.
- [ ] Pokemon Center PCs have one representation, with the terrain-specific PC
      presentation removed.
- [ ] The Celadon Game Corner poster remains on the existing sign path without
      duplication.
- [ ] Object overlays are composed dynamically and never persisted as terrain.
- [ ] Prompt changes are reviewed directly rather than protected by
      copy-assertion tests.
