"""Pydantic AI interface for PC Pokemon selection."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.text.tools.errors import TextActionUnavailableError
from agent.text.tools.select_pc_pokemon.service import (
    select_pc_pokemon as select_pc_pokemon_service,
)
from agent.text.utils import TextToolResult, complete_text_action

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_select_pc_pokemon_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the PC selection tool bound to the current text context."""

    async def select_pc_pokemon(pokemon_index: Annotated[int, Field(ge=0)]) -> TextToolResult:
        """Select a Pokemon from the open PC list in one action.

        Use the index in the current party when depositing, or the active PC box
        when withdrawing. This navigates the scrolling list and presses A once;
        choose the next action separately from the resulting menu.

        Args:
            pokemon_index: Zero-based Pokemon index in the current party or active PC box.

        Returns:
            Fresh text context after selecting the Pokemon.
        """
        previous_game_state = await context.emulator.get_game_state()
        try:
            result = await select_pc_pokemon_service(
                emulator=context.emulator,
                pokemon_index=pokemon_index,
            )
        except TextActionUnavailableError as error:
            result = str(error)
        return await complete_text_action(context, result, previous_game_state=previous_game_state)

    return Tool(select_pc_pokemon, require_parameter_descriptions=True)
