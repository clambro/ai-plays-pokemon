import struct

from sqlalchemy import LargeBinary, TypeDecorator
from sqlalchemy.dialects.sqlite import dialect


class Vector(TypeDecorator):
    """SQLAlchemy type for storing a list of floats as a BLOB, and loading it back as a list."""

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value: list[float], dialect: dialect) -> bytes:
        """Convert a list of floats to bytes."""
        return struct.pack(f"{len(value)}f", *value)

    def process_result_value(self, value: bytes, dialect: dialect) -> list[float]:
        """Convert bytes back to list of floats."""
        return list(struct.unpack(f"{len(value)//4}f", value))
