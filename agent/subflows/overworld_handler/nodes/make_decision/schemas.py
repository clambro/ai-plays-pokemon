from typing import Self

from pydantic import BaseModel, model_validator

from agent.schemas import NavigationArgs
from common.enums import Tool
from emulator.enums import Button
from memory.raw_memory import RawMemory


class MakeDecisionResponse(BaseModel):
    """The response from the overworld decision maker prompt."""

    thoughts: str
    button: Button | None = None
    navigation_args: NavigationArgs | None = None

    @model_validator(mode="after")
    def _validate_exclusive_fields(self) -> Self:
        if self.button is None and self.navigation_args is None:
            raise ValueError("Either button or navigation_args must be provided.")
        return self


class Decision(BaseModel):
    """The decision from the overworld decision maker prompt."""

    raw_memory: RawMemory
    tool: Tool | None
    navigation_args: NavigationArgs | None
