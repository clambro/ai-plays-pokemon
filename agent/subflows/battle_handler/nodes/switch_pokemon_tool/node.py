"""Switch pokémon tool node for the battle subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.battle_handler.nodes.switch_pokemon_tool.service import switch_pokemon
from agent.subflows.battle_handler.schemas import SwitchPokemonToolArgs
from agent.subflows.battle_handler.state import BattleHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class SwitchPokemonToolNode(Node[BattleHandlerStore]):
    """Switch to a different Pokemon."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the switch Pokémon tool node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: BattleHandlerStore) -> None:
        """The service for the node."""
        logger.info("Switching to a different Pokemon...")

        state = await store.get_state()
        if state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")
        if not isinstance(state.tool_args, SwitchPokemonToolArgs):
            raise TypeError("Tool args is not a SwitchPokemonToolArgs")

        rolling_memory = await switch_pokemon(
            rolling_memory=state.rolling_memory,
            tool_args=state.tool_args,
            emulator=self.emulator,
        )

        await store.set_rolling_memory(rolling_memory)
