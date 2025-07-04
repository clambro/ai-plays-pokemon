import pytest
from google import genai

from common.enums import AsciiTile
from common.settings import settings
from llm.schemas import GEMINI_FLASH_2_5

_client = genai.Client(api_key=settings.gemini_api_key)


@pytest.mark.integration
def test_one_token_per_tile() -> None:
    """
    Test that each ASCII map tile is encoded as a single token and that it doesn't combine
    characters into a single token if you repeat the same tile multiple times.

    The particular model shouldn't matter much. I think they all use the same tokenizer.
    """
    num_repeats = 10
    expected_tokens = num_repeats + 3  # Two newlines and an end of prompt token.
    errors = []
    for tile in AsciiTile:
        contents = "\n" + tile.value * num_repeats + "\n"
        response = _client.models.count_tokens(model=GEMINI_FLASH_2_5.model_id, contents=contents)
        if response.total_tokens != expected_tokens:
            errors.append(
                f"Tile {tile.name} = {tile.value} is not one token. Expected {expected_tokens}"
                f" tokens, but got {response.total_tokens} tokens."
            )

    assert not errors, "\n".join(errors)
