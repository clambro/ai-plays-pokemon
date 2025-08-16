from pydantic import BaseModel


class GeminiModel(BaseModel):
    """Model for the Gemini model."""

    model_id: str
    cost_1m_input_tokens: float
    cost_1m_output_tokens: float


GEMINI_PRO_2_5 = GeminiModel(
    model_id="gemini-2.5-pro",
    cost_1m_input_tokens=1.25,
    cost_1m_output_tokens=10,
)
GEMINI_FLASH_2_5 = GeminiModel(
    model_id="gemini-2.5-flash",
    cost_1m_input_tokens=0.3,
    cost_1m_output_tokens=2.5,
)
GEMINI_FLASH_LITE_2_5 = GeminiModel(
    model_id="gemini-2.5-flash-lite",
    cost_1m_input_tokens=0.1,
    cost_1m_output_tokens=0.4,
)
