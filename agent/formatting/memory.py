"""Shared model-facing formatting for goals and rolling memory."""

from typing import TYPE_CHECKING

from memory.goals import MAX_GOALS
from memory.rolling_memory.schemas import (
    CurrentMemoryBlock,
    MemorySummary,
    RawMemoryBlock,
    RollingMemory,
)

if TYPE_CHECKING:
    from memory.goals import Goals

type _MemoryEntry = CurrentMemoryBlock | RawMemoryBlock | MemorySummary


def format_goals(goals: Goals) -> str:
    """Format the agent's current goals for gameplay prompts."""
    out = "<goals_info>\n"
    out += (
        f"Here are the goals that you have set for yourself. You can keep up to {MAX_GOALS} goals"
        " at once. Goals are longer-term objectives or concerns that are relevant to your progress"
        " and worth remembering. Keep them in mind and generally work toward them as opportunities"
        " arise. When several distinct priorities are worth remembering, record each separately."
        " Goals can concern progression through the current area, team development, healing or"
        " resupplying, or investigating something you discovered. Do not use goals for individual"
        " button presses, routine movement, or other short-lived tasks. Goals must come from"
        " current structured information, observed game text, or recorded memory, never from"
        " assumptions about future game progression or general Pokemon knowledge."
    )
    out += "\n<goals>\n"
    if goals.goals:
        out += "\n".join(
            f"[{i}] {g.goal} (last updated at iteration {g.updated_at_iteration})"
            for i, g in enumerate(goals.goals)
        )
    else:
        out += "You don't have any active goals. You should have at least one."
    out += "\n</goals>\n"
    out += "</goals_info>"
    return out


def format_rolling_memory(memory: RollingMemory) -> str:
    """Format chronological rolling memory for gameplay prompts."""
    entries = (*memory.summary_frontier, *memory.raw_blocks)
    if not entries:
        return ""

    return (
        "Here is your memory from prior to this point. It is a fallible record of past "
        "experiences and beliefs, not an authoritative account of the game; entries may contain "
        "incomplete observations or mistaken conclusions. The bracketed numbers are application "
        "iteration numbers, with higher numbers representing more recent events. An entry with "
        "one number contains the uncompressed record from that iteration. An entry with a range "
        "is a compressed summary covering every iteration in that inclusive range, with older "
        "history represented in progressively less detail. Repeated claims are not independent "
        "confirmation. The current iteration is "
        f"{memory.current_block.iteration}. To give you a rough idea of the passage of time, "
        "each iteration takes a couple of seconds.\n"
        "<memory>\n" + "\n\n".join(_format_memory_entry(entry) for entry in entries) + "\n</memory>"
    )


def _format_memory_entry(entry: _MemoryEntry) -> str:
    """Format one exact or summarized memory entry."""
    if isinstance(entry, MemorySummary):
        return f"[{entry.start_iteration}-{entry.end_iteration}]: {entry.content}"
    return f"[{entry.iteration}]: {entry.content}"
