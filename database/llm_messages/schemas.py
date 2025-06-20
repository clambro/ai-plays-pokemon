from pydantic import BaseModel, ConfigDict

from llm.schemas import GeminiModel


class LLMMessageCreate(BaseModel):
    """Create model for an LLM message."""

    model: GeminiModel
    prompt_name: str
    prompt: str
    response: str
    prompt_tokens: int
    thought_tokens: int
    response_tokens: int

    model_config = ConfigDict(from_attributes=True)

    @property
    def cost(self) -> float:
        """Get the cost of the message. Thought tokens are counted as output tokens."""
        return (
            self.prompt_tokens * self.model.cost_per_1m_input_tokens
            + (self.thought_tokens + self.response_tokens) * self.model.cost_per_1m_output_tokens
        )
