> This ticket is a starting point for investigation, not a specification. It was written against an older version of the code, and the implementation may have changed since then. Verify the current behavior and code before making changes. The problem is real; the proposed solution is not set in stone.

# Navigation reliability and exit identity

## Problem

Several navigation failures can trap the run for an unreasonable amount of time.

First, navigation may act on stale terrain after a Cut tree has already been removed. The service still sees a Cut tile, faces it, presses A, and assumes that field-move dialogue will follow. If no interaction actually begins, the dialogue wait can continue indefinitely.

Second, the agent repeatedly tries routes blocked by scripted events. Before Brock is defeated, the Route 3 escort lets the player walk several tiles before returning them to the Gym. The Saffron guards similarly prevent passage until their condition is satisfied. Because these are not ordinary collisions, the agent treats every approach tile as a separate experiment and can spend many iterations trying equivalent paths through the same blocked transition.

Finally, indoor exit records use the ROM sentinel `OUTSIDE`, and that literal name is currently shown to the agent. `OUTSIDE` does not identify where an exit leads. In buildings with multiple doors, the agent cannot distinguish the exits and may repeatedly enter and leave through the same door while believing it is investigating a different route.

## Proposed direction

Make navigation validate what actually happened rather than assuming that the expected interaction or movement occurred. After attempting an HM action, confirm that the ROM entered the expected interaction state before handing control to dialogue processing. If it did not, refresh the current terrain and return a recoverable navigation result. No missing interaction should be able to leave the service waiting forever.

For scripted barriers, use routine dialog settlement as the observation boundary: the application controls only the A button during that interval, so a same-map coordinate change before overworld control returns is ROM-controlled displacement. Retain a small rolling history of map-qualified destinations and warn the agent when the same destination repeats. This is intentionally a heuristic advisory, not a permanent route closure or a model of individual game scripts.

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
- When scripted dialog returns the player to the same map-qualified destination three times within 20 iterations, the agent receives an actionable warning to try another route.
- Scripted displacement observations do not modify terrain or make routes unavailable.
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

### Commit 3: Warn about repeated scripted displacement

**Outcome:** When routine dialog repeatedly returns the player to the same location, the agent receives a concise warning that the route is probably blocked by a scripted event and should try something else.

**Implementation:**

- Observe the player before routine dialog is advanced and after overworld control returns. Treat a same-map coordinate change during that interval as ROM-controlled displacement; ignore ordinary text without movement, map transitions, battles, and interactions that have not returned control.
- Retain at most 20 map-qualified destinations from the last 20 application iterations in agent state. On the third arrival at the same destination, include an actionable warning in the immediate result and rolling memory.
- Keep this deliberately heuristic. A repeated destination is not a unique script identity, and the warning does not alter terrain, block routes, catalogue events, or attempt to model the underlying game condition.

**Tests included in the commit:**

- Verify that the third matching destination in the 20-iteration window is flagged, while the same coordinates on another map do not match, expired observations do not count, and retained history never exceeds 20 entries.
- Verify that the bounded history survives an agent-state round trip and that backups without it retain a backwards-compatible empty default.

**Documentation included in the commit:** Record the deliberately narrow signal and its limitations in this technical ticket. No public workflow documentation change is needed.

### Validation and review cadence

For each commit, run its focused tests while iterating, then run `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, `uv run python -m pytest`, and `git diff --check` before presenting it for review. Do not start the application, make live model calls, or use an unbounded emulator smoke test. Work in the numbered order and pause for review after each commit-sized stage.
