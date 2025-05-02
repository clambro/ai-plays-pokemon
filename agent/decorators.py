from burr.core.action import action
from functools import wraps
from typing import Callable, TypeVar, Any
from collections.abc import Awaitable

T = TypeVar("T")


def named_action(reads: list[str], writes: list[str]) -> Callable:
    """Wrapper around the Burr action decorator avoid losing the name when wrapping."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        @action.pydantic(reads=reads, writes=writes)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await func(*args, **kwargs)

        wrapper.__str__ = lambda: func.__name__
        return wrapper

    return decorator
