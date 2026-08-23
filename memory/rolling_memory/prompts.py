"""Prompts for hierarchical rolling-memory compaction."""

from typing import TYPE_CHECKING

from memory.rolling_memory.schemas import MemorySummary, RawMemoryBlock

if TYPE_CHECKING:
    from collections.abc import Iterable

type _CompactionSourceEntry = RawMemoryBlock | MemorySummary

SYSTEM_PROMPT = """
You maintain a compact, faithful history for an AI playing Pokémon Yellow Legacy.
Summarize only the supplied memory. Never invent events, outcomes, or explanations.
""".strip()

COMPACTION_PROMPT = """
Compress the memories below into durable first-person notes covering iterations
{start_iteration} through {end_iteration}.

Preserve:
- lasting outcomes and progress;
- unresolved goals, obstacles, and commitments;
- failed approaches when they should not be repeated;
- later corrections to earlier beliefs; and
- locations, characters, items, Pokémon, and game state that remain useful.

Remove repetition, transient mechanics, routine movement, and self-talk. Resolve
contradictions in favor of the later source, but do not infer anything that the
source does not establish. The summary must stand on its own and must not exceed
{max_characters} characters. Do not reference the iteration numbers at all. They
will be appended automatically after you're done.

Memory:
{source}
""".strip()


def format_compaction_source(entries: Iterable[_CompactionSourceEntry]) -> str:
    """Format exact or summarized memory entries for a compaction request."""
    return "\n\n".join(_format_compaction_entry(entry) for entry in entries)


def _format_compaction_entry(entry: _CompactionSourceEntry) -> str:
    """Format one memory entry with its iteration or inclusive range."""
    if isinstance(entry, MemorySummary):
        return f"[{entry.start_iteration}-{entry.end_iteration}]: {entry.content}"
    return f"[{entry.iteration}]: {entry.content}"
