"""Shared model-facing formatting for goals and rolling memory."""

from typing import TYPE_CHECKING

from memory.rolling_memory.schemas import (
    CurrentMemoryBlock,
    MemorySummary,
    RawMemoryBlock,
    RollingMemory,
)

if TYPE_CHECKING:
    from memory.goals import Goal, Goals

type _MemoryEntry = CurrentMemoryBlock | RawMemoryBlock | MemorySummary


def format_goals(goals: Goals) -> str:
    """Format the agent's current goals for gameplay prompts."""
    out = "<goals_info>\n"
    out += (
        "Here are the goals that you have set for yourself. Your primary goal is one major"
        " outcome established by your current context, while each secondary goal is one"
        " discrete step that directly supports it. Goals must come from current structured"
        " information, observed game text, or recorded memory, never from assumptions about"
        " future game progression or general Pokemon knowledge. The actions that you take and"
        " the thoughts that you think should all be in service of these goals."
    )
    out += "\n<goals>\n"
    if goals.goals:
        out += "\n".join(
            f"[{index}] {_format_goal(goal)}" for index, goal in enumerate(goals.goals)
        )
        if not any(not goal.is_primary for goal in goals.goals):
            out += "\nYou have not set any secondary goals yet."
    else:
        out += "You have not set any goals yet."
    out += "\n</goals>\n"
    out += "</goals_info>"
    return out


def format_rolling_memory(memory: RollingMemory) -> str:
    """Format chronological rolling memory for gameplay prompts."""
    entries = (*memory.summary_frontier, *memory.raw_blocks)
    if not entries:
        return ""

    return (
        "Here is your memory from prior to this point. The bracketed numbers are application "
        "iteration numbers, with higher numbers representing more recent events. An entry "
        "with one number contains the exact memory from that iteration. An entry with a range "
        "is a compressed summary covering every iteration in that inclusive range, with older "
        "history represented in progressively less detail. The current iteration is "
        f"{memory.current_block.iteration}. To give you a rough idea of the passage of time, "
        "each iteration takes a couple of seconds.\n"
        "<memory>\n" + "\n".join(_format_memory_entry(entry) for entry in entries) + "\n</memory>"
    )


def _format_goal(goal: Goal) -> str:
    """Format one goal with its role and most recent revision iteration."""
    role = "Primary goal" if goal.is_primary else "Secondary goal"
    return f"{role} (last updated at iteration {goal.updated_at_iteration}): {goal.goal}"


def _format_memory_entry(entry: _MemoryEntry) -> str:
    """Format one exact or summarized memory entry."""
    if isinstance(entry, MemorySummary):
        return f"[{entry.start_iteration}-{entry.end_iteration}]: {entry.content}"
    return f"[{entry.iteration}]: {entry.content}"
