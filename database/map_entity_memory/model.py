from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from common.enums import MapEntityType
from database.base import SQLAlchemyBase


class MapEntityMemoryDBModel(SQLAlchemyBase):
    """A table for map entities that are known to the Agent."""

    __tablename__ = "map_entity_memory"

    map_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[MapEntityType] = mapped_column(
        Enum(MapEntityType),
        nullable=False,
        primary_key=True,
    )
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    create_iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    update_iteration: Mapped[int] = mapped_column(Integer, nullable=False)
