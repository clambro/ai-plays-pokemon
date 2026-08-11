"""In-memory records for rolling memory."""

from dataclasses import dataclass, field

from loguru import logger


@dataclass(slots=True, kw_only=True)
class CurrentMemoryBlock:
    """Mutable raw memory for the active application iteration."""

    iteration: int
    content: str = ""

    def __str__(self) -> str:
        """Format the block with its application iteration."""
        return f"[{self.iteration}]: {self.content}"

    def append(self, content: str) -> None:
        """Append content in the order it was recorded."""
        separator = "\n\n" if self.content else ""
        self.content += f"{separator}{content}"


@dataclass(frozen=True, slots=True, kw_only=True)
class RawMemoryBlock:
    """Finalized raw memory from one application iteration."""

    iteration: int
    content: str

    def __str__(self) -> str:
        """Format the block with its application iteration."""
        return f"[{self.iteration}]: {self.content}"


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

    def __str__(self) -> str:
        """Format the summary with its covered iteration range."""
        return f"[{self.start_iteration}-{self.end_iteration}]: {self.content}"


@dataclass(slots=True, kw_only=True)
class RollingMemory:
    """In-memory rolling-memory view for the current workflow."""

    current_block: CurrentMemoryBlock = field(
        default_factory=lambda: CurrentMemoryBlock(iteration=1),
    )
    summary_frontier: tuple[MemorySummary, ...] = field(default_factory=tuple)
    loaded_raw_blocks: tuple[RawMemoryBlock, ...] = field(default_factory=tuple)

    def __str__(self) -> str:
        """Render the chronological memory view used in prompts."""
        entries = (*self.summary_frontier, *self.raw_blocks)
        if not entries:
            return ""

        return (
            "Here is your memory from prior to this point. The bracketed numbers are application "
            "iteration numbers, with higher numbers representing more recent events. An entry "
            "with one number contains the exact memory from that iteration. An entry with a range "
            "is a compressed summary covering every iteration in that inclusive range, with older "
            "history represented in progressively less detail. The current iteration is "
            f"{self.current_block.iteration}. To give you an indication of the passage of time, "
            "each iteration takes roughly three seconds.\n"
            "<memory>\n" + "\n".join(map(str, entries)) + "\n</memory>"
        )

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
