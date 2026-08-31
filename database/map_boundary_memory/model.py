"""SQLAlchemy model for observed map-boundary memory."""

from sqlalchemy import Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column

from common.enums import FacingDirection, MapId
from database.base import SQLAlchemyBase


class MapBoundaryMemoryDBModel(SQLAlchemyBase):
    """One known coordinate pair in an observed cardinal map connection."""

    __tablename__ = "map_boundary_memory"

    map_id: Mapped[MapId] = mapped_column(Integer, primary_key=True, index=True)
    direction: Mapped[FacingDirection] = mapped_column(
        Enum(FacingDirection),
        primary_key=True,
    )
    row: Mapped[int] = mapped_column(Integer, primary_key=True)
    col: Mapped[int] = mapped_column(Integer, primary_key=True)
    destination_map_id: Mapped[MapId] = mapped_column(Integer, nullable=False)
    destination_row: Mapped[int] = mapped_column(Integer, nullable=False)
    destination_col: Mapped[int] = mapped_column(Integer, nullable=False)
