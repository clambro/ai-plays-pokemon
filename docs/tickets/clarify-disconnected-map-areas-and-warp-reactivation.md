# Ticket: Clarify Disconnected Map Areas and Warp Reactivation

## Outcome

Explain two local navigation facts unambiguously:

- a map ID can contain multiple areas that are not reachable from one another
  without changing maps; and
- a step-on warp beneath the player is inactive until the player leaves it and
  deliberately enters it again.

Keep the existing current-region map view and map-local navigation tool. Do not
add cross-map routing, derived world graphs, other-region summaries, transition
history, or movement restrictions.

**Depends on:**

- [`enforce-code-structure-and-model-discipline.md`](enforce-code-structure-and-model-discipline.md)

## Problem

The current agent-facing map deliberately displays only the area reachable from
the player's position. This substantially improves coordinate reasoning, but
the model can incorrectly assume that one map ID always represents one
connected physical area. Route 2 is the representative outdoor example: its
northern and southern areas are connected only by leaving Route 2 and walking
through the Viridian Forest gates and Viridian Forest.

Multi-floor dungeons expose a related identity problem. Coordinates belong to
a specific map ID, so the same coordinates on two Mt. Moon floors identify
different locations. A map-local navigation failure must not be interpreted as
a broken pathfinder or as evidence that two floors share a coordinate system.

The previous warp guidance created a direct behavioral loop. After an
ordinary step-on warp changes maps, the player arrives standing on the
destination warp. It told the model to walk off that tile and step back onto
it. Although mechanically accurate, that was phrased as an action recipe and
encouraged the model to immediately return through the warp it just used.

The Mt. Moon B1F/B2F loop is the representative failure. On B1F the player
arrived at `(11, 17)` on a warp leading back to B2F, while another reachable
B1F warp at `(9, 25)` led to 1F. The model repeatedly followed the reactivation
recipe for the warp beneath it instead of selecting the other local warp.

## Required Changes

### Neutral Warp Reactivation Language

When the player is standing on a step-on warp, describe its current state
without prescribing a movement sequence. Explain that:

- the warp is currently inactive;
- it activates only when entered from another tile; and
- re-entering it should be deliberate because it travels to the destination
  already stated in the warp record.

Do not tell the model to "walk off and step back on." Do not prevent the player
from re-entering the warp or otherwise constrain movement.

### Connected-Area Invariant

Add a short general explanation beside the current-region map:

- one map ID can contain multiple disconnected areas;
- the displayed region is only the area currently reachable without changing
  maps, based on revealed terrain;
- another area with the same map ID may require leaving through a warp or map
  boundary and re-entering elsewhere; and
- coordinates are scoped to their map ID, so identical coordinates on
  different maps or floors are different locations.

Do not enumerate, summarize, label, or render the other areas. Continue showing
only the current region and its current local affordances.

### Navigation Failure Semantics

Replace the generic unreachable-target response with specific local feedback:

- an unseen target has no revealed route yet and should be approached by
  exploring;
- a revealed non-traversable target is not a valid movement destination; and
- a revealed walkable target outside the current reachable region cannot be
  reached by the map-local navigation tool. Explain that the tool is working as
  intended and that another area of the same map may require leaving and
  re-entering elsewhere.

Navigation remains strictly map-local and continues to reject inaccessible
targets.

## Out of Scope

- Deriving or persisting region identities.
- Displaying known exits, landmarks, terrain, or coordinates from other
  regions.
- Persisting warp-transition endpoints or traversal counts.
- Constructing a local-region or global world graph.
- Adding a cross-map route planner or semantic travel tool.
- Blocking, delaying, or requiring confirmation for any movement or warp.
- Predetermined routes or walkthrough knowledge.
- Changing the ASCII grid, crop, coordinate system, or local pathfinder.

## Validation

Review the model-facing prompt, formatting, and tool-result changes directly.
Do not add tests that assert their wording. Existing integration coverage
continues to protect ordinary reachable navigation behavior.

Before launch, replay the representative Route 2 and Mt. Moon save states in a
bounded manual model evaluation. The standard automated suite must not make live
model calls or start the indefinite gameplay loop.

## Acceptance Criteria

- [ ] Standing on a step-on warp never produces an instruction to step back
      onto it.
- [ ] Warp reactivation remains available and is never mechanically blocked.
- [ ] The prompt states that one map ID may contain multiple disconnected
      areas.
- [ ] The prompt states that coordinates are scoped to a map ID.
- [ ] The agent receives explicit local feedback when a revealed target lies
      outside the current reachable region.
- [ ] Unseen and non-traversable targets receive distinct feedback.
- [ ] No other-region summary, region graph, transition ledger, cross-map
      planner, new navigation tool, or persistent state is introduced.
- [ ] The current-region ASCII view and map-local navigation behavior remain
      otherwise unchanged.
