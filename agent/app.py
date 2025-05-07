from pathlib import Path

from agent.actions.build_agent_state.action import BUILD_AGENT_STATE
from agent.graph import build_agent_graph
from agent.state import AgentState
from burr.core import ApplicationBuilder
from burr.core.application import Application
from burr.integrations.pydantic import PydanticTypingSystem

from emulator.emulator import YellowLegacyEmulator


def build_agent_application(
    folder: Path,
    emulator: YellowLegacyEmulator,
) -> Application:
    """Build the agent application."""
    initial_state = AgentState(folder=folder)
    app = (
        ApplicationBuilder()
        .with_typing(PydanticTypingSystem(AgentState))
        .with_graph(build_agent_graph(emulator))
        .with_state(initial_state)
        .with_entrypoint(BUILD_AGENT_STATE)
        .build()
    )
    return app
