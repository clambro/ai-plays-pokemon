"""Recent raw memory rendered into agent context."""

from collections import OrderedDict
from dataclasses import dataclass, field

from loguru import logger

from common.constants import RAW_MEMORY_MAX_SIZE


@dataclass(slots=True, kw_only=True)
class RawMemoryPiece:
    """A single piece of information contained in the Agent's raw memory."""

    iteration: int
    content: str

    def __str__(self) -> str:
        """Get a string representation of the memory piece."""
        return f"[{self.iteration}]: {self.content}"

    def add_content(self, content: str) -> None:
        """Append content to the memory piece with a new line."""
        self.content += "\n" + content


@dataclass(slots=True, kw_only=True)
class RawMemory:
    """The Agent's raw memory."""

    max_size: int = RAW_MEMORY_MAX_SIZE
    pieces: OrderedDict[int, RawMemoryPiece] = field(default_factory=OrderedDict)

    def __str__(self) -> str:
        """Get a string representation of the memory."""
        if not self.pieces:
            return ""
        latest_iteration = list(self.pieces.keys())[-1]
        out = (
            f"Here are the raw thoughts you have had prior to this point. The bracketed number is"
            f" the incremented iteration number at which you had the thought. Higher numbers are"
            f" more recent. The latest iteration is {latest_iteration}. Only the most recent"
            f" {self.max_size} thoughts are displayed in this section. To give you an indication of"
            f" the passage of time, each iteration takes roughly three seconds."
        )
        out += "\n<raw_memory>\n"
        out += "\n".join([str(piece) for piece in self.pieces.values()])
        out += "\n</raw_memory>"
        return out

    def add_memory(self, iteration: int, content: str) -> None:
        """Append content and publish the resulting rolling memory.

        Content for an existing iteration is appended to that memory piece. The collection is
        sorted, truncated to ``max_size``, and then sent to the streaming background.

        Args:
            iteration: Agent iteration associated with the content.
            content: Thought or observation to append.
        """
        # Injecting the dependency here to avoid circular imports.
        from streaming.server import update_background_log_from_memory  # noqa: PLC0415

        if iteration in self.pieces:
            logger.info(f"Appending to thought: {content}")
            self.pieces[iteration].add_content(content)
        else:
            logger.info(f"Adding new thought: [{iteration}]: {content}")
            self.pieces[iteration] = RawMemoryPiece(iteration=iteration, content=content)
        self.pieces = OrderedDict(sorted(self.pieces.items(), key=lambda x: x[0])[-self.max_size :])
        update_background_log_from_memory(self)
