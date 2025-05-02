from pathlib import Path

from agent.actions.build_agent_state.action import BUILD_AGENT_STATE
from agent.graph import build_agent_graph
from agent.state import AgentState
from burr.core import ApplicationBuilder
from burr.core.application import Application
from burr.integrations.pydantic import PydanticTypingSystem

from emulator.emulator import YellowLegacyEmulator


def build_agent_application(
    memory_dir: Path,
    backup_dir: Path,
    emulator: YellowLegacyEmulator,
) -> Application:
    """Build the agent application."""
    initial_state = AgentState(
        iteration=0,
        game_state=None,
        screenshot=None,
        memory_dir=memory_dir,
        backup_dir=backup_dir,
    )
    app = (
        ApplicationBuilder()
        .with_typing(PydanticTypingSystem(AgentState))
        .with_graph(build_agent_graph(emulator))
        .with_state(initial_state)
        .with_entrypoint(BUILD_AGENT_STATE)
        .build()
    )
    return app
