from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import SQLAlchemyBase


class MapMemoryDBModel(SQLAlchemyBase):
    """A table for maps in the agent's memory."""

    __tablename__ = "map_memory"

    map_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tiles: Mapped[str] = mapped_column(String, nullable=False)
    create_iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    update_iteration: Mapped[int] = mapped_column(Integer, nullable=False)
