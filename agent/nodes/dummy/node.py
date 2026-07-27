"""Dummy node for the top-level agent graph."""

from junjo import BaseStore, Node


class DummyNode(Node[BaseStore]):
    """Generic dummy node used to streamline graph building."""

    def __init__(self) -> None:
        """Initialize the dummy node."""
        super().__init__()

    async def service(self, store: BaseStore) -> None:
        """Required method for the node."""
