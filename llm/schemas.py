from enum import StrEnum


class GeminiLLMEnum(StrEnum):
    """Enum for the Gemini model names."""

    PRO = "gemini-2.5-pro"
    FLASH = "gemini-2.5-flash"
    FLASH_LITE = "gemini-2.5-flash-lite-preview-06-17"
