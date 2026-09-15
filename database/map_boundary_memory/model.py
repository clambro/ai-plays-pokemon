"""SQLAlchemy model for observed coordinate-based map connections."""

from sqlalchemy import Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column

from common.enums import MapId, WarpActivation
from database.base import SQLAlchemyBase


class MapBoundaryMemoryDBModel(SQLAlchemyBase):
    """One known coordinate pair in an observed map connection."""

    __tablename__ = "map_boundary_memory"

    map_id: Mapped[MapId] = mapped_column(Integer, primary_key=True, index=True)
    activation: Mapped[WarpActivation] = mapped_column(
        Enum(WarpActivation),
        primary_key=True,
    )
    row: Mapped[int] = mapped_column(Integer, primary_key=True)
    col: Mapped[int] = mapped_column(Integer, primary_key=True)
    destination_map_id: Mapped[MapId] = mapped_column(Integer, nullable=False)
    destination_row: Mapped[int] = mapped_column(Integer, nullable=False)
    destination_col: Mapped[int] = mapped_column(Integer, nullable=False)
