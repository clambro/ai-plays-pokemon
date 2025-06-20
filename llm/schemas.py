from enum import Enum

from pydantic import BaseModel


class _GeminiModel(BaseModel):
    """Model for the Gemini model."""

    model: str
    cost_1m_input_tokens: float
    cost_1m_output_tokens: float


class GeminiModel(Enum):
    """Enum for the Gemini model names."""

    PRO = _GeminiModel(
        model="gemini-2.5-pro",
        cost_1m_input_tokens=1.25,
        cost_1m_output_tokens=10,
    )
    FLASH = _GeminiModel(
        model="gemini-2.5-flash",
        cost_1m_input_tokens=0.3,
        cost_1m_output_tokens=2.5,
    )
    FLASH_LITE = _GeminiModel(
        model="gemini-2.5-flash-lite-preview-06-17",
        cost_1m_input_tokens=0.1,
        cost_1m_output_tokens=0.4,
    )

    @property
    def model(self) -> str:
        """Get the name of the model."""
        return self.value.model

    @property
    def cost_per_1m_input_tokens(self) -> float:
        """Get the cost per 1M input tokens."""
        return self.value.cost_1m_input_tokens

    @property
    def cost_per_1m_output_tokens(self) -> float:
        """Get the cost per 1M output tokens."""
        return self.value.cost_1m_output_tokens
