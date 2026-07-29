"""Pydantic AI interface for battle button input."""

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field
from pydantic_ai import Tool

from agent.subflows.battle_handler.tools.press_buttons.service import (
    press_buttons as press_buttons_service,
)
from agent.subflows.battle_handler.utils import BattleToolResult, complete_battle_action
from common.enums import Button

if TYPE_CHECKING:
    from agent.subflows.battle_handler.context import BattleContext

type BattleButton = Literal[
    Button.A,
    Button.B,
    Button.UP,
    Button.DOWN,
    Button.LEFT,
    Button.RIGHT,
]


def build_press_buttons_tool(context: BattleContext) -> Tool[BattleContext]:
    """Build the button-input tool bound to the current battle context."""

    async def press_buttons(
        buttons: Annotated[list[BattleButton], Field(min_length=1)],
    ) -> BattleToolResult:
        """Press buttons to navigate a battle screen directly.

        The available buttons are:

        - ``a`` selects the highlighted option or progresses on-screen text.
        - ``b`` returns to the previous screen or declines a question.
        - ``up`` moves the cursor up one row.
        - ``down`` moves the cursor down one row.
        - ``left`` moves the cursor left one column.
        - ``right`` moves the cursor right one column.

        Use this for dialog, forced selections, and screens not covered by the
        semantic tools. Prefer one button at a time. Use a short sequence only
        when navigating to a clearly identified menu choice.

        Args:
            buttons: Buttons to press in order.

        Returns:
            Fresh battle context after pressing the buttons.
        """
        result = await press_buttons_service(
            context=context,
            buttons=buttons,
        )
        return await complete_battle_action(context, result)

    return Tool(press_buttons, require_parameter_descriptions=True)
