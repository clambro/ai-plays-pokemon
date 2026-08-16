# Ticket: Add Provisional Map Regions and Cross-Map Routing

## Outcome

Derive connected regions from revealed terrain, explain them compactly in map
prompts, and build a deterministic global graph that can route between locally
separate areas through other maps.

The current agent-facing map already derives and displays the region reachable
from the player's position while retaining the complete revealed map in
persistence. This ticket extends that foundation to other derived regions and
cross-map routing; it does not replace the current map view or partition stored
maps.

Warp activation, rigid map-local warp IDs, normal destination coordinates,
exact coordinates on observed map changes, and bounded outdoor map connections
are already available to the routing work.

**Depends on:**

- [`enforce-code-structure-and-model-discipline.md`](enforce-code-structure-and-model-discipline.md)

## Core Principle

Unseen terrain is unknown, not blocked. Regions are provisional snapshots of
what is currently revealed and may merge when exploration exposes another path
or the player gains a traversal ability.

Persist maps, coordinates, entities, and transition endpoints. Never persist a
region label as durable identity.

Every derived region must retain the map's existing coordinate system. A
cropped or separately connected region may start at a nonzero row or column,
but its coordinates must never be rebased or renumbered. Previously remembered
coordinates must remain valid when regions expand, merge, or are approached
through another map.

## Local Region Model

- Build a movement graph only from revealed terrain.
- Reuse the actual movement rules for collision pairs, ledges, spinners, Cut,
  Surf, warps, and holes.
- Calculate regions for every visited map, not only the player's current
  reachable area.
- Use weak connectivity for human-readable broad regions while retaining
  directed edges for reachability and path execution.
- Treat dynamic occupancy such as NPCs and Pikachu as temporary path blockers,
  not permanent topology.
- Recompute regions when terrain, collision knowledge, or traversal abilities
  change.
- Assign deterministic temporary labels, such as coordinate-sorted `R1`,
  `R2`, solely for the current derived view.

Each region summary should identify useful landmarks, portals, exploration
frontiers, whether it contains the player, and important one-way exits.

## Global Routing

Build a derived graph whose nodes are current provisional regions and whose
directed edges are known map transitions. Assign each transition endpoint to
the region currently containing its coordinate.

The graph is derived from authoritative explored-map state and persisted
transition endpoints, not from rolling-memory prose or a reconstructed sequence
of where the agent remembers walking. Include both warp transitions and bounded
outdoor map connections. Region-limited prompt presentation must not remove
known portals in other regions or maps from the planner's source data.

This must be a graph rather than a tree. Maps can have multiple entrances,
transitions can form cycles, and locally separate regions may reconnect through
other maps.

Treat every portal endpoint as map-qualified. Coordinates are only meaningful
within their map and must never identify a portal globally. In particular, two
warps at the same coordinates on different maps are distinct endpoints with
different destinations. Retain the rigid map-local warp ID alongside the source
map, source coordinates, destination map, and destination coordinates.

If a destination coordinate is known but surrounding terrain has not been
revealed, retain it as an unresolved endpoint rather than inventing a region.

The global planner should:

- resolve the player's and target's current regions;
- find a route through known directed portal edges;
- return only the first portal/waypoint on the current map;
- use the existing local pathfinder to reach it;
- re-read state and replan after every transition or interruption; and
- advance from the observed destination endpoint rather than selecting the
  locally prominent arrival portal merely because the player is standing on it.

The LLM chooses semantic intent—explore, reach a known landmark, revisit a map,
or investigate a portal. Deterministic code chooses the portal sequence and
local waypoint.

Expose that division through a goal-oriented routing tool rather than a tool
that merely dumps the known warp graph. The model should select a known map,
landmark, region, or unexplored portal as its destination. The tool should
derive the route, select the next map-qualified portal on the current map, and
hand that coordinate to the existing local navigator. A graph inspection view
may be useful for diagnosis, but it is not a substitute for deterministic route
selection.

