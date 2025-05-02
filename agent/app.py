from pathlib import Path

from agent.actions.build_agent_state.action import BUILD_AGENT_STATE
from agent.graph import AGENT_GRAPH
from agent.state import AgentState
from burr.core import ApplicationBuilder
from burr.core.application import Application
from burr.integrations.pydantic import PydanticTypingSystem


def build_agent_application(memory_dir: Path, backup_dir: Path) -> Application:
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
        .with_graph(AGENT_GRAPH)
        .with_state(initial_state)
        .with_entrypoint(BUILD_AGENT_STATE)
        .build()
    )
    return app
