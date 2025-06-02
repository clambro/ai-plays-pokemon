from pydantic import BaseModel, ConfigDict


class LLMMessageCreate(BaseModel):
    """Create model for an LLM message."""

    model: str
    prompt_name: str
    prompt: str
    response: str
    prompt_tokens: int
    thought_tokens: int
    response_tokens: int

    model_config = ConfigDict(from_attributes=True)
