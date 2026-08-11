"""Pydantic AI interface for creating long-term memory."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.overworld.tools.create_long_term_memory.service import (
    LongTermMemoryAlreadyExistsError,
)
from agent.overworld.tools.create_long_term_memory.service import (
    create_long_term_memory as create_long_term_memory_service,
)
from agent.overworld.tools.utils import (
    OverworldToolResult,
    complete_overworld_action,
)

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_create_long_term_memory_tool(
    context: AgentContext,
    available_long_term_memory_titles: list[str],
) -> Tool[AgentContext]:
    """Build the long-term-memory creation tool."""

    async def create_long_term_memory(
        title: Annotated[str, Field(min_length=1)],
        content: Annotated[str, Field(min_length=1)],
    ) -> OverworldToolResult:
        """Create a new long-term memory object for future reference.

        Think of your long-term memory as a NoSQL database of documents
        containing useful information on your past experiences. The current
        prompt contains your memories, information about the current game
        state, and the existing titles in your long-term memory.

        Long-term memory titles are unique. You cannot re-create or edit an
        existing title with this tool; use the update tool for an existing
        document. Create a totally new memory document only if you have
        learned something important that is not already represented in your
        long-term memory.

        Good candidates for new long-term memory are:

        - New maps: If you have entered a new area, you can keep notes on what
          is in it and how to navigate it. You should create a new long-term
          memory object for each new map you enter. Do not attempt to draw the
          map itself in your long-term memory; you have separate map data for
          reading the spatial layout of the game world. Prefix such titles
          with ``MAP_`` for easy reference.
        - Major characters: If you have met a new character, you can keep
          notes on your interactions with them. Notes about an opposing
          character's Pokemon team could be kept here as well. Prefix such
          titles with ``CHAR_`` for easy reference.
        - New Pokemon: If you have caught a new Pokemon for your team, you can
          keep notes on it. Prefix such titles with ``TEAM_`` for easy
          reference. It might be wise to note down type effectiveness against
          other Pokemon in such a memory.
        - Generic notes or strategies: If you have learned something
          important, you can keep notes on it. Prefix such titles with
          ``NOTE_`` for easy reference.

        The above are not exhaustive. You can create a new long-term memory
        object for any information that you feel is important to remember.
        Keep titles concise, consistent, and descriptive.

        Guidelines for creating new long-term memory objects:

        - Titles must be in SCREAMING_SNAKE_CASE with no punctuation.
        - Never include coordinates in your content, such as for warp points
          or sprites. The game's memory will provide coordinate information as
          needed.
        - Do not create duplicate or near-duplicate memories. If you already
          have a memory with a similar title, do not create a new one; update
          the existing memory instead.
        - Titles must be unique.
        - Long-term memory objects must be concise and to the point: a couple
          of paragraphs maximum.
        - Long-term memory objects must not include mundane information such
          as wild Pokemon that were defeated or individual moves that were
          used. A good rule of thumb is that everything in long-term memory
          should still be relevant a thousand iterations from now. If it will
          not be, it does not need to be there.

        You do not have to create a new long-term memory object if you have
        nothing to add. Do not create more than one new long-term memory object
        during a single overworld run.

        Args:
            title: Title of the new long-term memory object in
                SCREAMING_SNAKE_CASE with no punctuation.
            content: Content of the new long-term memory object.

        Returns:
            Fresh screenshot and the actual creation result.
        """
        try:
            memory = await create_long_term_memory_service(
                title=title,
                content=content,
                iteration=context.state.iteration,
                existing_titles=available_long_term_memory_titles,
            )
        except LongTermMemoryAlreadyExistsError as error:
            result = str(error)
        else:
            long_term_memory = context.state.long_term_memory.model_copy(deep=True)
            long_term_memory.pieces[memory.title] = memory
            context.state.long_term_memory = long_term_memory
            available_long_term_memory_titles.append(memory.title)
            result = (
                f"Created long-term memory:\n<memory>\n{memory.title}\n{memory.content}\n</memory>"
            )

        context.state.rolling_memory.add_memory(result)
        return await complete_overworld_action(context, result)

    return Tool(create_long_term_memory, require_parameter_descriptions=True)
