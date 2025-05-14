from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import SQLAlchemyBase
from emulator.enums import MapLocation


class MapMemoryDBModel(SQLAlchemyBase):
    """A table for maps in the agent's memory."""

    __tablename__ = "map_memory"

    map_id: Mapped[MapLocation] = mapped_column(Integer, primary_key=True, index=True)
    tiles: Mapped[str] = mapped_column(String, nullable=False)
