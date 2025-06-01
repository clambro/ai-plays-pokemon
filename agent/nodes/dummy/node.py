from junjo import BaseStore, Node


class DummyNode(Node[BaseStore]):
    """Generic dummy node used to streamline graph building."""

    def __init__(self) -> None:
        super().__init__()

    async def service(self, store: BaseStore) -> None:
        """Required method for the node."""
