"""Pydantic AI interface for assigning an in-game name."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.subflows.text_handler.tools.assign_name.service import (
    assign_name as assign_name_service,
)
from agent.subflows.text_handler.tools.errors import TextActionUnavailableError
from agent.subflows.text_handler.utils import TextToolResult, complete_text_action

if TYPE_CHECKING:
    from agent.subflows.text_handler.context import TextContext


def build_assign_name_tool(context: TextContext) -> Tool[TextContext]:
    """Build the naming tool bound to the current text context."""

    async def assign_name(
        name: Annotated[str, Field(pattern=r"^[A-Z ]{1,10}$")],
    ) -> TextToolResult:
        """Choose and enter a name while the naming screen is open.

        This tool works only on the naming screen (i.e. the screen displaying
        the full alphabet). Use it when the game is asking for the player's
        name, the rival's name, or a Pokemon nickname. The recent memory and
        player information indicate which subject is being named.

        Names must:

        - contain only uppercase letters and spaces;
        - contain at least one character;
        - not begin or end with a space; and
        - be creative, unique, and different from default names.

        The player and rival names are 7 characters max. Pokemon nicknames are
        10 characters max.

        Args:
            name: Name to enter exactly as written.

        Returns:
            Fresh text context after attempting to enter the name.
        """
        try:
            result = await assign_name_service(
                emulator=context.emulator,
                name=name,
            )
        except TextActionUnavailableError as error:
            return await complete_text_action(context, str(error))
        return await complete_text_action(context, result)

    return Tool(assign_name, require_parameter_descriptions=True)