The Mt. Moon B1F/B2F loop is the representative failure case. B1F has one warp
at `(9, 25)` leading to 1F, while B2F has a different warp at `(9, 25)` leading
back to B1F. Despite receiving the correct map-qualified warp records, the LLM
collapsed those coordinates into one place and traversed the B1F/B2F edge more
than 180 times. Rolling memory then reinforced the invented topology. A route
to 1F must select the B1F portal itself; arriving at the same coordinates on
B2F must not satisfy or replace that waypoint.

## Discarded Transition-History Approach

Do not solve this by adding another prompt section that restates recent map
visits, entered and exited warps, previous-map context, or traversal counts. A
structured version of that information was explored and discarded: the same
facts were already present in exact map-change results and rolling memory, and
there was no indication that another presentation changed the agent's routing
behavior.

The failure is not primarily missing history. It is asking the model to infer
and execute graph topology from locally presented observations. Persist the
transition facts once, derive the graph deterministically, and expose a routing
operation instead of another narrative history. A diagnostic graph view may
show traversal history when investigating a failure, but history must not
become the graph's source of truth or routine prompt payload.

## Prompt Design

Keep region information outside the ASCII grid so the established one-token
tile representation and coordinate counting are not disturbed.

Add bounded sections describing:

- the player's current provisional region;
- other relevant regions on the current map;
- relevant landmarks, portals, and frontier counts; and
- short known routes that leave and re-enter the map.

Use explicit uncertainty language:

- “provisional”;
- “based only on revealed terrain”;
- “not currently known to be connected”; and
- “unseen terrain may connect these regions.”

Do not dump the complete world graph into every prompt.

Do not duplicate rolling memory with a recent-transition ledger. Prompt context
should describe the player's current provisional region and only the route or
portals relevant to the current decision. The deterministic planner may use the
complete known graph without exposing it wholesale to the model.

When no route is known, return a useful reason and information-gaining options,
such as exploring current/reachable frontiers, visiting an untraversed portal,
or acquiring a required ability.

## Out of Scope

- Reading full ROM collision maps to determine regions.
- Claiming apparent separation is permanent.
- Replacing the persistent whole-map record with separately stored components.
- Rebasing coordinates relative to a region crop.
- Treating rolling memory or a traversal-history log as authoritative topology.
- A predetermined walkthrough.
- One uninterrupted multi-map action sequence.
- Strongly connected subregions unless one-way puzzles later justify them.
- Incremental union-find or durable region IDs.

## Validation

Use synthetic maps and representative game fixtures to cover:

- two apparent regions that later merge through newly revealed terrain;
- two areas connected only through another floor/map;
- one-way ledges and spinners;
- Cut/Surf changing region membership;
- dynamic sprites not splitting topology;
- unresolved and directed transition endpoints;
- equal coordinates belonging to distinct map-qualified portal endpoints;
- route progress after arriving while standing on a reciprocal return warp;
- route selection and replanning; and
- prompt wording that exposes no unseen terrain.

## Acceptance Criteria

- [ ] All regions are derived solely from revealed terrain and current
      traversal rules.
- [ ] Unknown tiles never become graph nodes or confirmed walls.
- [ ] Derived regions preserve original map coordinates and never partition the
      persistent whole-map record.
- [ ] Broad regions use weak connectivity; execution retains directed edges.
- [ ] Region membership updates automatically as knowledge and abilities
      change.
- [ ] Dynamic occupancy does not create durable regions.
- [ ] Portal identity is map-qualified; equal coordinates on different maps
      cannot be conflated.
- [ ] Global routing uses coordinate-based directed transitions and returns the
      next local portal.
- [ ] The routing tool accepts semantic intent and deterministically selects the
      next portal instead of asking the LLM to traverse a graph dump.
- [ ] Rolling memory and recent transition history are not used as graph
      authority or duplicated into routine prompt context.
- [ ] The vertical-wall/two-ladder scenario routes through the basement.
- [ ] The Mt. Moon B1F/B2F scenario routes to the correct B1F-to-1F warp without
      cycling through the identically positioned B2F return warp.
- [ ] Prompts provide compact provisional-region and relevant-route context
      without changing the ASCII grid.
- [ ] Persistent state contains no region IDs.
