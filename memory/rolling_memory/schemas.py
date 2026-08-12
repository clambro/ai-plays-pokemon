"""In-memory records for rolling memory."""

from dataclasses import dataclass, field

from loguru import logger


@dataclass(slots=True, kw_only=True)
class CurrentMemoryBlock:
    """Mutable raw memory for the active application iteration."""

    iteration: int
    content: str = ""

    def append(self, content: str) -> None:
        """Append content in the order it was recorded."""
        separator = "\n\n" if self.content else ""
        self.content += f"{separator}{content}"


@dataclass(frozen=True, slots=True, kw_only=True)
class RawMemoryBlock:
    """Finalized raw memory from one application iteration."""

    iteration: int
    content: str


@dataclass(frozen=True, slots=True, kw_only=True)
class MemorySummary:
    """A derived summary covering an inclusive iteration range.

    Level 0 is the implicit raw-memory layer, so stored summaries begin at
    level 1.
    """

    start_iteration: int
    end_iteration: int
    level: int
    content: str


@dataclass(slots=True, kw_only=True)
class RollingMemory:
    """In-memory rolling-memory view for the current workflow."""

    current_block: CurrentMemoryBlock = field(
        default_factory=lambda: CurrentMemoryBlock(iteration=1),
    )
    summary_frontier: tuple[MemorySummary, ...] = field(default_factory=tuple)
    loaded_raw_blocks: tuple[RawMemoryBlock, ...] = field(default_factory=tuple)

    @property
    def raw_blocks(self) -> tuple[RawMemoryBlock | CurrentMemoryBlock, ...]:
        """Get the loaded raw blocks, including the current iteration."""
        if not self.current_block.content:
            return self.loaded_raw_blocks
        return (*self.loaded_raw_blocks, self.current_block)

    def add_memory(self, content: str) -> None:
        """Add content to the current application iteration."""
        if self.current_block.content:
            logger.info(f"Appending to thought: {content}")
        else:
            logger.info(f"Adding new thought: [{self.current_block.iteration}]: {content}")
        self.current_block.append(content)
