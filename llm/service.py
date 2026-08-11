"""OpenAI client integration for LLM requests."""

from typing import TYPE_CHECKING

from genai_prices import calc_price, extract_usage
from openai import AsyncOpenAI

from common.settings import settings
from llm.usage import update_llm_usage

if TYPE_CHECKING:
    from openai.types.responses import (
        Response,
        ResponseUsage,
    )

MODEL = "gpt-5.6-luna"
REASONING_EFFORT = "low"
TIMEOUT_SECONDS = 60
MAX_RETRIES = 2
INPUT_TOKEN_OVERHEAD = 6


class OpenAILLMService:
    """Shared GPT-5.6 Luna client and request boundary."""

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
        system_prompt: str,
    ) -> str:
        """Get an ordinary text response from GPT-5.6 Luna.

        Args:
            prompt: Text to send to the model.
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
            reasoning={"effort": REASONING_EFFORT},
        )
        await self._record_usage(response)
        self._validate_response(response)
        if not response.output_text:
            raise ValueError("OpenAI returned no response text.")
        return response.output_text

    async def count_input_tokens(self, text: str) -> int:
        """Count the GPT-5.6 Luna input tokens for text."""
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
            OpenAILLMService._calculate_cost(response.model, usage),
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

    @staticmethod
    def _calculate_cost(model: str, usage: ResponseUsage) -> float:
        """Calculate the response cost using the shared GenAI pricing database."""
        usage_data = extract_usage(
            {
                "model": model,
                "usage": usage.model_dump(),
            },
            provider_id="openai",
            api_flavor="responses",
        )
        if usage_data.model is None:
            raise ValueError(f"No pricing information for OpenAI model {model}.")
        return float(
            calc_price(
                usage_data.usage,
                model_ref=usage_data.model.id,
                provider_id="openai",
            ).total_price
        )
