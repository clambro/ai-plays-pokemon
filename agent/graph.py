from burr.core.graph import GraphBuilder, Graph

from agent.actions.build_agent_state.action import build_agent_state, BUILD_AGENT_STATE
from agent.actions.generic_decision_maker.action import (
    generic_decision_maker,
    GENERIC_DECISION_MAKER,
)
from emulator.emulator import YellowLegacyEmulator


def build_agent_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the Burr agent graph."""
    return (
        GraphBuilder()
        .with_actions(
            **{
                BUILD_AGENT_STATE: build_agent_state.bind(emulator=emulator),
                GENERIC_DECISION_MAKER: generic_decision_maker.bind(emulator=emulator),
            }
        )
        .with_transitions(
            (BUILD_AGENT_STATE, GENERIC_DECISION_MAKER),
            (GENERIC_DECISION_MAKER, BUILD_AGENT_STATE),
        )
        .build()
    )
