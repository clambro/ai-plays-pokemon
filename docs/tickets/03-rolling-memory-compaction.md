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

## Staged implementation plan

This plan is intentionally a starting sequence rather than a complete up-front design. Each stage is one independently shippable commit: it delivers a coherent behavior change, includes its own tests and documentation, leaves the repository passing, and can be reviewed and merged before the next stage is designed in detail. Later stages should be revised when earlier implementation or runtime evidence changes the assumptions below; no commit should land speculative scaffolding for a later stage.

### Commit 1: Keep compacted memory factual and durable

**Outcome:** Rolling-memory summaries preserve durable history without turning prior reasoning into instructions for the future agent. Routine movement, incidental coordinates, exact action sequences, transient tactics, and self-talk disappear unless they produced a lasting consequence.

**Implementation:**

- Tighten the compaction guidance around neutral factual records: confirmed lasting outcomes, observed corrections, unresolved obstacles, and failed approaches whose result still matters. Treat plans and interpretations as unconfirmed, and explicitly exclude commands, recommendations, transient state, and routine tactical details.
- Remove incidental coordinates while retaining exact coordinates that identify a durable, non-obvious route, warp, ladder, or interaction that would otherwise need to be rediscovered.
- Set one 2,000-character limit. Give an overlong response one explicit shortening request; if that rewrite also exceeds the limit, emit a warning and store the best-effort result so length compliance never blocks compaction.
- Preserve the existing logarithmic hierarchy and model-facing memory format. This stage changes what a summary retains and makes length compliance best effort, not when otherwise eligible compaction runs.

**Tests included in the commit:** Retain and run the rolling-memory schema, formatting, and lifecycle tests as regressions. Review the prompt and best-effort length behavior directly; do not add tests that merely restate thin request orchestration or assert prompt wording and generated prose.

**Investigation evidence:** The 4,660-iteration run in `outputs/database/memory.db` contains 450 summaries across eight levels. Nine exceed the configured 3,000-character limit, including the 4,115-character summary covering iterations 1–2560. Older summaries retain obsolete current-party snapshots, combat tactics, incidental coordinates, flavor text, and imperative language. Confirmed raw transitions show that Vermilion was reached at iteration 1915 and the S.S. Anne was boarded at iteration 1951, yet later merges describe Vermilion as both reached and still being pursued before eventually claiming it had not been reached. This demonstrates that later agent reasoning is overriding earlier observed outcomes.

**Documentation included in the commit:** Record the factual-history policy, coordinate exception, best-effort length-revision behavior, and demonstrated live-run failures in this technical ticket. No public workflow documentation change is needed.

### Commit 2: Bound rolling-memory maintenance per iteration

**Outcome:** Finalizing one gameplay iteration selects at most one eligible range for compaction, so a large frontier cannot pause gameplay for a burst of simultaneous maintenance. That range uses one initial LLM request and, only when necessary, the single length-revision request introduced in commit 1. Continued successful iterations still compact the raw tail and every eligible parent merge while preserving the same logarithmic memory structure.

**Implementation:**

- Replace the current submit-everything behavior with a deterministic one-range budget. Prefer an eligible raw leaf when the raw tail reaches its limit; otherwise process one eligible adjacent same-level summary pair, allowing parent work to advance between leaf creations.
- Keep the database as the source of truth and reconstruct the frontier after successful maintenance. Preserve the existing recoverable-warning behavior when selection, summarization, storage, or reload fails; gameplay must continue from the finalized raw iteration.
- Do not add background tasks, queues, database migrations, or a second in-memory authority for pending work. Eligibility remains derivable from the persisted summaries and raw blocks already loaded for the current iteration.

**Tests included in the commit:**

- Add service-level behavior tests showing that one call selects no more than one eligible range, chooses raw work when the tail requires it, otherwise advances an eligible parent merge, and performs no request when nothing is eligible.
- Exercise many synthetic iterations through the public maintenance behavior and assert that raw leaves and higher-level merges both make progress, the raw tail stays bounded after successful maintenance, and the reconstructed frontier remains chronological and non-overlapping.
- Retain the lifecycle regression proving that a compaction failure advances the persisted iteration without crashing gameplay.

**Documentation included in the commit:** Record the selected budget, scheduling rule, demonstrated bounds, and failure behavior in this technical ticket. No public workflow documentation change is needed.

### Commit 3: Force periodic collection-level goal review

**Outcome:** The overworld agent cannot ignore goal maintenance indefinitely. After 300 iterations without a successful review, its next overworld turn permits only goal review; one successful review ends the maintenance turn, and normal gameplay tools return on the next turn.

**Implementation:**

- Make one persisted collection-level review iteration the source of truth for staleness, including when the goal list is empty. Restore older backups with a safe default derived from the state they already contain rather than requiring a migration or failing to load.
- Let one goal action submit the reviewed collection coherently, with zero to four distinct goals. An unchanged or empty collection may be an intentional successful review, while invalid input remains a recoverable tool result and does not clear the maintenance requirement.
- Use the same successful collection update during ordinary play to refresh the review iteration. When maintenance is due, expose only that action, then return control to the dispatcher after success so the next overworld activation rebuilds the normal toolset.
- Keep goals optional and do not reward placeholder entries. The maintenance mechanism enforces review of the collection, not a required number of goals or a walkthrough-derived objective.

**Tests included in the commit:**

- Add goal-domain tests for coherent zero-to-four-goal replacement, rejection without partial mutation, intentional identical and empty reviews, collection-level staleness, backup round trips, and backwards-compatible loading.
- Add overworld behavior coverage showing that normal tools remain available before the threshold, only goal review is available when due, an invalid review keeps maintenance active, and a successful review restores the normal toolset on the next turn.
- Test tool availability and state transitions without asserting prompt prose, tool-description wording, or making live model calls.

**Documentation included in the commit:** Record the collection-level staleness contract, empty-list behavior, and maintenance-turn lifecycle in this technical ticket. Keep the threshold and persistence mechanics out of the public workflow document.

### Validation and review cadence

For each commit, run its focused tests while iterating, then run `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, `uv run python -m pytest`, and `git diff --check` before presenting it for review. Do not start the application, make live model calls, or use an unbounded emulator smoke test. Work in the numbered order and pause for review after each commit-sized stage.
