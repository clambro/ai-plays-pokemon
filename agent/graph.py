from burr.core.graph import GraphBuilder

from agent.actions.build_agent_state.action import build_agent_state
from agent.actions.press_random_button.action import press_random_button


AGENT_GRAPH = (
    GraphBuilder()
    .with_actions(
        build_agent_state=build_agent_state,
        press_random_button=press_random_button,
    )
    .with_transitions(
        (str(build_agent_state), str(press_random_button)),
        (str(press_random_button), str(build_agent_state)),
    )
    .build()
)
