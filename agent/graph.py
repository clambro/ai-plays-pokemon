from burr.core.graph import GraphBuilder, Graph

from agent.actions.build_agent_state.action import build_agent_state, BUILD_AGENT_STATE
from agent.actions.press_random_button.action import press_random_button, PRESS_RANDOM_BUTTON
from emulator.emulator import YellowLegacyEmulator


def build_agent_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the Burr agent graph."""
    return (
        GraphBuilder()
        .with_actions(
            **{
                BUILD_AGENT_STATE: build_agent_state.bind(emulator=emulator),
                PRESS_RANDOM_BUTTON: press_random_button.bind(emulator=emulator),
            }
        )
        .with_transitions(
            (BUILD_AGENT_STATE, PRESS_RANDOM_BUTTON),
            (PRESS_RANDOM_BUTTON, BUILD_AGENT_STATE),
        )
        .build()
    )
