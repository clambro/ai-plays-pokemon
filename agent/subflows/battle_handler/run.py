"""Run one Pydantic AI battle-agent decision."""

from typing import TYPE_CHECKING

from agent.subflows.battle_handler.agent import BATTLE_AGENT, build_battle_agent_input
from llm.usage import update_pydantic_ai_usage

if TYPE_CHECKING:
    from agent.subflows.battle_handler.context import BattleContext


async def run_battle_decision(context: BattleContext) -> None:
    """Run until the battle agent executes one function tool."""
    async with BATTLE_AGENT.iter(
        build_battle_agent_input(context),
        deps=context,
    ) as agent_run:
        try:
            node = agent_run.next_node
            while not BATTLE_AGENT.is_end_node(node):
                node = await agent_run.next(node)
                if agent_run.usage.tool_calls == 1:
                    break
        finally:
            await update_pydantic_ai_usage(agent_run.new_messages())

    if agent_run.usage.tool_calls != 1:
        raise ValueError("The battle agent returned without using a tool.")
