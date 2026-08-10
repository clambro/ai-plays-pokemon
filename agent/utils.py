"""Shared utilities and lifecycle hooks for gameplay agents."""

import asyncio
from dataclasses import dataclass, field
from io import BytesIO
from typing import TYPE_CHECKING

from pydantic_ai import (
    BinaryContent,
    ModelResponse,
    RunContext,
    ToolDefinition,
)
from pydantic_ai.capabilities.hooks import Hooks

from agent.context import AgentContext
from common.enums import Button
from streaming.server import update_background_from_states

if TYPE_CHECKING:
    from PIL import Image
    from pydantic_ai.messages import ToolCallPart
    from pydantic_ai.models import ModelRequestContext

    from emulator.emulator import Emulator
    from emulator.game_state import GameState
    from emulator.schemas import DialogBox


def build_screenshot_content(screenshot: Image.Image) -> BinaryContent:
    """Encode a screenshot for a multimodal model message."""
    image_buffer = BytesIO()
    screenshot.save(image_buffer, format="PNG")
    return BinaryContent(
        data=image_buffer.getvalue(),
        media_type="image/png",
        vendor_metadata={"detail": "original"},
    )


def is_battle_handler_state(game_state: GameState) -> bool:
    """Determine whether the game state belongs to the battle handler."""
    # The nickname screen after catching a Pokemon is considered a battle state by the game,
    # but we need to route it to the text handler instead.
    return game_state.battle.is_in_battle and not game_state.is_naming_screen()


async def record_model_response(
    ctx: RunContext[AgentContext],
    *,
    request_context: ModelRequestContext,  # noqa: ARG001
    response: ModelResponse,
) -> ModelResponse:
    """Account for a model response and retain its ordinary-text reasoning."""
    await ctx.deps.add_llm_usage(
        response.usage.total_tokens,
        float(response.cost().total_price),
    )
    if reasoning := response.text:
        ctx.deps.state.rolling_memory.add_memory(reasoning)
    return response


async def publish_before_tool(
    ctx: RunContext[AgentContext],
    *,
    call: ToolCallPart,  # noqa: ARG001
    tool_def: ToolDefinition,  # noqa: ARG001
    args: dict[str, object],
) -> dict[str, object]:
    """Publish shared state before an ordinary function tool executes."""
    game_state = await ctx.deps.emulator.get_game_state()
    update_background_from_states(ctx.deps.state, game_state)
    return args


AGENT_HOOKS = Hooks[AgentContext](
    after_model_request=record_model_response,
    before_tool_execute=publish_before_tool,
)


@dataclass(slots=True)
class DialogReader:
    """Capture complete dialog pages while advancing an emulator."""

    emulator: Emulator
    _pages: list[DialogBox] = field(default_factory=list, init=False)

    def observe(self, game_state: GameState) -> None:
        """Capture the most complete snapshot of the visible dialog page."""
        dialog_box = game_state.get_dialog_box()
        if not dialog_box or (not dialog_box.top_line and not dialog_box.bottom_line):
            return
        if not self._pages:
            self._pages.append(dialog_box)
            return

        previous_page = self._pages[-1]
        previous_lines = (previous_page.top_line, previous_page.bottom_line)
        current_lines = (dialog_box.top_line, dialog_box.bottom_line)
        if current_lines == previous_lines:
            if dialog_box.has_cursor and not previous_page.has_cursor:
                self._pages[-1] = dialog_box
            return

        top_line_continues = dialog_box.top_line == previous_page.top_line or (
            bool(previous_page.top_line) and dialog_box.top_line.startswith(previous_page.top_line)
        )
        top_line_scrolled = bool(previous_page.bottom_line) and dialog_box.top_line.startswith(
            previous_page.bottom_line,
        )
        if not previous_page.has_cursor and top_line_continues and not top_line_scrolled:
            self._pages[-1] = dialog_box
        else:
            self._pages.append(dialog_box)

    async def observe_current_state(self) -> GameState:
        """Capture and return the emulator's current state."""
        game_state = await self.emulator.get_game_state()
        self.observe(game_state)
        return game_state

    async def wait_for_animation(self) -> GameState:
        """Capture transient dialog while waiting for the current animation."""
        return await self.emulator.wait_for_animation_to_finish(
            on_game_state=self.observe,
        )

    async def advance(self) -> GameState:
        """Press A and capture dialog while the resulting animation runs."""
        await self.emulator.press_button(Button.A, wait_for_animation=False)
        return await self.wait_for_animation()

    async def is_cursor_blinking(self) -> bool:
        """Check for the blinking cursor while retaining every observed dialog page."""
        blink_wait_time = 0.1
        max_checks = 6  # Cursor blinks on/off a bit more than 2x per second.
        for _ in range(max_checks):
            await asyncio.sleep(blink_wait_time)
            game_state = await self.emulator.get_game_state()
            self.observe(game_state)
            dialog_box = game_state.get_dialog_box()
            if dialog_box and dialog_box.has_cursor:
                return True
        return False

    @property
    def text(self) -> str:
        """Combine captured pages without repeating lines that scrolled upward."""
        text: list[str] = []
        for dialog_box in self._pages:
            top_line = dialog_box.top_line
            bottom_line = dialog_box.bottom_line
            previous_lines = [
                text[-1] if text else None,
                text[-2] if len(text) > 1 else None,
            ]
            if not text or (top_line and top_line not in previous_lines):
                text.append(top_line)
            if not text or (bottom_line and bottom_line not in previous_lines):
                text.append(bottom_line)
        return " ".join(text).strip()
