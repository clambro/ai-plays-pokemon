"""Behavior tests for typed gameplay-agent orchestration."""

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent import app
from agent.context import AgentContext
from agent.state import AgentState
from emulator.control_events import ControlBoundary, ControlHandoff

if TYPE_CHECKING:
    from pathlib import Path


type Handler = Callable[[AgentContext], Awaitable[None]]


def _game_state(
    *,
    is_battle: bool = False,
    is_naming: bool = False,
    has_text: bool = False,
    map_height: int = 1,
    map_width: int = 1,
) -> MagicMock:
    """Build the game-state behavior needed by root classification."""
    game_state = MagicMock()
    game_state.battle.is_in_battle = is_battle
    game_state.is_naming_screen.return_value = is_naming
    game_state.is_text_on_screen.return_value = has_text
    game_state.map.height = map_height
    game_state.map.width = map_width
    return game_state


@pytest.mark.unit
@pytest.mark.parametrize(
    ("game_state", "control_boundary", "expected_handler"),
    [
        pytest.param(
            _game_state(is_battle=True, has_text=True),
            ControlBoundary.TEXT_INPUT_READY,
            app.run_battle,
            id="battle",
        ),
        pytest.param(
            _game_state(is_battle=True, is_naming=True, has_text=True),
            ControlBoundary.INTERACTIVE_READY,
            app.run_text,
            id="post-catch-naming",
        ),
        pytest.param(
            _game_state(has_text=True),
            ControlBoundary.TEXT_INPUT_READY,
            app.run_text,
            id="text",
        ),
        pytest.param(
            _game_state(),
            ControlBoundary.INTERACTIVE_READY,
            app.run_text,
            id="custom-interface",
        ),
        pytest.param(_game_state(map_height=0), None, app.run_text, id="zero-height-map"),
        pytest.param(_game_state(map_width=0), None, app.run_text, id="zero-width-map"),
        pytest.param(
            _game_state(has_text=True),
            ControlBoundary.OVERWORLD_READY,
            app.run_overworld,
            id="rendered-overworld",
        ),
    ],
)
def test_select_agent_handler(
    game_state: MagicMock,
    control_boundary: ControlBoundary | None,
    expected_handler: Handler,
) -> None:
    """Preserve routing precedence and transition-map fallbacks."""
    assert app.select_agent_handler(game_state, control_boundary) is expected_handler


@pytest.mark.unit
async def test_dispatch_agent_uses_the_shared_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Observe once before invoking the selected handler."""
    game_state = _game_state()
    emulator = MagicMock()
    emulator.get_game_state_with_control_boundary = AsyncMock(
        return_value=(game_state, ControlBoundary.OVERWORLD_READY)
    )
    context = AgentContext(
        state=AgentState(folder=tmp_path),
        emulator=emulator,
    )
    handler = AsyncMock()
    select_handler = MagicMock(return_value=handler)
    monkeypatch.setattr(app, "select_agent_handler", select_handler)

    await app.dispatch_agent(context)

    emulator.get_game_state_with_control_boundary.assert_awaited_once_with()
    select_handler.assert_called_once_with(game_state, ControlBoundary.OVERWORLD_READY)
    handler.assert_awaited_once_with(context)


@pytest.mark.unit
async def test_dispatch_agent_handles_control_handoff(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Return normally when ROM control has moved to another handler."""
    emulator = MagicMock()
    emulator.get_game_state_with_control_boundary = AsyncMock(
        return_value=(_game_state(), ControlBoundary.OVERWORLD_READY)
    )
    context = AgentContext(state=AgentState(folder=tmp_path), emulator=emulator)
    monkeypatch.setattr(
        app,
        "select_agent_handler",
        MagicMock(return_value=AsyncMock(side_effect=ControlHandoff)),
    )

    await app.dispatch_agent(context)
