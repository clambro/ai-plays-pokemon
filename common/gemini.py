from enum import StrEnum
from typing import TypeVar
from google import genai
from google.genai.types import (
    GenerateContentConfig,
    HarmBlockThreshold,
    SafetySetting,
    HarmCategory,
    ThinkingConfig,
)
from pydantic import BaseModel
from common.prompts import SYSTEM_PROMPT
from common.settings import settings
from PIL.Image import Image

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
    ) -> PydanticModel:
        """
        Get a Pydantic model from the Gemini LLM, parsed from a JSON response.

        :param messages: The messages to send to the Gemini LLM.
        :param schema: The schema to use for the response.
        :param system_prompt: The system prompt to send to the Gemini LLM.
        :param temperature: The temperature to use for the response.
        :return: A Pydantic model from the Gemini LLM.
        """
        if isinstance(messages, str):
            messages = [messages]
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=messages,  # type: ignore -- This is a Gemini API issue.
            config=GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=temperature,
                safety_settings=SAFETY_SETTINGS,
                thinking_config=ThinkingConfig(thinking_budget=0),
            ),
        )
        if not isinstance(response.parsed, schema):
            raise ValueError("Failed to parse response from Gemini")
        return response.parsed
