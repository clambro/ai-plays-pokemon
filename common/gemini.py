from enum import StrEnum
from typing import TypeVar

from google import genai
from google.genai.types import (
    GenerateContentConfig,
    HarmBlockThreshold,
    HarmCategory,
    SafetySetting,
    ThinkingConfig,
)
from PIL.Image import Image
from pydantic import BaseModel

from common.prompts import SYSTEM_PROMPT
from common.settings import settings
from database.llm_messages.repository import create_llm_message
from database.llm_messages.schemas import LLMMessageCreate

PydanticModel = TypeVar("PydanticModel", bound=BaseModel)

SAFETY_SETTINGS = [
    SafetySetting(category=cat, threshold=HarmBlockThreshold.BLOCK_NONE)
    for cat in HarmCategory
    if cat != HarmCategory.HARM_CATEGORY_UNSPECIFIED  # Can't unblock the unspecified category.
]


class GeminiModel(StrEnum):
    """Enum for the Gemini model names."""

    FLASH = "gemini-2.5-flash-preview-04-17"
    FLASH_LITE = "gemini-2.0-flash-lite"


class Gemini:
    """Wrapper for the Gemini LLM API."""

    def __init__(self, model: GeminiModel) -> None:
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = model

    async def get_llm_response_pydantic(
        self,
        messages: str | list[str | Image],
        schema: type[PydanticModel],
        system_prompt: str = SYSTEM_PROMPT,
        temperature: float = 0.0,
        thinking_tokens: int | None = 256,
    ) -> PydanticModel:
        """
        Get a Pydantic model from the Gemini LLM, parsed from a JSON response.

        :param messages: The messages to send to the Gemini LLM.
        :param schema: The schema to use for the response.
        :param system_prompt: The system prompt to send to the Gemini LLM.
        :param temperature: The temperature to use for the response.
        :param thinking_tokens: The number of tokens to use for the thinking. None is for
            non-thinking models.
        :return: A Pydantic model from the Gemini LLM.
        """
        if isinstance(messages, str):
            messages = [messages]
        thinking_config = (
            ThinkingConfig(thinking_budget=thinking_tokens) if thinking_tokens else None
        )
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=messages,  # type: ignore -- This is a Gemini API issue.
            config=GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=temperature,
                safety_settings=SAFETY_SETTINGS,
                thinking_config=thinking_config,
            ),
        )
        if not response.text or not response.usage_metadata:
            raise ValueError("No response from Gemini.")
        message_str = "\n\n".join("<IMAGE>" if isinstance(m, Image) else m for m in messages)
        await create_llm_message(
            LLMMessageCreate(
                model=self.model,
                prompt=message_str,
                response=response.text,
                prompt_tokens=response.usage_metadata.prompt_token_count or 0,
                thought_tokens=response.usage_metadata.thoughts_token_count or 0,
                response_tokens=response.usage_metadata.candidates_token_count or 0,
            ),
        )
        if not isinstance(response.parsed, schema):
            raise ValueError(f"Failed to parse response from Gemini. Got {response.text}")
        return response.parsed
