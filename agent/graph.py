from burr.core.graph import GraphBuilder, Graph

from agent.actions.build_agent_state.action import build_agent_state, BUILD_AGENT_STATE
from agent.actions.decision_maker_overworld.action import (
    decision_maker_overworld,
    DECISION_MAKER_OVERWORLD,
)
from agent.actions.decision_maker_battle.action import (
    decision_maker_battle,
    DECISION_MAKER_BATTLE,
)
from agent.actions.update_current_map.action import (
    update_current_map,
    UPDATE_CURRENT_MAP,
)
from agent.conditions import field_equals_value
from agent.state import AgentStateParams
from common.enums import StateHandler
from emulator.emulator import YellowLegacyEmulator


def build_agent_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the Burr agent graph."""
    return (
        GraphBuilder()
        .with_actions(
            **{
                BUILD_AGENT_STATE: build_agent_state.bind(emulator=emulator),
                UPDATE_CURRENT_MAP: update_current_map.bind(emulator=emulator),
                DECISION_MAKER_OVERWORLD: decision_maker_overworld.bind(emulator=emulator),
                DECISION_MAKER_BATTLE: decision_maker_battle.bind(emulator=emulator),
            }
        )
        .with_transitions(
            (
                BUILD_AGENT_STATE,
                UPDATE_CURRENT_MAP,
                field_equals_value(AgentStateParams.handler, StateHandler.OVERWORLD),
            ),
            (UPDATE_CURRENT_MAP, DECISION_MAKER_OVERWORLD),
            (
                BUILD_AGENT_STATE,
                DECISION_MAKER_BATTLE,
                field_equals_value(AgentStateParams.handler, StateHandler.BATTLE),
            ),
            (DECISION_MAKER_BATTLE, BUILD_AGENT_STATE),
            (DECISION_MAKER_OVERWORLD, BUILD_AGENT_STATE),
        )
        .build()
    )
