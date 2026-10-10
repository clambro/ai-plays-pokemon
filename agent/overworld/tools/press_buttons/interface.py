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
        rotate in place. Use navigation for ordinary movement and the other
        dedicated tools for actions they support.

        Directional buttons behave differently depending on the direction you
        are currently facing. Pressing a different direction rotates you to
        face that direction without moving. Pressing the direction you are
        already facing attempts to move you one tile.

        The available buttons are:

        - ``a``: Interact with what you are facing.
        - ``b``: Normally has no effect while standing in the overworld.
        - ``start``: Open the main menu.
        - ``up``: Turn up, or attempt to move up when already facing up.
        - ``down``: Turn down, or attempt to move down when already facing down.
        - ``left``: Turn left, or attempt to move left when already facing left.
        - ``right``: Turn right, or attempt to move right when already facing
          right.

        Follow the map's instructions for each warp tile: walk on or through
        the warp rather than pressing the action button.

        Use the action button while facing the entity you want to interact
        with. Normally, stand on an adjacent tile. If the map note gives an
        exact interaction position, such as for a sprite across a counter,
        stand there instead and face the entity.

        Combine known inputs, such as turning toward an entity and pressing
        ``a``, in one call. Stop to observe when the next input depends on the
        result. Execution stops early after an interaction, collision, map
        transition, or departure from overworld control; remaining buttons
        are not carried over.

        Args:
            buttons: Buttons to press in order, accounting for the current
                facing direction.

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
