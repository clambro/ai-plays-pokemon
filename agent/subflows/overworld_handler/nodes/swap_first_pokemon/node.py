"""Swap first pokémon node for the overworld subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.swap_first_pokemon.service import (
    SwapFirstPokemonService,
)
from agent.subflows.overworld_handler.state import OverworldHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class SwapFirstPokemonNode(Node[OverworldHandlerStore]):
    """Swap the first Pokemon in the party with another Pokemon."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the swap-first-Pokémon node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Swapping the first Pokemon...")

        state = await store.get_state()
        if state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")

        service = SwapFirstPokemonService(
            rolling_memory=state.rolling_memory,
            emulator=self.emulator,
        )
        rolling_memory = await service.swap_first_pokemon()

        await store.set_rolling_memory(rolling_memory)
