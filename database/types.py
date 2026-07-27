"""Custom SQLAlchemy column types."""

import struct
from typing import TYPE_CHECKING

from sqlalchemy import LargeBinary, TypeDecorator

if TYPE_CHECKING:
    from sqlalchemy.engine import Dialect


class Vector(TypeDecorator[list[float]]):
    """SQLAlchemy type for storing a list of floats as a BLOB, and loading it back as a list."""

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(
        self,
        value: list[float] | None,
        dialect: Dialect,  # noqa: ARG002
    ) -> bytes | None:
        """Convert a list of floats to bytes."""
        if value is None:
            return None
        return struct.pack(f"{len(value)}f", *value)

    def process_result_value(
        self,
        value: object,
        dialect: Dialect,  # noqa: ARG002
    ) -> list[float] | None:
        """Convert database bytes back to a vector.

        Args:
            value: Raw value returned by the database.
            dialect: SQLAlchemy dialect performing the conversion.

        Returns:
            The decoded vector, or ``None`` for a database null.

        Raises:
            TypeError: The database returns a non-byte value.
        """
        if value is None:
            return None
        if not isinstance(value, bytes):
            msg = f"Expected bytes from the database, got {type(value).__name__}"
            raise TypeError(msg)
        return list(struct.unpack(f"{len(value) // 4}f", value))
