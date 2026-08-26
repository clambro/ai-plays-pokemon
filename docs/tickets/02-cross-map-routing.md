> This ticket is a starting point for investigation, not a specification. It was written against an older version of the code, and the implementation may have changed since then. Verify the current behavior and code before making changes. The problem is real; the proposed solution is not set in stone.

# Cross-map routing

## Problem

The agent has excellent local navigation inside its current connected region but no durable representation of how previously visited regions connect. After reaching Lavender Town through Rock Tunnel and then wiping without establishing a local recovery point, it returned to the far side of Rock Tunnel and spent hours wandering between Cerulean and Vermilion. It had no concise representation that Lavender was reached through Route 9, Route 10, and Rock Tunnel.

Map IDs alone cannot solve this. A single map may contain multiple disconnected regions, such as the two halves of Route 2, and multiple dungeon areas may share a familiar location name while requiring specific ladders or exits to move between them.

## Proposed direction

Use successful observed transitions to build a small persistent graph of visited connected regions. Nodes must preserve connected-region identity rather than collapsing everything with the same map ID. Edges should represent transitions the agent has actually taken, including ordinary warps and walk-off-map connections. The graph should not reveal unexplored world data.

The agent should receive only a compact route relevant to its present problem, not a dump of the complete graph. For example, when trying to return to Lavender, it could be reminded of the known sequence through Route 9, Route 10, and Rock Tunnel. Ordinary building interiors should not clutter the high-level route presentation, although the underlying graph may need to preserve them when they connect two meaningful regions.

This is route memory, not an automatic cross-map navigation service. The agent should continue making local decisions and exploring unknown transitions itself.

## Relevant code

- `emulator/parsers/warp.py` parses ROM-maintained source and destination warp identities.
- `emulator/parsers/map.py` parses cardinal map connections.
- `agent/context.py` observes completed ordinary warp transitions and currently records their usage.
- `overworld_map/service.py` and `database/map_entity_memory/` persist warp usage timestamps.
- `agent/overworld/map_view.py` computes the current ephemeral connected region.
- `overworld_map/schemas.py` currently stores explored state primarily by map ID and will need to be considered when defining durable region identity.
- `agent/overworld/prompts.py` is the eventual presentation boundary for any compact route information.

## Questions to answer during investigation

- What is the smallest stable identity for a connected region across reloads and incremental map discovery?
- Can observed source and destination warp indices provide enough identity for region entry points without introducing a separate global map parser?
- How should cardinal map connections be recorded when there is no ordinary warp identity?
- Which interiors should be omitted or collapsed in the high-level presentation without losing route continuity?
- Should the prompt show one shortest known route to a relevant destination, a short list of nearby known transitions, or both?
- How should a route destination be selected when the agent has not explicitly named it in a goal?

## Success criteria

- The agent retains a usable high-level route between previously visited regions across wipes, reloads, and long runs.
- Disconnected regions sharing a map ID are not falsely collapsed into one node.
- Only observed transitions and otherwise player-visible information are revealed.
- The model receives a small relevant route, not a large world graph or an automated walkthrough.

## Staged implementation plan

This is a starting sequence, not a complete up-front design. Each stage is one independently shippable commit with its own meaningful behavioral coverage and documentation, and each stage should be reviewed and merged before work begins on the next. Later stages may change when implementation or runtime evidence invalidates an assumption below; no stage should add speculative machinery for work that belongs to a later commit.

### Commit 1: Persist observed map transitions

**Outcome:** The application durably remembers each map transition the player has actually completed, including the source map and coordinate, directional input, and resulting map and coordinate. It does not persist connected regions or ordinary movement within a map.

**Scope:**

- Store one directed row for each observed transition from `(source map, source coordinate, direction)` to `(destination map, destination coordinate)`.
- Record only transitions caused by directional input issued from an external overworld decision boundary. Require the operation to return to overworld control and match either the ROM's ordinary-warp identity or the loaded cardinal connection exactly, so passive relocation, Fly, blackout recovery, and scripted escorts cannot create route evidence.
- Do not record movement between transition points, infer that endpoints on the same map connect, parse an unexplored global ROM graph, or maintain persistent connected-region identities.
- Treat every demonstrated connection as directed. The ROM does not guarantee reciprocal warp records, so an observed transition never creates an unobserved reverse edge.
- Make repeated observations idempotent and retain the existing warp-discovery and usage behavior. Persistence failures must remain recoverable and must not interrupt gameplay.

