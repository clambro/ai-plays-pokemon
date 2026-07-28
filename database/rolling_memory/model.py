"""SQLAlchemy models for rolling memory."""

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.base import SQLAlchemyBase


class RawMemoryBlockDBModel(SQLAlchemyBase):
    """A finalized raw-memory block for one application iteration."""

    __tablename__ = "raw_memory_block"

    iteration: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class MemorySummaryDBModel(SQLAlchemyBase):
    """A derived summary covering an inclusive range of application iterations.

    Level 0 is the implicit raw-memory layer, so stored summaries begin at
    level 1.
    """

    __tablename__ = "memory_summary"

    start_iteration: Mapped[int] = mapped_column(Integer, primary_key=True)
    end_iteration: Mapped[int] = mapped_column(Integer, primary_key=True)
    level: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
