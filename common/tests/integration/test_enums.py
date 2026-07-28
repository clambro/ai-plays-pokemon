"""Tests for shared enumerations."""

import pytest

from common.enums import AsciiTile
from llm.service import OpenAILLMService

llm_service = OpenAILLMService()


@pytest.mark.integration
async def test_one_token_per_tile() -> None:
    """Test that GPT-5.6 Luna encodes each ASCII map tile as one token."""
    num_repeats = 10
    expected_tokens = await llm_service.count_input_tokens("\n\n") + num_repeats
    errors = []
    for tile in AsciiTile:
        contents = "\n" + tile.value * num_repeats + "\n"
        total_tokens = await llm_service.count_input_tokens(contents)
        if total_tokens != expected_tokens:
            errors.append(
                f"Tile {tile.name} = {tile.value} is not one token. Expected {expected_tokens}"
                f" tokens, but got {total_tokens} tokens."
            )

    assert not errors, "\n".join(errors)
