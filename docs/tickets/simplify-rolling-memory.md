# Ticket: Replace Raw and Summary Memory with Rolling Memory

## Outcome

Replace the separate raw-memory and summary-memory systems with one coherent
rolling-memory system that can cover an entire playthrough:

- raw memory remains an append-only record of application iterations;
- prompts contain exact recent iterations and progressively coarser summaries
  of older history;
- SQLite stores the complete raw history and the derived summary tree; and
- the HTML activity log continues to show raw iteration memories, independent
  of the representation used in prompts.

Long-term memory remains a separate title-based system.

## Iteration-Level Memory

The unit of raw memory remains the current application iteration. It is not an
individual model request, response, tool call, or future Pydantic AI agent
step.

Multiple memory writes during one iteration append to the same in-memory
block, preserving their order. Once the iteration is complete, that block is
finalized and written to SQLite once. Summary generation must only consume
finalized iteration blocks; it must never summarize a block that can still
change.

This boundary may be reconsidered after the agentic orchestration work, but
changing it is not part of this ticket.

## Persistence

Add a rolling-memory database package following the existing repository
structure.

The database should contain:

- an append-only raw-memory table with at most one finalized block per
  iteration; and
- a summary table containing immutable derived summaries for explicit
  iteration ranges and tree levels.

Raw blocks are the source of truth and are never deleted by compaction.
Summary rows are rebuildable derived data. Do not add importance, decay, or
last-accessed fields.

The active agent state should retain only bounded working data, including the
current unfinished iteration and the memory view needed by the current
workflow. The complete history belongs in SQLite and is therefore included in
the existing database backups rather than repeatedly serialized into
`AgentState`.

## Hierarchical Summaries

Use an OptMem-inspired binary summary tree rather than one repeatedly rewritten
global summary.

Start with fixed, aligned ranges of finalized iterations. A leaf summary
compresses the raw blocks within one range. When two adjacent summaries at the
same level exist, they can be combined into one parent whose range covers both
children. Each higher level therefore represents twice as much history.

Keep the child summaries and raw blocks after creating a parent. This makes
the tree inspectable and allows summaries and prompt views to be rebuilt
without losing the original record.

Initial sizes should preserve approximately the current cost profile. For
example, twenty-iteration leaf ranges produce fewer than one summary operation
per ten iterations on average once parent merges are included. Treat the exact
range and output limits as named configuration values that can be tuned later.

Perform at most one summary operation per application iteration. If a parent
summary is still pending, its existing children remain usable in the prompt
view; gameplay does not need to wait for the tree to become completely merged.

## Prompt View

Render one chronological rolling-memory section:

1. Load the current summary frontier: the highest existing non-overlapping
   nodes that cover older history.
2. Because the frontier follows the binary tree, it naturally uses smaller
   ranges near the present and increasingly large ranges farther in the past.
3. Follow those summaries with the most recent iteration blocks verbatim,
   including the current unfinished iteration when it has content.

Every summary shown to the model must identify the iteration range it covers.
The selected ranges must not overlap or leave gaps in finalized history.

The summarization prompt should retain lasting outcomes, unresolved work,
failed approaches, and later corrections while removing repetition,
transient mechanics, and self-talk. It must derive its answer only from the
raw range or child summaries supplied to it and must not invent outcomes.

The renderer should use the raw database records and summary tree as inputs.
Pydantic AI message-history compaction and provider-native conversation
compaction are not substitutes for this gameplay-memory view.

## HTML Activity Log

The HTML display continues to use raw iteration memories only. Summary
creation must never alter the visible log.

Stream the loaded raw working set directly. The browser already scrolls the log
to the bottom, so the viewport naturally shows however many recent entries fit
on screen. Do not introduce another buffer or memory limit for the display:

- every write to the current iteration updates its visible entry immediately;
- the complete finalized history remains in SQLite after blocks leave the
  loaded working set; and
- startup and backup restoration repopulate the raw working set from the most
  recent finalized database blocks, plus any unfinished iteration restored
  from agent state.

Continue publishing the loaded raw blocks to the background server after every
raw-memory mutation so the HTML remains live during long navigation, battle,
and text operations. The application-level memory service should coordinate
the mutation and publication; the database model and raw block records
themselves should not depend on the streaming server.

## Step-by-Step Implementation Plan

1. **Add rolling-memory persistence.**
   Create the raw-block and summary database models, boundary schemas, and
   repository operations. Support finalizing one iteration, reading recent raw
   blocks, reading a raw iteration range, storing summaries, and loading only
   the current top-level non-overlapping summary frontier. Register the models
   during fresh database initialization.

2. **Introduce the rolling-memory domain model.**
   Add a small internal model for the current iteration and bounded prompt
   view. Preserve the existing behavior where repeated writes to one
   iteration append in order. Keep the current iteration as a mutable working
   block, and create an immutable raw block only when that iteration is
   loaded back from SQLite. Treat the loaded raw blocks and summary frontier as
   immutable database read views. Use the same loaded raw blocks for the live
   HTML log. Keep database and streaming dependencies outside the stored
   memory records.

3. **Persist completed iterations.**
   Move iteration finalization to the end of a completed top-level workflow.
   Write the combined block once, reload the bounded raw view from SQLite, and
   then begin the next mutable iteration. Hydrate the same view from the copied
   database after startup or backup restoration. Include any unfinished
   iteration restored from agent state without duplicating a finalized
   database block. Update existing memory-writing services to target the
   unified iteration-level interface without changing their gameplay
   behavior.

4. **Build hierarchical compaction.**
   Replace the periodic summary-memory updater with a service that finds the
   next eligible leaf or parent range, requests one bounded summary, and stores
   it only after a successful response. Limit it to one summary operation per
   application iteration and leave its source blocks untouched.

5. **Render the rolling prompt view.**
   Load the summary frontier for older history, append exact recent blocks, and
   expose one chronological memory string to the top-level and subflow state
   builders. Keep direct access to the current raw iteration for services that
   continue or amend the current thought.

6. **Wire the live HTML view.**
   Publish the loaded raw blocks after every mutation of the current raw
   iteration and let the browser viewport determine how many are visible. Keep
   summary content out of the activity log.

7. **Remove the old split memory systems.**
   Delete `RawMemory`, `SummaryMemory`, summary pieces, importance and decay
   logic, the old periodic summary node, and their separate size constants.
   Replace the two state fields with the bounded rolling-memory working state
   and update backup serialization accordingly.

8. **Update the memory documentation and behavioral coverage.**
   Document the raw database record, hierarchical prompt view, and
   iteration-finalization boundary. Cover the important behavior: multiple
   writes form one finalized iteration, recent HTML entries remain raw, prompt
   ranges are chronological and complete, compaction never removes source
   history, and database-backed memory survives backup restoration. Avoid
   tests that merely freeze internal implementation details.

## Out of Scope

- Changing the application iteration boundary to individual agent or model
  steps.
- Redesigning title-based long-term memory.
- Embedding retrieval or RAG.
- Making historical summaries selectable agent tools.
- Replacing Junjo or implementing the later Pydantic AI orchestration.
- Sending the complete raw history to either normal prompts or the HTML
  polling response.

## References

- [OptMem](https://github.com/VictorTaelin/OptMem)
- [Recursively Summarizing Books with Human Feedback](https://arxiv.org/abs/2109.10862)
- [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)
- [LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory](https://arxiv.org/abs/2410.10813)
