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
from agent.actions.decision_maker_text.action import DECISION_MAKER_TEXT, decision_maker_text
from agent.actions.handle_dialog_box.action import HANDLE_DIALOGUE_BOX, handle_dialog_box
from agent.actions.update_current_map.action import (
    update_current_map,
    UPDATE_CURRENT_MAP,
)
from agent.actions.update_goals.action import UPDATE_GOALS, update_goals
from agent.actions.update_onscreen_entities.action import (
    UPDATE_ONSCREEN_ENTITIES,
    update_onscreen_entities,
)
from agent.conditions import field_equals_value
from agent.state import AgentStateParams
from common.enums import AgentStateHandler
from emulator.emulator import YellowLegacyEmulator


def build_agent_graph(emulator: YellowLegacyEmulator) -> Graph:
    """Build the Burr agent graph."""
    return (
        GraphBuilder()
        .with_actions(
            **{
                BUILD_AGENT_STATE: build_agent_state.bind(emulator=emulator),
                UPDATE_CURRENT_MAP: update_current_map.bind(emulator=emulator),
                UPDATE_ONSCREEN_ENTITIES: update_onscreen_entities.bind(emulator=emulator),
                HANDLE_DIALOGUE_BOX: handle_dialog_box.bind(emulator=emulator),
                DECISION_MAKER_OVERWORLD: decision_maker_overworld.bind(emulator=emulator),
                DECISION_MAKER_BATTLE: decision_maker_battle.bind(emulator=emulator),
                DECISION_MAKER_TEXT: decision_maker_text.bind(emulator=emulator),
                UPDATE_GOALS: update_goals.bind(emulator=emulator),
            }
        )
        .with_transitions(
            (
                BUILD_AGENT_STATE,
                UPDATE_CURRENT_MAP,
                field_equals_value(AgentStateParams.handler, AgentStateHandler.OVERWORLD),
            ),
            (UPDATE_CURRENT_MAP, UPDATE_ONSCREEN_ENTITIES),
            (UPDATE_ONSCREEN_ENTITIES, DECISION_MAKER_OVERWORLD),
            (
                BUILD_AGENT_STATE,
                DECISION_MAKER_BATTLE,
                field_equals_value(AgentStateParams.handler, AgentStateHandler.BATTLE),
            ),
            (
                BUILD_AGENT_STATE,
                HANDLE_DIALOGUE_BOX,
                field_equals_value(AgentStateParams.handler, AgentStateHandler.TEXT),
            ),
            (
                HANDLE_DIALOGUE_BOX,
                DECISION_MAKER_TEXT,
                field_equals_value(AgentStateParams.handler, AgentStateHandler.TEXT),
            ),
            (
                HANDLE_DIALOGUE_BOX,
                UPDATE_GOALS,
                ~field_equals_value(AgentStateParams.handler, AgentStateHandler.TEXT),
            ),
            (DECISION_MAKER_BATTLE, UPDATE_GOALS),
            (DECISION_MAKER_OVERWORLD, UPDATE_GOALS),
            (DECISION_MAKER_TEXT, UPDATE_GOALS),
            (UPDATE_GOALS, BUILD_AGENT_STATE),
        )
        .build()
    )
