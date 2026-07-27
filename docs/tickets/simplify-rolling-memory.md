# Ticket: Replace Raw and Summary Memory with Rolling Memory

## Outcome

Replace the separate raw-memory and summary-memory systems with one small
rolling-memory domain model:

- recent gameplay events remain verbatim;
- older recent events are represented by one bounded editable summary; and
- compaction occurs only when the recent buffer exceeds its configured limit.

The design borrows OptMem's append-first, bounded-context, deterministic
compaction ideas without installing its CLI, copying its unlicensed source, or
implementing its filesystem and summary tree.

**Depends on:**

- [`replace-llm-message-db-with-logfire.md`](replace-llm-message-db-with-logfire.md)
- [`replace-gemini-with-gpt-5-6-luna.md`](replace-gemini-with-gpt-5-6-luna.md)

**Does not change:** Database-backed long-term memory

## Design

`RollingMemory` should be an internal standard-library dataclass containing:

- one event per iteration, with multiple writes appended in order;
- a chronological recent-event collection;
- one summary string; and
- a cursor identifying the newest event removed by successful compaction.

Pydantic remains at the LLM response and v2 backup boundaries rather than
being the internal memory model.

Use named, provider-independent limits. Initial values may retain the current
50-iteration recent window, compact the oldest 20 entries at a time, and cap
the summary at roughly 12,000 characters, but finalize them from representative
v2 transcripts.

## Compaction Contract

- Appending an event never requires an LLM call.
- At or below the recent-event limit, no compaction call occurs.
- Above the limit, code selects the exact oldest batch.
- The model receives only the existing summary and selected batch.
- The response is one replacement summary with a configured length limit.
- The new summary may reconcile corrected information and remove repetition,
  resolved transient details, and self-talk, but must not invent outcomes.
- Replace the summary and delete the selected events only after the response
  and batch identity are validated.
- On any failure, retain the previous summary and every source event. Temporary
  overflow is preferable to data loss.
- Attempt at most one compaction per gameplay iteration and make persistent
  overflow visible in logs and telemetry.

The compactor must be independent of Junjo. A workflow node may invoke it
temporarily, but the memory model and compaction service must not depend on
workflow types.

## Integration Changes

- Replace `raw_memory` and `summary_memory` in agent/subflow state with one
  `rolling_memory` value.
- Replace the periodic summary-update node, importance values, decay logic,
  and separate size constants.
- Give normal prompts one memory section containing older summary followed by
  exact recent events.
- Give loop detection and the activity stream the recent-only view.
- Remove the streaming-server side effect from memory append; streaming should
  occur at the orchestration boundary.
- Keep retrieved long-term memories separate from rolling compaction and normal
  rendering.
- Define one v2 backup representation and test its round trip without a
  load-time LLM call.
- Record compaction prompt name, token/cost use, batch size, duration, and
  failures through the telemetry system.

## Out of Scope

- Redesigning long-term memory.
- An unbounded raw archive or hierarchical summary tree.
- OptMem subprocess or filesystem integration.
- Importance scores, decay, immutable summary pieces, or hidden truncation.
- Junjo removal.
- Broad gameplay prompt rewrites.

## Validation

Use unit tests for append behavior, deterministic batch selection, rendering,
cursor advancement, stale-batch rejection, and failure atomicity. Integration
tests should cover every subflow, prompt rendering, stream output, v2 backup
round trip, long-term-memory interaction, and recovery after a failed
compaction.

Evaluate summary quality on recorded gameplay transcripts. Compare retained
milestones, unresolved goals, failed approaches, corrections, token use, and
summary size rather than exact wording.

## Acceptance Criteria

- [ ] Agent state and subflows use one rolling-memory value.
- [ ] Recent events remain ordered and verbatim.
- [ ] One bounded summary represents compacted recent history.
- [ ] Compaction is triggered by overflow and selects its batch
      deterministically.
- [ ] Only the existing summary and selected events enter the compaction
      prompt.
- [ ] Failed or stale compaction loses no information.
- [ ] Importance, decay, periodic summary calls, and their old models are
      removed.
- [ ] Loop detection, prompts, streaming, telemetry, and the v2 backup format
      use the correct rolling-memory views.
- [ ] Long-term memory remains a separate durable tier.
- [ ] The domain model is independent of Junjo and uses standard dataclasses.

## References

- [OptMem repository](https://github.com/VictorTaelin/OptMem)
- [GitHub licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
