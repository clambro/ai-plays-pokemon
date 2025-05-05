from burr.core.graph import GraphBuilder, Graph

from agent.actions.build_agent_state.action import build_agent_state, BUILD_AGENT_STATE
from agent.actions.decision_maker_overworld.action import (
    decision_maker_overworld,
    DECISION_MAKER_OVERWORLD,
)
from emulator.emulator import YellowLegacyEmulator


def build_agent_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the Burr agent graph."""
    return (
        GraphBuilder()
        .with_actions(
            **{
                BUILD_AGENT_STATE: build_agent_state.bind(emulator=emulator),
                DECISION_MAKER_OVERWORLD: decision_maker_overworld.bind(emulator=emulator),
            }
        )
        .with_transitions(
            (BUILD_AGENT_STATE, DECISION_MAKER_OVERWORLD),
            (DECISION_MAKER_OVERWORLD, BUILD_AGENT_STATE),
        )
        .build()
    )
