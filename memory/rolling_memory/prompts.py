"""Prompts for hierarchical rolling-memory compaction."""

from typing import TYPE_CHECKING

from memory.rolling_memory.schemas import MemorySummary, RawMemoryBlock

if TYPE_CHECKING:
    from collections.abc import Iterable

type _CompactionSourceEntry = RawMemoryBlock | MemorySummary

SYSTEM_PROMPT = """
You compress chronological gameplay records for an AI playing Pokémon Yellow Legacy. Write a faithful historical record, not advice to the future agent. The records are a partial snapshot of an ongoing game: they may begin mid-progress, and the game continues beyond them.

The source may contain raw single-iteration records and earlier compressed summaries. In raw records, labeled game dialogue and action results authoritatively record what the game or tools returned, while unlabeled prose contains the agent's fallible reasoning and interpretation. Earlier summaries may contain mistakes or missing context.

Treat plans, predictions, assumptions, interpretations, and other unsupported agent claims as unconfirmed. Confirmed outcomes and explicit observations take precedence. Never invent events, outcomes, explanations, or certainty that the source does not establish. Preserve uncertainty and scope; compression must not turn partial progress into completion or broaden the source's claims.
""".strip()

COMPACTION_PROMPT = """
Summarize the records from iterations {start_iteration} through {end_iteration} into a concise first-person, past-tense history.

Keep important events, progress, discoveries, and unfinished matters. Omit coordinates and detailed navigation descriptions, routine actions, temporary state, repetition, and incidental details. Do not add advice, plans, or conclusions unsupported by the records.

Return only the summary, without source labels or iteration numbers, in no more than {max_characters} characters including spaces and line breaks.

Records:
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
