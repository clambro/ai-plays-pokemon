"""Behavior tests for deterministic text handling."""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.context import AgentContext
from agent.state import AgentState
from agent.subflows.text_handler import utils

if TYPE_CHECKING:
    from pathlib import Path

    from emulator.game_state import YellowLegacyGameState


@pytest.mark.unit
async def test_plain_dialog_is_published_before_it_advances(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Show deterministic dialog state before emulator input changes it."""
    initial_state = _game_state(has_dialog=True, has_outside_text=False)
    final_state = _game_state(has_dialog=False, has_outside_text=True)
    events: list[str] = []
    dialog_reader = MagicMock()
    dialog_reader.observe_current_state = AsyncMock(
        side_effect=[initial_state, final_state],
    )

    async def advance() -> None:
        events.append("advance")

    dialog_reader.advance = AsyncMock(side_effect=advance)
    dialog_reader.is_cursor_blinking = AsyncMock(return_value=False)
    dialog_reader.text = "Welcome to the Pokémon Center."
    monkeypatch.setattr(utils, "DialogReader", MagicMock(return_value=dialog_reader))
    monkeypatch.setattr(utils.asyncio, "sleep", AsyncMock())

    def publish(_state: AgentState, _game_state: YellowLegacyGameState) -> None:
        events.append("publish")

    monkeypatch.setattr(utils, "update_background_from_states", publish)
    context = AgentContext(
        state=AgentState(folder=tmp_path),
        emulator=MagicMock(),
    )

    dialog = await utils.handle_text_dialog(context)

    assert dialog == "Welcome to the Pokémon Center."
    assert events == ["publish", "advance"]


def _game_state(*, has_dialog: bool, has_outside_text: bool) -> MagicMock:
    """Build the text-state behavior needed by deterministic dialog handling."""
    game_state = MagicMock()
    game_state.get_dialog_box.return_value = MagicMock() if has_dialog else None
    game_state.is_text_on_screen.return_value = has_outside_text
    game_state.battle.is_in_battle = False
    game_state.is_naming_screen.return_value = False
    return game_state
