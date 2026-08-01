"""Tests for overworld tool availability."""

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from agent.state import AgentState
from agent.subflows.overworld_handler.context import OverworldContext
from agent.subflows.overworld_handler.tools.registry import build_overworld_toolset

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.unit
@pytest.mark.parametrize(
    ("titles", "expected_tools"),
    [
        ((), set()),
        (("TEAM_PIKACHU",), {"retrieve_long_term_memory"}),
    ],
)
def test_retrieval_tool_requires_an_existing_memory(
    tmp_path: Path,
    titles: tuple[str, ...],
    expected_tools: set[str],
) -> None:
    """Expose retrieval only when its prepared title snapshot is non-empty."""
    current_map = MagicMock()
    current_map.known_sprites = {}
    current_map.known_signs = {}
    context = OverworldContext(
        state=AgentState(folder=tmp_path),
        emulator=MagicMock(),
        current_map=current_map,
        available_long_term_memory_titles=titles,
    )
    game_state = MagicMock()
    game_state.player.is_biking = True
    game_state.party = []
    game_state.inventory.items = []
    game_state.can_use_strength = False

    toolset = build_overworld_toolset(context, game_state)

    assert {"create_goal", "update_goal", "delete_goal"} <= toolset.tools.keys()
    assert toolset.tools.keys() & {"retrieve_long_term_memory"} == expected_tools
