# Ticket: Update Luna Pricing and Reassess Cost-Driven Design

## Outcome

Update the application's cost accounting for the July 30, 2026 GPT-5.6 Luna
price reduction, then revisit orchestration decisions that were made primarily
to limit model spend.

Luna now costs $0.20 per million input tokens, $0.02 per million cached input
tokens, and $1.20 per million output tokens. The existing long-context and
cache-write multipliers still apply.

## Pricing Update

Both the direct OpenAI response path and Pydantic AI's `ModelResponse.cost()`
calculate cost through `genai-prices`. OpenAI applies the lower billing rates
automatically, but the application's displayed and persisted cost remains an
estimate from the locally available pricing data.

Wait for `genai-prices` to publish data containing the new date-aware Luna
rates, then update the direct dependency and lockfile. A Pydantic AI release is
not required. Confirm that:

- requests before July 30 retain the old price;
- requests from July 30 onward use the new price;
- uncached input, cache reads, cache writes, output, and long-context pricing
  are represented correctly; and
- the direct OpenAI and Pydantic AI accounting paths produce consistent totals.

Do not rewrite correctly accumulated historical cost. Check whether any calls
made after the price change were persisted using the stale rate and correct
that aggregate only if necessary and recoverable from telemetry.

Keep pricing package-versioned by default. Consider the opt-in
`genai-prices.UpdatePrices` runtime downloader only if automatic future price
updates justify introducing mutable remote pricing data during application
runs.

## Design Review

The same Luna workload now costs one-fifth as much, so raw model spend should
no longer dominate agent orchestration decisions. Reassess the relevant v2
plans, especially:

- whether every player-moving overworld tool still needs to end the agent loop;
- whether longer local agent loops would produce more coherent behavior;
- whether an iteration should represent one agent turn rather than one complete
  end-to-end handler run;
- whether low reasoning effort remains the right quality and latency tradeoff;
  and
- which safeguards exist for semantic turn boundaries and genuinely runaway
  loops rather than merely limiting cost.

Retain prompt caching, bounded context, rolling-memory compression, telemetry,
and visible token and cost totals. Cached input remains ten times cheaper than
uncached input, output remains more expensive than input, and prompts above
272K input tokens still enter the higher pricing tier. These mechanisms remain
useful for performance, comprehension, and operational control even when cost
pressure is much lower.

Revisit rolling-memory granularity alongside the iteration boundary. The
current design finalizes one raw memory block for an entire overworld, battle,
or text-handler activation, even when that run contains many model turns and
tool calls. Consider making each agent turn one iteration so iteration numbers,
raw memory, and the visible activity history correspond to individual model
decisions.

That finer granularity must not cause recent exact context to disappear after
only a handful of decisions. As part of the same change, increase the base
rolling-memory window substantially and size it in agent turns rather than in
complete handler runs. Reassess the compaction threshold, prompt size, cache
behavior, and treatment of deterministic observations that occur between model
turns as one coherent lifecycle change.

Record any resulting decisions in the relevant Pydantic AI migration tickets.
Keep architectural changes in those implementation tickets rather than
expanding this pricing update into a separate orchestration refactor.

## Completion

- `genai-prices` contains the July 30 Luna rates and both accounting paths use
  them.
- The HTML and persisted totals reflect the applicable price for new calls
  without corrupting pre-cut history.
- Stale cost expectations are updated.
- Cost-driven loop, caching, context, and reasoning assumptions have been
  reviewed and the affected implementation tickets reflect the decisions.
- Iteration granularity and the corresponding larger exact rolling-memory
  window have been reviewed together.
