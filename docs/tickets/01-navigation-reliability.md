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

## Staged implementation plan

This plan is intentionally a starting sequence rather than a complete up-front design. Each stage is one independently shippable commit: it delivers a coherent behavior change, includes its own tests and documentation, leaves the repository passing, and can be reviewed and merged before the next stage is designed in detail. Later stages should be revised when earlier implementation or emulator evidence changes the assumptions below; no commit should land speculative scaffolding for a later stage.

### Commit 1: Refresh terrain before navigation returns

**Outcome:** Every completed same-map navigation step is incorporated into explored terrain before the navigation call returns. In particular, when Cut removes a tree on the same step that reaches the requested target, the remembered tree is removed rather than surviving as stale terrain that a later route can mistake for a live HM interaction.

**Implementation:**

- Apply the final decision-ready game observation to the current map before returning a same-map navigation result, including the target-reached result. Continue to avoid updating the current map after control leaves the overworld or the player changes maps.
- Preserve the existing Cut and Surf interaction flow and navigation results. This stage fixes ownership and ordering of the authoritative terrain refresh rather than adding a second recovery path for stale state.

**Tests included in the commit:**

- Add a Cut integration case that navigates directly onto the tree tile, which naturally exercises the terminal field-move step. Assert that Cut succeeds, the player reaches the requested tile, and the same map object no longer contains a Cut tree there when navigation returns.
- Keep the existing successful Cut traversal and Surf integration cases as field-move regressions.

**Documentation included in the commit:** Record the demonstrated stale-map lifecycle and corrected refresh contract in this technical ticket. No public workflow documentation change is needed.

### Commit 2: Resolve dynamic indoor-exit endpoints from ROM state

**Outcome:** An actionable indoor exit displays the concrete map and endpoint that the ROM would currently use instead of the raw `OUTSIDE` sentinel. Separate exit records retain their own destination warp indices and coordinates without introducing application-owned endpoint state or cross-map route planning.

**Implementation:**

- Resolve an indoor warp record's `OUTSIDE`/`LAST_MAP` sentinel through the live `wLastMap` value while parsing `GameState`. Continue using the record's own destination warp index to resolve its destination coordinates from the ROM map tables.
- Treat an invalid raw destination or invalid `wLastMap` as recoverable degradation: emit a rate-limited warning, preserve `MapId.UNKNOWN` as the fallback, and continue constructing the game state. Formatting describes that fallback as unresolved rather than exposing a sentinel as a place.
- Keep ordinary ROM-resolved destinations and existing warp-usage timestamps unchanged. Do not add endpoint persistence, database migrations, previous-state tracking, region nodes, graph traversal, or route selection.

**Tests included in the commit:**

- Use the existing Mt. Moon Pokémon Center save state to assert that both raw `LAST_MAP` exit records resolve to Route 4 warp 0 at `(5, 11)`.
- Deliberately invalidate `wLastMap` in the bounded emulator fixture and assert that parsing continues with `MapId.UNKNOWN` and no fabricated coordinates.
- Retain the existing screen, navigation, and warp-usage suites as regressions. Review the unresolved model-facing wording directly rather than testing prose.

**Documentation included in the commit:** Record that live ROM state, not application persistence, owns dynamic exit resolution. No public workflow documentation change is needed.

### Commit 3: Recognize, remember, and temporarily avoid scripted route rejection

**Outcome:** Navigation recognizes a generic scripted displacement, stops using the obsolete remainder of its path, records the rejected transition as short-lived workflow state, and avoids immediately planning another target through the same transition. The transition becomes eligible again after relevant progress or bounded expiry.

**Investigation checkpoint:** First reproduce at least one real Route 3 or Saffron rejection and verify whether `ControlResult.step_observations` captures the complete movement imposed between the accepted directional input and the restored `OVERWORLD_READY` boundary. Also verify normal turns, collisions, ledges, spinners, warps, and HM movement so the rejection rule is based on positive evidence. If the current observations cannot distinguish scripted rejection, add the smallest generic control metadata needed to expose that fact; do not infer it from a final coordinate alone and do not add map IDs, coordinates, NPC names, or walkthrough conditions.

**Implementation:**

- Request step observations for ordinary directional movement in navigation and direct overworld button sequences, then reduce the observed trajectory into a movement outcome shared by both services.
- Compare the actual trajectory and terminal boundary with the movement the accepted input was expected to perform. Report and stop on autonomous displacement or a return path that is inconsistent with an ordinary step, while preserving the established special cases for turning, Pikachu yielding, ledges, spinners, warps, encounters, and HM movement.
- Define rejection identity around the attempted transition rather than the requested target coordinate. Start with a map-qualified directed entry edge, and use a proven generic script identity or equivalent observed trajectory to group multiple entry tiles only if the real fixtures show that an edge alone is insufficient. If no generic observation can support the required grouping, revise this stage instead of hardcoding a barrier.
- Add a small route-rejection model owned by `AgentState` and the coordinating context, with a backwards-compatible empty default for old backups. Keep this state separate from persisted terrain and map-entity memory so a scripted condition never becomes a permanent physical wall; rolling memory may describe the failure but is not its source of truth.
- Overlay active rejected transitions only when building the current reachable view and calculating paths. Targets whose routes require the same rejected transition should be rejected before another emulator input, while unrelated targets and routes remain available. Show a concise temporary-blockage note in the overworld decision context so the model understands why the region changed.
- Give every rejection explicit reconsideration rules based on player-visible progress available in the current `GameState`, initially including badge changes, inventory item identity changes, and HM capability changes, plus a conservative maximum age as a fallback. A later successful traversal removes the rejection immediately. Do not read hidden story flags solely to decide whether a route should reopen.

**Tests included in the commit:**

- Add behavior tests showing that a multi-step scripted displacement or out-and-back trajectory is classified as rejection, while a turn, collision, ordinary step, ledge, spinner, warp, encounter handoff, and successful HM action are not.
- Add a navigation-level test in which one observed rejection prevents two different targets from immediately reusing the equivalent transition but does not block an unrelated path.
- Add lifecycle tests showing that the rejection survives ordinary iterations and a backup round trip, then becomes eligible after the chosen progress signals, successful traversal, or maximum age. Use a real emulator save for at least one scripted barrier when a reproducible local fixture is available.

**Documentation included in the commit:** Record the proven emulator signal, equivalence rule, and reconsideration lifecycle in this technical ticket so later work does not have to rediscover them. No public workflow documentation change is needed.

### Validation and review cadence

For each commit, run its focused tests while iterating, then run `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, `uv run python -m pytest`, and `git diff --check` before presenting it for review. Do not start the application, make live model calls, or use an unbounded emulator smoke test. Work in the numbered order and pause for review after each commit-sized stage.
