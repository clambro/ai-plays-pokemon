"""OpenAI client integration for LLM requests."""

from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from common.settings import settings
from llm.usage import update_llm_usage

if TYPE_CHECKING:
    from openai.types.responses import Response

    from common.enums import ReasoningEffort

MODEL = "gpt-6-luna"
TIMEOUT_SECONDS = 60
MAX_RETRIES = 2
INPUT_TOKEN_OVERHEAD = 6
LONG_CONTEXT_TOKEN_THRESHOLD = 272_000


def calculate_luna_cost(
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
    cache_write_tokens: int,
) -> float:
    """Estimate GPT-6 Luna request cost from OpenAI's published token rates."""
    # genai-prices does not recognize GPT-6 Luna yet. Use these rates until the library adds it.
    long_context = input_tokens > LONG_CONTEXT_TOKEN_THRESHOLD
    input_multiplier = 2 if long_context else 1
    output_multiplier = 1.5 if long_context else 1
    uncached_tokens = input_tokens - cache_read_tokens - cache_write_tokens
    input_cost = (
        uncached_tokens * 0.10 + cache_read_tokens * 0.01 + cache_write_tokens * 0.125
    ) * input_multiplier
    output_cost = output_tokens * 0.50 * output_multiplier
    return (input_cost + output_cost) / 1_000_000


class OpenAILLMService:
    """Shared GPT-6 Luna client and request boundary."""

    def __init__(self) -> None:
        """Initialize the OpenAI client."""
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=TIMEOUT_SECONDS,
            max_retries=MAX_RETRIES,
        )

    async def get_llm_response(
        self,
        prompt: str,
        *,
        reasoning_effort: ReasoningEffort,
        system_prompt: str,
    ) -> str:
        """Get an ordinary text response from GPT-6 Luna.

        Args:
            prompt: Text to send to the model.
            reasoning_effort: Reasoning effort for this request.
            system_prompt: Instruction supplied to the model.

        Returns:
            The model's response text.

        Raises:
            ValueError: OpenAI returns an unsuccessful response or no response text.
        """
        response = await self.client.responses.create(
            model=MODEL,
            input=prompt,
            instructions=system_prompt,
            reasoning={"effort": reasoning_effort.value},
        )
        await self._record_usage(response)
        self._validate_response(response)
        if not response.output_text:
            raise ValueError("OpenAI returned no response text.")
        return response.output_text

    async def count_input_tokens(self, text: str) -> int:
        """Count the GPT-6 Luna input tokens for text."""
        response = await self.client.responses.input_tokens.count(model=MODEL, input=text)
        # The endpoint includes fixed Responses API message framing in addition to
        # the supplied text. Remove it so this method reports only the text tokens.
        return response.input_tokens - INPUT_TOKEN_OVERHEAD

    @staticmethod
    async def _record_usage(response: Response) -> None:
        """Add one OpenAI response's tokens and cost to the active run."""
        usage = response.usage
        if usage is None:
            raise ValueError("OpenAI returned no usage information.")
        await update_llm_usage(
            usage.total_tokens,
            calculate_luna_cost(
                usage.input_tokens,
                usage.output_tokens,
                usage.input_tokens_details.cached_tokens,
                usage.input_tokens_details.cache_write_tokens,
            ),
        )

    @staticmethod
    def _validate_response(response: Response) -> None:
        """Raise a clear error for unsuccessful terminal responses."""
        for output in response.output:
            if output.type == "message":
                for content in output.content:
                    if content.type == "refusal":
                        raise ValueError(f"OpenAI refused the request: {content.refusal}")

        if response.status == "completed":
            return
        if response.error is not None:
            raise ValueError(f"OpenAI response failed: {response.error.message}")
        if response.incomplete_details is not None:
            raise ValueError(f"OpenAI response incomplete: {response.incomplete_details.reason}")
        raise ValueError(f"OpenAI response ended with status {response.status}.")
