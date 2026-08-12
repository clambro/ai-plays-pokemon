# Ticket: Add Provisional Map Regions and Cross-Map Routing

## Outcome

Derive connected regions from revealed terrain, explain them compactly in map
prompts, and build a deterministic global graph that can route between locally
separate areas through other maps.

Warp activation, normal destination coordinates, and bounded outdoor map
connections are already available to the routing work.

**Depends on:**

- [`enforce-code-structure-and-model-discipline.md`](enforce-code-structure-and-model-discipline.md)

## Core Principle

Unseen terrain is unknown, not blocked. Regions are provisional snapshots of
what is currently revealed and may merge when exploration exposes another path
or the player gains a traversal ability.

Persist maps, coordinates, entities, and transition endpoints. Never persist a
region label as durable identity.

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

If a destination coordinate is known but surrounding terrain has not been
revealed, retain it as an unresolved endpoint rather than inventing a region.

The global planner should:

- resolve the player's and target's current regions;
- find a route through known directed portal edges;
- return only the first portal/waypoint on the current map;
- use the existing local pathfinder to reach it; and
- re-read state and replan after every transition or interruption.

The LLM chooses semantic intent—explore, reach a known landmark, revisit a map,
or investigate a portal. Deterministic code chooses the portal sequence and
local waypoint.

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

When no route is known, return a useful reason and information-gaining options,
such as exploring current/reachable frontiers, visiting an untraversed portal,
or acquiring a required ability.

## Out of Scope

- Reading full ROM collision maps to determine regions.
- Claiming apparent separation is permanent.
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
- route selection and replanning; and
- prompt wording that exposes no unseen terrain.

## Acceptance Criteria

- [ ] All regions are derived solely from revealed terrain and current
      traversal rules.
- [ ] Unknown tiles never become graph nodes or confirmed walls.
- [ ] Broad regions use weak connectivity; execution retains directed edges.
- [ ] Region membership updates automatically as knowledge and abilities
      change.
- [ ] Dynamic occupancy does not create durable regions.
- [ ] Global routing uses coordinate-based directed transitions and returns the
      next local portal.
- [ ] The vertical-wall/two-ladder scenario routes through the basement.
- [ ] Prompts provide compact provisional-region and relevant-route context
      without changing the ASCII grid.
- [ ] Persistent state contains no region IDs.
