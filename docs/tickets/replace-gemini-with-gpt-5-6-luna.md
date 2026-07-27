# Ticket: Replace Gemini with GPT-5.6 Luna and Remove All Critics

## Outcome

Remove Gemini completely, make the explicit `gpt-5.6-luna` model the only
generation model, replace Gemini embeddings with OpenAI embeddings, and delete
every global and overworld critique mechanism.

**Depends on:**

- [`01-upgrade-python-3.14.md`](01-upgrade-python-3.14.md)
- [`replace-llm-message-db-with-logfire.md`](replace-llm-message-db-with-logfire.md)

This should land before new map, memory-quality, or prompt work so behavioral
changes can be attributed to the provider transition.

## Generation

- Remove `google-genai`, Gemini model/pricing types, `GEMINI_API_KEY`, Gemini
  safety settings, thinking budgets, and provider-specific retries.
- Add the current OpenAI Python SDK and `OPENAI_API_KEY`.
- Use one `AsyncOpenAI` client boundary and the Responses API.
- Set the model explicitly to `gpt-5.6-luna`; do not use the `gpt-5.6` alias,
  which currently selects Sol.
- Keep calls stateless with `store=False`.
- Send system instructions through `instructions`.
- Preserve ordered text and screenshot content. Encode Pillow screenshots as
  in-memory PNG data URLs and begin with `detail="original"`.
- Use Pydantic Structured Outputs through `responses.parse` for typed calls
  and ordinary Responses text extraction for plain text.
- Set an explicit reasoning effort and bounded output limit for every workload.
  Start simple selection work at `none` and ordinary decisions, map work, and
  memory work at `low`; tune from representative evaluations.
- Do not carry Gemini temperature or token-budget settings across
  mechanically.
- Handle refusals, incomplete/truncated output, missing parsed values,
  validation failures, rate limits, authentication errors, and timeouts as
  explicit outcomes.
- Use one bounded retry policy rather than nesting SDK and Tenacity retries.

Keep the existing prompts substantially intact for the first Luna baseline.
Provider-required edits and removal of critic language are in scope; broad
prompt optimization is not.

## Embeddings

Use `text-embedding-3-small` with 768 float dimensions. Define one stable input
format:

- documents: title, blank line, content;
- queries: query text.

Store provider, model, dimensions, and input-format version with vectors and
reject mismatched embedding identities. V2 starts with a fresh database and
empty long-term memory, so there is no re-embedding or data-import path.

Recalibrate the semantic-similarity threshold for the new embedding model.

## Tokens, Cost, and Logfire

Replace Google Gen AI instrumentation with
`logfire.instrument_openai()` without duplicating spans. Keep the local usage
tracker authoritative for the UI.

Map OpenAI usage carefully:

- cached and cache-write tokens are input subsets;
- reasoning tokens are an output subset;
- total tokens are input plus output, without counting reasoning twice; and
- embedding usage and cost are tracked separately from generation.

As of 2026-07-26, published Luna pricing is $1.00/M input, $0.10/M cached input,
and $6.00/M output. Inputs above 272,000 tokens currently apply 2× input and
1.5× output pricing to the full request; cache writes are 1.25× uncached input.
`text-embedding-3-small` is $0.02/M input. Verify live pricing during
implementation and cover the pricing boundaries in tests.

Replace the Gemini token-counter integration with OpenAI input-token counting.
If the map glyphs tokenize differently, measure the effect and either adjust
the palette or explicitly accept the cost change.

## Remove All Critics

Delete both critique systems completely:

- the global `ShouldCritique` decision and critique node;
- the overworld critique node and tool option;
- their prompts and response schemas;
- critique-related conditions, constants, counters, state, and store methods;
- all graph edges and prompt guidance that expose critique.

Rewire the top-level graph so retrieval and no-retrieval paths proceed directly
to handler selection. Remove critique from the overworld structured tool enum
and graph. Regenerate the workflow documentation and graph visualizations.

There is no critique call using Luna or another model.

## Out of Scope

- GPT-5.6 Sol/Terra, routing, or provider fallbacks.
- OpenAI Agents SDK, hosted tools, or persisted reasoning.
- Explicit prompt-cache management.
- Memory or orchestration redesign.
- Broad prompt rewrites.
- Live billable calls in normal automated tests.

## Validation

Mock the OpenAI boundary for text, Pydantic, image, error, retry, concurrency,
usage, and cost cases. Verify every response schema, embedding identity,
similarity behavior, and the absence of mixed vector spaces. Add graph
structure tests proving that no critique path remains.

Use a small opt-in, cost-capped live smoke test for authentication, text,
structured output, image input, embeddings, and returned usage. Evaluate Luna
on representative gameplay decisions and compare task success, schema
reliability, latency, token use, and cost rather than exact wording.

## Acceptance Criteria

- [ ] `google-genai`, Gemini configuration, imports, models, and API calls are
      gone.
- [ ] Every generation request uses Responses and explicit
      `gpt-5.6-luna`.
- [ ] Luna is the only generation model and every call specifies reasoning
      effort and an output bound.
- [ ] Typed responses use Pydantic Structured Outputs.
- [ ] Screenshots remain in memory and their token use is measured.
- [ ] OpenAI refusals, incomplete responses, errors, and retries are handled
      explicitly.
- [ ] OpenAI embeddings include identity metadata and cannot be mixed.
- [ ] Generation and embedding tokens and costs remain accurate in the UI.
- [ ] Logfire instruments OpenAI without duplicate spans.
- [ ] All global and overworld critic code, state, prompts, tools, and graph
      paths are removed.
- [ ] Normal tests make no billable network calls.

## References

- [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [Latest model guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [Responses API migration](https://developers.openai.com/api/docs/guides/migrate-to-responses)
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Images and vision](https://developers.openai.com/api/docs/guides/images-vision)
- [Token counting](https://developers.openai.com/api/docs/guides/token-counting)
- [Embeddings](https://developers.openai.com/api/docs/guides/embeddings)
- [Logfire OpenAI integration](https://logfire.pydantic.dev/docs/integrations/llms/openai/)
