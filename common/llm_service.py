import asyncio
from enum import StrEnum
from typing import TypeVar

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

PydanticModel = TypeVar("PydanticModel", bound=BaseModel)

TIMEOUT = 60
SAFETY_SETTINGS = [
    SafetySetting(category=cat, threshold=HarmBlockThreshold.BLOCK_NONE)
    for cat in HarmCategory
    if cat != HarmCategory.HARM_CATEGORY_UNSPECIFIED  # Can't unblock the unspecified category.
]


class GeminiLLMEnum(StrEnum):
    """Enum for the Gemini model names."""

    PRO = "gemini-2.5-pro-preview-06-05"
    FLASH = "gemini-2.5-flash-preview-04-17"
    FLASH_LITE = "gemini-2.0-flash-lite-001"


class GeminiLLMService:
    """Wrapper for the Gemini LLM API."""

    def __init__(self, model: GeminiLLMEnum) -> None:
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = model

    async def get_llm_response(
        self,
        messages: str | list[str | Image],
        prompt_name: str,
        system_prompt: str = SYSTEM_PROMPT,
        temperature: float = 0.0,
        thinking_tokens: int | None = 256,
    ) -> str:
        """
        Get a response from the Gemini LLM as a string.

        :param messages: The messages to send to the Gemini LLM.
        :param prompt_name: The name of the prompt to use as a label in the database.
        :param system_prompt: The system prompt to send to the Gemini LLM.
        :param temperature: The temperature to use for the response.
        :param thinking_tokens: The number of tokens to use for the thinking. None is for
            non-thinking models.
        :return: A string from the Gemini LLM.
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

    async def get_llm_response_pydantic(  # noqa: PLR0913
        self,
        messages: str | list[str | Image],
        schema: type[PydanticModel],
        prompt_name: str,
        system_prompt: str = SYSTEM_PROMPT,
        temperature: float = 0.0,
        thinking_tokens: int | None = 256,
    ) -> PydanticModel:
        """
        Get a Pydantic model from the Gemini LLM, parsed from a JSON response.

        :param messages: The messages to send to the Gemini LLM.
        :param schema: The schema to use for the response.
        :param prompt_name: The name of the prompt to use as a label in the database.
        :param system_prompt: The system prompt to send to the Gemini LLM.
        :param temperature: The temperature to use for the response.
        :param thinking_tokens: The number of tokens to use for the thinking. None is for
            non-thinking models.
        :return: A Pydantic model from the Gemini LLM.
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
        messages: str | list[str | Image],
        schema: type[PydanticModel] | None,
        prompt_name: str,
        system_prompt: str,
        temperature: float,
        thinking_tokens: int | None,
    ) -> GenerateContentResponse:
        """
        Get a response from the Gemini LLM.

        :param messages: The messages to send to the Gemini LLM.
        :param schema: The schema to use for the response.
        :param prompt_name: The name of the prompt to use as a label in the database.
        :param system_prompt: The system prompt to send to the Gemini LLM.
        :param temperature: The temperature to use for the response.
        :param thinking_tokens: The number of tokens to use for the thinking. None is for
            non-thinking models.
        :return: A response from the Gemini LLM.
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
                model=self.model,
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
