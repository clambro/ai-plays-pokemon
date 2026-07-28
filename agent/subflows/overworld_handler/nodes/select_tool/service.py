"""Business logic for select tool in the overworld subflow."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.subflows.overworld_handler.enums import OverworldTool
from agent.subflows.overworld_handler.nodes.select_tool.prompts import (
    BUTTON_TOOL_INFO,
    NAVIGATION_TOOL_BIKING_INFO,
    NAVIGATION_TOOL_INFO,
    SELECT_TOOL_PROMPT,
    SOKOBAN_SOLVER_TOOL_INFO,
    SWAP_FIRST_POKEMON_TOOL_INFO,
    USE_ITEM_TOOL_INFO,
)
from agent.subflows.overworld_handler.nodes.select_tool.schemas import SelectToolResponse
from common.enums import AsciiTile, SpriteLabel
from llm.service import OpenAILLMService

if TYPE_CHECKING:
    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState
    from memory.rolling_memory import RollingMemory
    from overworld_map.schemas import OverworldMap

llm_service = OpenAILLMService()


async def select_tool(
    *,
    rolling_memory: RollingMemory,
    current_map: OverworldMap,
    state_string_builder: StateStringBuilder,
    emulator: YellowLegacyEmulator,
) -> tuple[OverworldTool, RollingMemory]:
    """Select an available overworld tool for the current game state.

    Args:
        rolling_memory: Recent memory to update with the model's reasoning.
        current_map: Explored map used to determine available navigation tools.
        state_string_builder: Formatter for the current overworld state and map context.
        emulator: Running emulator used to inspect the state and capture its screen.

    Returns:
        The selected tool and updated rolling memory. Provider or validation failures select the
        button-pressing tool and leave memory unchanged.
    """
    game_state, img = await emulator.get_game_state_with_screenshot()
    prompt = SELECT_TOOL_PROMPT.format(
        state=state_string_builder(game_state),
        tools=_get_available_tool_info(game_state, current_map),
    )
    try:
        response = await llm_service.get_llm_response_pydantic(
            messages=[img, prompt],
            schema=SelectToolResponse,
        )
        tool = OverworldTool(response.tool)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error selecting tool. Defaulting to pressing buttons. {e}")
        return OverworldTool.PRESS_BUTTONS, rolling_memory

    rolling_memory.add_memory(
        content=(
            f"Current map: {game_state.map.id.name} at coordinates"
            f" {game_state.player.coords}, facing {game_state.player.direction.name}."
            f" {response.thoughts}"
        ),
    )
    return tool, rolling_memory


def _get_available_tool_info(
    game_state: YellowLegacyGameState,
    current_map: OverworldMap,
) -> str:
    """Get the information about the available tools."""
    info = [BUTTON_TOOL_INFO]  # Always available.
    if game_state.player.is_biking:
        info.append(NAVIGATION_TOOL_BIKING_INFO)
    else:
        info.append(NAVIGATION_TOOL_INFO)

    if len(game_state.party) > 1:
        info.append(SWAP_FIRST_POKEMON_TOOL_INFO)

    if len(game_state.inventory.items) > 0:
        info.append(USE_ITEM_TOOL_INFO)

    tiles = [t for row in current_map.ascii_tiles for t in row]
    has_goal = any(t in (AsciiTile.BOULDER_HOLE, AsciiTile.PRESSURE_PLATE) for t in tiles)
    has_boulder = any(
        s.label == SpriteLabel.BOULDER and s.is_rendered for s in current_map.known_sprites.values()
    )
    if has_boulder and has_goal and game_state.can_use_strength:
        info.append(SOKOBAN_SOLVER_TOOL_INFO)

    return "\n".join(info)
