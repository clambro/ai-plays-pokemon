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
