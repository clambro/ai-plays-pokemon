"""Gemini client integration for structured LLM requests."""

import asyncio
from typing import TYPE_CHECKING

from google import genai
from google.genai.errors import ServerError
from google.genai.types import (
    GenerateContentConfig,
    GenerateContentResponse,
    HarmBlockThreshold,
    HarmCategory,
    SafetySetting,
    ThinkingConfig,
)
from PIL.Image import Image
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from common.prompts import SYSTEM_PROMPT
from common.settings import settings
from database.llm_messages.repository import create_llm_message
from database.llm_messages.schemas import LLMMessageCreate

if TYPE_CHECKING:
    from llm.schemas import GeminiModel

TIMEOUT = 60
SAFETY_SETTINGS = [
    SafetySetting(category=category, threshold=HarmBlockThreshold.BLOCK_NONE)
    for category in (
        HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        HarmCategory.HARM_CATEGORY_HARASSMENT,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
    )
]
MIN_THINKING_TOKENS = 512  # This is the minimum allowed for the 2.5 models.
DEFAULT_TEMPERATURE = 1  # This noise is necessary for creativity and not getting stuck in loops.


class GeminiLLMService:
    """Wrapper for the Gemini LLM API."""

    def __init__(self, model: GeminiModel) -> None:
        """Initialize the Gemini LLM service."""
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = model

    async def get_llm_response(
        self,
        messages: str | list[str | Image],
        prompt_name: str,
        system_prompt: str = SYSTEM_PROMPT,
        temperature: float = DEFAULT_TEMPERATURE,
        thinking_tokens: int = MIN_THINKING_TOKENS,
    ) -> str:
        """Get a text response from the Gemini model.

        Args:
            messages: Text and images to send to the model.
            prompt_name: Stable label recorded with the request telemetry.
            system_prompt: Instruction supplied as the model's system prompt.
            temperature: Sampling temperature for the response.
            thinking_tokens: Maximum tokens allocated to model reasoning.

        Returns:
            The model's response text.

        Raises:
            ValueError: Gemini returns no response text.
            ServerError: Gemini still fails after the configured retries.
        """
        response = await self._get_llm_response(
            messages=messages,
            schema=None,
            prompt_name=prompt_name,
            system_prompt=system_prompt,
            temperature=temperature,
            thinking_tokens=thinking_tokens,
        )
        if not response.text:
            raise ValueError("No response from Gemini.")
        return response.text

    async def get_llm_response_pydantic[ResponseModel: BaseModel](  # noqa: PLR0913
        self,
        messages: str | list[str | Image],
        schema: type[ResponseModel],
        prompt_name: str,
        *,
        system_prompt: str = SYSTEM_PROMPT,
        temperature: float = DEFAULT_TEMPERATURE,
        thinking_tokens: int = MIN_THINKING_TOKENS,
    ) -> ResponseModel:
        """Get a Pydantic model parsed from a structured Gemini response.

        Args:
            messages: Text and images to send to the model.
            schema: Pydantic model describing the required response.
            prompt_name: Stable label recorded with the request telemetry.
            system_prompt: Instruction supplied as the model's system prompt.
            temperature: Sampling temperature for the response.
            thinking_tokens: Maximum tokens allocated to model reasoning.

        Returns:
            The validated structured response.

        Raises:
            ValueError: Gemini returns no valid structured response.
            ServerError: Gemini still fails after the configured retries.
        """
        response = await self._get_llm_response(
            messages=messages,
            schema=schema,
            prompt_name=prompt_name,
            system_prompt=system_prompt,
            temperature=temperature,
            thinking_tokens=thinking_tokens,
        )
        return schema.model_validate(response.parsed)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception_type(ServerError),  # The experimental models are unstable.
        reraise=True,
    )
    async def _get_llm_response(  # noqa: PLR0913
        self,
        *,
        messages: str | list[str | Image],
        schema: type[BaseModel] | None,
        prompt_name: str,
        system_prompt: str,
        temperature: float,
        thinking_tokens: int | None,
    ) -> GenerateContentResponse:
        """Send a request to Gemini and persist its response telemetry.

        Args:
            messages: Text and images to send to the model.
            schema: Optional Pydantic model describing a structured response.
            prompt_name: Stable label recorded with the request telemetry.
            system_prompt: Instruction supplied as the model's system prompt.
            temperature: Sampling temperature for the response.
            thinking_tokens: Maximum reasoning tokens, or ``None`` for a non-thinking model.

        Returns:
            Gemini's complete generated-content response.

        Raises:
            ValueError: Gemini omits response data or fails to produce the requested schema.
            ServerError: Gemini still fails after the configured retries.
        """
        if isinstance(messages, str):
            messages = [messages]
        thinking_config = (
            ThinkingConfig(thinking_budget=thinking_tokens) if thinking_tokens is not None else None
        )
        content_config = GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            safety_settings=SAFETY_SETTINGS,
            thinking_config=thinking_config,
        )
        if schema:
            content_config.response_mime_type = "application/json"
            content_config.response_schema = schema
        response = await asyncio.wait_for(
            self.client.aio.models.generate_content(
                model=self.model.model_id,
                contents=messages,  # type: ignore -- This is a Gemini API issue.
                config=content_config,
            ),
            timeout=TIMEOUT,
        )
        if not response.text or not response.usage_metadata:
            raise ValueError("No response from Gemini.")
        message_str = "\n\n".join("<IMAGE>" if isinstance(m, Image) else m for m in messages)
        await create_llm_message(
            LLMMessageCreate(
                model=self.model,
                prompt_name=prompt_name,
                prompt=message_str,
                response=response.text,
                prompt_tokens=response.usage_metadata.prompt_token_count or 0,
                thought_tokens=response.usage_metadata.thoughts_token_count or 0,
                response_tokens=response.usage_metadata.candidates_token_count or 0,
            ),
        )
        if schema and not isinstance(response.parsed, schema):
            raise ValueError(f"Failed to parse response from Gemini. Got {response.text}")
        return response
