"""Prompts for hierarchical rolling-memory compaction."""

from typing import TYPE_CHECKING

from memory.rolling_memory.schemas import MemorySummary, RawMemoryBlock

if TYPE_CHECKING:
    from collections.abc import Iterable

type _CompactionSourceEntry = RawMemoryBlock | MemorySummary

SYSTEM_PROMPT = """
You compress chronological gameplay records for an AI playing Pokémon Yellow Legacy. Write a faithful historical record, not advice to the future agent.

The source may combine agent reasoning, intentions, hypotheses, tool results, and observed game text. Treat plans, predictions, assumptions, and statements of intent as unconfirmed. Confirmed outcomes and explicit observations take precedence over agent reasoning.

Never invent events, outcomes, explanations, or certainty that the source does not establish.
""".strip()

COMPACTION_PROMPT = """
Compress the memories below into a concise first-person, past-tense historical record covering iterations {start_iteration} through {end_iteration}.

Retain only information likely to remain useful well after this period:
- confirmed, durable progress such as major victories, key items, permanent unlocks, important discoveries, and lasting consequences;
- observed corrections to earlier beliefs;
- material obstacles or clues that were still unresolved at the end of the period;
- failed approaches only when they establish a durable factual constraint that prevents meaningfully equivalent attempts; and
- exact coordinates only when they identify a durable, non-obvious route, warp, ladder, or interaction that would otherwise need to be rediscovered.

Use evidence carefully:
- Tool outcomes, map transitions, acquired items, battle results, and observed game text are evidence.
- Agent plans, predictions, interpretations, and intended actions are not evidence that something happened.
- Later material supersedes earlier material only when it reports an observed change or correction. A later unsupported belief must not erase an earlier confirmed outcome.
- If the evidence genuinely conflicts and does not establish a resolution, state the uncertainty briefly or omit the disputed claim.

Describe unresolved conditions as historical facts about the end of this period. Never turn them into commands, recommendations, goals, or instructions for what the agent should do next.

Remove:
- the all-caps source labels that prefix game dialogue, action results, and scripted-loop notices; use their content as evidence without repeating the labels;
- plans, intentions, self-talk, speculation, recommendations, and imperatives;
- exact button sequences, routine paths, incidental coordinates and waypoints, routine movement, collisions, and pathfinding failures;
- temporary snapshots such as current location, party order, HP, PP, status conditions, and short-lived inventory state;
- routine battle turns, move-by-move tactics, ordinary type-matchup advice, and inconsequential encounters;
- flavor text, incidental NPC dialogue, prices, exhibits, and minor items unless they caused lasting progress; and
- repetition, resolved obstacles, and details made obsolete by later observed events.

Write only the compressed history. Do not mention iteration numbers; they are attached separately. Use as few characters as the durable facts require. Return no more than {max_characters} characters, including spaces and line breaks; omit lower-priority details rather than exceeding the limit.

Memory:
{source}
""".strip()

COMPACTION_REVISION_PROMPT = """
The historical summary below is {actual_characters} characters long and exceeds the limit. Return a shorter version of no more than {max_characters} characters, including spaces and line breaks.

Preserve the most important confirmed, durable facts. Remove source labels, instructions, plans, repetition, temporary state, routine navigation and battle details, and incidental coordinates. Retain an exact coordinate only when it is necessary to preserve a durable, non-obvious route, warp, ladder, or interaction. Do not add any fact that is not already present.

Return only the shortened summary. Omit lower-priority details rather than exceeding {max_characters} characters.

Summary:
{summary}
""".strip()


def format_compaction_source(entries: Iterable[_CompactionSourceEntry]) -> str:
    """Format exact or summarized memory entries for a compaction request."""
    return "\n\n".join(_format_compaction_entry(entry) for entry in entries)


def _format_compaction_entry(entry: _CompactionSourceEntry) -> str:
    """Format one memory entry with its iteration or inclusive range."""
    if isinstance(entry, MemorySummary):
        return f"[{entry.start_iteration}-{entry.end_iteration}]: {entry.content}"
    return f"[{entry.iteration}]: {entry.content}"
