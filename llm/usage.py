"""Task-local routing for LLM usage updates."""

from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_ai import ModelResponse

type LLMUsageUpdater = Callable[[int, float], Awaitable[None]]

_usage_updater: ContextVar[LLMUsageUpdater] = ContextVar("llm_usage_updater")


@contextmanager
def bind_llm_usage_updater(update_usage: LLMUsageUpdater) -> Iterator[None]:
    """Bind usage updates to the current agent run."""
    token = _usage_updater.set(update_usage)
    try:
        yield
    finally:
        _usage_updater.reset(token)


async def update_llm_usage(tokens: int, cost: float) -> None:
    """Add one LLM call's usage to the active agent state.

    Raises:
        RuntimeError: No agent run has bound a usage updater.
    """
    try:
        update_usage = _usage_updater.get()
    except LookupError as error:
        raise RuntimeError("LLM usage updater is not bound to an agent run") from error
    await update_usage(tokens, cost)


async def update_pydantic_ai_usage(response: ModelResponse) -> tuple[int, float]:
    """Add one Pydantic AI model response's usage to the active agent state."""
    tokens = response.usage.total_tokens
    cost = float(response.cost().total_price)
    await update_llm_usage(tokens, cost)
    return tokens, cost
