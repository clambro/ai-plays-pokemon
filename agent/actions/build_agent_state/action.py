import asyncio
from burr.core.action import action
from loguru import logger
from agent.actions.build_agent_state.service import BuildAgentStateService
from agent.state import AgentState, AgentStateParams
from emulator.emulator import YellowLegacyEmulator


BUILD_AGENT_STATE = "Build Agent State"


@action.pydantic(
    # We need to be able to read and write everything in this action.
    reads=[*AgentStateParams.__members__.values()],
    writes=[*AgentStateParams.__members__.values()],
)
async def build_agent_state(state: AgentState, emulator: YellowLegacyEmulator) -> AgentState:
    """
    The first action in the agent loop. Builds the agent state based on the emulator and the
    previous state.
    """
    logger.info("Building agent state...")

    service = BuildAgentStateService(emulator)
    await service.wait_for_animations()

    state.iteration += 1
    state.buttons_pressed = []
    state.handler = await service.determine_handler()
    return state
