"""Working state for rolling memory."""

from dataclasses import dataclass, field

from loguru import logger

from database.rolling_memory.repository import (
    finalize_raw_memory_block,
    get_memory_summary_frontier,
    get_raw_memory_blocks_after,
)
from database.rolling_memory.schemas import RawMemoryBlockCreate
from memory.compaction.service import compact_memory


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
        from streaming.server import update_background_log_from_memory  # noqa: PLC0415

        if self.current_block.content:
            logger.info(f"Appending to thought: {content}")
        else:
            logger.info(f"Adding new thought: [{self.current_block.iteration}]: {content}")
        self.current_block.append(content)
        update_background_log_from_memory(self)


async def initialize_memory(current_block: CurrentMemoryBlock) -> RollingMemory:
    """Initialize a loop's working memory from SQLite and its current block."""
    summary_records = await get_memory_summary_frontier()
    summary_frontier = tuple(
        MemorySummary(
            start_iteration=record.start_iteration,
            end_iteration=record.end_iteration,
            level=record.level,
            content=record.content,
        )
        for record in summary_records
    )
    covered_iteration = summary_frontier[-1].end_iteration if summary_frontier else -1
    raw_records = await get_raw_memory_blocks_after(covered_iteration)
    loaded_raw_blocks = tuple(
        RawMemoryBlock(
            iteration=record.iteration,
            content=record.content,
        )
        for record in raw_records
    )

    latest_finalized_iteration = (
        loaded_raw_blocks[-1].iteration if loaded_raw_blocks else covered_iteration
    )
    if current_block.iteration <= latest_finalized_iteration:
        current_block = CurrentMemoryBlock(
            iteration=latest_finalized_iteration + 1,
        )

    return RollingMemory(
        current_block=current_block,
        summary_frontier=summary_frontier,
        loaded_raw_blocks=loaded_raw_blocks,
    )


async def finalize_iteration(memory: RollingMemory) -> None:
    """Persist and compact the completed iteration."""
    record = await finalize_raw_memory_block(
        RawMemoryBlockCreate(
            iteration=memory.current_block.iteration,
            content=memory.current_block.content,
        ),
    )
    finalized_block = RawMemoryBlock(
        iteration=record.iteration,
        content=record.content,
    )
    await compact_memory(
        RollingMemory(
            current_block=memory.current_block,
            summary_frontier=memory.summary_frontier,
            loaded_raw_blocks=(*memory.loaded_raw_blocks, finalized_block),
        ),
    )
