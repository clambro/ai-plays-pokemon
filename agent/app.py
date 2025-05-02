from pathlib import Path

from agent.actions.build_agent_state.action import build_agent_state
from agent.graph import AGENT_GRAPH
from agent.state import AgentState
from burr.core import ApplicationBuilder
from burr.core.application import Application
from emulator.context import get_emulator


def build_agent_application(memory_dir: Path, backup_dir: Path) -> Application:
    """Build the agent application."""
    emulator = get_emulator()
    if not emulator:
        raise RuntimeError("No emulator instance available in the current context")

    initial_state = AgentState(
        iteration=0,
        game_state=emulator.game_state,
        screenshot=emulator.take_screenshot(),
        memory_dir=memory_dir,
        backup_dir=backup_dir,
    )

    app = (
        ApplicationBuilder()
        .with_graph(AGENT_GRAPH)
        .with_state(initial_state)
        .with_entrypoint(str(build_agent_state))
        .build()
    )
    return app
