# Ticket: Replace the LLM Message Table with Logfire

## Outcome

Remove per-call LLM telemetry from SQLite. Send detailed traces to Logfire and
keep a small local usage accumulator as the authoritative source for token and
cost totals displayed by the application.

**Depends on:** [`01-upgrade-python-3.14.md`](01-upgrade-python-3.14.md)  
**Precedes:** [`replace-gemini-with-gpt-5-6-luna.md`](replace-gemini-with-gpt-5-6-luna.md)

## Motivation

Every successful LLM call currently inserts the complete prompt, response,
usage, and cost into `llm_message`. Stream refreshes then aggregate that growing
table to display cost, and backups copy the full history. Detailed traces are
observability data, not gameplay state.

## Scope

- Delete the `llm_message` model, schemas, repository, registration, writes,
  reads, and tests.
- Stop querying SQLite from the stream for LLM totals.
- Replace the Junjo Server telemetry exporter with Logfire while leaving Junjo
  orchestration in place.
- Instrument the current provider once and attach an application span for each
  logical `prompt_name`.
- Keep telemetry opt-in and allow the application to work normally without a
  Logfire token or connection.
- Add an application-owned, concurrency-safe in-memory usage tracker.
- Store a serializable usage snapshot in v2 agent state so active-run totals
  survive v2 backup and restore.
- Display request count, total tokens, useful token categories, and total cost
  in the stream.
- Initialize fresh v2 usage totals at zero; do not import rows from the removed
  table.

## Design Decisions

### Local accounting is authoritative

Logfire retention, sampling, or availability must not affect the UI. Record a
usage delta locally exactly once for each provider attempt that returns usage,
including responses that later fail application-level schema validation.

Use provider-neutral categories so the Luna migration does not redesign the
tracker:

- input tokens;
- cached and cache-write input subsets when available;
- output tokens;
- reasoning/thought tokens as a documented output subset;
- request and failed-attempt counts;
- total tokens without double-counting subsets; and
- cost calculated from the pricing snapshot active for that call.

The tracker must apply concurrent updates atomically and perform no filesystem,
database, or network I/O.

### Logfire owns detailed traces

Capture:

- prompt name and provider model;
- duration and outcome;
- retry/attempt relationship;
- provider usage;
- calculated cost; and
- errors, refusals, and validation failures.

Configure one global OpenTelemetry provider. Do not retain the Junjo Server
exporter beside Logfire or generate duplicate provider spans.

Prompt and response content must be an explicit policy. Default to safe
scrubbing and do not export screenshots accidentally. API keys must never
appear in attributes or content.

The initial implementation may use Logfire's Google Gen AI instrumentation.
The Luna ticket replaces that provider-specific hook with OpenAI
instrumentation while retaining the same logical spans and local tracker.

### V2 state and stream

Keep the cumulative snapshot small and model-neutral. Synchronize it into
agent state before a v2 backup and initialize the tracker from it when resuming
that v2 run.

The stream receives the already-calculated snapshot. It must not query Logfire,
recalculate totals in JavaScript, or open a database session.

## Out of Scope

- Removing SQLite from map or memory persistence.
- Removing Junjo as the workflow engine.
- Changing model providers or pricing policy.
- Using Logfire as game-state storage.
- Backfilling removed SQLite telemetry.
- Querying Logfire from the application hot path.

## Validation

Cover:

- token subset and total calculations;
- price calculation and accumulation;
- concurrent updates and retries without double counting;
- successful, failed, refused, and schema-invalid call outcomes;
- v2 backup/restore of the local snapshot;
- operation with telemetry disabled or unavailable;
- Logfire span hierarchy and content-scrubbing policy; and
- absence of `llm_message` and database access from LLM/stream paths.

Tests must use mocked providers and an in-memory Logfire exporter.

## Acceptance Criteria

- [ ] Fresh databases do not create `llm_message`.
- [ ] LLM calls and stream refreshes perform no telemetry-related SQLite I/O.
- [ ] Local token categories, totals, request counts, and costs are accurate.
- [ ] Usage totals remain available when Logfire is disabled or unavailable.
- [ ] V2 backup/restore preserves the active run's usage snapshot.
- [ ] The stream displays tokens and cost from local state.
- [ ] Logfire records one filterable logical span per `prompt_name`, with
      provider attempts and errors correlated correctly.
- [ ] Prompt/response capture is explicit, scrubbed, and safe for screenshots.
- [ ] Junjo Server telemetry configuration is removed.

## References

- [Logfire LLM integrations](https://logfire.pydantic.dev/docs/integrations/llms/)
- [Logfire configuration](https://logfire.pydantic.dev/docs/reference/configuration/)
- [Manual tracing](https://logfire.pydantic.dev/docs/guides/onboarding-checklist/add-manual-tracing/)
- [Sensitive-data scrubbing](https://logfire.pydantic.dev/docs/how-to-guides/scrubbing/)
- [Testing Logfire](https://logfire.pydantic.dev/docs/reference/api/testing/)

