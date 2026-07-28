"""OpenAI client integration for LLM requests."""

import base64
from io import BytesIO
from typing import TYPE_CHECKING

from genai_prices import calc_price, extract_usage
from openai import AsyncOpenAI
from openai.lib._parsing._responses import type_to_text_format_param
from pydantic import BaseModel

from common.prompts import SYSTEM_PROMPT
from common.settings import settings
from llm.usage import update_llm_usage

if TYPE_CHECKING:
    from openai.types.responses import (
        Response,
        ResponseInputContentParam,
        ResponseInputParam,
        ResponseUsage,
    )
    from PIL.Image import Image

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
        messages: str | list[str | Image],
        system_prompt: str = SYSTEM_PROMPT,
    ) -> str:
        """Get an ordinary text response from GPT-5.6 Luna.

        Args:
            messages: Text and images to send to the model.
            system_prompt: Instruction supplied to the model.

        Returns:
            The model's response text.

        Raises:
            ValueError: OpenAI returns an unsuccessful response or no response text.
        """
        response = await self.client.responses.create(
            model=MODEL,
            input=self._build_input(messages),
            instructions=system_prompt,
            reasoning={"effort": REASONING_EFFORT},
        )
        await self._record_usage(response)
        self._validate_response(response)
        if not response.output_text:
            raise ValueError("OpenAI returned no response text.")
        return response.output_text

    async def get_llm_response_pydantic[ResponseModel: BaseModel](
        self,
        messages: str | list[str | Image],
        schema: type[ResponseModel],
        *,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> ResponseModel:
        """Get a Pydantic model parsed from a GPT-5.6 Luna response.

        Args:
            messages: Text and images to send to the model.
            schema: Pydantic model describing the required response.
            system_prompt: Instruction supplied to the model.

        Returns:
            The validated structured response.

        Raises:
            ValueError: OpenAI returns an unsuccessful or invalid structured response.
        """
        response = await self.client.responses.create(
            model=MODEL,
            input=self._build_input(messages),
            instructions=system_prompt,
            reasoning={"effort": REASONING_EFFORT},
            text={"format": type_to_text_format_param(schema)},
        )
        await self._record_usage(response)
        self._validate_response(response)
        if not response.output_text:
            raise ValueError("OpenAI returned no valid structured response.")
        return schema.model_validate_json(response.output_text)

    async def count_input_tokens(self, text: str) -> int:
        """Count the GPT-5.6 Luna input tokens for text."""
        response = await self.client.responses.input_tokens.count(model=MODEL, input=text)
        # The endpoint includes fixed Responses API message framing in addition to
        # the supplied text. Remove it so this method reports only the text tokens.
        return response.input_tokens - INPUT_TOKEN_OVERHEAD

    @staticmethod
    def _build_input(messages: str | list[str | Image]) -> str | ResponseInputParam:
        """Convert text and Pillow images into Responses API input."""
        if isinstance(messages, str):
            return messages

        content: list[ResponseInputContentParam] = []
        for message in messages:
            if isinstance(message, str):
                content.append({"type": "input_text", "text": message})
            else:
                content.append(
                    {
                        "type": "input_image",
                        "image_url": OpenAILLMService._image_data_url(message),
                        "detail": "original",
                    }
                )
        input_messages: ResponseInputParam = [{"role": "user", "content": content}]
        return input_messages

    @staticmethod
    def _image_data_url(image: Image) -> str:
        """Convert a Pillow image to an in-memory PNG data URL."""
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        encoded_image = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{encoded_image}"

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
