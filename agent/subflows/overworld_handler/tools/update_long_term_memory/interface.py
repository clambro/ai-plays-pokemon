"""Pydantic AI interface for updating long-term memory."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.subflows.overworld_handler.tools.update_long_term_memory.schemas import (
    UpdateType,  # noqa: TC001  # Pydantic AI evaluates tool annotations at runtime.
)
from agent.subflows.overworld_handler.tools.update_long_term_memory.service import (
    LongTermMemoryNotLoadedError,
)
from agent.subflows.overworld_handler.tools.update_long_term_memory.service import (
    update_long_term_memory as update_long_term_memory_service,
)
from agent.subflows.overworld_handler.utils import (
    OverworldToolResult,
    complete_overworld_action,
)

if TYPE_CHECKING:
    from agent.subflows.overworld_handler.context import OverworldContext


def build_update_long_term_memory_tool(
    context: OverworldContext,
) -> Tool[OverworldContext]:
    """Build the long-term-memory update tool."""

    async def update_long_term_memory(
        title: Annotated[str, Field(min_length=1)],
        update_type: UpdateType,
        content: Annotated[str, Field(min_length=1)],
    ) -> OverworldToolResult:
        """Update a currently available long-term memory object.

        The long-term memory objects in the current prompt are the only
        memories that you have access to at the moment. You can update only a
        memory from that list or one created earlier in this conversation.

        Guidelines for updating long-term memory objects:

        - Never include coordinates in your content, such as for warp points
          or sprites. The game's memory will provide coordinate information as
          needed.
        - Each piece of long-term memory is meant to be a document containing
          polished notes on a specific topic. Do not fill your content with
          useless noise straight from your raw and summary memories.
          Everything in your long-term memory should be useful to you. You
          still have the raw and summary memories to refer to separately if
          you need to.
        - Keep your long-term memory documents concise and to the point: a
          couple of paragraphs maximum.
        - If a piece of long-term memory is getting too long, meaning more
          than a couple of paragraphs, rewrite the whole thing in a more
          concise manner. Strip out unnecessary information and focus on the
          most important details.
        - Do not add mundane information to long-term memory, such as wild
          Pokemon that were defeated or individual moves that were used. A
          good rule of thumb is that everything in long-term memory should
          still be relevant a thousand iterations from now. If it will not be,
          it does not need to be there.
        - You can update only the long-term memory objects listed in the
          current prompt or created earlier in this conversation. Attempting
          to update another object will result in an error.

        You do not have to update any long-term memory objects if you have
        nothing to add. When in doubt, do not make an update.

        Args:
            title: Title of the long-term memory object to update, exactly as
                it appears in the current memory. If this does not match a
                loaded title, you will receive an error.
            update_type: Type of update to perform: append new information to
                the existing content or rewrite the entire content.
            content: Content to apply. For an append, this is added to the end
                of the existing content with a newline. For a rewrite, this
                replaces the existing content entirely, so include all the
                information you want to keep.

        Returns:
            Fresh screenshot and the actual update result.
        """
        try:
            memory = await update_long_term_memory_service(
                title=title,
                update_type=update_type,
                content=content,
                iteration=context.state.iteration,
                loaded_memories=context.state.long_term_memory.pieces,
            )
        except LongTermMemoryNotLoadedError as error:
            result = str(error)
        else:
            long_term_memory = context.state.long_term_memory.model_copy(deep=True)
            long_term_memory.pieces[memory.title] = memory
            context.state.long_term_memory = long_term_memory
            result = (
                f"Updated long-term memory using {update_type.value}:\n"
                f"<memory>\n{memory.title}\n{memory.content}\n</memory>"
            )

        context.state.rolling_memory.add_memory(result)
        return await complete_overworld_action(context, result)

    return Tool(update_long_term_memory, require_parameter_descriptions=True)
