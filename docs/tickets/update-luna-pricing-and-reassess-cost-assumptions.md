# Ticket: Upgrade Dependencies and Rework Luna-Era Iteration Boundaries

## Outcome

Upgrade the complete dependency set, update forward-looking GPT-5.6 Luna cost
accounting, and change application iterations from whole handler activations to
individual completed agent decisions. Reassess the overworld agent-run boundary
separately so longer conversations do not depend on the memory iteration
boundary.

Implement the work as the five ordered, self-contained commits below. Each
commit must include any tests and documentation required by its own behavior.
There is no final documentation-only commit.

## Constraints

- All pricing work is forward-looking. There is no historical usage to migrate,
  preserve, backfill, or price according to an old request date.
- Keep pricing data package-versioned. Do not add the optional
  `genai-prices.UpdatePrices` runtime downloader.
- Prompt caching must remain enabled throughout the iteration and agent-loop
  changes. Preserve stable cache keys, instructions, tool definitions, and
  conversation prefixes wherever they are stable today.
- Keep bounded context, rolling-memory compaction, telemetry, visible token and
  cost totals, and deterministic gameplay tools.
- Do not reconstruct an agent or restart its Pydantic AI conversation merely to
  advance the application iteration.
- Documentation describing a behavior change belongs in the same commit as the
  code implementing that change.

## Current Behavior

`run_overworld`, `run_battle`, and `run_text` each initialize one rolling-memory
iteration when the handler starts and finalize it when the handler returns.
Every model response, tool result, and deterministic observation produced during
that handler activation is appended to the same mutable block.

This makes the meaning of an iteration depend on the handler:

- a battle of any length is one iteration;
- a complete text interaction is one iteration; and
- an overworld activation is one iteration, usually ending after the player
  moves or the gameplay domain changes.

The iteration number, persisted raw-memory blocks, compaction window, and HTML
activity log therefore describe handler activations rather than individual
model decisions.

The application also currently makes the memory iteration boundary and the
Pydantic AI conversation boundary coincide. These are separate concerns. A
conversation can remain alive across several decisions while each completed
decision is finalized as its own application iteration.

## Target Iteration Semantics

For model-driven gameplay, one iteration is one completed decision cycle:

1. observe the state needed for the decision;
2. receive the model response and selected tool call;
3. execute the tool; and
4. record the deterministic action result and resulting observation.

Finalize the iteration only after the tool node has completed. The existing
`after_model_request` hook is too early because the selected action has not yet
executed and its actual result is not yet known.

Dialog or other deterministic observations caused by a tool belong to the same
iteration as the decision that caused them. Deterministic-only work that
produces durable activity without any model decision receives its own iteration;
do not create empty iterations.

Advancing an iteration inside a handler must not restart the active
`agent.iter(...)` run. Subsequent model calls must retain the existing message
history, stable prompt prefix, prompt-cache key, instructions, and tool schema.

## Commit Plan

### Commit 1: Upgrade all dependencies

Update every direct runtime and development dependency to its latest compatible
release and regenerate the complete lockfile. This includes `genai-prices`,
OpenAI, Pydantic AI, Logfire, the database packages, and development tooling.
Keep PyBoy exactly pinned because emulator upgrades can invalidate existing save
states; update the pin only if a newer version is deliberately accepted with
that consequence.

Include all compatibility, typing, lint, formatting, and stale expectation
changes required for the upgraded environment to work as a complete commit.
Do not mix iteration-boundary refactoring into this dependency upgrade.

### Commit 2: Align Luna cost accounting

Confirm that both accounting paths use the current Luna prices supplied by the
upgraded `genai-prices` package:

- direct OpenAI Responses API calls through `OpenAILLMService`; and
- Pydantic AI responses through `ModelResponse.cost()`.

No request-date branching or historical pricing test matrix is needed. Use one
representative usage case to verify that both paths produce the same total, and
retain or update the existing long-context assertion so the higher tier remains
covered without duplicating every token category.

Update the README cost guidance in this commit. Keep the HTML and persisted
totals backed by `AgentState.total_cost`; do not introduce a second cost ledger
or a historical correction path.

### Commit 3: Separate iteration lifecycle from handler lifecycle

Refactor rolling-memory lifecycle operations so a live handler can finalize the
current non-empty block and immediately advance to the next block without being
restarted. Keep the externally observable handler-level iteration behavior
unchanged in this commit.

The lifecycle operation must keep these values synchronized:

- the finalized SQLite raw-memory record;
- the in-memory exact raw tail and summary frontier;
- the new mutable current block; and
- `AgentState.iteration` used by gameplay services and the HTML view.

Define failure ordering so persistence, compaction, and the in-memory counter
cannot silently disagree.

This commit must not alter prompt caching. Do not change the three
`openai_prompt_cache_key` values, agent instructions, tool schemas, agent input,
or Pydantic AI conversation lifetime. The refactor only makes the memory
lifecycle capable of advancing inside an already-running conversation.

### Commit 4: Make completed decisions individual iterations

Use the new lifecycle operation in all three gameplay handlers. After each
model-selected tool node finishes and its deterministic results have been
recorded, finalize that decision and advance the iteration while leaving the
active Pydantic AI conversation alive.

Apply the same semantics to overworld, battle, and text in this commit so the
iteration number never has different meanings in different handlers. Handle
deterministic-only activity explicitly and avoid empty or half-completed
iterations.

Increase the rolling-memory leaf size to preserve a substantial exact tail when
the unit changes from handler activations to decisions. Size the window in
completed decisions, then keep the existing hierarchical compaction model for
older history. Reassess the compaction trigger and prompt size as part of this
same change.

Prompt caching remains mandatory. Do not rebuild the agent or initial prompt on
each iteration. Calls inside one handler continue through the same
`agent.iter(...)` conversation, allowing the stable prefix and growing message
history to remain cacheable.

Update `docs/workflow.md` and `docs/philosophy.md` in this commit so iteration,
memory, compaction, deterministic activity, and the HTML activity log are
documented according to the implemented behavior.

### Commit 5: Extend the overworld conversation boundary

Reassess the current rule that returns to the dispatcher after any player
movement. Continue the same overworld Pydantic AI conversation across ordinary
same-map actions when the next decision can be made from refreshed state.

Before continuing, refresh the relevant overworld observation and ensure that
tools validate dynamic game state at execution time. End the run at semantic
boundaries such as entering battle or text mode, changing to a map that requires
new prepared context, or reaching an invalid gameplay state.

Add a bounded-turn or elapsed-time safeguard for genuine no-progress loops. The
safeguard exists for operational control, not merely to cap model cost.

Preserve prompt caching by keeping the same active agent conversation and stable
tool definitions across continued turns. Do not trade away the existing cache
keys or stable prompt prefix to obtain longer loops.

Update the overworld sections of `docs/workflow.md` and any affected design text
in this commit. Remove this completed ticket in the same commit once the full
plan is implemented.

## Completion

- All direct and transitive dependencies are current and locked.
- Both Luna accounting paths produce the same current forward-looking cost.
- Token and cost totals continue to persist in backups and appear in the HTML
  view.
- Each completed model decision is one iteration, including its executed action
  and deterministic result.
- Deterministic-only durable activity has explicit non-empty iteration behavior.
- The exact rolling-memory window is appropriately larger in decision units and
  older history still compacts hierarchically.
- Battle and text conversations remain alive across their existing local loops.
- The overworld conversation continues across safe same-map actions and exits at
  semantic boundaries or a genuine loop safeguard.
- Prompt caching remains enabled with stable cache keys and conversation
  prefixes throughout all agent loops.
- Documentation is updated alongside the code it describes.
