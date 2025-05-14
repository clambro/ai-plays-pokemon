from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import SQLAlchemyBase
from emulator.enums import MapLocation


class SpriteMemoryDBModel(SQLAlchemyBase):
    """A table for sprite tiles that are known to the Agent."""

    __tablename__ = "sprite_memory"

    map_id: Mapped[MapLocation] = mapped_column(Integer, primary_key=True, index=True)
    sprite_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
