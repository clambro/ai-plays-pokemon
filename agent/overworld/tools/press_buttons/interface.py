"""Pydantic AI interface for overworld button input."""

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field
from pydantic_ai import Tool

from agent.overworld.tools.press_buttons.service import (
    press_buttons as press_buttons_service,
)
from agent.overworld.tools.utils import (
    OverworldToolResult,
    complete_overworld_action,
)
from common.enums import Button

if TYPE_CHECKING:
    from agent.context import AgentContext

type OverworldButton = Literal[
    Button.A,
    Button.B,
    Button.START,
    Button.UP,
    Button.DOWN,
    Button.LEFT,
    Button.RIGHT,
]


def build_press_buttons_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the button-input tool bound to the current overworld context."""

    async def press_buttons(
        buttons: Annotated[list[OverworldButton], Field(min_length=1)],
    ) -> OverworldToolResult:
        """Press one or more buttons directly in the overworld.

        Use this tool to interact with entities, change direction, open the
        main menu, cross a map boundary or directional warp, or deliberately
        rotate in place. Do not use it for general movement when the navigation
        tool is available.

        The available buttons are:

        - ``a``: The action button. Used to interact with objects in the game.
          Make sure you are facing the direction of the object that you wish to
          interact with before pressing the action button.
        - ``b``: Does nothing in the overworld. You shouldn't need to press
          this button.
        - ``start``: Used to open the main menu. You shouldn't need to do this,
          but it is included for completeness.
        - ``up``: Used to move the player upwards.
        - ``down``: Used to move the player downwards.
        - ``left``: Used to move the player left.
        - ``right``: Used to move the player right.

        Follow the map's instructions for each warp tile: walk on or through
        the warp rather than pressing the action button.

        You can interact with sprites or signs using the action button, but you
        must be facing the entity you wish to interact with before doing so. If
        the sprite's position is ``(r, c)`` and you are at ``(r, c + 1)``, then
        you must face left to interact with it. If you are at ``(r - 1, c)``,
        then you must face down to interact with it. If you are at
        ``(r, c - 1)``, then you must face right to interact with it. If you are
        at ``(r + 1, c)``, then you must face up to interact with it.

        To rotate in place repeatedly in tall grass, use ``up, left, down,
        right, up, left, down, right``. If this fails to find wild Pokemon, you
        may not be standing in an encounter area; having at least two adjacent
        grass tiles is a useful indication.

        If you see specific button presses in your rolling memory, do not treat
        them as mandatory. You have more information available to you in the
        current prompt than you did when the memory was generated, so you are
        allowed to overrule it if the request does not make sense (e.g. if it
        is asking you to face right to interact with a sprite that is to your
        left). Determine what the memory is trying to tell you and choose the
        best button(s) from the list of available buttons.

        You should generally prefer to press a single button at a time, but you
        can use a combination of buttons to, say, rotate the player and then
        interact with an object.

        Args:
            buttons: Buttons to press in order.

        Returns:
            Fresh screenshot and the actual button-sequence result.
        """
        result = await press_buttons_service(
            rolling_memory=context.state.rolling_memory,
            emulator=context.emulator,
            buttons=list(buttons),
        )
        return await complete_overworld_action(context, result)

    return Tool(press_buttons, require_parameter_descriptions=True)
