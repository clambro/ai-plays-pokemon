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

        The button tool allows you to submit one or more button presses to the
        emulator. It is useful for:

        - Interacting with entities in the game (speaking to NPCs, picking up
          items, reading signs, activating objects, etc.).
        - Opening the main menu.
        - Changing the direction that you are facing.
        - Transitioning from one map to another if you are at the edge of the
          current map or on/near a warp tile.
        - Rotating in place repeatedly in tall grass to find wild Pokemon. If
          you are doing this and failing to find wild Pokemon, you may not be
          standing in a place where wild Pokemon can be found. You should have
          at least two grass tiles adjacent to you to be confident that you are
          in a tall grass area.

        The button tool can be used to move around the map, but it is not as
        reliable as the navigation tool. Do not use the button tool for general
        navigation if the navigation tool is available.

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

        You can interact with warp tiles by walking on or through them,
        depending on the instructions provided for the warp tile.

        You can interact with sprites or signs using the action button, but you
        must be facing the entity you wish to interact with before doing so. If
        the sprite's position is ``(r, c)`` and you are at ``(r, c + 1)``, then
        you must face left to interact with it. If you are at ``(r - 1, c)``,
        then you must face down to interact with it. If you are at
        ``(r, c - 1)``, then you must face right to interact with it. If you are
        at ``(r + 1, c)``, then you must face up to interact with it.

        With nearly all sprites, you must be directly adjacent to them before
        using the action button. The only exceptions are if you are interacting
        with a clerk at a mart, a nurse at a Pokemon Center, or a guard at a
        gate. In these cases, you interact with the counter in front of the
        sprite, meaning that you must be two tiles away from the sprite
        (horizontally or vertically depending on the counter, but not
        diagonally).

        If you have been given instructions to rotate in place repeatedly in
        tall grass to find wild Pokemon, use ``up, left, down, right, up, left,
        down, right``.

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
