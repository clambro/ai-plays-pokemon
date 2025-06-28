from agent.utils import append_dialog_to_list_inplace, is_blinking_cursor_on_screen
from common.enums import Button
from emulator.emulator import YellowLegacyEmulator
from memory.raw_memory import RawMemory, RawMemoryPiece


class HandleSubsequentTextService:
    """Handles reading the subsequent text (if present) after a tool has been used."""

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.emulator = emulator

    async def handle_subsequent_text(self) -> RawMemory:
        """Handle reading the dialog box."""
        text: list[str] = []
        await self.emulator.wait_for_animation_to_finish()
        while True:
            game_state = self.emulator.get_game_state()
            dialog_box = game_state.get_dialog_box()
            if not dialog_box:
                break
            append_dialog_to_list_inplace(text, dialog_box)

            if await is_blinking_cursor_on_screen(self.emulator):
                await self.emulator.press_button(Button.A)
                continue

            prev_state = game_state
            # Double check for animations because there's sometimes a slight pause between them.
            await self.emulator.wait_for_animation_to_finish()
            await self.emulator.wait_for_animation_to_finish()
            game_state = self.emulator.get_game_state()
            if game_state.screen.text == prev_state.screen.text:
                break  # Nothing is scrolling, and no animations are happening, so we're done.

        joined_text = " ".join(text).strip()
        if not joined_text:
            return self.raw_memory

        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                content=(
                    f'The following text was read from the battle dialog box: "{joined_text}"'
                ),
            ),
        )
        return self.raw_memory
