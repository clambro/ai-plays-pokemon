"""Pydantic AI interface for retrieving long-term memory."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.overworld.tools.retrieve_long_term_memory.service import (
    retrieve_long_term_memory as retrieve_long_term_memory_service,
)
from agent.overworld.utils import (
    OverworldToolResult,
    complete_overworld_action,
)

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_retrieve_long_term_memory_tool(
    context: AgentContext,
    available_long_term_memory_titles: list[str],
) -> Tool[AgentContext]:
    """Build the long-term-memory retrieval tool."""

    async def retrieve_long_term_memory(
        title: Annotated[str, Field(min_length=1)],
    ) -> OverworldToolResult:
        """Retrieve one long-term memory relevant to the current situation.

        The available memory titles are listed in the initial prompt under
        ``available_long_term_memory_titles``. A memory created later in this
        conversation is also available, as reported by its tool result.
        Titles use SCREAMING_SNAKE_CASE. Select exactly one available title,
        and use this tool only when that memory is relevant.

        Args:
            title: One available long-term-memory title to load.

        Returns:
            Fresh screenshot and the complete retrieval result.
        """
        retrieved_memory = await retrieve_long_term_memory_service(
            title=title,
            available_titles=available_long_term_memory_titles,
        )
        if retrieved_memory.pieces:
            long_term_memory = context.state.long_term_memory.model_copy(deep=True)
            long_term_memory.pieces.update(retrieved_memory.pieces)
            context.state.long_term_memory = long_term_memory

        if retrieved_memory.pieces:
            result = f"Retrieved long-term memory:\n{retrieved_memory}"
        else:
            result = "No long-term memories were retrieved."
        return await complete_overworld_action(context, result)

    return Tool(retrieve_long_term_memory, require_parameter_descriptions=True)
