from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.swap_first_pokemon.service import (
    SwapFirstPokemonService,
)
from agent.subflows.overworld_handler.state import OverworldHandlerStore
from emulator.emulator import YellowLegacyEmulator


class SwapFirstPokemonNode(Node[OverworldHandlerStore]):
    """Swap the first Pokemon in the party with another Pokemon."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Swapping the first Pokemon...")

        state = await store.get_state()
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")
        if state.iteration is None:
            raise ValueError("Iteration is not set")

        service = SwapFirstPokemonService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            emulator=self.emulator,
        )
        raw_memory = await service.swap_first_pokemon()

        await store.set_raw_memory(raw_memory)