**Tests included in the commit:**

- Cover directly controlled ordinary warps and cardinal boundary crossings, including rejection of control handoffs and relocations that do not match the activated ROM transition.
- Cover directed observation, rejection of invalid transitions, and recoverable persistence failure through the owning overworld service.

**Documentation included in the commit:** Record the observed-transition model, observation rules, and recoverable failure behavior in this technical ticket. No agent-facing route guidance or public workflow change belongs in this stage.

### Commit 2: Add shortest known route recall

**Outcome:** The overworld agent can ask for a previously visited map and receive one concise shortest known route from its current reachable region to the nearest known entry into that map. Route recall informs the agent but does not move the player or take control of local navigation.

**Scope:**

- Add an on-demand route-recall tool whose destination is resolved only against visited map names. Do not expose the complete `MapId` enum, unvisited destinations, unobserved connections, or the complete stored graph through the tool schema or result.
- Build the route graph transiently. Use the existing explored terrain, blockages, traversal rules, and current field-move capabilities to connect stored arrival and departure coordinates that are presently reachable within the same map; do not persist those derived connections.
- Start route search from transitions reachable from the player's current coordinate and treat every observed arrival on the requested map as an acceptable destination. Choose one deterministic shortest route; Route 2 from Pewter may therefore end at its northern entry, while Route 2 from Viridian may end at its southern entry.
- Keep endpoint and disconnected-area distinctions internal. The result should describe the necessary map sequence and identify exact warps, ladders, or boundary coordinates only where they help the agent execute the route without ambiguity.
- Search only observed directed map transitions and connectivity derived from explored local terrain. This keeps disconnected parts of Route 2 separate before Cut is usable and joins them when the existing traversal rules can actually cross the tree.
- Return a recoverable, useful result when the destination is unvisited, already reached, ambiguous, or has no demonstrated route. The tool must never block gameplay or attempt a multi-map control loop; the existing local navigation and button tools remain responsible for executing each step.

**Tests included in the commit:**

- Cover shortest-path selection from the current reachable endpoints to any entry on the destination map, including the nearest-side Route 2 case.
- Prove that two disconnected areas sharing a map ID do not create an invalid through-route and that current traversal capabilities can change the derived local connectivity without rewriting route history.
- Cover directed and cyclic dungeon routes, deterministic tie-breaking, visited-map filtering, already-present and no-route outcomes, and tool registration without asserting model-facing wording.

**Documentation included in the commit:** Add a concise public workflow description of route recall as an informational tool for previously visited maps, without documenting graph internals. Update this technical ticket with the final search and censoring behavior.

### Validation and review cadence

For each commit, run focused lifecycle, persistence, routing, and tool tests while iterating, then run `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, `uv run python -m pytest`, and `git diff --check` before presenting it for review. Do not start the indefinite application, make live model calls, or use an unbounded emulator smoke test. Work in the numbered order and pause for review after each commit-sized stage.

## Commit 1 implementation notes

- A route transition stores only the source map and coordinate, directional input, destination map and coordinate, and first-observed iteration. There are no named or persisted connected regions.
- The manual-button and local-navigation services already own direct overworld input, so they record a transition after the accepted operation returns. Ordinary warps must match the ROM's source and destination records; cardinal crossings must match the loaded connection and coordinate transform. No reverse edge is inferred.
- Intra-map connectivity will be derived on demand in commit 2 from existing explored-map data and traversal rules. Repeated observations are idempotent.
- Route persistence is recoverable state: a failed write emits a warning and gameplay continues. No route is exposed to the agent until commit 2.

## Commit 2 implementation notes

- The route tool accepts a map name as text and resolves it only against the maps already present in explored-map memory. Its schema does not enumerate map IDs, and an unvisited destination reveals no new world information.
- Each request derives local connectivity from the current reachable region plus remembered terrain and blockages, using the player's current field-move capabilities. The search keeps each map-qualified arrival coordinate distinct and follows only observed directed transitions, so disconnected parts of one map remain separate unless the remembered terrain is currently traversable between them.
- A breadth-first search returns the first deterministic route with the fewest observed transitions to any known entry into the requested map. The result is informational and does not move the player. It distinguishes step-on warps such as doors and ladders, directional warps, and cardinal map boundaries so each step names the correct coordinate and execution method.
- Missing routes and route-memory read failures return recoverable action results. A read failure emits a warning and gameplay continues.
