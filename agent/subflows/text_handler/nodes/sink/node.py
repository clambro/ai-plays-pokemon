from junjo import Node

from agent.subflows.text_handler.state import TextHandlerStore


class SinkNode(Node[TextHandlerStore]):
    """Dummy sink node to collect the text handler subflow."""

    def __init__(self) -> None:
        super().__init__()

    async def service(self, store: TextHandlerStore) -> None:
        """Required method for the node."""
