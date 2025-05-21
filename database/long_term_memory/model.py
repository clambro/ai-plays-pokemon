from uuid import uuid4

from pydantic import UUID4
from sqlalchemy import UUID, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import SQLAlchemyBase
from database.types import Vector


class LongTermMemoryDBModel(SQLAlchemyBase):
    """A table for long-term memory."""

    __tablename__ = "long_term_memory"

    id: Mapped[UUID4] = mapped_column(UUID, primary_key=True, index=True, default=uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    content: Mapped[str] = mapped_column(String, nullable=False)
    importance: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector, nullable=False)
    create_iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    update_iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    last_accessed_iteration: Mapped[int] = mapped_column(Integer, nullable=False)
