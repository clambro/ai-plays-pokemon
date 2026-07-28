# Ticket: Replace Gemini with GPT-5.6 Luna and Remove All Critics

## Outcome

Remove Gemini completely, make the explicit `gpt-5.6-luna` model the only
generation model, and delete every global and overworld critique mechanism.

**Depends on:**

- [`simplify-long-term-memory.md`](simplify-long-term-memory.md)

The long-term-memory work removes embeddings first, so this ticket only needs
to migrate generation.

## Generation

- Replace `google-genai` with the current OpenAI Python SDK and replace
  `GEMINI_API_KEY` with `OPENAI_API_KEY`.
- Use one `AsyncOpenAI` client boundary and the Responses API.
- Always request `gpt-5.6-luna` explicitly. Do not use the `gpt-5.6` alias.
- Keep calls stateless with `store=False`.
- Preserve the existing order of text and screenshots. Convert Pillow images
  to in-memory PNG data URLs and initially use original image detail.
- Send the shared system prompt through `instructions`.
- Use Pydantic Structured Outputs for typed responses and ordinary response
  text for plain-text calls.
- Give every workload an explicit reasoning effort and output limit. Start
  simple selections at `none` and ordinary gameplay and memory work at `low`,
  then tune from representative runs.
- Use one bounded retry policy and handle provider errors, refusals,
  incomplete output, and missing or invalid structured responses clearly.

Keep the existing prompts substantially intact for the first Luna baseline.
Only make provider-required changes and remove critic-specific guidance.

## Tokens, Cost, and Logfire

Replace Google Gen AI instrumentation with OpenAI instrumentation without
creating duplicate spans. Keep the existing local usage tracker authoritative
for the HTML display.

Map OpenAI response usage into the current per-run totals. Cached input tokens
are part of input, reasoning tokens are part of output, and neither should be
counted twice. Calculate cost from uncached input, cached input, cache writes,
and output using the pricing verified during implementation.

Replace or remove the Gemini token-counting integration. Measure how Luna
tokenizes the ASCII map glyphs before deciding whether the palette needs to
change; normal automated tests must not make billable calls.

## Remove All Critics

Delete both critique systems:

- the root `ShouldCritique` decision and critique node;
- the overworld critique node and tool option;
- their prompts and response schemas;
- critique counters, state, conditions, constants, and store methods; and
- graph edges and shared prompt guidance that expose the critics.

Rewire both graphs so their remaining paths proceed directly. Luna must not be
used to recreate either critic.

## Project Updates

Update dependencies, settings, `.env.example`, the README, workflow
documentation, and graph visualizations so the repository no longer instructs
users to configure or expect Gemini or critics.

Mock the OpenAI boundary in normal tests. Cover plain text, structured output,
image input, usage accounting, pricing boundaries, retryable failures, and
terminal response failures without making live calls.

## Completion

- `google-genai`, Gemini settings, models, imports, API calls, and telemetry
  instrumentation are gone.
- Every generation request uses Responses with explicit `gpt-5.6-luna`,
  reasoning effort, and an output limit.
- Screenshots remain in memory and structured responses remain Pydantic
  validated.
- Token and cost totals remain accurate in the HTML display.
- No critic code, state, prompt content, tool, or graph path remains.
- Normal tests make no billable network calls.

## References

- [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [Model guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [Responses API migration](https://developers.openai.com/api/docs/guides/migrate-to-responses)
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Images and vision](https://developers.openai.com/api/docs/guides/images-vision)
- [Logfire OpenAI integration](https://logfire.pydantic.dev/docs/integrations/llms/openai/)
