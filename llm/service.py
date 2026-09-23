"""OpenAI client integration for LLM requests."""

from functools import cache
from typing import TYPE_CHECKING

from genai_prices import extract_usage
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from common.settings import settings
from llm.usage import update_llm_usage

if TYPE_CHECKING:
    from openai.types.responses import Response

    from common.enums import ReasoningEffort

_MODEL = "gpt-6-luna"
TIMEOUT_SECONDS = 60
MAX_RETRIES = 2
INPUT_TOKEN_OVERHEAD = 6


@cache
def build_agent_model(*, max_retries: int = MAX_RETRIES) -> OpenAIResponsesModel:
    """Build a shared agent model with an explicit OpenAI retry policy."""
    return OpenAIResponsesModel(
        _MODEL,
        provider=OpenAIProvider(
            openai_client=AsyncOpenAI(api_key=settings.openai_api_key, max_retries=max_retries)
        ),
    )


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
            model=_MODEL,
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
        response = await self.client.responses.input_tokens.count(model=_MODEL, input=text)
        # The endpoint includes fixed Responses API message framing in addition to
        # the supplied text. Remove it so this method reports only the text tokens.
        return response.input_tokens - INPUT_TOKEN_OVERHEAD

    @staticmethod
    async def _record_usage(response: Response) -> None:
        """Add one OpenAI response's tokens and cost to the active run."""
        usage = response.usage
        if usage is None:
            raise ValueError("OpenAI returned no usage information.")
        extracted_usage = extract_usage(
            {"model": response.model, "usage": usage.model_dump()},
            provider_id="openai",
            api_flavor="responses",
        )
        await update_llm_usage(
            usage.total_tokens,
            float(extracted_usage.calc_price().total_price),
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
