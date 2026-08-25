> This ticket is a starting point for investigation, not a specification. It was written against an older version of the code, and the implementation may have changed since then. Verify the current behavior and code before making changes. The problem is real; the proposed solution is not set in stone.

# Rolling memory and goal maintenance

## Problem

Compacted memory is retaining too many incidental waypoints, exact movements, and transient tactical details. It is also becoming advisory: summaries contain instructions and imperatives about what the agent should do next instead of neutrally recording what happened and what remains unresolved. This makes old summaries noisier and more authoritative than they should be.

Compaction can also interrupt the stream for several minutes. A single finalized iteration can currently schedule every eligible compaction in the loaded memory tree. Near a large tree boundary, enough summaries may become eligible together that gameplay appears to stop while memory maintenance finishes.

The logarithmic memory structure itself is still desirable. The problem is the amount of work permitted during one gameplay iteration, not the hierarchy.

The separate goal system is also not reliably producing long-term thinking. The agent usually creates one goal near the beginning of a run, rarely adds another, and often leaves the existing goal unchanged long after it has become stale. The current reminder after 100 iterations is easy to ignore. Removing goals entirely may discard useful long-term context, but leaving the current behavior unchanged provides little value.

## Proposed direction

Tighten the compaction prompt around neutral factual history. Preserve durable outcomes, corrections, unresolved obstacles, material game state, and failed approaches whose result still matters. Remove commands, recommendations, plans presented as instructions, exact button sequences, routine navigation, incidental waypoints, self-talk, and combat minutiae unless they produced a lasting consequence.

Give compaction a small per-iteration work budget and defer the remaining eligible merges. The same eligible ranges should eventually be compacted as gameplay continues, preserving the logarithmic tree while amortizing its maintenance. Investigation should determine whether the budget counts requests, source size, expected latency, or some combination, but the initial implementation should remain simple.

Raw-leaf creation and higher-level merges must both make progress without starving one another or allowing the uncompacted raw tail to grow without bound. Avoid introducing unmanaged background tasks unless the synchronous budget cannot meet the viewing requirement; background ownership, shutdown, backup consistency, and failure recovery would add complexity.

Retain the goal system initially and add a hard maintenance threshold after a substantially longer interval, tentatively 300 iterations. When no successful goal update has occurred within that interval, give the overworld agent a maintenance turn in which goal editing is the only available action. After one successful update, normal tools return on the next turn. This should force periodic review without making goal editing part of ordinary movement.

Track staleness for the goal collection as a whole rather than forcing every individual goal to remain fresh. Investigation should determine how to represent the last successful review when the list is empty and whether replacing a goal with identical text should count. Encourage multiple distinct goals when the agent genuinely has several durable concerns, but do not require it to fill all four slots.

## Relevant code

- `memory/rolling_memory/service.py` finalizes iterations, discovers every eligible parent pair, and currently submits all selected summaries with `asyncio.gather`.
- `memory/rolling_memory/prompts.py` defines the compaction system and request prompts.
- `memory/rolling_memory/schemas.py` defines raw blocks, summary levels, and the in-memory frontier.
- `database/rolling_memory/repository.py` persists raw blocks and summaries and reconstructs the highest non-overlapping frontier.
- `database/rolling_memory/model.py` and `database/rolling_memory/schemas.py` define the persistence boundary.
- `common/constants.py` contains leaf size, raw-tail limits, and summary-size limits.
- `agent/context.py` synchronously finalizes memory at the end of a gameplay iteration.
- `memory/goals.py` defines the goal collection and per-goal update iteration.
- `agent/overworld/tools/set_goal/interface.py` and `agent/overworld/tools/set_goal/service.py` implement indexed goal changes.
- `agent/overworld/tools/registry.py` constructs the normal overworld toolset and is a likely place to investigate a goal-only maintenance turn.
- `agent/overworld/prompts.py` computes the current 100-iteration warning and presents goals to the overworld agent.
- `agent/formatting/memory.py` formats goals and rolling memory for model prompts.

## Questions to answer during investigation

- Which examples from the live run demonstrate the unwanted advisory tone and unnecessary details most clearly?
- What is the smallest per-iteration budget that keeps maintenance current without creating visible pauses?
- In what order should raw-leaf work and parent merges be selected when both are eligible?
- Does the current LLM client actually execute parallel compactions concurrently, or are requests effectively serialized downstream?
- Can the same eventual frontier be demonstrated under deferred scheduling without depending on exact prompt output?
- Should the forced threshold measure the last successful goal-tool call, the newest goal timestamp, or an explicit collection-level review timestamp?
- What should happen when the goal list is empty at the threshold?
- Should an identical replacement count as a completed review, or should the agent be required to make a meaningful change?
- Is one goal-only tool call sufficient, or does the indexed tool make it impossible to conduct a coherent review of several goals in one maintenance turn?

## Success criteria

- Compacted summaries read as neutral records rather than advice to the future agent.
- Routine moves, incidental coordinates, and exact action sequences disappear unless they remain materially relevant.
- The number of compaction requests started by one gameplay iteration is explicitly bounded.
- Deferred work is eventually completed and the logarithmic memory invariant is preserved.
- Compaction failures remain recoverable warnings and cannot crash gameplay.
- The agent cannot ignore goal maintenance indefinitely.
- A forced review interrupts normal play for no more than the necessary maintenance turn or turns.
- Goals remain optional in number and meaningful in content; empty padding is not rewarded.
- Algorithmic tests cover scheduling and frontier invariants where useful; do not add tests that assert prompt wording or formatted model-facing prose.
