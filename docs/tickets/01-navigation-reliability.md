> This ticket is a starting point for investigation, not a specification. It was written against an older version of the code, and the implementation may have changed since then. Verify the current behavior and code before making changes. The problem is real; the proposed solution is not set in stone.

# Navigation reliability and exit identity

## Problem

Several navigation failures can trap the run for an unreasonable amount of time.

First, navigation may act on stale terrain after a Cut tree has already been removed. The service still sees a Cut tile, faces it, presses A, and assumes that field-move dialogue will follow. If no interaction actually begins, the dialogue wait can continue indefinitely.

Second, the agent repeatedly tries routes blocked by scripted events. Before Brock is defeated, the Route 3 escort lets the player walk several tiles before returning them to the Gym. The Saffron guards similarly prevent passage until their condition is satisfied. Because these are not ordinary collisions, the agent treats every approach tile as a separate experiment and can spend many iterations trying equivalent paths through the same blocked transition.

Finally, indoor exit records use the ROM sentinel `OUTSIDE`, and that literal name is currently shown to the agent. `OUTSIDE` does not identify where an exit leads. In buildings with multiple doors, the agent cannot distinguish the exits and may repeatedly enter and leave through the same door while believing it is investigating a different route.

## Proposed direction

Make navigation validate what actually happened rather than assuming that the expected interaction or movement occurred. After attempting an HM action, confirm that the ROM entered the expected interaction state before handing control to dialogue processing. If it did not, refresh the current terrain and return a recoverable navigation result. No missing interaction should be able to leave the service waiting forever.

For scripted barriers, first determine how the current control boundaries and observations represent the full interruption. The simplest useful result would identify that an attempted route was rejected by a script, especially when the player is displaced or returned, and preserve enough short-lived state for equivalent approaches to count as the same failed route rather than unrelated failed tiles. This must not permanently close the route: it needs to become eligible for reconsideration after meaningful game progress or other evidence that the blocking condition may have changed.

Do not hardcode Brock, the Saffron guards, or individual coordinates unless investigation proves there is no general signal available. The desired behavior is generic recognition of repeated scripted rejection.

Persist the actual endpoint of an indoor exit after the agent traverses it. Formatting should prefer the learned destination over the raw `OUTSIDE` sentinel. Before an exit has been used, describe it as unresolved rather than pretending that `OUTSIDE` is a place. This should solve local door identity without depending on the larger cross-map routing work.

## Relevant code

- `agent/overworld/tools/navigate/service.py` owns path execution, HM activation, interruption reporting, and map refreshes during navigation.
- `agent/overworld/tools/press_buttons/service.py` reports collisions and map changes for direct input sequences.
- `agent/overworld/navigation.py` owns local pathfinding and traversability.
- `common/enums.py` defines `MapId.OUTSIDE`.
- `emulator/parsers/warp.py` parses raw warp destinations and ROM-maintained source and destination warp identities.
- `emulator/control_events.py` defines the control boundaries returned by emulator operations.
- `emulator/emulator.py`, `emulator/text_events.py`, and `emulator/pyboy_worker.py` own dialogue waits and their timeout behavior.
- `agent/context.py` observes completed ordinary warp transitions and currently records their usage.
- `agent/overworld/formatting.py` currently renders warp destinations, including `OUTSIDE`.
- `overworld_map/service.py` refreshes persisted terrain and records ordinary warp usage.
- `database/map_entity_memory/` persists warp usage timestamps and may be the simplest place to extend learned exit identity.
- `memory/rolling_memory/` and any new route-state persistence should be reviewed before deciding where a temporary scripted blockage belongs.

## Questions to answer during investigation

- Can the ROM or existing control observations distinguish a scripted displacement from an ordinary collision without adding map-specific knowledge?
- At what point after Cut does the persisted terrain become stale, and can the map be refreshed immediately from live state?
- Which dialogue waits are intentionally unbounded, and which one is responsible for the observed hang?
- What event should make a previously rejected scripted route worth trying again?
- Can equivalent approaches be grouped by the transition being attempted rather than by exact coordinates?
- Is the existing ordinary-warp transition observation sufficient to resolve every `OUTSIDE` exit after use?
- What is the smallest persisted endpoint record needed to distinguish doors without coupling this ticket to high-level routing?

## Success criteria

- A stale Cut-tree marker cannot hang navigation or crash the application.
- A missing HM interaction produces a bounded, useful result and refreshes the state used for subsequent movement.
- After a scripted route rejects the player, the agent does not immediately test every equivalent approach or repeat the same plan for many iterations.
- Routes blocked by game progression remain available for later reconsideration.
- A previously used indoor exit displays its actual learned destination rather than `OUTSIDE`.
- Different exits from the same building remain distinguishable after they have been traversed.
- The solution remains generic and does not encode a walkthrough for specific barriers.
