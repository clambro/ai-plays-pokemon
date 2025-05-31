from junjo import Node

from agent.subflows.overworld_handler.state import OverworldHandlerStore


class SinkNode(Node[OverworldHandlerStore]):
    """Dummy sink node to collect the overworld handler subflow."""

    def __init__(self) -> None:
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """Required method for the node."""
